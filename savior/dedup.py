"""Content-based deduplication for efficient backup storage."""

import os
import json
import hashlib
import shutil
from pathlib import Path
from typing import Dict, Set, Optional, Tuple, List
from datetime import datetime
import threading


class DeduplicationStore:
    """Manages deduplicated storage of file content."""

    def __init__(self, backup_dir: Path):
        self.backup_dir = backup_dir
        self.store_dir = backup_dir / '.dedup_store'
        self.chunks_dir = self.store_dir / 'chunks'
        self.index_file = self.store_dir / 'index.json'
        self.stats_file = self.store_dir / 'stats.json'
        self._lock = threading.Lock()
        self._index_cache: Optional[Dict] = None
        self._init_store()

    def _init_store(self):
        """Initialize deduplication store directories."""
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.chunks_dir.mkdir(parents=True, exist_ok=True)

        # Initialize index if it doesn't exist
        if not self.index_file.exists():
            self._save_index({})

        # Initialize stats if it doesn't exist
        if not self.stats_file.exists():
            self._save_stats({
                'total_stored': 0,
                'total_deduplicated': 0,
                'space_saved': 0,
                'dedup_ratio': 0.0
            })

    def _load_index(self) -> Dict:
        """Load deduplication index from disk."""
        if self._index_cache is not None:
            return self._index_cache

        try:
            with open(self.index_file, 'r') as f:
                self._index_cache = json.load(f)
                return self._index_cache
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_index(self, index: Dict):
        """Save deduplication index to disk."""
        with self._lock:
            with open(self.index_file, 'w') as f:
                json.dump(index, f, indent=2)
            self._index_cache = index

    def _load_stats(self) -> Dict:
        """Load deduplication statistics."""
        try:
            with open(self.stats_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {
                'total_stored': 0,
                'total_deduplicated': 0,
                'space_saved': 0,
                'dedup_ratio': 0.0
            }

    def _save_stats(self, stats: Dict):
        """Save deduplication statistics."""
        with open(self.stats_file, 'w') as f:
            json.dump(stats, f, indent=2)

    def _calculate_file_hash(self, file_path: Path, chunk_size: int = 65536) -> str:
        """Calculate SHA256 hash of a file."""
        hasher = hashlib.sha256()

        try:
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    hasher.update(chunk)
            return hasher.hexdigest()
        except (IOError, OSError):
            return None

    def _get_chunk_path(self, content_hash: str) -> Path:
        """Get storage path for a content chunk."""
        # Use first 2 chars as directory for better file system performance
        subdir = self.chunks_dir / content_hash[:2]
        subdir.mkdir(exist_ok=True)
        return subdir / content_hash

    def store_file(self, file_path: Path, backup_id: str) -> Optional[Dict]:
        """
        Store a file with deduplication.
        Returns metadata about the stored file.
        """
        if not file_path.exists() or not file_path.is_file():
            return None

        # Calculate file hash
        content_hash = self._calculate_file_hash(file_path)
        if not content_hash:
            return None

        file_size = file_path.stat().st_size
        chunk_path = self._get_chunk_path(content_hash)

        # Load current index
        index = self._load_index()

        # Check if content already exists
        if content_hash in index:
            # Content already stored, just update references
            if isinstance(index[content_hash]['refs'], list):
                refs = set(index[content_hash]['refs'])
            else:
                refs = index[content_hash]['refs']
            refs.add(backup_id)
            index[content_hash]['refs'] = list(refs)  # Store as list for JSON
            index[content_hash]['ref_count'] = len(refs)

            # Update stats for deduplication
            stats = self._load_stats()
            stats['total_deduplicated'] += file_size
            stats['space_saved'] += file_size
            self._save_stats(stats)
        else:
            # New content, store it
            try:
                # Copy file to chunk store
                shutil.copy2(file_path, chunk_path)

                # Add to index
                index[content_hash] = {
                    'size': file_size,
                    'refs': [backup_id],  # Store as list for JSON
                    'ref_count': 1,
                    'first_seen': datetime.now().isoformat(),
                    'chunk_path': str(chunk_path.relative_to(self.store_dir))
                }

                # Update stats for new storage
                stats = self._load_stats()
                stats['total_stored'] += file_size
                self._save_stats(stats)
            except (IOError, OSError) as e:
                return None

        # Save updated index
        self._save_index(index)

        # Return metadata for manifest
        return {
            'hash': content_hash,
            'size': file_size,
            'deduplicated': content_hash in index and index[content_hash]['ref_count'] > 1
        }

    def retrieve_file(self, content_hash: str, destination: Path) -> bool:
        """Retrieve a deduplicated file by its hash."""
        index = self._load_index()

        if content_hash not in index:
            return False

        chunk_path = self._get_chunk_path(content_hash)

        if not chunk_path.exists():
            return False

        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(chunk_path, destination)
            return True
        except (IOError, OSError):
            return False

    def remove_reference(self, content_hash: str, backup_id: str) -> bool:
        """
        Remove a reference to deduplicated content.
        If no references remain, delete the content.
        """
        index = self._load_index()

        if content_hash not in index:
            return False

        # Convert to set, remove reference, convert back to list
        refs = set(index[content_hash].get('refs', []))
        refs.discard(backup_id)
        index[content_hash]['refs'] = list(refs)
        index[content_hash]['ref_count'] = len(refs)

        # If no more references, delete the chunk
        if index[content_hash]['ref_count'] == 0:
            chunk_path = self._get_chunk_path(content_hash)
            try:
                if chunk_path.exists():
                    chunk_path.unlink()

                # Update stats
                stats = self._load_stats()
                stats['total_stored'] -= index[content_hash]['size']
                self._save_stats(stats)

                # Remove from index
                del index[content_hash]
            except (IOError, OSError):
                pass

        self._save_index(index)
        return True

    def get_dedup_stats(self) -> Dict:
        """Get deduplication statistics."""
        stats = self._load_stats()

        # Calculate dedup ratio
        if stats['total_stored'] > 0:
            total_logical = stats['total_stored'] + stats['total_deduplicated']
            stats['dedup_ratio'] = stats['total_deduplicated'] / total_logical
        else:
            stats['dedup_ratio'] = 0.0

        # Add current index stats
        index = self._load_index()
        stats['unique_chunks'] = len(index)
        stats['total_references'] = sum(item['ref_count'] for item in index.values())

        return stats

    def cleanup_orphaned_chunks(self) -> int:
        """Remove chunks that have no references."""
        index = self._load_index()
        cleaned = 0

        # Find orphaned chunks in the filesystem
        for chunk_dir in self.chunks_dir.iterdir():
            if chunk_dir.is_dir():
                for chunk_file in chunk_dir.iterdir():
                    if chunk_file.is_file():
                        chunk_hash = chunk_file.name

                        # If not in index or has no refs, delete
                        if chunk_hash not in index or index[chunk_hash]['ref_count'] == 0:
                            try:
                                chunk_file.unlink()
                                cleaned += 1
                            except (IOError, OSError):
                                pass

        # Clean up empty directories
        for chunk_dir in self.chunks_dir.iterdir():
            if chunk_dir.is_dir() and not any(chunk_dir.iterdir()):
                try:
                    chunk_dir.rmdir()
                except (IOError, OSError):
                    pass

        return cleaned


class DedupBackupManifest:
    """Manages backup manifests for deduplicated backups."""

    def __init__(self, backup_dir: Path):
        self.backup_dir = backup_dir
        self.manifests_dir = backup_dir / '.dedup_manifests'
        self.manifests_dir.mkdir(exist_ok=True)

    def create_manifest(self, backup_id: str, files: Dict[Path, Dict]) -> Path:
        """
        Create a manifest for a deduplicated backup.
        files: Dict mapping file paths to their dedup metadata
        """
        manifest = {
            'backup_id': backup_id,
            'timestamp': datetime.now().isoformat(),
            'files': {}
        }

        for file_path, metadata in files.items():
            manifest['files'][str(file_path)] = metadata

        # Calculate manifest stats
        manifest['stats'] = {
            'total_files': len(files),
            'total_size': sum(m['size'] for m in files.values()),
            'deduplicated_files': sum(1 for m in files.values() if m.get('deduplicated', False))
        }

        # Save manifest
        manifest_path = self.manifests_dir / f"{backup_id}.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)

        return manifest_path

    def load_manifest(self, backup_id: str) -> Optional[Dict]:
        """Load a backup manifest."""
        manifest_path = self.manifests_dir / f"{backup_id}.json"

        if not manifest_path.exists():
            return None

        try:
            with open(manifest_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def list_manifests(self) -> List[Dict]:
        """List all backup manifests."""
        manifests = []

        for manifest_file in self.manifests_dir.glob('*.json'):
            try:
                with open(manifest_file, 'r') as f:
                    manifest = json.load(f)
                    manifests.append({
                        'backup_id': manifest['backup_id'],
                        'timestamp': manifest['timestamp'],
                        'total_files': manifest['stats']['total_files'],
                        'total_size': manifest['stats']['total_size'],
                        'deduplicated_files': manifest['stats']['deduplicated_files']
                    })
            except (json.JSONDecodeError, IOError):
                continue

        return sorted(manifests, key=lambda m: m['timestamp'], reverse=True)


class SmartDeduplicator:
    """Smart deduplication with file type awareness."""

    # File extensions that typically don't deduplicate well
    SKIP_DEDUP_EXTENSIONS = {
        # Already compressed
        '.zip', '.gz', '.bz2', '.xz', '.7z', '.rar',
        '.jpg', '.jpeg', '.png', '.gif', '.webp',
        '.mp3', '.mp4', '.avi', '.mkv', '.mov',
        '.pdf',
        # Binary executables
        '.exe', '.dll', '.so', '.dylib',
        # Database files (change frequently)
        '.db', '.sqlite', '.mdb'
    }

    # Minimum file size for deduplication (skip tiny files)
    MIN_DEDUP_SIZE = 1024  # 1KB

    @staticmethod
    def should_deduplicate(file_path: Path) -> bool:
        """Determine if a file should be deduplicated."""
        # Skip if file is too small
        try:
            file_size = file_path.stat().st_size
            if file_size < SmartDeduplicator.MIN_DEDUP_SIZE:
                return False
        except (IOError, OSError):
            return False

        # Skip if extension indicates poor deduplication
        if file_path.suffix.lower() in SmartDeduplicator.SKIP_DEDUP_EXTENSIONS:
            return False

        # Deduplicate everything else (source code, text files, etc.)
        return True

    @staticmethod
    def estimate_dedup_savings(files: List[Path]) -> Dict:
        """Estimate potential deduplication savings."""
        hash_map = {}
        total_size = 0
        duplicates_size = 0

        for file_path in files:
            try:
                size = file_path.stat().st_size
                total_size += size

                # Quick hash for estimation (first 1MB + last 1MB)
                quick_hash = SmartDeduplicator._quick_hash(file_path)

                if quick_hash in hash_map:
                    duplicates_size += size
                else:
                    hash_map[quick_hash] = size
            except (IOError, OSError):
                continue

        return {
            'total_size': total_size,
            'unique_size': total_size - duplicates_size,
            'potential_savings': duplicates_size,
            'estimated_ratio': duplicates_size / total_size if total_size > 0 else 0
        }

    @staticmethod
    def _quick_hash(file_path: Path) -> str:
        """Quick hash for dedup estimation (not cryptographically secure)."""
        hasher = hashlib.md5()

        try:
            with open(file_path, 'rb') as f:
                # Hash first 1KB
                hasher.update(f.read(1024))

                # Hash last 1KB if file is large enough
                file_size = file_path.stat().st_size
                if file_size > 2048:
                    f.seek(-1024, 2)
                    hasher.update(f.read(1024))

                # Include file size in hash
                hasher.update(str(file_size).encode())

            return hasher.hexdigest()
        except (IOError, OSError):
            return str(file_path)