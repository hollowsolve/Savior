"""Comprehensive tests for deduplication functionality."""

import os
import json
import shutil
import hashlib
import tempfile
import unittest
from pathlib import Path
from datetime import datetime

from savior.dedup import (
    DeduplicationStore,
    DedupBackupManifest,
    SmartDeduplicator
)


class TestDeduplicationStore(unittest.TestCase):
    """Test the deduplication store functionality."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp(prefix='test_dedup_'))
        self.dedup_store = DeduplicationStore(self.test_dir)

        # Create test files
        self.test_files = {}
        for i in range(5):
            file_path = self.test_dir / f'test_file_{i}.txt'
            content = f'Test content {i}' if i < 3 else 'Test content 0'  # Duplicate content
            file_path.write_text(content)
            self.test_files[f'file_{i}'] = file_path

    def tearDown(self):
        """Clean up test environment."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_initialization(self):
        """Test deduplication store initialization."""
        self.assertTrue(self.dedup_store.store_dir.exists())
        self.assertTrue(self.dedup_store.chunks_dir.exists())
        self.assertTrue(self.dedup_store.index_file.exists())
        self.assertTrue(self.dedup_store.stats_file.exists())

    def test_file_hashing(self):
        """Test file hash calculation."""
        test_file = self.test_files['file_0']
        hash1 = self.dedup_store._calculate_file_hash(test_file)
        hash2 = self.dedup_store._calculate_file_hash(test_file)

        # Same file should produce same hash
        self.assertEqual(hash1, hash2)

        # Different content should produce different hash
        test_file2 = self.test_files['file_1']
        hash3 = self.dedup_store._calculate_file_hash(test_file2)
        self.assertNotEqual(hash1, hash3)

    def test_store_file_new(self):
        """Test storing a new file."""
        test_file = self.test_files['file_0']
        backup_id = 'backup_001'

        metadata = self.dedup_store.store_file(test_file, backup_id)

        self.assertIsNotNone(metadata)
        self.assertIn('hash', metadata)
        self.assertIn('size', metadata)
        self.assertFalse(metadata.get('deduplicated', False))

        # Check chunk was created
        chunk_path = self.dedup_store._get_chunk_path(metadata['hash'])
        self.assertTrue(chunk_path.exists())

    def test_store_file_duplicate(self):
        """Test storing duplicate files (deduplication)."""
        test_file1 = self.test_files['file_0']
        test_file2 = self.test_files['file_3']  # Has same content as file_0

        # Store first file
        metadata1 = self.dedup_store.store_file(test_file1, 'backup_001')
        self.assertFalse(metadata1.get('deduplicated', False))

        # Store duplicate file
        metadata2 = self.dedup_store.store_file(test_file2, 'backup_002')
        self.assertTrue(metadata2.get('deduplicated', False))

        # Both should have same hash
        self.assertEqual(metadata1['hash'], metadata2['hash'])

        # Check stats
        stats = self.dedup_store.get_dedup_stats()
        self.assertGreater(stats['space_saved'], 0)

    def test_retrieve_file(self):
        """Test retrieving a deduplicated file."""
        test_file = self.test_files['file_0']
        backup_id = 'backup_001'

        # Store file
        metadata = self.dedup_store.store_file(test_file, backup_id)
        content_hash = metadata['hash']

        # Retrieve to new location
        restore_path = self.test_dir / 'restored_file.txt'
        success = self.dedup_store.retrieve_file(content_hash, restore_path)

        self.assertTrue(success)
        self.assertTrue(restore_path.exists())

        # Content should match
        self.assertEqual(
            test_file.read_text(),
            restore_path.read_text()
        )

    def test_reference_counting(self):
        """Test reference counting for deduplicated content."""
        test_file = self.test_files['file_0']

        # Store file from multiple backups
        metadata1 = self.dedup_store.store_file(test_file, 'backup_001')
        metadata2 = self.dedup_store.store_file(test_file, 'backup_002')
        metadata3 = self.dedup_store.store_file(test_file, 'backup_003')

        content_hash = metadata1['hash']

        # Check reference count
        index = self.dedup_store._load_index()
        self.assertEqual(index[content_hash]['ref_count'], 3)

        # Remove one reference
        self.dedup_store.remove_reference(content_hash, 'backup_001')
        index = self.dedup_store._load_index()
        self.assertEqual(index[content_hash]['ref_count'], 2)

        # Chunk should still exist
        chunk_path = self.dedup_store._get_chunk_path(content_hash)
        self.assertTrue(chunk_path.exists())

        # Remove all references
        self.dedup_store.remove_reference(content_hash, 'backup_002')
        self.dedup_store.remove_reference(content_hash, 'backup_003')

        # Chunk should be deleted
        self.assertFalse(chunk_path.exists())

    def test_cleanup_orphaned_chunks(self):
        """Test cleanup of orphaned chunks."""
        # Create orphaned chunk manually
        orphan_hash = 'orphaned_chunk_hash_12345'
        orphan_path = self.dedup_store._get_chunk_path(orphan_hash)
        orphan_path.parent.mkdir(parents=True, exist_ok=True)
        orphan_path.write_text('orphaned content')

        # Store valid file
        test_file = self.test_files['file_0']
        self.dedup_store.store_file(test_file, 'backup_001')

        # Run cleanup
        cleaned = self.dedup_store.cleanup_orphaned_chunks()

        self.assertEqual(cleaned, 1)
        self.assertFalse(orphan_path.exists())

    def test_dedup_stats(self):
        """Test deduplication statistics."""
        # Store multiple files with some duplicates
        self.dedup_store.store_file(self.test_files['file_0'], 'backup_001')
        self.dedup_store.store_file(self.test_files['file_1'], 'backup_001')
        self.dedup_store.store_file(self.test_files['file_3'], 'backup_002')  # Duplicate of file_0
        self.dedup_store.store_file(self.test_files['file_4'], 'backup_002')  # Duplicate of file_0

        stats = self.dedup_store.get_dedup_stats()

        self.assertIn('total_stored', stats)
        self.assertIn('total_deduplicated', stats)
        self.assertIn('space_saved', stats)
        self.assertIn('dedup_ratio', stats)
        self.assertIn('unique_chunks', stats)
        self.assertIn('total_references', stats)

        self.assertEqual(stats['unique_chunks'], 2)  # Only 2 unique contents
        self.assertGreater(stats['dedup_ratio'], 0)


