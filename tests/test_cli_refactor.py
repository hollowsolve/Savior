"""Tests for refactored CLI modules."""

import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from datetime import datetime, timedelta
from click.testing import CliRunner
import tempfile
import shutil

from savior.cli_utils import (
    format_time_ago,
    format_size,
    select_from_list,
    display_stats
)

from savior.commands.backup import watch, save, stop, status
from savior.commands.restore import restore, list as list_backups
from savior.commands.cloud import cloud


class TestCliUtils(unittest.TestCase):
    """Test CLI utility functions."""

    def test_format_time_ago(self):
        """Test time formatting."""
        now = datetime.now()

        # Just now
        self.assertEqual(
            format_time_ago(now - timedelta(seconds=30)),
            "just now"
        )

        # Minutes
        self.assertEqual(
            format_time_ago(now - timedelta(minutes=5)),
            "5 minutes ago"
        )
        self.assertEqual(
            format_time_ago(now - timedelta(minutes=1)),
            "1 minute ago"
        )

        # Hours
        self.assertEqual(
            format_time_ago(now - timedelta(hours=3)),
            "3 hours ago"
        )
        self.assertEqual(
            format_time_ago(now - timedelta(hours=1)),
            "1 hour ago"
        )

        # Days
        self.assertEqual(
            format_time_ago(now - timedelta(days=2)),
            "2 days ago"
        )
        self.assertEqual(
            format_time_ago(now - timedelta(days=1)),
            "1 day ago"
        )

    def test_format_size(self):
        """Test size formatting."""
        self.assertEqual(format_size(500), "500.0 B")
        self.assertEqual(format_size(1024), "1.0 KB")
        self.assertEqual(format_size(1024 * 1024), "1.0 MB")
        self.assertEqual(format_size(1024 * 1024 * 1024), "1.0 GB")
        self.assertEqual(format_size(1024 * 1024 * 1024 * 1024), "1.0 TB")

    def test_display_stats(self):
        """Test statistics display."""
        # This is mainly for coverage, actual display is visual
        stats = {
            'total_size': 1024 * 1024,
            'dedup_ratio': 0.75,
            'files_count': 100
        }

        # Should not raise any errors
        try:
            with patch('click.echo'):
                display_stats(stats)
        except Exception as e:
            self.fail(f"display_stats raised {e}")


