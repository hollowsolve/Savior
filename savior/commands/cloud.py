"""Cloud storage related CLI commands."""

import click
from pathlib import Path
from colorama import Fore

from ..cloud import CloudStorage
from ..core import Savior
from ..cli_utils import (
    print_success, print_error, print_warning, print_info,
    format_size, confirm_action, select_from_list
)


@click.group()
def cloud():
    """Cloud backup management commands."""
    pass


@cloud.command()
def setup():
    """Configure cloud storage provider."""
    print_info("🌥️  Savior Cloud Setup Wizard")
    click.echo("=" * 40)

    providers = [
        ("AWS S3", "s3"),
        ("Google Cloud Storage", "gcs"),
        ("Azure Blob Storage", "azure"),
        ("MinIO (self-hosted S3)", "minio"),
        ("Backblaze B2", "b2"),
        ("Wasabi", "wasabi"),
        ("Local NAS/Network Drive", "local"),
        ("Custom S3-compatible", "custom")
    ]

    # Select provider
    print_info("\nChoose your storage provider:")
    for i, (name, _) in enumerate(providers, 1):
        click.echo(f"{i}. {name}")

    choice = click.prompt('\nEnter choice (1-8)', type=int)

    if not 1 <= choice <= len(providers):
        print_error("Invalid choice")
        return

    provider_name, provider_type = providers[choice - 1]
    print_info(f"\nConfiguring {provider_name}...")

    cloud_storage = CloudStorage()

    # Get provider-specific configuration
    config = {}

    if provider_type in ['s3', 'custom', 'wasabi', 'minio']:
        config['access_key'] = click.prompt('AWS Access Key ID', hide_input=True)
        config['secret_key'] = click.prompt('AWS Secret Access Key', hide_input=True)
        config['region'] = click.prompt('AWS Region', default='us-east-1')
        config['bucket'] = click.prompt('Bucket name', default='savior-backups')

        if provider_type == 'minio':
            config['endpoint'] = click.prompt('MinIO endpoint URL')
        elif provider_type == 'custom':
            config['endpoint'] = click.prompt('S3-compatible endpoint URL')

    elif provider_type == 'gcs':
        config['credentials_path'] = click.prompt('Path to service account JSON')
        config['bucket'] = click.prompt('Bucket name', default='savior-backups')

    elif provider_type == 'azure':
        config['account_name'] = click.prompt('Storage account name')
        config['account_key'] = click.prompt('Storage account key', hide_input=True)
        config['container'] = click.prompt('Container name', default='savior-backups')

    elif provider_type == 'b2':
        config['key_id'] = click.prompt('B2 Application Key ID')
        config['application_key'] = click.prompt('B2 Application Key', hide_input=True)
        config['bucket'] = click.prompt('Bucket name', default='savior-backups')

    elif provider_type == 'local':
        config['path'] = click.prompt('Network path or mount point')

    # Encryption option
    config['encrypt'] = confirm_action('Encrypt backups?', default=True)
    if config['encrypt']:
        config['encryption_key'] = click.prompt('Encryption passphrase', hide_input=True)

    # Auto-sync option
    config['auto_sync'] = confirm_action(
        'Auto-sync with cloud after each backup?',
        default=True
    )

    # Save configuration
    cloud_storage.provider = provider_type
    cloud_storage.config = config

    if cloud_storage.save_config():
        print_success("Configuration saved to ~/.savior/cloud.conf")

        # Test connection
        print_info("\nTesting connection...")
        if cloud_storage.test_connection():
            print_success("Successfully connected to cloud storage!")
            print_info("Run 'savior cloud sync' to start syncing!")
        else:
            print_error("Failed to connect. Please check your credentials.")
    else:
        print_error("Failed to save configuration")


@cloud.command()
@click.option('--upload-only', is_flag=True, help='Only upload to cloud')
@click.option('--download-only', is_flag=True, help='Only download from cloud')
def sync(upload_only, download_only):
    """Sync local backups with cloud storage."""
    project_dir = Path.cwd()
    backup_dir = project_dir / '.savior'

    cloud_storage = CloudStorage()
    if not cloud_storage.load_config():
        print_error("Cloud storage not configured. Run 'savior cloud setup' first.")
        return

    print_info("☁️  Syncing with cloud storage...")

    try:
        if download_only:
            downloaded = cloud_storage.sync_from_cloud(backup_dir)
            print_success(f"Downloaded {downloaded} backup(s) from cloud")
        elif upload_only:
            uploaded = cloud_storage.sync_to_cloud(backup_dir)
            print_success(f"Uploaded {uploaded} backup(s) to cloud")
        else:
            # Full sync
            uploaded = cloud_storage.sync_to_cloud(backup_dir)
            downloaded = cloud_storage.sync_from_cloud(backup_dir)
            print_success(f"✓ Uploaded {uploaded} new backup(s) to cloud")
            print_success(f"✓ Downloaded {downloaded} backup(s) from cloud")
            print_info("✓ Sync complete!")
    except Exception as e:
        print_error(f"Sync failed: {e}")


@cloud.command(name='list')
def list_cloud():
    """List all cloud backups."""
    cloud_storage = CloudStorage()
    if not cloud_storage.load_config():
        print_error("Cloud storage not configured. Run 'savior cloud setup' first.")
        return

    print_info("☁️  Fetching cloud backups...")

    try:
        backups = cloud_storage.list_backups()

        if not backups:
            print_info("No backups in cloud storage")
            return

        print_info(f"Cloud backups for {Path.cwd().name}:")

        total_size = 0
        for backup in backups[:20]:
            click.echo(f"  {backup['name']} - {format_size(backup['size'])}")
            total_size += backup['size']

        if len(backups) > 20:
            click.echo(f"  ... and {len(backups) - 20} more")

        print_info(f"\nTotal: {len(backups)} backups, {format_size(total_size)}")
    except Exception as e:
        print_error(f"Failed to list backups: {e}")


@cloud.command()
@click.argument('backup_name')
def download(backup_name):
    """Download a specific backup from cloud."""
    project_dir = Path.cwd()
    backup_dir = project_dir / '.savior'

    cloud_storage = CloudStorage()
    if not cloud_storage.load_config():
        print_error("Cloud storage not configured. Run 'savior cloud setup' first.")
        return

    print_info(f"Downloading {backup_name}...")

    try:
        local_path = backup_dir / backup_name
        if cloud_storage.download_backup(backup_name, local_path):
            size = local_path.stat().st_size
            print_success(f"Downloaded {backup_name} ({format_size(size)})")
        else:
            print_error(f"Failed to download {backup_name}")
    except Exception as e:
        print_error(f"Download failed: {e}")


@cloud.command()
@click.option('--force', is_flag=True, help='Force delete without confirmation')
def clear(force):
    """Clear all cloud backups for this project."""
    cloud_storage = CloudStorage()
    if not cloud_storage.load_config():
        print_error("Cloud storage not configured. Run 'savior cloud setup' first.")
        return

    project_name = Path.cwd().name

    print_warning(f"This will delete ALL cloud backups for '{project_name}'")

    if not force and not confirm_action("Are you sure?"):
        return

    print_info("Clearing cloud backups...")

    try:
        deleted = cloud_storage.clear_project_backups(project_name)
        print_success(f"Deleted {deleted} cloud backup(s)")
    except Exception as e:
        print_error(f"Clear failed: {e}")