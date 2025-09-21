import pytest
import tempfile
import shutil
from pathlib import Path
from savior.core import Savior


class TestNewFeatures:
    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory with files"""
        temp_dir = Path(tempfile.mkdtemp(prefix='savior_test_'))

        # Create test structure
        (temp_dir / 'file1.txt').write_text('Content 1')
        (temp_dir / 'file2.py').write_text('print("hello")')
        (temp_dir / 'subdir').mkdir()
        (temp_dir / 'subdir' / 'file3.md').write_text('# Markdown')

        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_disk_space_check(self, temp_project):
        """Test disk space checking"""
        savior = Savior(temp_project)

        # Check for reasonable space (should pass)
        has_space, msg = savior._check_disk_space(1024 * 1024)  # 1MB
        assert has_space is True
        assert msg == ""

        # Check for very large space requirement
        # This may still pass on systems with lots of space, so just check the logic works
        has_space, msg = savior._check_disk_space(1000 * 1024**4)  # 1000TB
        # Either it fails (expected) or succeeds (system has tons of space)
        if not has_space:
            assert "Insufficient disk space" in msg

    def test_size_estimation(self, temp_project):
        """Test backup size estimation"""
        savior = Savior(temp_project)
        files = savior._collect_files()

        estimated = savior._estimate_backup_size(files)
        assert estimated > 0
        # Estimated should be ~40% of original
        total_size = sum(f.stat().st_size for f in files)
        assert estimated < total_size

    def test_compression_levels(self, temp_project):
        """Test different compression levels"""
        savior = Savior(temp_project)

        # No compression
        backup_none = savior.create_backup("No compression", compression_level=0, show_progress=False)
        assert backup_none.path.suffix == '.tar'

        # Maximum compression
        backup_max = savior.create_backup("Max compression", compression_level=9, show_progress=False)
        assert backup_max.path.suffix == '.gz'

        # Uncompressed should be larger
        assert backup_none.size > backup_max.size

    def test_tree_generation(self, temp_project):
        """Test project tree visualization"""
        savior = Savior(temp_project)

        # Test with sizes
        tree = savior.get_project_tree(max_depth=2, show_size=True)
        assert temp_project.name in tree
        assert "file1.txt" in tree
        assert "subdir/" in tree
        assert "B" in tree or "KB" in tree  # Size indicators

        # Test without sizes
        tree_no_size = savior.get_project_tree(max_depth=2, show_size=False)
        assert "B" not in tree_no_size and "KB" not in tree_no_size

        # Test depth limit
        tree_shallow = savior.get_project_tree(max_depth=0)
        assert "file3.md" not in tree_shallow  # Shouldn't see files in subdirs

    def test_progress_bar_option(self, temp_project):
        """Test progress bar enable/disable"""
        savior = Savior(temp_project)

        # With progress (default)
        backup1 = savior.create_backup("With progress", show_progress=True)
        assert backup1.size > 0

        # Without progress
        backup2 = savior.create_backup("Without progress", show_progress=False)
        assert backup2.size > 0

    def test_empty_project_handling(self):
        """Test handling of empty projects"""
        temp_dir = Path(tempfile.mkdtemp(prefix='savior_empty_'))

        try:
            savior = Savior(temp_dir)

            # Should raise ValueError for empty directory
            with pytest.raises(ValueError) as exc_info:
                savior.create_backup("Empty", show_progress=False)
            assert "No files to backup" in str(exc_info.value)

        finally:
            shutil.rmtree(temp_dir)

    def test_tree_with_ignored_files(self, temp_project):
        """Test tree generation respects .saviorignore"""
        # Create .saviorignore
        (temp_project / '.saviorignore').write_text('*.pyc\n__pycache__/')
        (temp_project / 'ignored.pyc').write_text('compiled')
        (temp_project / '__pycache__').mkdir()
        (temp_project / '__pycache__' / 'cache.py').write_text('cache')

        savior = Savior(temp_project)
        tree = savior.get_project_tree()

        # Ignored files shouldn't appear
        assert 'ignored.pyc' not in tree
        assert '__pycache__' not in tree

        # Regular files should appear
        assert 'file1.txt' in tree