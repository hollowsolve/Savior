import os
import time
import json
import shutil
import tarfile
import hashlib
import threading
import tempfile
import psutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Set, Tuple
import fnmatch
from tqdm import tqdm
try:
    from .cloud import CloudStorage
    from .conflicts import ConflictDetector, ConflictResolver, ConflictType, ConflictResolution
    from .safety import (
        FileLock, SymlinkValidator, ResourceMonitor,
        SafeFileOperations, BackupIntegrityChecker
    )
except ImportError:
    from cloud import CloudStorage
    from conflicts import ConflictDetector, ConflictResolver, ConflictType, ConflictResolution
    from safety import (
        FileLock, SymlinkValidator, ResourceMonitor,
        SafeFileOperations, BackupIntegrityChecker
    )
try:
    from .dedup import DeduplicationStore, DedupBackupManifest, SmartDeduplicator
except ImportError:
    from dedup import DeduplicationStore, DedupBackupManifest, SmartDeduplicator

class SaviorIgnore:
    def __init__(self, ignore_file: Path, exclude_git: bool = False, extra_patterns: List[str] = None):
        self.patterns = self._load_ignore_patterns(ignore_file, exclude_git, extra_patterns)

    def _load_ignore_patterns(self, ignore_file: Path, exclude_git: bool, extra_patterns: List[str]) -> List[str]:
        # Always ignore .savior to prevent recursion
        patterns = ['.savior/', '__pycache__/', '*.pyc', '.DS_Store']

        # Only ignore .git if explicitly requested
        if exclude_git:
            patterns.append('.git/')

        # Add extra patterns from command line
        if extra_patterns:
            patterns.extend(extra_patterns)

        if ignore_file.exists():
            try:
                with open(ignore_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            patterns.append(line)
            except (IOError, UnicodeDecodeError):
                pass  # Ignore if file can't be read

        return patterns

    def should_ignore(self, path: str) -> bool:
        for pattern in self.patterns:
            if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(os.path.basename(path), pattern):
                return True
            if pattern.endswith('/') and (pattern[:-1] in path.split(os.sep)):
                return True
        return False


class Backup:
    def __init__(self, timestamp: datetime, path: Path, description: str = "", size: int = 0):
        self.timestamp = timestamp
        self.path = path
        self.description = description
        self.size = size

    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp.isoformat(),
            'path': str(self.path),
            'description': self.description,
            'size': self.size
        }

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(
            timestamp=datetime.fromisoformat(data['timestamp']),
            path=Path(data['path']),
            description=data.get('description', ''),
            size=data.get('size', 0)
        )


