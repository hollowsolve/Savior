import unittest
from unittest.mock import Mock, MagicMock, patch, mock_open, ANY
from pathlib import Path
import tempfile
import shutil
import json
import configparser
from datetime import datetime
import sys

from savior.cloud import CloudStorage, LocalStorageClient


class TestCloudStorage(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.config_file = self.test_dir / 'cloud.conf'
        self.backup_file = self.test_dir / 'test_backup.tar.gz'

        # Create test backup file
        self.backup_file.write_bytes(b'test backup content')

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def create_config(self, provider='aws', **kwargs):
        """Helper to create a config file"""
        config = configparser.ConfigParser()
        config['cloud'] = {
            'provider': provider,
            'access_key': kwargs.get('access_key', 'test_key'),
            'secret_key': kwargs.get('secret_key', 'test_secret'),
            'bucket': kwargs.get('bucket', 'test-bucket'),
            'region': kwargs.get('region', 'us-east-1'),
            'endpoint': kwargs.get('endpoint', ''),
            'encrypt': str(kwargs.get('encrypt', False)),
            'auto_sync': str(kwargs.get('auto_sync', True))
        }

        with open(self.config_file, 'w') as f:
            config.write(f)

    def test_load_config_no_file(self):
        """Test loading config when file doesn't exist"""
        storage = CloudStorage(config_file=self.test_dir / 'nonexistent.conf')
        self.assertEqual(storage.config, {})
        self.assertIsNone(storage.client)

    def test_load_config_with_file(self):
        """Test loading config from file"""
        self.create_config(provider='aws')
        storage = CloudStorage(config_file=self.config_file)

        self.assertEqual(storage.config['provider'], 'aws')
        self.assertEqual(storage.config['access_key'], 'test_key')
        self.assertEqual(storage.config['bucket'], 'test-bucket')
        self.assertTrue(storage.config['auto_sync'])

    def test_init_local_storage(self):
        """Test local storage client initialization"""
        storage_path = self.test_dir / 'local_storage'
        storage_path.mkdir(exist_ok=True)
        self.create_config(provider='local', endpoint=str(storage_path))

        storage = CloudStorage(config_file=self.config_file)
        self.assertIsInstance(storage.client, LocalStorageClient)

    def test_upload_backup_with_mock_client(self):
        """Test uploading backup with mocked client"""
        self.create_config(provider='aws')
        storage = CloudStorage(config_file=self.config_file)

        # Mock the client
        mock_client = MagicMock()
        storage.client = mock_client
        storage.config['provider'] = 'aws'

        result = storage.upload_backup(self.backup_file, 'test-project')

        self.assertTrue(result)
        mock_client.put_object.assert_called_once()
        call_kwargs = mock_client.put_object.call_args[1]
        self.assertEqual(call_kwargs['Bucket'], 'test-bucket')
        self.assertIn('test-project/', call_kwargs['Key'])

    def test_download_backup_with_mock_client(self):
        """Test downloading backup with mocked client"""
        self.create_config(provider='aws')
        storage = CloudStorage(config_file=self.config_file)

        # Mock the client
        mock_client = MagicMock()
        mock_response = {'Body': MagicMock(read=lambda: b'backup content')}
        mock_client.get_object.return_value = mock_response
        storage.client = mock_client
        storage.config['provider'] = 'aws'

        dest = self.test_dir / 'downloaded.tar.gz'
        result = storage.download_backup('test-project/backup.tar.gz', dest)

        self.assertTrue(result)
        self.assertTrue(dest.exists())
        self.assertEqual(dest.read_bytes(), b'backup content')

    def test_list_backups_with_mock_client(self):
        """Test listing backups with mocked client"""
        self.create_config(provider='aws')
        storage = CloudStorage(config_file=self.config_file)

        # Mock the client
        mock_client = MagicMock()
        mock_response = {
            'Contents': [
                {
                    'Key': 'test-project/backup1.tar.gz',
                    'Size': 1024,
                    'LastModified': datetime.now()
                },
                {
                    'Key': 'test-project/backup2.tar.gz',
                    'Size': 2048,
                    'LastModified': datetime.now()
                }
            ]
        }
        mock_client.list_objects_v2.return_value = mock_response
        storage.client = mock_client
        storage.config['provider'] = 'aws'

        backups = storage.list_backups('test-project')

        self.assertEqual(len(backups), 2)
        self.assertEqual(backups[0]['key'], 'test-project/backup1.tar.gz')
        self.assertEqual(backups[1]['size'], 2048)

    def test_sync_backups_with_mock_client(self):
        """Test syncing local and cloud backups with mocked client"""
        self.create_config(provider='aws')
        storage = CloudStorage(config_file=self.config_file)

        # Mock the client
        mock_client = MagicMock()
        storage.client = mock_client
        storage.config['provider'] = 'aws'

        # Create local backup directory with some backups
        backup_dir = self.test_dir / 'backups'
        backup_dir.mkdir()
        (backup_dir / 'local1.tar.gz').write_bytes(b'local1')
        (backup_dir / 'local2.tar.gz').write_bytes(b'local2')

        # Mock cloud backups list
        mock_client.list_objects_v2.return_value = {
            'Contents': [
                {'Key': 'test-project/cloud1.tar.gz', 'Size': 100, 'LastModified': datetime.now()}
            ]
        }

        # Mock download
        mock_client.get_object.return_value = {
            'Body': MagicMock(read=lambda: b'cloud content')
        }

        result = storage.sync_backups(backup_dir, 'test-project')

        # Should upload 2 local files and download 1 cloud file
        self.assertEqual(result['uploaded'], 2)
        self.assertEqual(result['downloaded'], 1)
        self.assertEqual(len(result.get('errors', [])), 0)

    def test_calculate_checksum(self):
        """Test checksum calculation"""
        storage = CloudStorage(config_file=self.test_dir / 'nonexistent.conf')
        checksum = storage._calculate_checksum(self.backup_file)

        # Should be a valid SHA256 hex string
        self.assertEqual(len(checksum), 64)
        self.assertTrue(all(c in '0123456789abcdef' for c in checksum))

    def test_is_configured(self):
        """Test checking if cloud storage is configured"""
        # Not configured
        storage = CloudStorage(config_file=self.test_dir / 'nonexistent.conf')
        self.assertFalse(storage.is_configured())

        # Configured with mock client
        storage.client = MagicMock()
        self.assertTrue(storage.is_configured())

    def test_gcs_upload_with_mock(self):
        """Test Google Cloud Storage upload"""
        self.create_config(provider='gcs')
        storage = CloudStorage(config_file=self.config_file)

        # Mock GCS bucket and blob
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        storage.bucket = mock_bucket
        storage.client = MagicMock()
        storage.config['provider'] = 'gcs'

        result = storage.upload_backup(self.backup_file, 'test-project')

        self.assertTrue(result)
        mock_bucket.blob.assert_called_once()
        mock_blob.upload_from_string.assert_called_once()

    def test_azure_upload_with_mock(self):
        """Test Azure Blob Storage upload"""
        self.create_config(provider='azure')
        storage = CloudStorage(config_file=self.config_file)

        # Mock Azure container
        mock_container = MagicMock()
        mock_blob_client = MagicMock()
        mock_container.get_blob_client.return_value = mock_blob_client
        storage.container = mock_container
        storage.client = MagicMock()
        storage.config['provider'] = 'azure'

        result = storage.upload_backup(self.backup_file, 'test-project')

        self.assertTrue(result)
        mock_container.get_blob_client.assert_called_once()
        mock_blob_client.upload_blob.assert_called_once()


class TestLocalStorageClient(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.client = LocalStorageClient(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_save_and_load(self):
        """Test saving and loading data"""
        test_data = b'test data content'
        key = 'project/backup.tar.gz'

        self.client.save(key, test_data)

        file_path = self.test_dir / key
        self.assertTrue(file_path.exists())

        loaded_data = self.client.load(key)
        self.assertEqual(loaded_data, test_data)

    def test_list(self):
        """Test listing files"""
        # Create test files
        project_dir = self.test_dir / 'test-project'
        project_dir.mkdir(parents=True)
        (project_dir / 'backup1.tar.gz').write_bytes(b'data1')
        (project_dir / 'backup2.tar.gz').write_bytes(b'data2')
        (project_dir / 'other.txt').write_bytes(b'other')

        results = self.client.list('test-project')

        # Should only list .tar.gz files
        self.assertEqual(len(results), 2)
        keys = [r['key'] for r in results]
        self.assertIn('test-project/backup1.tar.gz', keys)
        self.assertIn('test-project/backup2.tar.gz', keys)


class TestCloudIntegration(unittest.TestCase):
    """Test integration with Savior core"""

    @patch('savior.core.CloudStorage')
    def test_savior_with_cloud_enabled(self, mock_cloud_storage):
        """Test Savior initialization with cloud enabled"""
        from savior.core import Savior

        mock_storage = MagicMock()
        mock_storage.is_configured.return_value = True
        mock_storage.config = {'auto_sync': True}
        mock_cloud_storage.return_value = mock_storage

        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            savior = Savior(project_dir, enable_cloud=True)

            self.assertTrue(savior.enable_cloud)
            self.assertEqual(savior.cloud_storage, mock_storage)
            mock_cloud_storage.assert_called_once()

    @patch('savior.core.CloudStorage')
    def test_backup_with_cloud_sync(self, mock_cloud_storage):
        """Test that backups are uploaded to cloud when enabled"""
        from savior.core import Savior

        mock_storage = MagicMock()
        mock_storage.is_configured.return_value = True
        mock_storage.config = {'auto_sync': True}
        mock_storage.upload_backup.return_value = True
        mock_cloud_storage.return_value = mock_storage

        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            # Create test file to backup
            (project_dir / 'test.txt').write_text('test content')

            savior = Savior(project_dir, enable_cloud=True)
            backup = savior.create_backup('test backup')

            # Check that upload was called
            mock_storage.upload_backup.assert_called_once()
            call_args = mock_storage.upload_backup.call_args[0]
            self.assertEqual(call_args[1], project_dir.name)  # project name

    def test_savior_without_cloud(self):
        """Test Savior works normally without cloud"""
        from savior.core import Savior

        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir)
            (project_dir / 'test.txt').write_text('test content')

            savior = Savior(project_dir, enable_cloud=False)

            self.assertFalse(savior.enable_cloud)
            self.assertIsNone(savior.cloud_storage)

            # Should work normally without cloud
            backup = savior.create_backup('test backup')
            self.assertTrue(backup.path.exists())


if __name__ == '__main__':
    unittest.main()