import hashlib
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
import configparser


class CloudStorage:
    """
    Self-hosted cloud storage integration
    Supports S3-compatible storage (MinIO, Wasabi, Backblaze B2, etc.)
    """

    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file or Path.home() / '.savior' / 'cloud.conf'
        self.config = self._load_config()
        self.client = None
        self._init_client()

    def _load_config(self) -> Dict:
        """Load cloud configuration from file"""
        if not self.config_file.exists():
            return {}

        config = configparser.ConfigParser()
        config.read(self.config_file)

        return {
            'endpoint': config.get('cloud', 'endpoint', fallback=''),
            'access_key': config.get('cloud', 'access_key', fallback=''),
            'secret_key': config.get('cloud', 'secret_key', fallback=''),
            'bucket': config.get('cloud', 'bucket', fallback='savior-backups'),
            'encrypt': config.getboolean('cloud', 'encrypt', fallback=True),
            'provider': config.get('cloud', 'provider', fallback='s3'),  # aws, gcs, azure, s3, minio, backblaze, etc.
            'region': config.get('cloud', 'region', fallback='us-east-1'),
            'project_id': config.get('cloud', 'project_id', fallback=''),  # For GCS
            'auto_sync': config.getboolean('cloud', 'auto_sync', fallback=False)
        }

    def _init_client(self):
        """Initialize storage client based on provider"""
        provider = self.config.get('provider', 's3')

        # AWS S3 doesn't need endpoint
        if provider == 'aws':
            self._init_aws_s3()
        elif provider == 'gcs':
            self._init_gcs()
        elif provider == 'azure':
            self._init_azure_blob()
        elif provider in ['s3', 'minio', 'wasabi', 'backblaze']:
            if self.config.get('endpoint'):
                self._init_s3_compatible()
        elif provider == 'local':
            self._init_local_storage()

    def _init_aws_s3(self):
        """Initialize AWS S3 client"""
        try:
            import boto3

            self.client = boto3.client(
                's3',
                aws_access_key_id=self.config['access_key'],
                aws_secret_access_key=self.config['secret_key'],
                region_name=self.config.get('region', 'us-east-1')
            )

            # Create bucket if it doesn't exist
            try:
                self.client.head_bucket(Bucket=self.config['bucket'])
            except:
                # Create bucket with location constraint if not us-east-1
                if self.config.get('region') != 'us-east-1':
                    self.client.create_bucket(
                        Bucket=self.config['bucket'],
                        CreateBucketConfiguration={'LocationConstraint': self.config['region']}
                    )
                else:
                    self.client.create_bucket(Bucket=self.config['bucket'])

        except ImportError:
            print("boto3 not installed. Run: pip install boto3")
        except Exception as e:
            print(f"Failed to initialize AWS S3: {e}")

    def _init_gcs(self):
        """Initialize Google Cloud Storage client"""
        try:
            from google.cloud import storage

            # Use service account key if provided, otherwise use default credentials
            if self.config.get('secret_key'):
                # secret_key contains path to service account JSON
                self.client = storage.Client.from_service_account_json(
                    self.config['secret_key'],
                    project=self.config.get('project_id')
                )
            else:
                # Use default credentials (gcloud auth)
                self.client = storage.Client(project=self.config.get('project_id'))

            # Get or create bucket
            try:
                self.bucket = self.client.get_bucket(self.config['bucket'])
            except:
                self.bucket = self.client.create_bucket(
                    self.config['bucket'],
                    location=self.config.get('region', 'US')
                )

        except ImportError:
            print("google-cloud-storage not installed. Run: pip install google-cloud-storage")
        except Exception as e:
            print(f"Failed to initialize Google Cloud Storage: {e}")

    def _init_azure_blob(self):
        """Initialize Azure Blob Storage client"""
        try:
            from azure.storage.blob import BlobServiceClient

            # Connection string format: DefaultEndpointsProtocol=https;AccountName=xxx;AccountKey=xxx;EndpointSuffix=core.windows.net
            if 'DefaultEndpoints' in self.config.get('access_key', ''):
                # Using connection string
                self.client = BlobServiceClient.from_connection_string(self.config['access_key'])
            else:
                # Using account key
                account_url = f"https://{self.config['endpoint']}.blob.core.windows.net"
                self.client = BlobServiceClient(
                    account_url=account_url,
                    credential=self.config['secret_key']
                )

            # Get or create container
            self.container = self.client.get_container_client(self.config['bucket'])
            if not self.container.exists():
                self.container.create_container()

        except ImportError:
            print("azure-storage-blob not installed. Run: pip install azure-storage-blob")
        except Exception as e:
            print(f"Failed to initialize Azure Blob Storage: {e}")

    def _init_s3_compatible(self):
        """Initialize S3-compatible storage client"""
        try:
            import boto3
            from botocore.client import Config

            self.client = boto3.client(
                's3',
                endpoint_url=self.config['endpoint'],
                aws_access_key_id=self.config['access_key'],
                aws_secret_access_key=self.config['secret_key'],
                config=Config(signature_version='s3v4')
            )

            # Create bucket if it doesn't exist
            try:
                self.client.head_bucket(Bucket=self.config['bucket'])
            except:
                self.client.create_bucket(Bucket=self.config['bucket'])

        except ImportError:
            print("boto3 not installed. Run: pip install boto3")
        except Exception as e:
            print(f"Failed to initialize cloud storage: {e}")

    def _init_local_storage(self):
        """Initialize local network storage (NAS, shared drive)"""
        storage_path = Path(self.config['endpoint'])
        if storage_path.exists():
            self.client = LocalStorageClient(storage_path)

    def is_configured(self) -> bool:
        """Check if cloud storage is configured"""
        return self.client is not None

    def upload_backup(self, backup_path: Path, project_name: str) -> bool:
        """Upload a backup to cloud storage"""
        if not self.client:
            return False

        try:
            # Generate cloud path
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            cloud_key = f"{project_name}/{backup_path.name}"

            # Calculate checksum
            checksum = self._calculate_checksum(backup_path)

            # Encrypt if enabled
            if self.config.get('encrypt'):
                backup_data = self._encrypt_backup(backup_path)
            else:
                with open(backup_path, 'rb') as f:
                    backup_data = f.read()

            # Upload to cloud
            provider = self.config.get('provider')

            if provider in ['aws', 's3', 'minio', 'wasabi', 'backblaze']:
                self.client.put_object(
                    Bucket=self.config['bucket'],
                    Key=cloud_key,
                    Body=backup_data,
                    Metadata={
                        'checksum': checksum,
                        'project': project_name,
                        'timestamp': timestamp
                    }
                )
            elif provider == 'gcs':
                blob = self.bucket.blob(cloud_key)
                blob.metadata = {
                    'checksum': checksum,
                    'project': project_name,
                    'timestamp': timestamp
                }
                blob.upload_from_string(backup_data)
            elif provider == 'azure':
                blob_client = self.container.get_blob_client(cloud_key)
                blob_client.upload_blob(
                    backup_data,
                    overwrite=True,
                    metadata={
                        'checksum': checksum,
                        'project': project_name,
                        'timestamp': timestamp
                    }
                )
            else:
                # Local storage
                self.client.save(cloud_key, backup_data)

            return True

        except Exception as e:
            print(f"Upload failed: {e}")
            return False

    def download_backup(self, cloud_key: str, destination: Path) -> bool:
        """Download a backup from cloud storage"""
        if not self.client:
            return False

        try:
            provider = self.config.get('provider')

            if provider in ['aws', 's3', 'minio', 'wasabi', 'backblaze']:
                response = self.client.get_object(
                    Bucket=self.config['bucket'],
                    Key=cloud_key
                )
                backup_data = response['Body'].read()
            elif provider == 'gcs':
                blob = self.bucket.blob(cloud_key)
                backup_data = blob.download_as_bytes()
            elif provider == 'azure':
                blob_client = self.container.get_blob_client(cloud_key)
                backup_data = blob_client.download_blob().readall()
            else:
                # Local storage
                backup_data = self.client.load(cloud_key)

            # Decrypt if needed
            if self.config.get('encrypt'):
                backup_data = self._decrypt_backup(backup_data)

            # Save to destination
            with open(destination, 'wb') as f:
                f.write(backup_data)

            return True

        except Exception as e:
            print(f"Download failed: {e}")
            return False

    def list_backups(self, project_name: str) -> List[Dict]:
        """List all backups for a project in cloud storage"""
        if not self.client:
            return []

        try:
            backups = []

            if hasattr(self.client, 'list_objects_v2'):
                response = self.client.list_objects_v2(
                    Bucket=self.config['bucket'],
                    Prefix=f"{project_name}/"
                )

                for obj in response.get('Contents', []):
                    backups.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'modified': obj['LastModified'],
                        'metadata': obj.get('Metadata', {})
                    })
            else:
                # Local storage
                backups = self.client.list(project_name)

            return backups

        except Exception as e:
            print(f"List failed: {e}")
            return []

    def sync_backups(self, local_backup_dir: Path, project_name: str) -> Dict:
        """Sync local backups with cloud storage"""
        if not self.client:
            return {'error': 'Cloud storage not configured'}

        results = {
            'uploaded': 0,
            'downloaded': 0,
            'errors': []
        }

        try:
            # Get local backups
            local_backups = set()
            for backup in local_backup_dir.glob('*.tar.gz'):
                local_backups.add(backup.name)

            # Get cloud backups
            cloud_backups = self.list_backups(project_name)
            cloud_names = {b['key'].split('/')[-1] for b in cloud_backups}

            # Upload missing backups to cloud
            for backup_name in local_backups - cloud_names:
                backup_path = local_backup_dir / backup_name
                if self.upload_backup(backup_path, project_name):
                    results['uploaded'] += 1
                else:
                    results['errors'].append(f"Failed to upload {backup_name}")

            # Download missing backups from cloud
            for backup_name in cloud_names - local_backups:
                cloud_key = f"{project_name}/{backup_name}"
                destination = local_backup_dir / backup_name
                if self.download_backup(cloud_key, destination):
                    results['downloaded'] += 1
                else:
                    results['errors'].append(f"Failed to download {backup_name}")

            return results

        except Exception as e:
            return {'error': str(e)}

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _encrypt_backup(self, backup_path: Path) -> bytes:
        """Encrypt backup data (implement with cryptography library)"""
        # For now, just return the raw data
        # In production, use: from cryptography.fernet import Fernet
        with open(backup_path, 'rb') as f:
            return f.read()

    def _decrypt_backup(self, encrypted_data: bytes) -> bytes:
        """Decrypt backup data"""
        # For now, just return as-is
        return encrypted_data

    def setup_wizard(self):
        """Interactive setup wizard for cloud configuration"""
        print("🌥️  Savior Cloud Setup Wizard")
        print("=" * 40)
        print("\nChoose your storage provider:")
        print("1. AWS S3")
        print("2. Google Cloud Storage")
        print("3. Azure Blob Storage")
        print("4. MinIO (self-hosted S3)")
        print("5. Backblaze B2")
        print("6. Wasabi")
        print("7. Local NAS/Network Drive")
        print("8. Custom S3-compatible")

        choice = input("\nEnter choice (1-8): ")

        config = configparser.ConfigParser()
        config['cloud'] = {}

        if choice == '1':  # AWS S3
            config['cloud']['provider'] = 'aws'
            config['cloud']['access_key'] = input("AWS Access Key ID: ")
            config['cloud']['secret_key'] = input("AWS Secret Access Key: ")
            config['cloud']['region'] = input("AWS Region (default: us-east-1): ") or 'us-east-1'
            config['cloud']['bucket'] = input("Bucket name (default: savior-backups): ") or 'savior-backups'

        elif choice == '2':  # Google Cloud Storage
            config['cloud']['provider'] = 'gcs'
            config['cloud']['project_id'] = input("GCP Project ID: ")
            key_path = input("Path to service account key JSON (or press Enter to use gcloud auth): ")
            if key_path:
                config['cloud']['secret_key'] = key_path
            config['cloud']['bucket'] = input("Bucket name (default: savior-backups): ") or 'savior-backups'
            config['cloud']['region'] = input("Region (default: US): ") or 'US'

        elif choice == '3':  # Azure Blob Storage
            config['cloud']['provider'] = 'azure'
            conn_or_key = input("Use connection string (c) or account key (k)? ")
            if conn_or_key.lower() == 'c':
                config['cloud']['access_key'] = input("Azure Connection String: ")
            else:
                config['cloud']['endpoint'] = input("Storage Account Name: ")
                config['cloud']['secret_key'] = input("Account Key: ")
            config['cloud']['bucket'] = input("Container name (default: savior-backups): ") or 'savior-backups'

        elif choice in ['4', '5', '6', '8']:  # S3-compatible
            config['cloud']['provider'] = {
                '4': 'minio',
                '5': 'backblaze',
                '6': 'wasabi',
                '8': 's3'
            }[choice]
            config['cloud']['endpoint'] = input("Endpoint URL: ")
            config['cloud']['access_key'] = input("Access Key: ")
            config['cloud']['secret_key'] = input("Secret Key: ")
            config['cloud']['bucket'] = input("Bucket name (default: savior-backups): ") or 'savior-backups'

        elif choice == '7':  # Local NAS
            config['cloud']['provider'] = 'local'
            config['cloud']['endpoint'] = input("Network path (e.g., /mnt/nas/backups): ")

        # Common options
        if choice != '7':
            config['cloud']['encrypt'] = input("Encrypt backups? (y/n): ").lower() == 'y'
            config['cloud']['auto_sync'] = input("Auto-sync with cloud after each backup? (y/n): ").lower() == 'y'

        # Save configuration
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            config.write(f)

        print(f"\n✓ Configuration saved to {self.config_file}")
        print("  Run 'savior cloud sync' to start syncing!")


class LocalStorageClient:
    """Simple client for local/network storage"""

    def __init__(self, base_path: Path):
        self.base_path = base_path

    def save(self, key: str, data: bytes):
        file_path = self.base_path / key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'wb') as f:
            f.write(data)

    def load(self, key: str) -> bytes:
        file_path = self.base_path / key
        with open(file_path, 'rb') as f:
            return f.read()

    def list(self, prefix: str) -> List[Dict]:
        results = []
        search_path = self.base_path / prefix
        if search_path.exists():
            for file_path in search_path.glob('*.tar.gz'):
                results.append({
                    'key': str(file_path.relative_to(self.base_path)),
                    'size': file_path.stat().st_size,
                    'modified': datetime.fromtimestamp(file_path.stat().st_mtime)
                })
        return results