class TestBackupCommands(unittest.TestCase):
    """Test backup-related CLI commands."""

    def setUp(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.test_dir = Path(tempfile.mkdtemp(prefix='test_cli_'))

    def tearDown(self):
        """Clean up test environment."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    @patch('savior.commands.backup.Savior')
    def test_save_command(self, mock_savior_class):
        """Test save command."""
        mock_savior = Mock()
        mock_savior_class.return_value = mock_savior

        mock_backup = Mock()
        mock_backup.size = 1024 * 1024  # 1 MB
        mock_savior.create_backup.return_value = mock_backup

        with self.runner.isolated_filesystem():
            result = self.runner.invoke(save, ['Test backup'])

            self.assertEqual(result.exit_code, 0)
            mock_savior.create_backup.assert_called_once()
            self.assertIn('Saved backup', result.output)

    @patch('savior.commands.backup.Savior')
    def test_save_with_tree(self, mock_savior_class):
        """Test save command with tree option."""
        mock_savior = Mock()
        mock_savior_class.return_value = mock_savior
        mock_savior.get_project_tree.return_value = "project/\n├── src/\n└── README.md"

        mock_backup = Mock()
        mock_backup.size = 1024
        mock_savior.create_backup.return_value = mock_backup

        with self.runner.isolated_filesystem():
            result = self.runner.invoke(save, ['--tree', 'Test', '--no-progress'])

            self.assertEqual(result.exit_code, 0)
            mock_savior.get_project_tree.assert_called_once()
            self.assertIn('project/', result.output)

    @patch('savior.commands.backup.Savior')
    def test_status_command(self, mock_savior_class):
        """Test status command."""
        mock_savior = Mock()
        mock_savior_class.return_value = mock_savior

        # Mock metadata
        mock_savior._load_metadata.return_value = {'watching': True}

        # Mock backups
        mock_backup = Mock()
        mock_backup.size = 1024
        mock_backup.timestamp = datetime.now()
        mock_savior.list_backups.return_value = [mock_backup]

        with self.runner.isolated_filesystem():
            # Create .savior directory
            Path('.savior').mkdir()

            result = self.runner.invoke(status)

            self.assertEqual(result.exit_code, 0)
            self.assertIn('actively watching', result.output)
            self.assertIn('Total backups: 1', result.output)

    @patch('savior.commands.backup.Savior')
    def test_stop_command(self, mock_savior_class):
        """Test stop command."""
        mock_savior = Mock()
        mock_savior_class.return_value = mock_savior

        mock_savior._load_metadata.return_value = {'watching': True}
        mock_savior._save_metadata = Mock()

        with self.runner.isolated_filesystem():
            result = self.runner.invoke(stop)

            self.assertEqual(result.exit_code, 0)
            self.assertIn('Stopped watching', result.output)


class TestRestoreCommands(unittest.TestCase):
    """Test restore-related CLI commands."""

    def setUp(self):
        """Set up test environment."""
        self.runner = CliRunner()

    @patch('savior.commands.restore.Savior')
    def test_list_command(self, mock_savior_class):
        """Test list command."""
        mock_savior = Mock()
        mock_savior_class.return_value = mock_savior

        # Mock backups
        mock_backup1 = Mock()
        mock_backup1.timestamp = datetime.now() - timedelta(hours=1)
        mock_backup1.description = "Test backup 1"
        mock_backup1.size = 1024 * 1024

        mock_backup2 = Mock()
        mock_backup2.timestamp = datetime.now() - timedelta(hours=2)
        mock_backup2.description = "Test backup 2"
        mock_backup2.size = 2048 * 1024

        mock_savior.list_backups.return_value = [mock_backup1, mock_backup2]

        with self.runner.isolated_filesystem():
            result = self.runner.invoke(list_backups)

            self.assertEqual(result.exit_code, 0)
            self.assertIn('Test backup 1', result.output)
            self.assertIn('Test backup 2', result.output)
            self.assertIn('Found 2 backup(s)', result.output)

    @patch('savior.commands.restore.Savior')
    def test_list_no_backups(self, mock_savior_class):
        """Test list command with no backups."""
        mock_savior = Mock()
        mock_savior_class.return_value = mock_savior
        mock_savior.list_backups.return_value = []

        with self.runner.isolated_filesystem():
            result = self.runner.invoke(list_backups)

            self.assertEqual(result.exit_code, 0)
            self.assertIn('No backups found', result.output)

    @patch('savior.commands.restore.Savior')
    @patch('savior.commands.restore.select_from_list')
    @patch('savior.commands.restore.confirm_action')
    def test_restore_check_conflicts(self, mock_confirm, mock_select, mock_savior_class):
        """Test restore with conflict checking."""
        mock_savior = Mock()
        mock_savior_class.return_value = mock_savior

        # Mock backup
        mock_backup = Mock()
        mock_backup.timestamp = datetime.now()
        mock_backup.description = "Test backup"
        mock_savior.list_backups.return_value = [mock_backup]

        # Mock selection
        mock_select.return_value = 0

        with self.runner.isolated_filesystem():
            with patch('savior.commands.restore.ConflictDetector') as mock_detector:
                detector_instance = Mock()
                mock_detector.return_value = detector_instance
                detector_instance.detect_git_conflicts.return_value = {
                    'staged': [],
                    'modified': [],
                    'untracked': []
                }

                result = self.runner.invoke(restore, ['--check-conflicts'])

                self.assertEqual(result.exit_code, 0)
                self.assertIn('No git conflicts detected', result.output)


class TestCloudCommands(unittest.TestCase):
    """Test cloud-related CLI commands."""

    def setUp(self):
        """Set up test environment."""
        self.runner = CliRunner()

    @patch('savior.commands.cloud.CloudStorage')
    def test_cloud_sync(self, mock_cloud_class):
        """Test cloud sync command."""
        mock_cloud = Mock()
        mock_cloud_class.return_value = mock_cloud
        mock_cloud.load_config.return_value = True
        mock_cloud.sync_to_cloud.return_value = 3
        mock_cloud.sync_from_cloud.return_value = 2

        with self.runner.isolated_filesystem():
            # Create .savior directory
            Path('.savior').mkdir()

            result = self.runner.invoke(cloud, ['sync'])

            self.assertEqual(result.exit_code, 0)
            self.assertIn('Uploaded 3', result.output)
            self.assertIn('Downloaded 2', result.output)

    @patch('savior.commands.cloud.CloudStorage')
    def test_cloud_not_configured(self, mock_cloud_class):
        """Test cloud command when not configured."""
        mock_cloud = Mock()
        mock_cloud_class.return_value = mock_cloud
        mock_cloud.load_config.return_value = False

        with self.runner.isolated_filesystem():
            result = self.runner.invoke(cloud, ['sync'])

            self.assertEqual(result.exit_code, 0)
            self.assertIn('not configured', result.output)

    @patch('savior.commands.cloud.CloudStorage')
    def test_cloud_list(self, mock_cloud_class):
        """Test cloud list command."""
        mock_cloud = Mock()
        mock_cloud_class.return_value = mock_cloud
        mock_cloud.load_config.return_value = True
        mock_cloud.list_backups.return_value = [
            {'name': 'backup1.tar.gz', 'size': 1024 * 1024},
            {'name': 'backup2.tar.gz', 'size': 2048 * 1024}
        ]

        with self.runner.isolated_filesystem():
            result = self.runner.invoke(cloud, ['list'])

            self.assertEqual(result.exit_code, 0)
            self.assertIn('backup1.tar.gz', result.output)
            self.assertIn('backup2.tar.gz', result.output)


class TestCommandIntegration(unittest.TestCase):
    """Integration tests for command modules."""

    def setUp(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.test_dir = Path(tempfile.mkdtemp(prefix='test_integration_'))

    def tearDown(self):
        """Clean up test environment."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_full_backup_restore_workflow(self):
        """Test complete backup and restore workflow."""
        with self.runner.isolated_filesystem():
            # Create test project
            Path('src').mkdir()
            Path('src/main.py').write_text('print("hello")')
            Path('README.md').write_text('# Test')

            # Initialize Savior
            from savior.core import Savior
            savior = Savior(Path.cwd())

            # Create backup using CLI
            result = self.runner.invoke(save, ['Initial backup', '--no-progress'])
            self.assertEqual(result.exit_code, 0)

            # List backups
            result = self.runner.invoke(list_backups)
            self.assertEqual(result.exit_code, 0)
            self.assertIn('Initial backup', result.output)

            # Check status
            result = self.runner.invoke(status)
            self.assertEqual(result.exit_code, 0)

    def test_cli_error_handling(self):
        """Test CLI error handling."""
        with self.runner.isolated_filesystem():
            # Try to restore without any backups
            result = self.runner.invoke(restore)

            # Should handle gracefully
            self.assertEqual(result.exit_code, 0)
            self.assertIn('No backups found', result.output)

            # Try to list in directory without .savior
            result = self.runner.invoke(list_backups)
            self.assertEqual(result.exit_code, 0)


class TestCliImportStructure(unittest.TestCase):
    """Test the modular import structure."""

    def test_command_imports(self):
        """Test that all commands can be imported."""
        try:
            from savior.commands import (
                watch, save, stop, status,
                restore, list, purge,
                cloud
            )
        except ImportError as e:
            self.fail(f"Failed to import commands: {e}")

    def test_utils_imports(self):
        """Test that CLI utils can be imported."""
        try:
            from savior.cli_utils import (
                format_time_ago,
                format_size,
                print_success,
                print_error
            )
        except ImportError as e:
            self.fail(f"Failed to import CLI utils: {e}")

    def test_command_module_structure(self):
        """Test the command module structure."""
        from savior import commands

        # Check that package has expected modules
        self.assertTrue(hasattr(commands, 'backup'))
        self.assertTrue(hasattr(commands, 'restore'))
        self.assertTrue(hasattr(commands, 'cloud'))
        self.assertTrue(hasattr(commands, 'recovery'))


if __name__ == '__main__':
    unittest.main()