class Savior:
    def __init__(self, project_dir: Path, exclude_git: bool = False, extra_ignores: List[str] = None, enable_cloud: bool = False):
        self.project_dir = Path(project_dir).resolve()
        self.backup_dir = self.project_dir / '.savior'
        self.metadata_file = self.backup_dir / 'metadata.json'
        self.lock_file = self.backup_dir / '.lock'
        self.ignore_file = self.project_dir / '.saviorignore'
        self.exclude_git = exclude_git
        self.extra_ignores = extra_ignores or []
        self.ignore = SaviorIgnore(self.ignore_file, exclude_git, self.extra_ignores)
        self.watch_interval = 20 * 60  # 20 minutes in seconds
        self.watching = False
        self._watch_thread = None
        self._last_activity = time.time()
        self._metadata_lock = threading.Lock()
        self.enable_cloud = enable_cloud
        self.cloud_storage = CloudStorage() if enable_cloud else None

    def _ensure_backup_dir(self):
        self.backup_dir.mkdir(exist_ok=True)

    def _load_metadata(self) -> Dict:
        with self._metadata_lock:
            if self.metadata_file.exists():
                try:
                    with open(self.metadata_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except (json.JSONDecodeError, IOError):
                    # If metadata is corrupted, start fresh
                    return {'backups': [], 'watching': False}
            return {'backups': [], 'watching': False}

    def _save_metadata(self, metadata: Dict):
        with self._metadata_lock:
            self._ensure_backup_dir()
            # Use atomic write with a temporary file
            temp_fd, temp_path = tempfile.mkstemp(dir=self.backup_dir, prefix='.metadata_', suffix='.tmp')
            try:
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)
                # Atomic replace on POSIX systems
                os.replace(temp_path, self.metadata_file)
            except Exception:
                # Clean up temp file on error
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise

    def _get_file_hash(self, filepath: Path) -> str:
        hasher = hashlib.md5()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _collect_files(self) -> Set[Path]:
        files = set()
        # Use followlinks=False to avoid symlink loops
        for root, dirs, filenames in os.walk(self.project_dir, followlinks=False):
            root_path = Path(root)
            try:
                rel_root = root_path.relative_to(self.project_dir)
            except ValueError:
                continue  # Skip if path is outside project dir

            # Filter directories to skip
            dirs[:] = [d for d in dirs if not self.ignore.should_ignore(str(rel_root / d))]

            for filename in filenames:
                rel_path = rel_root / filename
                if not self.ignore.should_ignore(str(rel_path)):
                    file_path = root_path / filename
                    try:
                        # Check if file is readable and not too large
                        stat = file_path.stat()
                        if stat.st_size < 100 * 1024 * 1024 and os.access(file_path, os.R_OK):
                            files.add(file_path)
                    except (OSError, IOError):
                        # Skip files we can't access
                        continue

        return files

    def _check_disk_space(self, required_bytes: int) -> Tuple[bool, str]:
        """Check if there's enough disk space for the backup."""
        try:
            stat = psutil.disk_usage(self.backup_dir)
            # Require at least 10% free space or required_bytes + 100MB
            min_free = max(stat.total * 0.1, required_bytes + 100 * 1024 * 1024)

            if stat.free < min_free:
                free_gb = stat.free / (1024**3)
                required_gb = min_free / (1024**3)
                return False, f"Insufficient disk space. Available: {free_gb:.2f}GB, Required: {required_gb:.2f}GB"
            return True, ""
        except Exception as e:
            return True, ""  # Proceed if we can't check

    def _estimate_backup_size(self, files: Set[Path]) -> int:
        """Estimate the size of the backup."""
        total_size = 0
        for file_path in files:
            try:
                total_size += file_path.stat().st_size
            except (OSError, IOError):
                continue
        # Estimate compressed size as ~40% of original
        return int(total_size * 0.4)

    def create_backup(self, description: str = "", compression_level: int = 6, show_progress: bool = True) -> Backup:
        self._ensure_backup_dir()

        # Auto-cleanup old backups (30+ days)
        self._cleanup_old_backups()

        # Collect files first
        files = self._collect_files()
        if not files:
            raise ValueError("No files to backup")

        # Check disk space
        estimated_size = self._estimate_backup_size(files)
        has_space, error_msg = self._check_disk_space(estimated_size)
        if not has_space:
            raise IOError(error_msg)

        timestamp = datetime.now()
        extension = ".tar.gz" if compression_level > 0 else ".tar"

        # Create folder with format: [HH:MM] [MM-DD-YYYY]
        # Example: [14:30] [09-21-2025]
        # Using dashes instead of slashes to avoid filesystem issues
        folder_name = timestamp.strftime("[%H:%M] [%m-%d-%Y]")

        # Create the backup folder
        backup_folder = self.backup_dir / folder_name
        backup_folder.mkdir(parents=True, exist_ok=True)

        # Create backup filename with description
        if description:
            # Clean up the description for filename
            import re
            clean_desc = re.sub(r'[^\w\s-]', '', description.lower())
            clean_desc = re.sub(r'[-\s]+', '-', clean_desc)
            clean_desc = clean_desc[:50].strip('-')
            backup_filename = f"{clean_desc}{extension}"
        else:
            backup_filename = f"backup{extension}"

        backup_path = backup_folder / backup_filename

        # Set compression level (0=none, 9=max)
        if compression_level == 0:
            compress_mode = 'w'
            tar_kwargs = {}
        else:
            compress_mode = 'w:gz'
            tar_kwargs = {'compresslevel': min(max(compression_level, 1), 9)}

        # Create backup with progress bar
        if show_progress:
            file_list = list(files)
            with tqdm(total=len(file_list), desc="Creating backup", unit="files", disable=not show_progress) as pbar:
                with tarfile.open(backup_path, compress_mode, **tar_kwargs) as tar:
                    for file_path in file_list:
                        try:
                            rel_path = file_path.relative_to(self.project_dir)
                            tar.add(file_path, arcname=str(rel_path))
                            pbar.update(1)
                        except (OSError, IOError):
                            # Skip files that can't be added (permissions, etc)
                            pbar.update(1)
                            continue
        else:
            with tarfile.open(backup_path, compress_mode, **tar_kwargs) as tar:
                for file_path in files:
                    try:
                        rel_path = file_path.relative_to(self.project_dir)
                        tar.add(file_path, arcname=str(rel_path))
                    except (OSError, IOError):
                        continue

        backup = Backup(
            timestamp=timestamp,
            path=backup_path,
            description=description or "Automatic backup",
            size=backup_path.stat().st_size
        )

        metadata = self._load_metadata()
        metadata['backups'].append(backup.to_dict())
        self._save_metadata(metadata)

        # Upload to cloud if enabled and configured
        if self.cloud_storage and self.cloud_storage.is_configured():
            if self.cloud_storage.config.get('auto_sync', False):
                project_name = self.project_dir.name
                try:
                    if self.cloud_storage.upload_backup(backup_path, project_name):
                        print(f"  ☁️ Uploaded to cloud storage")
                except Exception as e:
                    print(f"  ⚠️ Cloud upload failed: {e}")

        self._cleanup_old_backups()

        return backup

    def sync_with_cloud(self) -> Dict:
        """Sync local backups with cloud storage"""
        if not self.cloud_storage or not self.cloud_storage.is_configured():
            return {'error': 'Cloud storage not configured'}

        project_name = self.project_dir.name
        return self.cloud_storage.sync_backups(self.backup_dir, project_name)

    def _cleanup_old_backups(self):
        """Smart cleanup: Keep recent backups, transition to daily/weekly, remove 30+ day old backups"""
        metadata = self._load_metadata()
        backups = [Backup.from_dict(b) for b in metadata['backups']]

        now = datetime.now()
        kept_backups = []
        removed_count = 0

        # Always keep the 10 most recent backups
        recent_backups = sorted(backups, key=lambda b: b.timestamp, reverse=True)[:10]
        kept_backups.extend(recent_backups)
        recent_paths = {b.path for b in recent_backups}

        for backup in sorted(backups, key=lambda b: b.timestamp, reverse=True):
            if backup.path in recent_paths:
                continue  # Already kept as recent

            age = now - backup.timestamp

            # Remove backups older than 30 days
            if age > timedelta(days=30):
                if backup.path.exists():
                    backup.path.unlink()
                    removed_count += 1
            elif age < timedelta(hours=24):
                # Keep all backups from last 24 hours
                kept_backups.append(backup)
            elif age < timedelta(days=7) and backup.timestamp.hour % 6 == 0:
                # Keep one backup every 6 hours for the past week
                kept_backups.append(backup)
            elif age < timedelta(days=30) and backup.timestamp.day % 7 == 0:
                # Keep one backup per week for the past month
                kept_backups.append(backup)
            else:
                # Remove intermediate backups
                if backup.path.exists():
                    backup.path.unlink()
                    removed_count += 1
                    # If this was in a folder and the folder is now empty, remove it
                    parent = backup.path.parent
                    if parent != self.backup_dir and parent.exists():
                        try:
                            if not any(parent.iterdir()):
                                parent.rmdir()
                        except OSError:
                            pass

        # Remove duplicates while preserving order
        seen = set()
        unique_backups = []
        for b in kept_backups:
            if b.path not in seen:
                seen.add(b.path)
                unique_backups.append(b)

        metadata['backups'] = [b.to_dict() for b in unique_backups]
        self._save_metadata(metadata)

        if removed_count > 0:
            print(f"  (Cleaned up {removed_count} old backup{'s' if removed_count != 1 else ''})")

    def restore_backup(self, backup_index: int, check_conflicts: bool = True,
                       auto_backup: bool = True, force: bool = False) -> bool:
        """Restore a backup with conflict detection and resolution.

        Args:
            backup_index: Index of backup to restore
            check_conflicts: Whether to check for conflicts before restoring
            auto_backup: Whether to create a pre-restore backup
            force: Force restore without conflict checking
        """
        metadata = self._load_metadata()
        backups = [Backup.from_dict(b) for b in metadata['backups']]

        if not backups or backup_index < 0 or backup_index >= len(backups):
            return False

        backup = sorted(backups, key=lambda b: b.timestamp, reverse=True)[backup_index]

        if not backup.path.exists():
            return False

        # Use tempfile for cross-platform compatibility
        temp_dir = Path(tempfile.mkdtemp(prefix='savior_restore_'))
        temp_dir.mkdir(exist_ok=True)

        try:
            # Extract backup to temp directory first
            with tarfile.open(backup.path, 'r:gz') as tar:
                tar.extractall(temp_dir, filter='data')

            # Build backup file metadata
            backup_files = {}
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    src_file = Path(root) / file
                    rel_path = src_file.relative_to(temp_dir)

                    # Calculate hash for conflict detection
                    import hashlib
                    hasher = hashlib.sha256()
                    with open(src_file, 'rb') as f:
                        for chunk in iter(lambda: f.read(4096), b''):
                            hasher.update(chunk)

                    stat = src_file.stat()
                    backup_files[rel_path] = {
                        'hash': hasher.hexdigest(),
                        'size': stat.st_size,
                        'mode': stat.st_mode
                    }

            # Conflict detection and resolution
            if check_conflicts and not force:
                detector = ConflictDetector(self.project_dir)
                resolver = ConflictResolver(self.project_dir, self.backup_dir)

                # Detect conflicts
                file_conflicts = detector.detect_file_conflicts(backup_files)
                git_conflicts = detector.detect_git_conflicts()

                # Check if there are any conflicts
                has_conflicts = any(file_conflicts.values()) or any(git_conflicts.values())

                if has_conflicts:
                    # Generate and return conflict report (caller should handle)
                    report = resolver.generate_conflict_report(file_conflicts, git_conflicts)
                    print(f"\n{report}")

                    # Create pre-restore backup if requested
                    if auto_backup:
                        pre_backup = resolver.create_pre_restore_backup()
                        if pre_backup:
                            print(f"\n✓ Created safety backup at: {pre_backup.name}")

                    # Apply suggested resolution strategy
                    strategy = resolver.suggest_resolution_strategy(file_conflicts)
                    actions = resolver.apply_resolution_strategy(file_conflicts, strategy)

                    if actions['backed_up']:
                        print(f"  Backed up {len(actions['backed_up'])} conflicting files")
                    if actions['skipped']:
                        print(f"  Skipping {len(actions['skipped'])} files")

            # Perform the actual restoration
            # Remove files that don't exist in the backup (except .savior directory)
            for root, dirs, files in os.walk(self.project_dir, followlinks=False):
                # Skip the .savior directory itself
                if '.savior' in Path(root).parts:
                    continue
                for file in files:
                    file_path = Path(root) / file
                    try:
                        rel_path = file_path.relative_to(self.project_dir)
                        if rel_path not in backup_files and not str(rel_path).startswith('.savior'):
                            file_path.unlink()
                    except (OSError, ValueError):
                        continue  # Skip files we can't remove

            # Restore files from backup
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    src_file = Path(root) / file
                    rel_path = src_file.relative_to(temp_dir)
                    dst_file = self.project_dir / rel_path

                    dst_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dst_file)

            shutil.rmtree(temp_dir)
            return True
        except Exception as e:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            print(f"Restore failed: {e}")
            return False

    def get_project_tree(self, max_depth: int = 3, show_size: bool = True) -> str:
        """Generate a tree visualization of the project files."""
        tree_lines = []

        def format_size(size: int) -> str:
            """Format file size in human-readable format."""
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f}{unit}"
                size /= 1024.0
            return f"{size:.1f}TB"

        def build_tree(path: Path, prefix: str = "", depth: int = 0) -> int:
            """Recursively build tree structure."""
            if depth > max_depth:
                return 0

            total_size = 0
            try:
                items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
                for i, item in enumerate(items):
                    # Skip ignored items
                    rel_path = item.relative_to(self.project_dir)
                    if self.ignore.should_ignore(str(rel_path)):
                        continue

                    is_last = i == len(items) - 1
                    current_prefix = "└── " if is_last else "├── "
                    next_prefix = prefix + ("    " if is_last else "│   ")

                    if item.is_dir() and not item.is_symlink():
                        dir_size = build_tree(item, next_prefix, depth + 1)
                        size_str = f" ({format_size(dir_size)})" if show_size and dir_size > 0 else ""
                        tree_lines.append(f"{prefix}{current_prefix}{item.name}/{size_str}")
                        total_size += dir_size
                    elif item.is_file():
                        try:
                            file_size = item.stat().st_size
                            size_str = f" ({format_size(file_size)})" if show_size else ""
                            tree_lines.append(f"{prefix}{current_prefix}{item.name}{size_str}")
                            total_size += file_size
                        except (OSError, IOError):
                            tree_lines.append(f"{prefix}{current_prefix}{item.name} (?)")
            except (OSError, IOError):
                pass

            return total_size

        # Start building from project root
        total = build_tree(self.project_dir)

        # Add header
        header = f"{self.project_dir.name}/"
        if show_size:
            header += f" ({format_size(total)})"

        return header + "\n" + "\n".join(tree_lines)

    def list_backups(self) -> List[Backup]:
        metadata = self._load_metadata()
        backups = [Backup.from_dict(b) for b in metadata['backups']]

        # Also check for backup files in directory if metadata is empty
        if not backups and self.backup_dir.exists():
            # Look for backups in both old format and new folder structure
            # Check for old format files in root
            for backup_file in self.backup_dir.glob('*.tar.gz'):
                # Parse timestamp from filename (YYYYMMDD_HHMMSS format)
                try:
                    name = backup_file.stem.replace('_incremental', '')
                    timestamp_str = name.split('.')[0]
                    timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')

                    backup = Backup(
                        timestamp=timestamp,
                        path=backup_file,
                        description="Incremental backup" if 'incremental' in backup_file.name else "Backup",
                        size=backup_file.stat().st_size
                    )
                    backups.append(backup)
                except (ValueError, IndexError):
                    continue  # Skip files that don't match expected format

            # Check for new folder structure: [HH:MM] [MM-DD-YYYY]
            for folder in self.backup_dir.iterdir():
                if folder.is_dir() and folder.name.startswith('['):
                    try:
                        # Parse folder name: [HH:MM] [MM-DD-YYYY]
                        # Extract time and date from folder name
                        import re
                        match = re.match(r'\[(\d{2}):(\d{2})\] \[(\d{2})-(\d{2})-(\d{4})\]', folder.name)
                        if match:
                            hour, minute, month, day, year = match.groups()
                            timestamp = datetime(int(year), int(month), int(day), int(hour), int(minute))

                            # Look for backup files in the folder
                            for backup_file in folder.glob('*.tar*'):
                                # Get description from filename
                                desc = backup_file.stem
                                if desc == 'backup':
                                    desc = "Manual backup"
                                else:
                                    desc = desc.replace('-', ' ').title()

                                backup = Backup(
                                    timestamp=timestamp,
                                    path=backup_file,
                                    description=desc,
                                    size=backup_file.stat().st_size
                                )
                                backups.append(backup)
                    except (ValueError, AttributeError):
                        continue

        return sorted(backups, key=lambda b: b.timestamp, reverse=True)

    def _watch_loop(self):
        while self.watching:
            time.sleep(2)

            if time.time() - self._last_activity > 2:
                if time.time() % self.watch_interval < 2:
                    self.create_backup("Automatic backup")
                    self._last_activity = time.time()

    def start_watching(self):
        if not self.watching:
            self.watching = True
            metadata = self._load_metadata()
            metadata['watching'] = True
            self._save_metadata(metadata)

            self._watch_thread = threading.Thread(target=self._watch_loop, daemon=True)
            self._watch_thread.start()

            self.create_backup("Initial backup")

    def stop_watching(self):
        self.watching = False
        metadata = self._load_metadata()
        metadata['watching'] = False
        self._save_metadata(metadata)

        if self._watch_thread:
            self._watch_thread.join(timeout=5)

    def is_watching(self) -> bool:
        metadata = self._load_metadata()
        return metadata.get('watching', False)

    def purge_backups(self, keep_recent: int = 5):
        metadata = self._load_metadata()
        backups = [Backup.from_dict(b) for b in metadata['backups']]

        sorted_backups = sorted(backups, key=lambda b: b.timestamp, reverse=True)

        for backup in sorted_backups[keep_recent:]:
            if backup.path.exists():
                backup.path.unlink()

        metadata['backups'] = [b.to_dict() for b in sorted_backups[:keep_recent]]
        self._save_metadata(metadata)