class TestDedupBackupManifest(unittest.TestCase):
    """Test backup manifest functionality."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp(prefix='test_manifest_'))
        self.manifest_manager = DedupBackupManifest(self.test_dir)

    def tearDown(self):
        """Clean up test environment."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_create_manifest(self):
        """Test creating a backup manifest."""
        backup_id = 'backup_20240101_120000'
        files = {
            Path('src/main.py'): {
                'hash': 'abc123',
                'size': 1024,
                'deduplicated': False
            },
            Path('src/utils.py'): {
                'hash': 'def456',
                'size': 2048,
                'deduplicated': True
            }
        }

        manifest_path = self.manifest_manager.create_manifest(backup_id, files)

        self.assertTrue(manifest_path.exists())
        self.assertEqual(manifest_path.name, f'{backup_id}.json')

        # Load and verify manifest
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)

        self.assertEqual(manifest['backup_id'], backup_id)
        self.assertIn('timestamp', manifest)
        self.assertEqual(len(manifest['files']), 2)
        self.assertEqual(manifest['stats']['total_files'], 2)
        self.assertEqual(manifest['stats']['total_size'], 3072)
        self.assertEqual(manifest['stats']['deduplicated_files'], 1)

    def test_load_manifest(self):
        """Test loading a backup manifest."""
        backup_id = 'backup_20240101_120000'
        files = {
            Path('test.txt'): {'hash': 'xyz789', 'size': 512}
        }

        # Create manifest
        self.manifest_manager.create_manifest(backup_id, files)

        # Load manifest
        loaded = self.manifest_manager.load_manifest(backup_id)

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded['backup_id'], backup_id)
        self.assertIn('test.txt', loaded['files'])

    def test_list_manifests(self):
        """Test listing all manifests."""
        # Create multiple manifests
        for i in range(3):
            backup_id = f'backup_2024010{i}_120000'
            files = {Path(f'file_{i}.txt'): {'hash': f'hash_{i}', 'size': 100 * i}}
            self.manifest_manager.create_manifest(backup_id, files)

        manifests = self.manifest_manager.list_manifests()

        self.assertEqual(len(manifests), 3)
        # Should be sorted by timestamp (reverse)
        self.assertEqual(manifests[0]['backup_id'], 'backup_20240102_120000')


