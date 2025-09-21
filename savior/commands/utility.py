"""Utility commands for Savior CLI."""

import click
from pathlib import Path
from datetime import datetime
from colorama import Fore, Style

from ..core import Savior
from ..cli_utils import (
    format_time_ago,
    format_size,
    print_info,
    print_warning,
    print_success,
    print_header
)


@click.command('tree')
@click.option('--depth', default=3, help='Maximum depth to display (default: 3)')
@click.option('--no-size', is_flag=True, help='Don\'t show file sizes')
@click.option('--all', '-a', is_flag=True, help='Show hidden files')
@click.option('--exclude-git', is_flag=True, help='Exclude .git directory from display')
@click.option('--ignore', default='', help='Additional patterns to ignore (comma-separated)')
def tree(depth, no_size, all, exclude_git, ignore):
    """Show project file tree."""
    project_dir = Path.cwd()

    # Parse additional ignore patterns
    extra_ignores = [p.strip() for p in ignore.split(',') if p.strip()] if ignore else []

    # Create savior with the exclude options
    savior = Savior(project_dir, exclude_git=exclude_git, extra_ignores=extra_ignores)

    click.echo(f"\n{Fore.CYAN}Project Structure:{Style.RESET_ALL}")
    tree_output = savior.get_project_tree(max_depth=depth, show_size=not no_size)
    click.echo(tree_output)

    # Show summary
    files = savior._collect_files()
    total_size = sum(f.stat().st_size for f in files if f.exists())
    click.echo(f"\n{Fore.GREEN}Summary:{Style.RESET_ALL}")
    click.echo(f"  Files to backup: {len(files)}")
    click.echo(f"  Total size: {format_size(total_size)}")
    click.echo(f"  Estimated backup size: {format_size(int(total_size * 0.4))}")


@click.command('paths')
def paths():
    """Show all Savior file locations."""
    project_dir = Path.cwd()
    savior = Savior(project_dir)

    click.echo(f"{Fore.CYAN}Savior File Locations:")
    click.echo("=" * 60)

    # Project paths
    click.echo(f"\n{Fore.GREEN}Project:")
    click.echo(f"  Current directory: {project_dir}")
    click.echo(f"  Backup directory:  {savior.backup_dir}")

    # Check if backup dir exists and show size
    if savior.backup_dir.exists():
        total_size = sum(f.stat().st_size for f in savior.backup_dir.glob('**/*') if f.is_file())
        click.echo(f"  Storage used:      {format_size(total_size)}")

        # List backup files
        try:
            backups = list(savior.backup_dir.glob('*.tar.gz'))
            if backups:
                click.echo(f"\n{Fore.GREEN}Backup Files ({len(backups)}):")
                for backup in sorted(backups)[-5:]:  # Show last 5
                    size = format_size(backup.stat().st_size)
                    click.echo(f"  • {backup.name} ({size})")
        except Exception:
            pass  # Skip if there's an issue listing files
    else:
        click.echo(f"  {Fore.YELLOW}No backups yet")

    # Config files
    click.echo(f"\n{Fore.GREEN}Config Files:")
    if savior.metadata_file.exists():
        click.echo(f"  ✓ Metadata:       {savior.metadata_file}")
    else:
        click.echo(f"  ✗ Metadata:       {savior.metadata_file} (not created)")

    if savior.ignore_file.exists():
        click.echo(f"  ✓ Ignore file:    {savior.ignore_file}")
    else:
        click.echo(f"  ✗ Ignore file:    {savior.ignore_file} (using defaults)")

    # Daemon files (global)
    daemon_dir = Path.home() / '.savior'
    click.echo(f"\n{Fore.GREEN}Daemon Files (Global):")
    click.echo(f"  Config directory: {daemon_dir}")

    if daemon_dir.exists():
        pid_file = daemon_dir / 'daemon.pid'
        projects_file = daemon_dir / 'projects.json'
        log_file = daemon_dir / 'daemon.log'

        if pid_file.exists():
            click.echo(f"  ✓ PID file:      {pid_file}")
        if projects_file.exists():
            click.echo(f"  ✓ Projects:      {projects_file}")
        if log_file.exists():
            size = format_size(log_file.stat().st_size)
            click.echo(f"  ✓ Log file:      {log_file} ({size})")

    click.echo("\n" + "=" * 60)
    click.echo(f"{Fore.CYAN}Tips:")
    click.echo(f"  • Open backup directory: {Fore.YELLOW}open {savior.backup_dir}{Style.RESET_ALL}")
    click.echo(f"  • Clear all backups:     {Fore.YELLOW}rm -rf {savior.backup_dir}{Style.RESET_ALL}")
    click.echo(f"  • Check daemon logs:     {Fore.YELLOW}tail -f ~/.savior/daemon.log{Style.RESET_ALL}")


