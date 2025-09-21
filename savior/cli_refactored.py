#!/usr/bin/env python3
"""Savior CLI - Refactored main entry point."""

import click
from colorama import init

# Initialize colorama for cross-platform colored output
init(autoreset=True)

# Import all command modules
from .commands import backup, restore, cloud, recovery
from .commands import utility, daemon as daemon_cmds, zombie as zombie_cmds


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Savior 🛟 - Automatic backups for developers who break things.

    Zero-configuration backup tool that watches your project and saves your work
    automatically. Never lose code again.

    Quick start:
        savior init      # Initialize in current directory (optional)
        savior watch     # Start auto-saving
        savior restore   # Restore when things break
    """
    if ctx.invoked_subcommand is None:
        # Show help if no command provided
        click.echo(ctx.get_help())


# Register backup commands
cli.add_command(backup.watch)
cli.add_command(backup.save)
cli.add_command(backup.stop)
cli.add_command(backup.status)

# Register restore commands
cli.add_command(restore.restore)
cli.add_command(restore.list, name='list')
cli.add_command(restore.purge)

# Register cloud commands
cli.add_command(cloud.cloud)

# Register recovery commands
cli.add_command(recovery.diff)
cli.add_command(recovery.resurrect)
cli.add_command(recovery.pray)

# Register utility commands
cli.add_command(utility.tree)
cli.add_command(utility.paths)
cli.add_command(utility.sessions)
cli.add_command(utility.init)
cli.add_command(utility.projects)
cli.add_command(utility.help, name='help')
cli.add_command(utility.commands)
cli.add_command(utility.cmds)
cli.add_command(utility.flags)

# Register daemon commands
cli.add_command(daemon_cmds.daemon)

# Register zombie commands
cli.add_command(zombie_cmds.zombie)


# Aliases for common commands
@cli.command('w')
@click.pass_context
def watch_alias(ctx):
    """Alias for 'watch' command."""
    ctx.invoke(backup.watch)


@cli.command('s')
@click.argument('description', required=False)
@click.option('--compression', default=6, help='Compression level (0-9)')
@click.option('--tree', is_flag=True, help='Show project structure before saving')
@click.option('--no-progress', is_flag=True, help='Disable progress bar')
@click.pass_context
def save_alias(ctx, description, compression, tree, no_progress):
    """Alias for 'save' command."""
    ctx.invoke(backup.save, description=description, compression=compression,
               tree=tree, no_progress=no_progress)


@cli.command('r')
@click.option('--files', help='Glob pattern for specific files to restore')
@click.option('--preview', is_flag=True, help='Preview what would be restored')
@click.option('--force', is_flag=True, help='Force restore without conflict checking')
@click.option('--no-backup', is_flag=True, help='Skip creating pre-restore safety backup')
@click.option('--check-conflicts', is_flag=True, help='Check for conflicts without restoring')
@click.pass_context
def restore_alias(ctx, files, preview, force, no_backup, check_conflicts):
    """Alias for 'restore' command."""
    ctx.invoke(restore.restore, files=files, preview=preview, force=force,
               no_backup=no_backup, check_conflicts=check_conflicts)


@cli.command('l')
@click.pass_context
def list_alias(ctx):
    """Alias for 'list' command."""
    ctx.invoke(restore.list)


# Additional aliases for compatibility
@cli.command('saves')
@click.pass_context
def saves_alias(ctx):
    """Show all saved backups (alias for 'list')."""
    ctx.invoke(restore.list)


@cli.command('kill')
@click.pass_context
def kill_alias(ctx):
    """Stop watching (alias for 'stop')."""
    ctx.invoke(backup.stop)


@cli.command('start')
@click.option('--interval', default=20, help='Backup interval in minutes')
@click.option('--no-smart', is_flag=True, help='Disable smart mode')
@click.option('--full', is_flag=True, help='Use full backups instead of incremental')
@click.option('--exclude-git', is_flag=True, help='Exclude .git directory')
@click.option('--compression', default=6, help='Compression level (0-9)')
@click.option('--cloud', is_flag=True, help='Enable cloud sync')
@click.option('--tree', is_flag=True, help='Show project structure first')
@click.pass_context
def start_alias(ctx, interval, no_smart, full, exclude_git, compression, cloud, tree):
    """Start auto-saving (alias for 'watch')."""
    ctx.invoke(backup.watch, interval=interval, no_smart=no_smart, full=full,
               exclude_git=exclude_git, compression=compression, cloud=cloud, tree=tree)


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == '__main__':
    main()