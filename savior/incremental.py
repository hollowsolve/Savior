import json
import hashlib
import tarfile
import shutil
from pathlib import Path
from typing import Dict, Set, Tuple, Optional
from datetime import datetime


class IncrementalBackup:
    def __init__(self, backup_dir: Path):
        self.backup_dir = backup_dir
        self.state_file = backup_dir / 'file_states.json'
        self.file_states = self._load_states()

    def _load_states(self) -> Dict:
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_states(self):
        # Ensure backup directory exists before saving
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.file_states, f, indent=2)

    def _get_file_hash(self, filepath: Path) -> str:
        hasher = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _get_file_info(self, filepath: Path) -> Dict:
        stat = filepath.stat()
        return {
            'hash': self._get_file_hash(filepath),
            'mtime': stat.st_mtime,
            'size': stat.st_size
        }

    def find_changed_files(self, files: Set[Path]) -> Tuple[Set[Path], Set[Path], Set[Path]]:
        """Returns (added, modified, deleted) files since last backup"""
        added = set()
        modified = set()
        current_files = {}

        for file_path in files:
            try:
                # FIX: Correctly calculate relative path from project directory
                rel_path = str(file_path.relative_to(self.project_dir))
                info = self._get_file_info(file_path)
                current_files[rel_path] = info

                if rel_path not in self.file_states:
                    added.add(file_path)
                elif self.file_states[rel_path]['hash'] != info['hash']:
                    modified.add(file_path)
            except Exception:
                pass

        # Find deleted files
        deleted_paths = set(self.file_states.keys()) - set(current_files.keys())

        # Update states with atomic write to prevent corruption
        self.file_states = current_files
        self._save_states()

        return added, modified, deleted_paths

    def create_incremental_backup(self, files: Set[Path], base_backup: Optional[Path] = None) -> Path:
        """Creates an incremental backup containing only changed files"""
        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now()
        # Create human-readable backup name
        # Format: incremental_2025-09-20_5-03pm.tar.gz
        time_str = timestamp.strftime("%Y-%m-%d_%I-%M%p").lower()
        backup_name = f"incremental_{time_str}.tar.gz"
        backup_path = self.backup_dir / backup_name

        added, modified, deleted = self.find_changed_files(files)

        # Create manifest
        manifest = {
            'timestamp': timestamp.isoformat(),
            'base_backup': str(base_backup) if base_backup else None,
            'deleted_files': list(deleted),
            'type': 'incremental'
        }

        manifest_file = self.backup_dir / f"{backup_name}.manifest"
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)

        # Create backup with only changed files
        with tarfile.open(backup_path, 'w:gz') as tar:
            # Add manifest
            tar.add(manifest_file, arcname='MANIFEST.json')

            # Add changed files
            for file_path in added | modified:
                rel_path = file_path.relative_to(file_path.parent.parent)
                tar.add(file_path, arcname=str(rel_path))

        manifest_file.unlink()  # Clean up temp manifest

        return backup_path

    def restore_incremental(self, incremental_backup: Path, base_backup: Path, target_dir: Path):
        """Restores from an incremental backup"""
        import tempfile

        # First restore base backup
        with tarfile.open(base_backup, 'r:gz') as tar:
            tar.extractall(target_dir)

        # Then apply incremental changes
        temp_dir = Path(tempfile.mkdtemp(prefix='savior_incremental_'))

        with tarfile.open(incremental_backup, 'r:gz') as tar:
            tar.extractall(temp_dir)

        # Read manifest
        manifest_path = temp_dir / 'MANIFEST.json'
        if manifest_path.exists():
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)

            # Delete files that were deleted
            for deleted_file in manifest.get('deleted_files', []):
                file_to_delete = target_dir / deleted_file
                if file_to_delete.exists():
                    file_to_delete.unlink()

        # Apply modified/added files
        for file_path in temp_dir.rglob('*'):
            if file_path.is_file() and file_path.name != 'MANIFEST.json':
                rel_path = file_path.relative_to(temp_dir)
                target_file = target_dir / rel_path
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, target_file)

        shutil.rmtree(temp_dir)