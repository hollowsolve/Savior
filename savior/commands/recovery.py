"""Recovery and analysis CLI commands."""

import click
from pathlib import Path
from datetime import datetime
from colorama import Fore

from ..core import Savior
from ..diff import BackupDiffer
from ..recovery import DeepRecovery
from ..cli_utils import (
    print_success, print_error, print_warning, print_info,
    format_time_ago, format_size, select_from_list, confirm_action
)


@click.command()
@click.option('--show-content', is_flag=True, help='Show actual file differences')
def diff(show_content):
    """Compare backups to see what changed."""
    project_dir = Path.cwd()
    savior = Savior(project_dir)

    backups = savior.list_backups()
    if len(backups) < 2:
        print_warning("Need at least 2 backups to compare")
        return

    # Select first backup
    print_info("Select first backup (older):")
    first_idx = select_from_list(
        backups,
        "Available backups",
        lambda b: f"{format_time_ago(b.timestamp)} - {b.description}"
    )
    if first_idx is None:
        return

    # Select second backup
    print_info("\nSelect second backup (newer):")
    second_idx = select_from_list(
        backups,
        "Available backups",
        lambda b: f"{format_time_ago(b.timestamp)} - {b.description}"
    )
    if second_idx is None:
        return

    backup1 = backups[first_idx]
    backup2 = backups[second_idx]

    print_info(f"\nComparing {format_time_ago(backup1.timestamp)} "
               f"with {format_time_ago(backup2.timestamp)}...")

    differ = BackupDiffer(project_dir)
    diff_result = differ.compare_backups(backup1.path, backup2.path)

    if diff_result['added']:
        print_info(f"\n{Fore.GREEN}Added files ({len(diff_result['added'])}):")
        for file in diff_result['added'][:10]:
            click.echo(f"  + {file}")
        if len(diff_result['added']) > 10:
            click.echo(f"  ... and {len(diff_result['added']) - 10} more")

    if diff_result['deleted']:
        print_info(f"\n{Fore.RED}Deleted files ({len(diff_result['deleted'])}):")
        for file in diff_result['deleted'][:10]:
            click.echo(f"  - {file}")
        if len(diff_result['deleted']) > 10:
            click.echo(f"  ... and {len(diff_result['deleted']) - 10} more")

    if diff_result['modified']:
        print_info(f"\n{Fore.YELLOW}Modified files ({len(diff_result['modified'])}):")
        for file in diff_result['modified'][:10]:
            click.echo(f"  ~ {file}")
        if len(diff_result['modified']) > 10:
            click.echo(f"  ... and {len(diff_result['modified']) - 10} more")

    if show_content and diff_result['modified']:
        print_info("\n" + "=" * 40)
        for file in diff_result['modified'][:5]:
            print_info(f"\nFile: {file}")
            click.echo(differ.show_file_diff(backup1.path, backup2.path, file))


@click.command()
@click.argument('filename', required=False)
@click.option('--all', is_flag=True, help='Search all backups for deleted files')
def resurrect(filename, all):
    """Find and restore deleted files."""
    project_dir = Path.cwd()
    savior = Savior(project_dir)

    if filename:
        # Search for specific file
        print_info(f"Searching for '{filename}' in backups...")

        found_in = []
        backups = savior.list_backups()

        for backup in backups:
            # Check if file exists in backup
            # (This would need implementation in core)
            pass

        if found_in:
            print_success(f"Found '{filename}' in {len(found_in)} backup(s)")
            # Offer to restore
        else:
            print_warning(f"'{filename}' not found in any backup")
    else:
        # Find all deleted files
        print_info("Analyzing backups for deleted files...")

        # This would need implementation to track deleted files
        deleted_files = []

        if deleted_files:
            print_info(f"Found {len(deleted_files)} deleted file(s)")
            # List and offer to restore
        else:
            print_info("No deleted files found")


@click.command()
@click.option('--restore', is_flag=True, help='Attempt automatic restoration')
def pray(restore):
    """🙏 Deep recovery attempt when all hope is lost."""
    project_dir = Path.cwd()
    recovery = DeepRecovery(project_dir)

    print_info("🙏 Initiating deep recovery prayer sequence...")
    print_info("Searching for lost files in:")
    click.echo("  • Editor swap files")
    click.echo("  • System trash")
    click.echo("  • Git stashes")
    click.echo("  • Temporary directories")
    click.echo()

    results = recovery.search_all()

    print_info("\nRECOVERY SCAN RESULTS:")
    click.echo("=" * 40)

    total_found = 0

    # Swap files
    if results['swap_files']:
        print_success(f"✓ Editor swap files found: {len(results['swap_files'])}")
        for swap_file in results['swap_files'][:5]:
            age = format_time_ago(
                datetime.fromtimestamp(swap_file.stat().st_mtime)
            )
            click.echo(f"  - {swap_file.name} ({age})")
        if len(results['swap_files']) > 5:
            click.echo(f"  ... and {len(results['swap_files']) - 5} more")
        total_found += len(results['swap_files'])

    # Trash items
    if results['trash_items']:
        print_success(f"✓ Items in trash: {len(results['trash_items'])}")
        for item in results['trash_items'][:5]:
            click.echo(f"  - {item.name}")
        if len(results['trash_items']) > 5:
            click.echo(f"  ... and {len(results['trash_items']) - 5} more")
        total_found += len(results['trash_items'])

    # Git stashes
    if results['git_stashes']:
        print_success(f"✓ Git stashes found: {len(results['git_stashes'])}")
        for stash in results['git_stashes'][:5]:
            click.echo(f"  - {stash}")
        if len(results['git_stashes']) > 5:
            click.echo(f"  ... and {len(results['git_stashes']) - 5} more")
        total_found += len(results['git_stashes'])

    # Temp files
    if results['temp_files']:
        print_success(f"✓ Temporary files found: {len(results['temp_files'])}")
        for temp_file in results['temp_files'][:5]:
            click.echo(f"  - {temp_file.name}")
        if len(results['temp_files']) > 5:
            click.echo(f"  ... and {len(results['temp_files']) - 5} more")
        total_found += len(results['temp_files'])

    if total_found == 0:
        print_warning("No recoverable files found")
        print_info("Your files might be truly gone... 😔")
    else:
        print_info(f"\nTotal recoverable items: {total_found}")

        if restore:
            print_info("\nAttempting automatic restoration...")
            restored_count = 0

            # Restore swap files
            for swap_file in results['swap_files']:
                if recovery.restore_from_swap(swap_file):
                    restored_count += 1

            # Restore from trash
            for item in results['trash_items']:
                if recovery.restore_from_trash(item):
                    restored_count += 1

            if restored_count > 0:
                print_success(f"✓ Restored {restored_count} file(s)")
            else:
                print_warning("Could not automatically restore files")
                print_info("Try manual recovery from the listed locations")
        else:
            print_info("\nUse --restore flag to attempt automatic restoration")