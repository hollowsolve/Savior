import os
import shutil
import subprocess
import hashlib
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Optional, Tuple
from enum import Enum


class ConflictType(Enum):
    UNCOMMITTED_CHANGES = "uncommitted_changes"
    MODIFIED_SINCE_BACKUP = "modified_since_backup"
    NEW_FILES = "new_files"
    DELETED_FILES = "deleted_files"
    PERMISSION_CHANGES = "permission_changes"


class ConflictResolution(Enum):
    OVERWRITE = "overwrite"  # Replace with backup version
    KEEP_CURRENT = "keep_current"  # Keep current version
    MERGE = "merge"  # Try to merge changes
    BACKUP_CURRENT = "backup_current"  # Save current then restore
    SKIP = "skip"  # Skip this file


class ConflictDetector:
    """Detects conflicts before restoration"""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.git_available = self._check_git_available()

    def _check_git_available(self) -> bool:
        """Check if project is a git repo"""
        return (self.project_dir / '.git').exists()

    def _get_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file"""
        if not file_path.exists():
            return ""

        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hasher.update(chunk)
        return hasher.hexdigest()

    def detect_git_conflicts(self) -> Dict[str, List[Path]]:
        """Detect uncommitted changes using git"""
        conflicts = {
            'staged': [],
            'modified': [],
            'untracked': []
        }

        if not self.git_available:
            return conflicts

        try:
            # Get staged files
            result = subprocess.run(
                ['git', 'diff', '--cached', '--name-only'],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0 and result.stdout:
                conflicts['staged'] = [
                    self.project_dir / f.strip()
                    for f in result.stdout.splitlines()
                ]

            # Get modified files
            result = subprocess.run(
                ['git', 'diff', '--name-only'],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0 and result.stdout:
                conflicts['modified'] = [
                    self.project_dir / f.strip()
                    for f in result.stdout.splitlines()
                ]

            # Get untracked files
            result = subprocess.run(
                ['git', 'ls-files', '--others', '--exclude-standard'],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0 and result.stdout:
                conflicts['untracked'] = [
                    self.project_dir / f.strip()
                    for f in result.stdout.splitlines()
                    if not f.strip().startswith('.savior/')
                ]

        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        return conflicts

    def detect_file_conflicts(self, backup_files: Dict[Path, Dict]) -> Dict[ConflictType, List[Dict]]:
        """
        Detect conflicts between current state and backup
        backup_files: Dict mapping file paths to their metadata (hash, mtime, etc)
        """
        conflicts = {
            ConflictType.MODIFIED_SINCE_BACKUP: [],
            ConflictType.NEW_FILES: [],
            ConflictType.DELETED_FILES: [],
            ConflictType.PERMISSION_CHANGES: []
        }

        current_files = {}

        # Scan current directory state
        for root, dirs, files in os.walk(self.project_dir):
            # Skip .savior directory
            if '.savior' in Path(root).parts:
                continue

            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(self.project_dir)

                try:
                    stat = file_path.stat()
                    current_files[rel_path] = {
                        'hash': self._get_file_hash(file_path),
                        'mtime': stat.st_mtime,
                        'size': stat.st_size,
                        'mode': stat.st_mode
                    }
                except (OSError, IOError):
                    continue

        # Compare with backup
        for backup_path, backup_meta in backup_files.items():
            if backup_path in current_files:
                current = current_files[backup_path]
                # Check if modified
                if current['hash'] != backup_meta.get('hash', ''):
                    conflicts[ConflictType.MODIFIED_SINCE_BACKUP].append({
                        'path': backup_path,
                        'current_hash': current['hash'],
                        'backup_hash': backup_meta.get('hash'),
                        'current_mtime': datetime.fromtimestamp(current['mtime']),
                        'current_size': current['size']
                    })
                # Check permissions
                if current['mode'] != backup_meta.get('mode', current['mode']):
                    conflicts[ConflictType.PERMISSION_CHANGES].append({
                        'path': backup_path,
                        'current_mode': oct(current['mode']),
                        'backup_mode': oct(backup_meta.get('mode'))
                    })
            else:
                # File exists in backup but not currently
                conflicts[ConflictType.DELETED_FILES].append({
                    'path': backup_path,
                    'backup_size': backup_meta.get('size', 0)
                })

        # Check for new files (exist now but not in backup)
        for current_path in current_files:
            if current_path not in backup_files:
                conflicts[ConflictType.NEW_FILES].append({
                    'path': current_path,
                    'size': current_files[current_path]['size'],
                    'mtime': datetime.fromtimestamp(current_files[current_path]['mtime'])
                })

        return conflicts


class ConflictResolver:
    """Handles conflict resolution during restoration"""

    def __init__(self, project_dir: Path, backup_dir: Path):
        self.project_dir = project_dir
        self.backup_dir = backup_dir
        self.detector = ConflictDetector(project_dir)
        self.pre_restore_backup = None

    def create_pre_restore_backup(self) -> Optional[Path]:
        """Create a safety backup before restoration"""
        # Create human-readable backup name
        time_str = datetime.now().strftime("%Y-%m-%d_%I-%M%p").lower()
        backup_name = f"pre-restore-safety_{time_str}.tar.gz"
        backup_path = self.backup_dir / backup_name

        try:
            import tarfile
            with tarfile.open(backup_path, 'w:gz') as tar:
                for root, dirs, files in os.walk(self.project_dir):
                    # Skip .savior directory
                    if '.savior' in Path(root).parts:
                        continue

                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(self.project_dir)
                        tar.add(file_path, arcname=arcname)

            self.pre_restore_backup = backup_path
            return backup_path
        except Exception:
            return None

    def apply_resolution_strategy(
        self,
        conflicts: Dict[ConflictType, List[Dict]],
        strategy: Dict[ConflictType, ConflictResolution]
    ) -> Dict[str, List[Path]]:
        """
        Apply resolution strategy to conflicts
        Returns dict of actions taken
        """
        actions = {
            'backed_up': [],
            'skipped': [],
            'overwritten': [],
            'kept': []
        }

        for conflict_type, items in conflicts.items():
            resolution = strategy.get(conflict_type, ConflictResolution.SKIP)

            for item in items:
                file_path = self.project_dir / item['path']

                if resolution == ConflictResolution.SKIP:
                    actions['skipped'].append(file_path)

                elif resolution == ConflictResolution.KEEP_CURRENT:
                    actions['kept'].append(file_path)

                elif resolution == ConflictResolution.OVERWRITE:
                    actions['overwritten'].append(file_path)

                elif resolution == ConflictResolution.BACKUP_CURRENT:
                    # Backup current file before overwriting
                    if file_path.exists():
                        backup_path = self.backup_dir / 'conflict_backups' / item['path']
                        backup_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(file_path, backup_path)
                        actions['backed_up'].append(file_path)
                        actions['overwritten'].append(file_path)

        return actions

    def generate_conflict_report(
        self,
        conflicts: Dict[ConflictType, List[Dict]],
        git_conflicts: Dict[str, List[Path]]
    ) -> str:
        """Generate human-readable conflict report"""
        lines = []

        # Git conflicts
        if any(git_conflicts.values()):
            lines.append("Git Status Conflicts:")
            lines.append("=" * 40)

            if git_conflicts['staged']:
                lines.append(f"\nStaged files ({len(git_conflicts['staged'])}):")
                for path in git_conflicts['staged'][:5]:
                    lines.append(f"  • {path.relative_to(self.project_dir)}")
                if len(git_conflicts['staged']) > 5:
                    lines.append(f"  ... and {len(git_conflicts['staged']) - 5} more")

            if git_conflicts['modified']:
                lines.append(f"\nModified files ({len(git_conflicts['modified'])}):")
                for path in git_conflicts['modified'][:5]:
                    lines.append(f"  • {path.relative_to(self.project_dir)}")
                if len(git_conflicts['modified']) > 5:
                    lines.append(f"  ... and {len(git_conflicts['modified']) - 5} more")

            if git_conflicts['untracked']:
                lines.append(f"\nUntracked files ({len(git_conflicts['untracked'])}):")
                for path in git_conflicts['untracked'][:5]:
                    lines.append(f"  • {path.relative_to(self.project_dir)}")
                if len(git_conflicts['untracked']) > 5:
                    lines.append(f"  ... and {len(git_conflicts['untracked']) - 5} more")

        # File conflicts
        if any(conflicts.values()):
            if lines:
                lines.append("\n")
            lines.append("File Conflicts:")
            lines.append("=" * 40)

            for conflict_type, items in conflicts.items():
                if items:
                    lines.append(f"\n{conflict_type.value.replace('_', ' ').title()} ({len(items)}):")
                    for item in items[:3]:
                        lines.append(f"  • {item['path']}")
                    if len(items) > 3:
                        lines.append(f"  ... and {len(items) - 3} more")

        if not lines:
            lines.append("No conflicts detected")

        return "\n".join(lines)

    def suggest_resolution_strategy(
        self,
        conflicts: Dict[ConflictType, List[Dict]]
    ) -> Dict[ConflictType, ConflictResolution]:
        """Suggest safe default resolution strategies"""
        strategy = {}

        for conflict_type in ConflictType:
            if conflict_type == ConflictType.UNCOMMITTED_CHANGES:
                # Always backup uncommitted changes
                strategy[conflict_type] = ConflictResolution.BACKUP_CURRENT
            elif conflict_type == ConflictType.MODIFIED_SINCE_BACKUP:
                # Backup modified files by default
                strategy[conflict_type] = ConflictResolution.BACKUP_CURRENT
            elif conflict_type == ConflictType.NEW_FILES:
                # Keep new files by default
                strategy[conflict_type] = ConflictResolution.KEEP_CURRENT
            elif conflict_type == ConflictType.DELETED_FILES:
                # Restore deleted files by default
                strategy[conflict_type] = ConflictResolution.OVERWRITE
            elif conflict_type == ConflictType.PERMISSION_CHANGES:
                # Skip permission changes by default
                strategy[conflict_type] = ConflictResolution.SKIP

        return strategy