@click.command('sessions')
def sessions():
    """Show watch session history."""
    project_dir = Path.cwd()
    savior = Savior(project_dir)

    metadata = savior._load_metadata()
    sessions = metadata.get('sessions', [])

    if not sessions:
        print_warning("No watch sessions found")
        click.echo(f"  Run '{Fore.CYAN}savior watch{Style.RESET_ALL}' to start your first session")
        return

    print_header("Watch Sessions")

    for i, session in enumerate(reversed(sessions[-10:]), 1):  # Show last 10 sessions
        started = datetime.fromisoformat(session['started'])
        stopped = datetime.fromisoformat(session['stopped']) if session['stopped'] else None

        if stopped:
            duration = stopped - started
            hours = int(duration.total_seconds() // 3600)
            minutes = int((duration.total_seconds() % 3600) // 60)
            status = f"{Fore.GREEN}✓ Completed{Style.RESET_ALL}"
            duration_str = f"{hours}h {minutes}m" if hours else f"{minutes}m"
        else:
            duration = datetime.now() - started
            hours = int(duration.total_seconds() // 3600)
            minutes = int((duration.total_seconds() % 3600) // 60)
            status = f"{Fore.YELLOW}⚡ Active{Style.RESET_ALL}"
            duration_str = f"{hours}h {minutes}m" if hours else f"{minutes}m"

        mode = session.get('mode', 'unknown')
        interval = session.get('interval', 20)

        click.echo(f"  {i}. {started.strftime('%b %d, %I:%M %p')} - {status}")
        click.echo(f"     Mode: {mode} | Interval: {interval}min | Duration: {duration_str}")

    click.echo("=" * 60)
    click.echo(f"Total sessions: {len(sessions)}")


@click.command('init')
@click.option('--exclude-git', is_flag=True, help='Exclude .git directory from backups')
@click.option('--interval', default=20, help='Default backup interval in minutes')
def init(exclude_git, interval):
    """Initialize Savior in current directory (optional)."""
    project_dir = Path.cwd()
    savior = Savior(project_dir)

    # Create .savior directory
    savior.backup_dir.mkdir(parents=True, exist_ok=True)

    # Create .saviorignore if it doesn't exist
    if not savior.ignore_file.exists():
        default_ignore = [
            "# Savior ignore patterns",
            "node_modules/",
            "*.pyc",
            "__pycache__/",
            ".DS_Store",
            "*.log",
            "build/",
            "dist/",
            ".venv/",
            "venv/",
            "*.swp",
            "*.swo",
            "*~"
        ]

        if exclude_git:
            default_ignore.append(".git/")

        savior.ignore_file.write_text('\n'.join(default_ignore))
        print_success(f"Created {savior.ignore_file}")

    # Save initial metadata
    metadata = savior._load_metadata()
    metadata.update({
        'initialized': datetime.now().isoformat(),
        'project_name': project_dir.name,
        'default_interval': interval,
        'exclude_git': exclude_git
    })
    savior._save_metadata(metadata)

    print_success(f"Initialized Savior in {project_dir}")
    click.echo(f"  Backup directory: {savior.backup_dir}")
    click.echo(f"  Ignore file: {savior.ignore_file}")
    click.echo(f"\nRun '{Fore.CYAN}savior watch{Style.RESET_ALL}' to start auto-saving")


@click.command('help')
@click.pass_context
def help(ctx):
    """Show help information."""
    click.echo(ctx.parent.get_help())


@click.command('commands')
def commands():
    """Show all available commands."""
    show_all_commands()


@click.command('cmds')
def cmds():
    """Show all available commands (alias)."""
    show_all_commands()


def show_all_commands():
    """Display all available commands in a formatted way."""
    print_header("Savior Commands")

    commands = {
        'Core Commands': [
            ('watch', 'Start auto-saving current directory'),
            ('save', 'Force a save right now'),
            ('restore', 'See all backups and restore one'),
            ('stop', 'Stop watching the current directory'),
            ('status', 'Check if Savior is watching'),
            ('list', 'Show all saved backups'),
            ('purge', 'Delete old backups to free space'),
        ],
        'Recovery Commands': [
            ('diff', 'Compare backups to see what changed'),
            ('resurrect', 'Find and restore deleted files'),
            ('pray', '🙏 Deep recovery attempt (searches everywhere)'),
        ],
        'Cloud Commands': [
            ('cloud setup', 'Configure cloud storage'),
            ('cloud sync', 'Sync backups with cloud'),
            ('cloud list', 'List cloud backups'),
            ('cloud download', 'Download specific backup from cloud'),
        ],
        'Daemon Commands': [
            ('daemon start', 'Start background daemon'),
            ('daemon stop', 'Stop daemon'),
            ('daemon status', 'See all watched projects'),
            ('daemon add', 'Watch multiple projects'),
            ('daemon remove', 'Stop watching a project'),
        ],
        'Utility Commands': [
            ('tree', 'Visualize project structure'),
            ('paths', 'Show all Savior file locations'),
            ('sessions', 'Show watch session history'),
            ('projects', 'List all Savior projects on system'),
            ('init', 'Initialize Savior in directory'),
        ],
        'Zombie Commands': [
            ('zombie scan', 'Find unused functions and classes'),
            ('zombie check', 'Check if specific code is dead'),
            ('zombie stats', 'Show dead code percentage'),
            ('zombie quarantine', 'Move dead code to quarantine'),
        ],
        'Help Commands': [
            ('help', 'Show this help message'),
            ('commands', 'Show all available commands'),
            ('flags', 'Show all available flags'),
        ],
    }

    for section, cmd_list in commands.items():
        click.echo(f"\n{Fore.CYAN}{section}:")
        for cmd, desc in cmd_list:
            click.echo(f"  {Fore.YELLOW}{cmd:20} {Fore.WHITE}{desc}")


@click.command('flags')
def flags():
    """Show all available flags for commands."""
    print_header("Savior Flags")

    flags_info = {
        'watch': [
            ('--interval N', 'Backup interval in minutes (default: 20)'),
            ('--no-smart', 'Disable smart mode'),
            ('--full', 'Use full backups instead of incremental'),
            ('--exclude-git', 'Exclude .git directory'),
            ('--compression N', 'Set compression level (0-9)'),
            ('--cloud', 'Enable cloud sync'),
            ('--tree', 'Show project structure first'),
        ],
        'save': [
            ('--compression N', 'Set compression level (0-9)'),
            ('--tree', 'Preview what will be backed up'),
            ('--no-progress', 'Disable progress bar'),
        ],
        'restore': [
            ('--files PATTERN', 'Restore only specific files'),
            ('--preview', 'See what would be restored'),
            ('--check-conflicts', 'Check for uncommitted changes'),
            ('--force', 'Skip conflict detection'),
            ('--no-backup', 'Don\'t create safety backup'),
        ],
        'diff': [
            ('--show-content', 'Show actual file differences'),
        ],
        'tree': [
            ('--depth N', 'Maximum depth to display'),
            ('--exclude-git', 'Hide .git directory'),
            ('--ignore PATTERN', 'Additional patterns to ignore'),
        ],
        'daemon add': [
            ('--interval N', 'Backup interval in minutes'),
            ('--no-smart', 'Disable smart mode'),
            ('--full', 'Use full backups'),
            ('--exclude-git', 'Exclude .git directory'),
        ],
    }

    for command, flags_list in flags_info.items():
        click.echo(f"\n{Fore.CYAN}savior {command}:")
        for flag, desc in flags_list:
            click.echo(f"  {Fore.YELLOW}{flag:25} {Fore.WHITE}{desc}")


@click.command()
@click.argument('paths', nargs=-1)
@click.option('--all', is_flag=True, help='List backups for all projects')
def projects(paths, all):
    """Manage multiple projects at once."""
    import os

    if all:
        # Find all projects with .savior directories
        home = Path.home()
        savior_projects = []

        for root, dirs, files in os.walk(home):
            if '.savior' in dirs:
                project_path = Path(root)
                if project_path != home:
                    savior_projects.append(project_path)

        if not savior_projects:
            print_warning("No Savior projects found")
            return

        click.echo(f"{Fore.CYAN}Found {len(savior_projects)} Savior project(s):\n")

        for project in savior_projects:
            savior = Savior(project)
            backups = savior.list_backups()

            if backups:
                latest = backups[0]
                total_size = sum(b.size for b in backups)

                click.echo(f"{Fore.GREEN}• {project}")
                click.echo(f"  Backups: {len(backups)}")
                click.echo(f"  Latest: {format_time_ago(latest.timestamp)}")
                click.echo(f"  Total size: {format_size(total_size)}")
            else:
                click.echo(f"{Fore.YELLOW}• {project}")
                click.echo("  No backups")
    elif paths:
        # Watch multiple specific paths
        for path_str in paths:
            path = Path(path_str).resolve()
            if not path.exists():
                print_warning(f"Path does not exist: {path}")
                continue

            savior = Savior(path)
            backups = savior.list_backups()

            click.echo(f"\n{Fore.CYAN}Project: {path}")
            if backups:
                click.echo(f"  Backups: {len(backups)}")
                click.echo(f"  Latest: {format_time_ago(backups[0].timestamp)}")
                click.echo(f"  Total size: {format_size(sum(b.size for b in backups))}")
            else:
                click.echo("  No backups yet")
    else:
        print_warning("Specify project paths or use --all to list all projects")