class TestSmartDeduplicator(unittest.TestCase):
    """Test smart deduplication logic."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp(prefix='test_smart_'))

    def tearDown(self):
        """Clean up test environment."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_should_deduplicate_file_types(self):
        """Test file type filtering for deduplication."""
        # Create test files (must be >= 1KB to be deduplicated)
        source_file = self.test_dir / 'main.py'
        source_file.write_text('print("hello")' * 100)  # Make it large enough

        zip_file = self.test_dir / 'archive.zip'
        zip_file.write_bytes(b'PK\x03\x04' + b'compressed data')

        jpg_file = self.test_dir / 'image.jpg'
        jpg_file.write_bytes(b'\xFF\xD8\xFF' + b'image data')

        # Source files should be deduplicated
        self.assertTrue(SmartDeduplicator.should_deduplicate(source_file))

        # Compressed files should not be deduplicated
        self.assertFalse(SmartDeduplicator.should_deduplicate(zip_file))
        self.assertFalse(SmartDeduplicator.should_deduplicate(jpg_file))

    def test_should_deduplicate_size_threshold(self):
        """Test size threshold for deduplication."""
        # Create tiny file (below threshold)
        tiny_file = self.test_dir / 'tiny.txt'
        tiny_file.write_text('hi')

        # Create normal file (above threshold)
        normal_file = self.test_dir / 'normal.txt'
        normal_file.write_text('x' * 2000)

        self.assertFalse(SmartDeduplicator.should_deduplicate(tiny_file))
        self.assertTrue(SmartDeduplicator.should_deduplicate(normal_file))

    def test_estimate_dedup_savings(self):
        """Test deduplication savings estimation."""
        files = []

        # Create files with duplicates
        for i in range(5):
            file_path = self.test_dir / f'file_{i}.txt'
            # Create duplicates for files 0, 2, 4
            content = 'duplicate content' if i % 2 == 0 else f'unique {i}'
            file_path.write_text(content * 100)  # Make large enough
            files.append(file_path)

        estimate = SmartDeduplicator.estimate_dedup_savings(files)

        self.assertIn('total_size', estimate)
        self.assertIn('unique_size', estimate)
        self.assertIn('potential_savings', estimate)
        self.assertIn('estimated_ratio', estimate)

        self.assertGreater(estimate['potential_savings'], 0)
        self.assertGreater(estimate['estimated_ratio'], 0)


class TestIntegration(unittest.TestCase):
    """Integration tests for deduplication with backups."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp(prefix='test_integration_'))
        self.project_dir = self.test_dir / 'project'
        self.project_dir.mkdir()

        # Create test project structure with files large enough to deduplicate (>= 1KB)
        (self.project_dir / 'src').mkdir()
        (self.project_dir / 'src' / 'main.py').write_text('def main(): pass\n' * 100)  # Make it > 1KB
        (self.project_dir / 'src' / 'utils.py').write_text('def util(): pass\n' * 100)  # Make it > 1KB
        (self.project_dir / 'README.md').write_text('# Test Project\n' * 100)  # Make it > 1KB

    def tearDown(self):
        """Clean up test environment."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_dedup_with_backup_workflow(self):
        """Test complete dedup workflow with backup creation."""
        from savior.core_dedup import SaviorWithDedup

        # Create Savior instance with dedup
        savior = SaviorWithDedup(self.project_dir, enable_dedup=True)

        # Create first backup
        backup1 = savior.create_backup_dedup('First backup', show_progress=False)
        self.assertIsNotNone(backup1)

        # Modify one file (keep it > 1KB)
        (self.project_dir / 'src' / 'main.py').write_text('def main(): print("changed")\n' * 100)

        # Create second backup - should deduplicate unchanged files
        backup2 = savior.create_backup_dedup('Second backup', show_progress=False)
        self.assertIsNotNone(backup2)

        # Check dedup stats
        stats = savior.dedup_store.get_dedup_stats()
        self.assertGreater(stats['space_saved'], 0)

        # Test restoration
        success = savior.restore_backup_dedup(0)
        self.assertTrue(success)

    def test_dedup_performance(self):
        """Test deduplication performance with many files."""
        # Create many duplicate files
        for i in range(100):
            file_path = self.project_dir / f'file_{i}.txt'
            # Create groups of duplicates
            content = f'content_group_{i % 10}' * 100
            file_path.write_text(content)

        from savior.core_dedup import SaviorWithDedup

        savior = SaviorWithDedup(self.project_dir, enable_dedup=True)

        # Measure time and space
        import time
        start_time = time.time()

        backup = savior.create_backup_dedup('Performance test', show_progress=False)

        elapsed_time = time.time() - start_time

        self.assertIsNotNone(backup)
        self.assertLess(elapsed_time, 10)  # Should complete in < 10 seconds

        # Check space savings
        stats = savior.dedup_store.get_dedup_stats()
        self.assertGreater(stats['dedup_ratio'], 0.5)  # At least 50% savings


if __name__ == '__main__':
    unittest.main()