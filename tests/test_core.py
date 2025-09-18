import pytest
import tempfile
import shutil
import time
from pathlib import Path
from datetime import datetime

from savior.core import Savior, Backup, SaviorIgnore


class TestSaviorCore:
    @pytest.fixture
    def temp_project(self):
        """Create a temporary project directory"""
        temp_dir = Path(tempfile.mkdtemp(prefix='savior_test_'))

        # Create some test files
        (temp_dir / 'main.py').write_text('print("Hello, World!")')
        (temp_dir / 'README.md').write_text('# Test Project')
        (temp_dir / 'data.txt').write_text('Some data')

        # Create subdirectory
        (temp_dir / 'src').mkdir()
        (temp_dir / 'src' / 'utils.py').write_text('def helper(): pass')

        yield temp_dir

        # Cleanup
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def savior(self, temp_project):
        """Create a Savior instance"""
        return Savior(temp_project)

    def test_initialization(self, savior, temp_project):
        """Test Savior initialization"""
        # Resolve both paths to handle macOS symlinks (/var vs /private/var)
        assert savior.project_dir == temp_project.resolve()
        assert savior.backup_dir == temp_project.resolve() / '.savior'
        assert savior.watch_interval == 20 * 60

    def test_create_backup(self, savior):
        """Test creating a backup"""
        backup = savior.create_backup("Test backup")

        assert backup.path.exists()
        assert backup.description == "Test backup"
        assert backup.size > 0
        assert '.tar.gz' in str(backup.path)

    def test_list_backups(self, savior):
        """Test listing backups"""
        # Create multiple backups
        savior.create_backup("First")
        time.sleep(1)  # Ensure different timestamps
        savior.create_backup("Second")

        backups = savior.list_backups()

        assert len(backups) == 2
        assert backups[0].description == "Second"  # Most recent first
        assert backups[1].description == "First"

    def test_restore_backup(self, savior, temp_project):
        """Test restoring a backup"""
        # Create initial backup
        savior.create_backup("Initial state")

        # Sleep to ensure different timestamps
        time.sleep(1)

        # Modify files
        (temp_project / 'main.py').write_text('print("Modified!")')
        (temp_project / 'new_file.txt').write_text('New content')

        # Create another backup
        savior.create_backup("Modified state")

        # Restore first backup
        success = savior.restore_backup(1)  # Index 1 is the first backup

        assert success
        assert (temp_project / 'main.py').read_text() == 'print("Hello, World!")'
        assert not (temp_project / 'new_file.txt').exists()

    def test_cleanup_old_backups(self, savior):
        """Test automatic cleanup of old backups"""
        # This would need to mock datetime to test properly
        # For now, just ensure the method runs without error
        savior._cleanup_old_backups()

    def test_savior_ignore(self, temp_project):
        """Test .saviorignore functionality"""
        # Create .saviorignore file
        ignore_content = """
        *.pyc
        __pycache__/
        test_*.txt
        """
        (temp_project / '.saviorignore').write_text(ignore_content)

        ignore = SaviorIgnore(temp_project / '.saviorignore')

        assert ignore.should_ignore('file.pyc')
        assert ignore.should_ignore('__pycache__/cache.py')
        assert ignore.should_ignore('test_data.txt')
        assert not ignore.should_ignore('main.py')


class TestBackup:
    def test_backup_creation(self):
        """Test Backup object creation"""
        now = datetime.now()
        path = Path('/tmp/backup.tar.gz')
        backup = Backup(now, path, "Test", 1024)

        assert backup.timestamp == now
        assert backup.path == path
        assert backup.description == "Test"
        assert backup.size == 1024

    def test_backup_serialization(self):
        """Test Backup to_dict and from_dict"""
        now = datetime.now()
        path = Path('/tmp/backup.tar.gz')
        backup = Backup(now, path, "Test", 1024)

        data = backup.to_dict()
        restored = Backup.from_dict(data)

        assert restored.timestamp == backup.timestamp
        assert restored.path == backup.path
        assert restored.description == backup.description
        assert restored.size == backup.size