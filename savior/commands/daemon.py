"""Daemon management commands for Savior CLI."""

import click
import time
from pathlib import Path
from colorama import Fore

from ..daemon import SaviorDaemon, DaemonClient
from ..cli_utils import (
    print_success,
    print_error,
    print_warning,
    print_info
)


@click.group()
def daemon():
    """Manage Savior daemon for background operation."""
    pass


@daemon.command('start')
def daemon_start():
    """Start the Savior daemon."""
    daemon = SaviorDaemon()
    if daemon.is_running():
        print_warning("Daemon is already running")
        return

    if daemon.start():
        print_success("Savior daemon started")
        click.echo("  Run 'savior daemon status' to check watched projects")
    else:
        print_error("Failed to start daemon")


@daemon.command('stop')
def daemon_stop():
    """Stop the Savior daemon."""
    client = DaemonClient()
    result = client.stop()

    if 'error' in result:
        print_error(result['error'])
    else:
        print_success("Savior daemon stopped")


@daemon.command('status')
def daemon_status():
    """Show daemon status and watched projects."""
    daemon = SaviorDaemon()
    if not daemon.is_running():
        print_warning("Daemon is not running")
        return

    client = DaemonClient()
    status = client.status()
    projects = client.list_projects()

    click.echo(f"{Fore.CYAN}Savior Daemon Status:")
    click.echo(f"  PID: {status.get('daemon_pid')}")
    click.echo(f"  Projects watched: {status.get('projects_count')}")

    if projects.get('projects'):
        click.echo(f"\n{Fore.CYAN}Watched Projects:")
        for path, info in projects['projects'].items():
            started = info.get('started', 'Unknown')
            options = info.get('options', {})
            mode = []
            if options.get('smart'):
                mode.append('smart')
            if options.get('incremental'):
                mode.append('incremental')
            mode_str = f" ({', '.join(mode)})" if mode else ""

            click.echo(f"  • {path}")
            click.echo(f"    Started: {started}")
            click.echo(f"    PID: {info['pid']}{mode_str}")


@daemon.command('add')
@click.argument('paths', nargs=-1, required=True)
@click.option('--interval', default=20, help='Backup interval in minutes')
@click.option('--no-smart', is_flag=True, help='Disable smart mode (save even during activity)')
@click.option('--full', is_flag=True, help='Use full backups instead of incremental')
@click.option('--exclude-git', is_flag=True, help='Exclude .git directory from backups (saves space)')
def daemon_add(paths, interval, no_smart, full, exclude_git):
    """Add projects to daemon watch list."""
    daemon = SaviorDaemon()
    if not daemon.is_running():
        print_info("Starting daemon first...")
        if not daemon.start():
            print_error("Failed to start daemon")
            return
        time.sleep(2)  # Give daemon time to start

    client = DaemonClient()

    for path_str in paths:
        path = Path(path_str).resolve()
        if not path.exists():
            print_error(f"Path does not exist: {path}")
            continue

        result = client.add_project(
            str(path),
            interval=interval,
            smart=not no_smart,  # Invert flag (smart is default)
            incremental=not full,  # Invert flag (incremental is default)
            exclude_git=exclude_git
        )

        if 'error' in result:
            print_error(f"{path}: {result['error']}")
        else:
            print_success(f"Added {path} (PID: {result['pid']})")


@daemon.command('remove')
@click.argument('paths', nargs=-1, required=True)
def daemon_remove(paths):
    """Remove projects from daemon watch list."""
    client = DaemonClient()

    for path_str in paths:
        path = Path(path_str).resolve()

        result = client.remove_project(str(path))

        if 'error' in result:
            print_error(f"{path}: {result['error']}")
        else:
            print_success(f"Removed {path}")