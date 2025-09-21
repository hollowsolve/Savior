"""Backup-related CLI commands."""

import click
import time
import sys
from pathlib import Path
from datetime import datetime
from colorama import Fore

from ..core import Savior
from ..core_dedup import SaviorWithDedup
from ..cli_utils import (
    print_success, print_error, print_warning, print_info,
    format_time_ago, format_size, check_keyboard_input
)
from ..activity import SmartWatcher
from ..incremental import IncrementalBackup
from ..dedup import SmartDeduplicator


@click.command()
@click.option('--interval', '-i', default=20, help='Backup interval in minutes')
@click.option('--no-smart', is_flag=True, help='Disable smart mode (immediate backups)')
@click.option('--full', is_flag=True, help='Force full backups instead of incremental')
@click.option('--exclude-git', is_flag=True, help='Exclude .git directory')
@click.option('--compression', '-c', type=click.IntRange(0, 9), default=6,
              help='Compression level (0=none, 9=max)')
@click.option('--ignore', multiple=True, help='Additional patterns to ignore')
@click.option('--background', '-b', is_flag=True, help='Run in background')
@click.option('--tree', is_flag=True, help='Show project structure before starting')
@click.option('--cloud', is_flag=True, help='Enable cloud backup sync')
def watch(interval, no_smart, full, exclude_git, compression, ignore, background, tree, cloud):
    """Start watching for changes and auto-backup."""
    project_dir = Path.cwd()

    # Create Savior instance with cloud support if requested
    savior = Savior(
        project_dir,
        exclude_git=exclude_git,
        extra_ignores=list(ignore),
        enable_cloud=cloud
    )

    # Show tree if requested
    if tree:
        print_info("Project Structure:")
        click.echo(savior.get_project_tree(max_depth=3))
        click.echo()

    if background:
        # Fork to background
        if sys.platform != 'win32':
            import os
            pid = os.fork()
            if pid > 0:
                print_success(f"Started watching in background (PID: {pid})")
                sys.exit(0)
        else:
            print_error("Background mode not supported on Windows")
            return

    # Create initial backup
    print_info("Creating initial backup...")
    backup = savior.create_backup("Initial backup", compression_level=compression)

    if backup:
        print_success(f"Initial backup created ({format_size(backup.size)})")
    else:
        print_error("Failed to create initial backup")
        return

    # Setup smart watcher if enabled
    if not no_smart:
        watcher = SmartWatcher(
            project_dir,
            backup_interval=interval * 60,
            compression_level=compression,
            use_incremental=not full,
            exclude_git=exclude_git
        )

        print_success(f"Savior is now watching your project")
        print_info(f"Will save after {interval} minutes of work + 2 seconds of inactivity")

        if cloud:
            print_info("☁️ Cloud sync enabled")

        # Start monitoring
        watcher.start()

        try:
            while True:
                time.sleep(1)
                if check_keyboard_input():
                    click.echo("\nStopping watch...")
                    break
        except KeyboardInterrupt:
            click.echo("\nStopping watch...")
        finally:
            watcher.stop()
    else:
        # Basic interval-based watching
        print_success(f"Savior is now watching your project (basic mode)")
        print_info(f"Backups every {interval} minutes")

        try:
            while True:
                time.sleep(interval * 60)
                backup = savior.create_backup(
                    "Automatic backup",
                    compression_level=compression
                )
                if backup:
                    print_success(f"Backup saved ({format_size(backup.size)})")

                if check_keyboard_input():
                    click.echo("\nStopping watch...")
                    break
        except KeyboardInterrupt:
            click.echo("\nStopping watch...")


@click.command()
@click.argument('description', default='Manual backup')
@click.option('--compression', '-c', type=click.IntRange(0, 9), default=6,
              help='Compression level (0=none, 9=max)')
@click.option('--tree', is_flag=True, help='Show what will be backed up')
@click.option('--no-progress', is_flag=True, help='Disable progress bar')
def save(description, compression, tree, no_progress):
    """Create a backup right now."""
    project_dir = Path.cwd()
    savior = Savior(project_dir)

    # Show tree if requested
    if tree:
        print_info("Files to backup:")
        click.echo(savior.get_project_tree(max_depth=3))
        click.echo()

        if not click.confirm('Proceed with backup?'):
            return

    # Create backup
    print_info(f"Creating backup: \"{description}\"")

    backup = savior.create_backup(
        description,
        compression_level=compression,
        show_progress=not no_progress
    )

    if backup:
        print_success(f"Saved backup: \"{description}\"")
        click.echo(f"  Size: {format_size(backup.size)}")
        click.echo(f"  Compression: level {compression}")

        # Show deduplication stats if available
        try:
            from ..dedup import DeduplicationStore
            dedup_store = DeduplicationStore(project_dir / '.savior')
            stats = dedup_store.get_dedup_stats()
            if stats['dedup_ratio'] > 0:
                click.echo(f"  Deduplication: {stats['dedup_ratio']:.1%} saved")
        except:
            pass
    else:
        print_error("Backup failed")


@click.command()
def stop():
    """Stop watching the current project."""
    project_dir = Path.cwd()
    savior = Savior(project_dir)

    metadata = savior._load_metadata()
    if metadata.get('watching'):
        metadata['watching'] = False
        savior._save_metadata(metadata)
        print_success("Stopped watching project")
    else:
        print_info("Project is not being watched")


@click.command()
def status():
    """Check if Savior is watching this project."""
    project_dir = Path.cwd()
    backup_dir = project_dir / '.savior'

    if not backup_dir.exists():
        print_info("Savior is not initialized in this project")
        return

    savior = Savior(project_dir)
    metadata = savior._load_metadata()

    if metadata.get('watching'):
        print_success("Savior is actively watching this project")
    else:
        print_info("Savior is not currently watching")

    # Show backup stats
    backups = savior.list_backups()
    if backups:
        click.echo(f"\n{Fore.CYAN}Backup Statistics:")
        click.echo(f"  Total backups: {len(backups)}")

        total_size = sum(b.size for b in backups)
        click.echo(f"  Total size: {format_size(total_size)}")

        latest = backups[0]
        click.echo(f"  Latest: {format_time_ago(latest.timestamp)}")

        # Show deduplication stats if available
        try:
            from ..dedup import DeduplicationStore
            dedup_store = DeduplicationStore(backup_dir)
            stats = dedup_store.get_dedup_stats()
            if stats['unique_chunks'] > 0:
                click.echo(f"\n{Fore.CYAN}Deduplication Statistics:")
                click.echo(f"  Space saved: {format_size(stats['space_saved'])}")
                click.echo(f"  Dedup ratio: {stats['dedup_ratio']:.1%}")
                click.echo(f"  Unique chunks: {stats['unique_chunks']}")
        except:
            pass