"""Enhanced core with deduplication support."""

from pathlib import Path
from typing import Optional, Dict, Set
from datetime import datetime
import tarfile

from .core import Savior, Backup
from .dedup import DeduplicationStore, DedupBackupManifest, SmartDeduplicator
from .cli_utils import format_size
from tqdm import tqdm


class SaviorWithDedup(Savior):
    """Enhanced Savior with deduplication capabilities."""

    def __init__(self, *args, enable_dedup: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.enable_dedup = enable_dedup
        if enable_dedup:
            self.dedup_store = DeduplicationStore(self.backup_dir)
            self.manifest_manager = DedupBackupManifest(self.backup_dir)

    def create_backup_dedup(self, description: str = "", compression_level: int = 6,
                           show_progress: bool = True) -> Optional[Backup]:
        """Create a deduplicated backup."""
        if not self.enable_dedup:
            # Fall back to regular backup
            return self.create_backup(description, compression_level, show_progress)

        self._ensure_backup_dir()
        self._cleanup_old_backups()

        # Collect files
        files = self._collect_files()
        if not files:
            return None

        # Check disk space
        estimated_size = self._estimate_backup_size(files)
        has_space, error_msg = self._check_disk_space(estimated_size)
        if not has_space:
            print(f"Error: {error_msg}")
            return None

        # Generate backup ID
        timestamp = datetime.now()
        backup_id = timestamp.strftime("%Y%m%d_%H%M%S_dedup")

        # Track deduplicated files
        dedup_files = {}
        skipped = 0
        deduplicated = 0
        new_files = 0

        # Process files with deduplication
        file_list = list(files)
        if show_progress:
            pbar = tqdm(total=len(file_list), desc="Deduplicating files", unit="files")

        for file_path in file_list:
            try:
                # Check if file should be deduplicated
                if SmartDeduplicator.should_deduplicate(file_path):
                    # Store with deduplication
                    rel_path = file_path.relative_to(self.project_dir)
                    metadata = self.dedup_store.store_file(file_path, backup_id)

                    if metadata:
                        dedup_files[rel_path] = metadata
                        if metadata.get('deduplicated'):
                            deduplicated += 1
                        else:
                            new_files += 1
                else:
                    # Skip deduplication for this file type
                    skipped += 1

                if show_progress:
                    pbar.update(1)
            except Exception:
                if show_progress:
                    pbar.update(1)
                continue

        if show_progress:
            pbar.close()

        # Create manifest
        manifest_path = self.manifest_manager.create_manifest(backup_id, dedup_files)

        # Get dedup stats
        stats = self.dedup_store.get_dedup_stats()

        # Create backup record
        backup = Backup(
            timestamp=timestamp,
            path=manifest_path,  # Point to manifest instead of tar
            description=f"{description} [DEDUP]",
            size=sum(f['size'] for f in dedup_files.values())
        )

        # Update metadata
        metadata = self._load_metadata()
        metadata['backups'].append(backup.to_dict())
        self._save_metadata(metadata)

        # Print stats
        if show_progress:
            print(f"✓ Backup created with deduplication")
            print(f"  New files: {new_files}")
            print(f"  Deduplicated: {deduplicated}")
            print(f"  Skipped: {skipped}")
            if stats['space_saved'] > 0:
                print(f"  Space saved: {format_size(stats['space_saved'])}")
                print(f"  Dedup ratio: {stats['dedup_ratio']:.1%}")

        return backup

    def restore_backup_dedup(self, backup_index: int) -> bool:
        """Restore from a deduplicated backup."""
        metadata = self._load_metadata()
        backups = [Backup.from_dict(b) for b in metadata['backups']]

        if not backups or backup_index < 0 or backup_index >= len(backups):
            return False

        backup = sorted(backups, key=lambda b: b.timestamp, reverse=True)[backup_index]

        # Check if this is a deduplicated backup
        if '[DEDUP]' not in backup.description:
            # Regular backup, use normal restore
            return self.restore_backup(backup_index)

        # Load manifest
        backup_id = backup.path.stem  # Get backup ID from manifest filename
        manifest = self.manifest_manager.load_manifest(backup_id)

        if not manifest:
            print("Error: Could not load backup manifest")
            return False

        print(f"Restoring {len(manifest['files'])} files from deduplicated backup...")

        # Restore files from dedup store
        restored = 0
        failed = 0

        for file_path_str, metadata in manifest['files'].items():
            file_path = self.project_dir / file_path_str
            content_hash = metadata['hash']

            if self.dedup_store.retrieve_file(content_hash, file_path):
                restored += 1
            else:
                failed += 1

        print(f"✓ Restored {restored} files")
        if failed > 0:
            print(f"⚠ Failed to restore {failed} files")

        return restored > 0

    def estimate_dedup_savings(self) -> Dict:
        """Estimate potential deduplication savings for current project."""
        files = list(self._collect_files())
        return SmartDeduplicator.estimate_dedup_savings(files)

    def cleanup_dedup_store(self) -> int:
        """Clean up orphaned chunks in dedup store."""
        if not self.enable_dedup:
            return 0

        return self.dedup_store.cleanup_orphaned_chunks()