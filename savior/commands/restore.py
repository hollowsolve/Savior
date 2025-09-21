"""Restore-related CLI commands."""

import click
import tempfile
import tarfile
import shutil
import fnmatch
from pathlib import Path
from colorama import Fore

from ..core import Savior
from ..cli_utils import (
    print_success, print_error, print_warning, print_info,
    format_time_ago, format_size, select_from_list, confirm_action
)
from ..conflicts import ConflictDetector, ConflictResolver


@click.command()
@click.option('--files', help='Glob pattern for specific files to restore')
@click.option('--preview', is_flag=True, help='Preview what would be restored')
@click.option('--force', is_flag=True, help='Force restore without conflict checking')
@click.option('--no-backup', is_flag=True, help='Skip creating pre-restore safety backup')
@click.option('--check-conflicts', is_flag=True, help='Check for conflicts without restoring')
def restore(files, preview, force, no_backup, check_conflicts):
    """Restore from a backup."""
    project_dir = Path.cwd()
    savior = Savior(project_dir)

    backups = savior.list_backups()
    if not backups:
        print_warning("No backups found to restore")
        return

    # Let user select backup
    def format_backup(backup):
        return f"{format_time_ago(backup.timestamp)} - \"{backup.description}\""

    backup_index = select_from_list(backups, "Available backups", format_backup)
    if backup_index is None:
        print_error("Invalid choice")
        return

    backup = backups[backup_index]

    if files or preview:
        # Partial restore or preview
        handle_partial_restore(savior, backup, files, preview, project_dir)
    else:
        # Full restore
        handle_full_restore(
            savior, backup, backup_index,
            check_conflicts, force, no_backup, project_dir
        )


def handle_partial_restore(savior, backup, pattern, preview, project_dir):
    """Handle partial file restore or preview."""
    temp_dir = Path(tempfile.mkdtemp(prefix='savior_restore_'))

    try:
        with tarfile.open(backup.path, 'r:gz') as tar:
            tar.extractall(temp_dir)

        files_to_restore = []
        for file_path in temp_dir.rglob('*'):
            if file_path.is_file():
                rel_path = file_path.relative_to(temp_dir)

                if pattern and not fnmatch.fnmatch(str(rel_path), pattern):
                    continue

                files_to_restore.append((file_path, rel_path))

        if not files_to_restore:
            print_warning(f"No files match pattern '{pattern}'")
            return

        if preview:
            print_info("Files that would be restored:")
            for _, rel_path in files_to_restore[:20]:
                click.echo(f"  - {rel_path}")
            if len(files_to_restore) > 20:
                click.echo(f"  ... and {len(files_to_restore) - 20} more")
        else:
            print_warning(f"This will overwrite {len(files_to_restore)} file(s)!")
            if confirm_action('Are you sure?'):
                for src_file, rel_path in files_to_restore:
                    dst_file = project_dir / rel_path
                    dst_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dst_file)

                print_success(f"Restored {len(files_to_restore)} file(s)")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def handle_full_restore(savior, backup, backup_index, check_conflicts,
                        force, no_backup, project_dir):
    """Handle full project restore."""
    if check_conflicts:
        # Only check and report conflicts
        detector = ConflictDetector(project_dir)
        resolver = ConflictResolver(project_dir, project_dir / '.savior')

        git_conflicts = detector.detect_git_conflicts()

        if any(git_conflicts.values()):
            print_warning("Git Status Warning:")
            if git_conflicts['staged']:
                click.echo(f"  - {len(git_conflicts['staged'])} staged file(s)")
            if git_conflicts['modified']:
                click.echo(f"  - {len(git_conflicts['modified'])} modified file(s)")
            if git_conflicts['untracked']:
                click.echo(f"  - {len(git_conflicts['untracked'])} untracked file(s)")
            print_info("\nConsider committing or stashing changes before restoring.")
        else:
            print_success("No git conflicts detected")
        return

    # Show enhanced warning based on conflict detection
    detector = ConflictDetector(project_dir)
    git_conflicts = detector.detect_git_conflicts()

    warning_msg = "WARNING: This will overwrite current files!"

    if any(git_conflicts.values()):
        total_conflicts = sum(len(v) for v in git_conflicts.values())
        warning_msg += f"\n  {Fore.RED}• {total_conflicts} uncommitted changes detected!"
        if not no_backup:
            warning_msg += f"\n  {Fore.CYAN}• A safety backup will be created before restore"

    print_warning(warning_msg)

    if confirm_action('Are you sure?'):
        if savior.restore_backup(
            backup_index,
            check_conflicts=not force,
            auto_backup=not no_backup,
            force=force
        ):
            print_success(f"Restored to {format_time_ago(backup.timestamp)}!")
        else:
            print_error("Failed to restore backup")


@click.command()
def list():
    """List all available backups."""
    project_dir = Path.cwd()
    savior = Savior(project_dir)

    backups = savior.list_backups()

    if not backups:
        print_info("No backups found")
        return

    print_info(f"Found {len(backups)} backup(s):\n")

    for i, backup in enumerate(backups, 1):
        time_ago = format_time_ago(backup.timestamp)
        size = format_size(backup.size)

        click.echo(f"{Fore.WHITE}{i}. {Fore.GREEN}{time_ago}")
        click.echo(f"   {Fore.YELLOW}\"{backup.description}\"")
        click.echo(f"   {Fore.CYAN}Size: {size}")

        if i >= 10:
            remaining = len(backups) - 10
            if remaining > 0:
                click.echo(f"\n... and {remaining} more")
            break


@click.command()
@click.option('--keep', default=10, help='Number of recent backups to keep')
@click.option('--older-than', type=int, help='Remove backups older than N days')
@click.option('--dry-run', is_flag=True, help='Show what would be deleted without deleting')
def purge(keep, older_than, dry_run):
    """Clean up old backups to free space."""
    project_dir = Path.cwd()
    savior = Savior(project_dir)

    backups = savior.list_backups()

    if not backups:
        print_info("No backups to purge")
        return

    to_remove = []

    if older_than:
        cutoff = datetime.now() - timedelta(days=older_than)
        to_remove = [b for b in backups if b.timestamp < cutoff]
    else:
        # Keep most recent N backups
        if len(backups) > keep:
            to_remove = backups[keep:]

    if not to_remove:
        print_info("No backups meet criteria for removal")
        return

    total_size = sum(b.size for b in to_remove)

    print_warning(f"Will remove {len(to_remove)} backup(s), freeing {format_size(total_size)}")

    for backup in to_remove[:5]:
        click.echo(f"  - {format_time_ago(backup.timestamp)}: {backup.description}")

    if len(to_remove) > 5:
        click.echo(f"  ... and {len(to_remove) - 5} more")

    if dry_run:
        print_info("(Dry run - no files deleted)")
        return

    if confirm_action("Proceed with deletion?"):
        removed = 0
        freed = 0

        for backup in to_remove:
            if backup.path.exists():
                size = backup.path.stat().st_size
                backup.path.unlink()
                removed += 1
                freed += size

        # Update metadata
        metadata = savior._load_metadata()
        remaining = [b for b in backups if b not in to_remove]
        metadata['backups'] = [b.to_dict() for b in remaining]
        savior._save_metadata(metadata)

        print_success(f"Removed {removed} backup(s), freed {format_size(freed)}")