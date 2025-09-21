import click
import time
import sys
import os
import tempfile
import tarfile
import shutil
import select
from pathlib import Path
from datetime import datetime, timedelta
from colorama import init, Fore, Style

try:
    # Try relative imports first (when run as module)
    from .core import Savior, Backup
    from .diff import BackupDiffer
    from .recovery import DeepRecovery
    from .activity import SmartWatcher
    from .incremental import IncrementalBackup
    from .zombie import ZombieScanner, QuarantineManager, RuntimeTracer
    from .cloud import CloudStorage
except ImportError:
    # Fall back to absolute imports (when run as script)
    from core import Savior, Backup
    from diff import BackupDiffer
    from recovery import DeepRecovery
    from activity import SmartWatcher
    from incremental import IncrementalBackup
    from zombie import ZombieScanner, QuarantineManager, RuntimeTracer
    from cloud import CloudStorage

init(autoreset=True)


def format_time_ago(timestamp: datetime) -> str:
    now = datetime.now()
    delta = now - timestamp

    if delta < timedelta(minutes=1):
        return "just now"
    elif delta < timedelta(hours=1):
        minutes = int(delta.total_seconds() / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif delta < timedelta(days=1):
        hours = int(delta.total_seconds() / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        days = delta.days
        return f"{days} day{'s' if days != 1 else ''} ago"


def format_size(size_bytes: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def check_keyboard_input():
    """Check if a key has been pressed (non-blocking)"""
    if sys.platform == 'win32':
        # Windows doesn't support select on stdin
        return None

    try:
        if select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.read(1)
    except:
        pass
    return None


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Savior 🛟 - Automatic backups every 20 minutes, no commits required"""
    if ctx.invoked_subcommand is None:
        # If no command provided, show help
        click.echo(ctx.get_help())


@cli.command('help')
@click.pass_context
def show_help(ctx):
    """Show help information"""
    click.echo(ctx.parent.get_help())

@cli.command('cmds')
@click.pass_context
def show_commands(ctx):
    """Show all available commands (alias for 'commands')"""
    show_all_commands(ctx)

@cli.command('commands')
@click.pass_context
def show_commands_full(ctx):
    """Show all available commands"""
    show_all_commands(ctx)

def show_all_commands(ctx):
    """Display all available commands in a formatted way"""
    click.echo(f"\n{Fore.CYAN}Savior Commands:{Style.RESET_ALL}")
    click.echo("=" * 60)

    commands = {
        'Core Commands': [
            ('watch', 'Start auto-saving current directory'),
            ('save', 'Force a save right now'),
            ('restore', 'See all backups and restore one'),
            ('stop', 'Stop watching the current directory'),
            ('status', 'Check if Savior is running'),
        ],
        'Backup Management': [
            ('list/saves', 'Show all saved backups'),
            ('diff', 'See what changed between backups'),
            ('purge', 'Delete old backups to free space'),
            ('tree', 'Show project file tree'),
        ],
        'Recovery': [
            ('resurrect', 'Recover specific deleted files'),
            ('pray', '🙏 Hail Mary recovery attempt'),
        ],
        'Advanced': [
            ('daemon', 'Manage background daemon'),
            ('projects', 'Manage multiple projects'),
            ('cloud', '☁️ Self-hosted cloud backup'),
            ('zombie', '🧟 Dead code detection'),
        ],
        'Information': [
            ('paths', 'Show all Savior file locations'),
            ('sessions', 'Show watch session history'),
            ('next', 'Show when next backup will occur'),
            ('flags', 'Show all available flags'),
            ('help/cmds/commands', 'Show this help'),
        ],
    }

    for category, cmds in commands.items():
        click.echo(f"\n{Fore.GREEN}{category}:{Style.RESET_ALL}")
        for cmd, desc in cmds:
            click.echo(f"  {Fore.YELLOW}{cmd:<20}{Style.RESET_ALL} {desc}")

    click.echo(f"\n{Fore.CYAN}Quick Start:{Style.RESET_ALL}")
    click.echo("  savior watch         # Start watching current directory")
    click.echo("  savior save          # Manual backup")
    click.echo("  savior restore       # Restore from backup")
    click.echo("\nUse 'savior [command] --help' for more info on a command")

@cli.command('flags')
def show_flags():
    """Show all available flags for all commands"""
    click.echo(f"\n{Fore.CYAN}Savior Flags & Options:{Style.RESET_ALL}")
    click.echo("=" * 60)

    flags_info = {
        'watch': [
            ('--interval N', 'Backup interval in minutes (default: 20)'),
            ('--no-smart', 'Disable smart mode (save even during activity)'),
            ('--full', 'Use full backups instead of incremental'),
            ('--exclude-git', 'Exclude .git directory'),
            ('--compression N', 'Compression level 0-9 (default: 6)'),
            ('--tree', 'Show project tree before starting'),
            ('-b, --background', 'Run in background as daemon'),
        ],
        'save': [
            ('--compression N', 'Compression level 0-9 (default: 6)'),
            ('--tree', 'Show what will be backed up'),
            ('--no-progress', 'Disable progress bar'),
        ],
        'restore': [
            ('--files PATTERN', 'Restore only specific files'),
            ('--preview', 'See what would be restored'),
        ],
        'diff': [
            ('--show-content', 'Show actual file differences'),
        ],
        'tree': [
            ('-d, --depth N', 'Maximum depth to display (default: 3)'),
            ('--no-size', 'Hide file sizes'),
            ('-a, --all', 'Show ignored files too'),
            ('--exclude-git', 'Exclude .git directory from display'),
            ('--ignore PATTERNS', 'Additional patterns to ignore (comma-separated)'),
        ],
        'purge': [
            ('--keep N', 'Number of recent backups to keep'),
            ('--force', 'Skip confirmation'),
        ],
        'daemon': [
            ('start', 'Start the daemon'),
            ('stop', 'Stop the daemon'),
            ('status', 'Check daemon status'),
            ('add PATH', 'Add project to watch'),
            ('remove PATH', 'Stop watching project'),
        ],
        'zombie scan': [
            ('--json FILE', 'Export results to JSON'),
            ('--verbose', 'Show detailed analysis'),
            ('--enhanced', 'Deep analysis with runtime tracing'),
            ('--quarantine', 'Move dead code to .zombie/'),
            ('--dry-run', 'Preview without making changes'),
        ],
    }

    for cmd, flags in flags_info.items():
        click.echo(f"\n{Fore.GREEN}savior {cmd}:{Style.RESET_ALL}")
        for flag, desc in flags:
            click.echo(f"  {Fore.YELLOW}{flag:<25}{Style.RESET_ALL} {desc}")

    click.echo(f"\n{Fore.CYAN}Global Flags:{Style.RESET_ALL}")
    click.echo(f"  {Fore.YELLOW}--help{Style.RESET_ALL}                    Show help for any command")
    click.echo(f"\n{Fore.CYAN}Examples:{Style.RESET_ALL}")
    click.echo("  savior watch --compression 9 --tree")
    click.echo("  savior save 'before big change' --compression 0")
    click.echo("  savior tree --depth 5 --no-size")
    click.echo("  savior restore --preview")

@cli.command()
@click.option('--interval', default=20, help='Backup interval in minutes (default: 20)')
@click.option('--no-smart', is_flag=True, help='Disable smart mode (save even during activity)')
@click.option('--full', is_flag=True, help='Use full backups instead of incremental')
@click.option('--exclude-git', is_flag=True, help='Exclude .git directory from backups (saves space)')
@click.option('--ignore', default='', help='Additional patterns to ignore (comma-separated, e.g. "*.mp4,temp/*")')
@click.option('--compression', '-c', type=click.IntRange(0, 9), default=6, help='Compression level (0=none, 9=max, default: 6)')
@click.option('--background', '-b', is_flag=True, help='Run in background as daemon')
@click.option('--tree', is_flag=True, help='Show project tree before starting')
@click.option('--cloud', is_flag=True, help='Enable automatic cloud backup syncing')
def watch(interval, no_smart, full, exclude_git, ignore, compression, background, tree, cloud):
    """Start auto-saving current directory"""
    project_dir = Path.cwd()

    # Parse additional ignore patterns
    extra_ignores = [p.strip() for p in ignore.split(',') if p.strip()] if ignore else []

    savior = Savior(project_dir, exclude_git=exclude_git, extra_ignores=extra_ignores, enable_cloud=cloud)

    # Show project tree if requested
    if tree:
        click.echo(f"\n{Fore.CYAN}Project Structure:{Style.RESET_ALL}")
        click.echo(savior.get_project_tree(max_depth=3))
        click.echo()

    # Check cloud configuration if enabled
    if cloud:
        if not savior.cloud_storage or not savior.cloud_storage.is_configured():
            click.echo(f"{Fore.YELLOW}⚠️ Cloud storage not configured. Run 'savior cloud setup' first.")
            return
        click.echo(f"{Fore.GREEN}☁️ Cloud sync enabled")

    if savior.is_watching():
        click.echo(f"{Fore.YELLOW}⚠ Savior is already watching this project")
        return

    if background:
        # Use the existing daemon functionality
        try:
            from .daemon import DaemonClient, SaviorDaemon
        except ImportError:
            from daemon import DaemonClient, SaviorDaemon

        daemon = SaviorDaemon()
        if not daemon.is_running():
            daemon.start()
            time.sleep(2)  # Give daemon time to start

        client = DaemonClient()
        result = client.add_project(
            str(project_dir),
            interval=interval,
            smart=not no_smart,
            incremental=not full,
            exclude_git=exclude_git
        )

        if 'error' in result:
            click.echo(f"{Fore.RED}✗ {result['error']}")
        else:
            click.echo(f"{Fore.GREEN}✓ Savior is now watching in background (PID: {result.get('pid', 'unknown')})")
            click.echo(f"  Use '{Fore.CYAN}savior stop{Style.RESET_ALL}' to stop watching")
            click.echo(f"  Use '{Fore.CYAN}savior sessions{Style.RESET_ALL}' to see watch history")
        return

    last_backup_time = datetime.now()
    next_backup_time = datetime.now() + timedelta(minutes=interval)
    backup_count = 0
    total_size = 0

    def save_callback():
        nonlocal last_backup_time, backup_count, total_size, next_backup_time
        if full:
            # Use full backup
            backup = savior.create_backup("Automatic backup")
            size = backup.size
            click.echo(f"\r{Fore.GREEN}✓ Backup saved ({format_size(size)}){' ' * 50}")
        else:
            # Use incremental backup (default)
            inc_backup = IncrementalBackup(savior.backup_dir)
            files = savior._collect_files()

            backups = savior.list_backups()
            base_backup = backups[0].path if backups else None

            backup_path = inc_backup.create_incremental_backup(files, base_backup)
            size = backup_path.stat().st_size

            # Save to metadata
            backup = Backup(
                timestamp=datetime.now(),
                path=backup_path,
                description="Incremental backup",
                size=size
            )
            metadata = savior._load_metadata()
            metadata['backups'].append(backup.to_dict())
            savior._save_metadata(metadata)

            click.echo(f"\r{Fore.GREEN}✓ Incremental backup saved ({format_size(size)}){' ' * 50}")

        last_backup_time = datetime.now()
        next_backup_time = datetime.now() + timedelta(minutes=interval)
        backup_count += 1
        total_size += size

        # Update next backup time in metadata
        metadata = savior._load_metadata()
        metadata['next_backup'] = next_backup_time.isoformat()
        savior._save_metadata(metadata)

    if no_smart:
        # Basic mode without smart detection
        savior.watch_interval = interval * 60

        # Check if this is the first time watching this project
        backups = savior.list_backups()
        is_first_time = len(backups) == 0

        # Force a full backup for the first time
        if is_first_time and not full:
            click.echo(f"{Fore.CYAN}Creating initial full backup...")
            backup = savior.create_backup("Initial backup")
            backup_count += 1
            total_size += backup.size
            click.echo(f"{Fore.GREEN}✓ Initial backup saved ({format_size(backup.size)})")
            last_backup_time = datetime.now()

        savior.start_watching()

        click.echo(f"{Fore.GREEN}✓ Savior is now watching your project (basic mode)")
        click.echo(f"{Fore.GREEN}✓ Backups every {interval} minutes to .savior/")
    else:
        # Smart mode (default)
        click.echo(f"{Fore.GREEN}✓ Savior is now watching your project")
        click.echo(f"{Fore.GREEN}✓ Will save after {interval} minutes of work + 2 seconds of inactivity")
        if cloud:
            click.echo(f"{Fore.GREEN}☁️ Backups will auto-sync to cloud storage")

        # Set watching flag and record session start
        metadata = savior._load_metadata()
        metadata['watching'] = True

        # Initialize sessions list if it doesn't exist
        if 'sessions' not in metadata:
            metadata['sessions'] = []

        # Add new session
        session = {
            'started': datetime.now().isoformat(),
            'stopped': None,
            'mode': 'smart',
            'interval': interval,
            'cloud': cloud
        }
        metadata['sessions'].append(session)

        # Store next backup time
        metadata['next_backup'] = (datetime.now() + timedelta(minutes=interval)).isoformat()
        metadata['watch_interval'] = interval

        savior._save_metadata(metadata)

        watcher = SmartWatcher(
            project_dir,
            save_callback,
            idle_time=2.0,
            check_interval=interval * 60
        )
        watcher.start()

        # Check if this is the first time watching this project
        backups = savior.list_backups()
        is_first_time = len(backups) == 0

        # Initial backup - force full backup if first time
        if is_first_time and not full:
            # Force a full backup for the first time
            click.echo(f"{Fore.CYAN}Creating initial full backup...")
            backup = savior.create_backup("Initial backup")
            size = backup.size
            backup_count += 1
            total_size += size
            click.echo(f"{Fore.GREEN}✓ Initial backup saved ({format_size(size)})")
        else:
            # Regular save callback
            save_callback()

        last_backup_time = datetime.now()
        next_backup_time = datetime.now() + timedelta(minutes=interval)

        # Status display loop for smart mode
        click.echo(f"\n{Fore.CYAN}Press Ctrl+C to stop | Press 's' to save now\n")

        try:
            while True:
                # Check for keyboard input
                key = check_keyboard_input()
                if key == 's':
                    click.echo(f"\r{Fore.YELLOW}Manual save triggered...{' ' * 50}")
                    save_callback()
                    click.echo(f"{Fore.GREEN}✓ Manual backup completed!{' ' * 50}")
                    time.sleep(1)

                # Calculate time until next backup
                now = datetime.now()
                time_since = format_time_ago(last_backup_time)
                time_until = int((next_backup_time - now).total_seconds())

                if time_until > 0:
                    mins, secs = divmod(time_until, 60)
                    status = f"Last backup: {time_since} | Next in: {mins:02d}:{secs:02d} | Saves: {backup_count} | Total: {format_size(total_size)}"
                else:
                    status = f"Last backup: {time_since} | Waiting for activity pause... | Saves: {backup_count} | Total: {format_size(total_size)}"

                click.echo(f"\r{Fore.CYAN}{status}{' ' * 20}", nl=False)
                time.sleep(1)
        except KeyboardInterrupt:
            watcher.stop()
            # Clear watching flag and record session end
            metadata = savior._load_metadata()
            metadata['watching'] = False

            # Update the last session with stop time
            if 'sessions' in metadata and metadata['sessions']:
                metadata['sessions'][-1]['stopped'] = datetime.now().isoformat()

            savior._save_metadata(metadata)
            click.echo(f"\n{Fore.YELLOW}✓ Savior stopped watching")
            return

    # Basic mode status display
    click.echo(f"\n{Fore.CYAN}Press Ctrl+C to stop | Press 's' to save now\n")

    try:
        while True:
            # Check for keyboard input
            key = check_keyboard_input()
            if key == 's':
                click.echo(f"\r{Fore.YELLOW}Manual save triggered...{' ' * 50}")
                save_callback()
                click.echo(f"{Fore.GREEN}✓ Manual backup completed!{' ' * 50}")
                time.sleep(1)

            # Calculate time until next backup
            now = datetime.now()
            time_since = format_time_ago(last_backup_time)
            time_until = int((next_backup_time - now).total_seconds())

            if time_until > 0:
                mins, secs = divmod(time_until, 60)
                status = f"Last backup: {time_since} | Next in: {mins:02d}:{secs:02d} | Saves: {backup_count} | Total: {format_size(total_size)}"
            else:
                status = f"Last backup: {time_since} | Saving... | Saves: {backup_count} | Total: {format_size(total_size)}"

            click.echo(f"\r{Fore.CYAN}{status}{' ' * 20}", nl=False)
            time.sleep(1)
    except KeyboardInterrupt:
        if no_smart:
            savior.stop_watching()
        click.echo(f"\n{Fore.YELLOW}✓ Savior stopped watching")


@cli.command('stop')
def stop_watching():
    """Stop watching the current directory"""
    project_dir = Path.cwd()
    savior = Savior(project_dir)

    if not savior.is_watching():
        click.echo(f"{Fore.YELLOW}⚠ Savior is not currently watching this project")
        return

    savior.stop_watching()
    click.echo(f"{Fore.GREEN}✓ Savior stopped watching")


@cli.command()
def status():
    """Check if Savior is running"""
    project_dir = Path.cwd()
    savior = Savior(project_dir)

    if savior.is_watching():
        click.echo(f"{Fore.GREEN}✓ Savior is actively watching this project")

        backups = savior.list_backups()
        if backups:
            latest = backups[0]
            click.echo(f"  Last backup: {format_time_ago(latest.timestamp)}")
            click.echo(f"  Total backups: {len(backups)}")
    else:
        click.echo(f"{Fore.YELLOW}✗ Savior is not watching this project")
        click.echo(f"  Run '{Fore.CYAN}savior watch{Style.RESET_ALL}' to start")


@cli.command()
def next():
    """Show when the next backup will occur"""
    project_dir = Path.cwd()
    savior = Savior(project_dir)

    if not savior.is_watching():
        click.echo(f"{Fore.YELLOW}✗ Savior is not watching this project")
        click.echo(f"  Run '{Fore.CYAN}savior watch{Style.RESET_ALL}' to start automatic backups")
        return

    backups = savior.list_backups()
    if backups:
        latest = backups[0]
        # Default interval is 20 minutes, but we can't know the actual interval from here
        # We'll estimate based on the default
        next_backup = latest.timestamp + timedelta(minutes=20)
        now = datetime.now()

        if next_backup > now:
            time_until = next_backup - now
            minutes = int(time_until.total_seconds() / 60)
            seconds = int(time_until.total_seconds() % 60)

            click.echo(f"{Fore.CYAN}⏰ Next backup in approximately {minutes} minutes, {seconds} seconds")
            click.echo(f"  Last backup: {format_time_ago(latest.timestamp)}")
            click.echo(f"  Expected at: {next_backup.strftime('%I:%M %p')}")
        else:
            click.echo(f"{Fore.YELLOW}⏳ Backup should happen any moment now...")
            click.echo(f"  Last backup: {format_time_ago(latest.timestamp)}")
    else:
        click.echo(f"{Fore.CYAN}⏰ First backup will occur within 20 minutes")
        click.echo("  Savior is watching and waiting for the right moment")


@cli.command()
@click.option('--depth', '-d', type=int, default=3, help='Maximum depth to display (default: 3)')
@click.option('--no-size', is_flag=True, help='Hide file sizes')
@click.option('--all', '-a', is_flag=True, help='Show ignored files too')
@click.option('--exclude-git', is_flag=True, help='Exclude .git directory from display')
@click.option('--ignore', default='', help='Additional patterns to ignore (comma-separated)')
def tree(depth, no_size, all, exclude_git, ignore):
    """Show project file tree"""
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

@cli.command()
def paths():
    """Show all Savior file locations"""
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


@cli.command()
def sessions():
    """Show watch session history"""
    project_dir = Path.cwd()
    savior = Savior(project_dir)

    metadata = savior._load_metadata()
    sessions = metadata.get('sessions', [])

    if not sessions:
        click.echo(f"{Fore.YELLOW}No watch sessions found")
        click.echo(f"  Run '{Fore.CYAN}savior watch{Style.RESET_ALL}' to start your first session")
        return

    click.echo(f"{Fore.CYAN}Watch Sessions:")
    click.echo("=" * 60)

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


@cli.command('list')
def list_backups():
    """Show all saved backups"""
    project_dir = Path.cwd()
    savior = Savior(project_dir)

    backups = savior.list_backups()

    if not backups:
        click.echo(f"{Fore.YELLOW}No backups found")
        click.echo(f"Run '{Fore.CYAN}savior watch{Style.RESET_ALL}' to start saving")
        return

    click.echo(f"{Fore.CYAN}Available backups:")
    click.echo(f"{Fore.CYAN}{'='*60}")

    for i, backup in enumerate(backups):
        time_ago = format_time_ago(backup.timestamp)
        size = format_size(backup.size)

        click.echo(f"{Fore.WHITE}{i+1:3}. {Fore.GREEN}{time_ago:20} "
                  f"{Fore.YELLOW}[{size:>10}] "
                  f"{Fore.CYAN}{backup.description}")

    click.echo(f"{Fore.CYAN}{'='*60}")
    click.echo(f"Total: {len(backups)} backups, "
              f"{format_size(sum(b.size for b in backups))} total")


@cli.command('saves')
def saves():
    """Show all saved backups (alias for 'list')"""
    ctx = click.get_current_context()
    ctx.invoke(list_backups)


@cli.command('kill')
def kill():
    """Stop watching (alias for 'stop')"""
    ctx = click.get_current_context()
    ctx.invoke(stop_watching)


@cli.command('start')
@click.option('--interval', default=20, help='Backup interval in minutes (default: 20)')
@click.option('--no-smart', is_flag=True, help='Disable smart mode (save even during activity)')
@click.option('--full', is_flag=True, help='Use full backups instead of incremental')
@click.option('--exclude-git', is_flag=True, help='Exclude .git directory from backups (saves space)')
@click.option('--ignore', default='', help='Additional patterns to ignore (comma-separated, e.g. "*.mp4,temp/*")')
@click.option('--background', '-b', is_flag=True, help='Run in background as daemon')
def start(interval, no_smart, full, exclude_git, ignore, background):
    """Start auto-saving (alias for 'watch')"""
    ctx = click.get_current_context()
    ctx.invoke(watch, interval=interval, no_smart=no_smart, full=full,
               exclude_git=exclude_git, ignore=ignore, background=background)


@cli.command()
@click.option('--files', help='Glob pattern for specific files to restore (e.g., "*.py")')
@click.option('--preview', is_flag=True, help='Preview what would be restored')
@click.option('--force', is_flag=True, help='Force restore without conflict checking')
@click.option('--no-backup', is_flag=True, help='Skip creating pre-restore safety backup')
@click.option('--check-conflicts', is_flag=True, help='Check for conflicts and show report without restoring')
def restore(files, preview, force, no_backup, check_conflicts):
    """See all backups and restore one"""
    project_dir = Path.cwd()
    savior = Savior(project_dir)

    backups = savior.list_backups()

    if not backups:
        click.echo(f"{Fore.YELLOW}No backups found to restore")
        return

    click.echo(f"{Fore.CYAN}Available backups:")
    for i, backup in enumerate(backups):
        time_ago = format_time_ago(backup.timestamp)
        click.echo(f"{Fore.WHITE}{i+1}. {Fore.GREEN}{time_ago} "
                  f"{Fore.YELLOW}- \"{backup.description}\"")

    click.echo()
    choice = click.prompt('Which backup?', type=int)

    if 1 <= choice <= len(backups):
        backup_index = choice - 1
        backup = backups[backup_index]

        if files or preview:
            # Partial restore or preview
            import fnmatch
            temp_dir = Path(tempfile.mkdtemp(prefix='savior_restore_'))

            with tarfile.open(backup.path, 'r:gz') as tar:
                tar.extractall(temp_dir)

            files_to_restore = []
            for file_path in temp_dir.rglob('*'):
                if file_path.is_file():
                    rel_path = file_path.relative_to(temp_dir)

                    if files:
                        if not fnmatch.fnmatch(str(rel_path), files):
                            continue

                    files_to_restore.append((file_path, rel_path))

            if not files_to_restore:
                click.echo(f"{Fore.YELLOW}No files match pattern '{files}'")
                shutil.rmtree(temp_dir)
                return

            if preview:
                click.echo(f"{Fore.CYAN}Files that would be restored:")
                for _, rel_path in files_to_restore[:20]:
                    click.echo(f"  - {rel_path}")
                if len(files_to_restore) > 20:
                    click.echo(f"  ... and {len(files_to_restore) - 20} more")
                shutil.rmtree(temp_dir)
                return

            click.echo(f"{Fore.YELLOW}⚠ WARNING: This will overwrite {len(files_to_restore)} file(s)!")
            if click.confirm('Are you sure?'):
                for src_file, rel_path in files_to_restore:
                    dst_file = project_dir / rel_path
                    dst_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dst_file)

                click.echo(f"{Fore.GREEN}✓ Restored {len(files_to_restore)} file(s) from {format_time_ago(backup.timestamp)}!")

            shutil.rmtree(temp_dir)
        else:
            # Full restore
            if check_conflicts:
                # Only check and report conflicts
                try:
                    from .conflicts import ConflictDetector, ConflictResolver
                except ImportError:
                    from conflicts import ConflictDetector, ConflictResolver
                detector = ConflictDetector(project_dir)
                resolver = ConflictResolver(project_dir, project_dir / '.savior')

                # Check for git conflicts
                git_conflicts = detector.detect_git_conflicts()

                if any(git_conflicts.values()):
                    click.echo(f"{Fore.YELLOW}⚠ Git Status Warning:")
                    if git_conflicts['staged']:
                        click.echo(f"  - {len(git_conflicts['staged'])} staged file(s)")
                    if git_conflicts['modified']:
                        click.echo(f"  - {len(git_conflicts['modified'])} modified file(s)")
                    if git_conflicts['untracked']:
                        click.echo(f"  - {len(git_conflicts['untracked'])} untracked file(s)")
                    click.echo(f"\n{Fore.CYAN}Consider committing or stashing changes before restoring.")
                else:
                    click.echo(f"{Fore.GREEN}✓ No git conflicts detected")
                return

            # Show enhanced warning based on conflict detection
            try:
                from .conflicts import ConflictDetector
            except ImportError:
                from conflicts import ConflictDetector
            detector = ConflictDetector(project_dir)
            git_conflicts = detector.detect_git_conflicts()

            warning_msg = f"{Fore.YELLOW}⚠ WARNING: This will overwrite current files!"

            if any(git_conflicts.values()):
                total_conflicts = sum(len(v) for v in git_conflicts.values())
                warning_msg += f"\n  {Fore.RED}• {total_conflicts} uncommitted changes detected!"
                if not no_backup:
                    warning_msg += f"\n  {Fore.CYAN}• A safety backup will be created before restore"

            click.echo(warning_msg)

            if click.confirm('Are you sure?'):
                if savior.restore_backup(backup_index,
                                       check_conflicts=not force,
                                       auto_backup=not no_backup,
                                       force=force):
                    click.echo(f"{Fore.GREEN}✓ Restored to {format_time_ago(backups[backup_index].timestamp)}!")
                else:
                    click.echo(f"{Fore.RED}✗ Failed to restore backup")
    else:
        click.echo(f"{Fore.RED}Invalid choice")


@cli.command()
@click.argument('description', default='Manual backup')
@click.option('--compression', '-c', type=click.IntRange(0, 9), default=6, help='Compression level (0=none, 9=max, default: 6)')
@click.option('--tree', is_flag=True, help='Show what will be backed up')
@click.option('--no-progress', is_flag=True, help='Disable progress bar')
def save(description, compression, tree, no_progress):
    """Force a save right now (without watching)"""
    project_dir = Path.cwd()
    savior = Savior(project_dir)

    # Show tree if requested
    if tree:
        click.echo(f"\n{Fore.CYAN}Files to backup:{Style.RESET_ALL}")
        click.echo(savior.get_project_tree(max_depth=2))
        click.echo()
        if not click.confirm('Proceed with backup?'):
            return

    try:
        backup = savior.create_backup(description, compression_level=compression, show_progress=not no_progress)
        click.echo(f"{Fore.GREEN}✓ Saved backup: \"{description}\"")
        click.echo(f"  Size: {format_size(backup.size)}")
        click.echo(f"  Compression: level {compression}")
    except IOError as e:
        click.echo(f"{Fore.RED}✗ Backup failed: {e}{Style.RESET_ALL}")
        sys.exit(1)
    except ValueError as e:
        click.echo(f"{Fore.YELLOW}⚠ {e}{Style.RESET_ALL}")
        sys.exit(1)


@cli.command()
@click.option('--keep', default=5, help='Number of recent backups to keep')
@click.option('--force', is_flag=True, help='Skip confirmation')
def purge(keep, force):
    """Delete old backups to free space"""
    project_dir = Path.cwd()
    savior = Savior(project_dir)

    backups = savior.list_backups()

    if len(backups) <= keep:
        click.echo(f"{Fore.YELLOW}Nothing to purge (only {len(backups)} backups exist)")
        return

    to_delete = len(backups) - keep
    space_freed = sum(b.size for b in backups[keep:])

    if not force:
        click.echo(f"{Fore.YELLOW}This will delete {to_delete} backup(s), "
                  f"freeing {format_size(space_freed)}")
        if not click.confirm('Continue?'):
            return

    savior.purge_backups(keep)
    click.echo(f"{Fore.GREEN}✓ Purged {to_delete} old backup(s)")
    click.echo(f"  Freed {format_size(space_freed)}")


@cli.command()
@click.option('--backup1', '-b1', type=int, default=1, help='First backup index (newer)')
@click.option('--backup2', '-b2', type=int, default=0, help='Second backup index (0=current, 1=latest backup)')
@click.option('--show-content', is_flag=True, help='Show actual diff content')
def diff(backup1, backup2, show_content):
    """See what changed between backups"""
    project_dir = Path.cwd()
    savior = Savior(project_dir)
    differ = BackupDiffer()

    backups = savior.list_backups()

    if not backups:
        click.echo(f"{Fore.YELLOW}No backups found")
        return

    if backup1 > len(backups) or backup2 > len(backups):
        click.echo(f"{Fore.RED}Invalid backup index")
        return

    if backup2 == 0:
        # Compare backup with current
        backup = backups[backup1 - 1]
        click.echo(f"{Fore.CYAN}Comparing {format_time_ago(backup.timestamp)} with current files...\n")
        added, deleted, modified, diffs = differ.diff_backup_with_current(backup.path, project_dir)
    else:
        # Compare two backups
        b1 = backups[backup1 - 1]
        b2 = backups[backup2 - 1]
        click.echo(f"{Fore.CYAN}Comparing {format_time_ago(b1.timestamp)} with {format_time_ago(b2.timestamp)}...\n")
        added, deleted, modified, diffs = differ.diff_backups(b1.path, b2.path)

    if added:
        click.echo(f"{Fore.GREEN}Added files ({len(added)}):")
        for file in added[:10]:
            click.echo(f"  + {file}")
        if len(added) > 10:
            click.echo(f"  ... and {len(added) - 10} more")

    if deleted:
        click.echo(f"\n{Fore.RED}Deleted files ({len(deleted)}):")
        for file in deleted[:10]:
            click.echo(f"  - {file}")
        if len(deleted) > 10:
            click.echo(f"  ... and {len(deleted) - 10} more")

    if modified:
        click.echo(f"\n{Fore.YELLOW}Modified files ({len(modified)}):")
        for file in modified[:10]:
            click.echo(f"  ~ {file}")
        if len(modified) > 10:
            click.echo(f"  ... and {len(modified) - 10} more")

    if show_content and diffs:
        click.echo(f"\n{Fore.CYAN}{'='*60}")
        for file, diff in diffs[:5]:
            click.echo(f"\n{Fore.WHITE}File: {file}")
            click.echo(diff)
            click.echo(f"{Fore.CYAN}{'-'*60}")
        if len(diffs) > 5:
            click.echo(f"\n... and {len(diffs) - 5} more files with changes")

    if not (added or deleted or modified):
        click.echo(f"{Fore.GREEN}No changes found")


@cli.group()
def cloud():
    """☁️ Self-hosted cloud backup management"""
    pass


@cloud.command('setup')
def cloud_setup():
    """Configure cloud storage (MinIO, Backblaze, NAS, etc.)"""
    storage = CloudStorage()
    storage.setup_wizard()


@cloud.command('sync')
@click.option('--upload-only', is_flag=True, help='Only upload to cloud')
@click.option('--download-only', is_flag=True, help='Only download from cloud')
def cloud_sync(upload_only, download_only):
    """Sync backups with cloud storage"""
    storage = CloudStorage()

    if not storage.is_configured():
        click.echo(f"{Fore.YELLOW}Cloud storage not configured. Run 'savior cloud setup' first.")
        return

    project_dir = Path.cwd()
    savior = Savior(project_dir)
    project_name = project_dir.name

    click.echo(f"{Fore.CYAN}☁️  Syncing with cloud storage...")

    if not download_only:
        # Upload local backups
        backups = savior.list_backups()
        uploaded = 0
        for backup in backups:
            if storage.upload_backup(backup.path, project_name):
                uploaded += 1
                click.echo(f"{Fore.GREEN}  ↑ Uploaded {backup.path.name}")

        if uploaded > 0:
            click.echo(f"{Fore.GREEN}✓ Uploaded {uploaded} backup(s)")

    if not upload_only:
        # Download cloud backups
        cloud_backups = storage.list_backups(project_name)
        downloaded = 0

        for cloud_backup in cloud_backups:
            local_path = savior.backup_dir / Path(cloud_backup['key']).name
            if not local_path.exists():
                if storage.download_backup(cloud_backup['key'], local_path):
                    downloaded += 1
                    click.echo(f"{Fore.GREEN}  ↓ Downloaded {local_path.name}")

        if downloaded > 0:
            click.echo(f"{Fore.GREEN}✓ Downloaded {downloaded} backup(s)")

    click.echo(f"{Fore.CYAN}✓ Sync complete!")


@cloud.command('list')
def cloud_list():
    """List backups in cloud storage"""
    storage = CloudStorage()

    if not storage.is_configured():
        click.echo(f"{Fore.YELLOW}Cloud storage not configured. Run 'savior cloud setup' first.")
        return

    project_name = Path.cwd().name
    backups = storage.list_backups(project_name)

    if not backups:
        click.echo(f"{Fore.YELLOW}No cloud backups found for {project_name}")
        return

    click.echo(f"{Fore.CYAN}☁️  Cloud backups for {project_name}:")
    click.echo(f"{Fore.CYAN}{'='*60}")

    total_size = 0
    for backup in backups:
        size = backup['size']
        total_size += size
        modified = backup['modified']
        name = Path(backup['key']).name

        click.echo(f"  • {name}")
        click.echo(f"    Size: {format_size(size)}")
        click.echo(f"    Modified: {modified}")

    click.echo(f"{Fore.CYAN}{'='*60}")
    click.echo(f"Total: {len(backups)} backups, {format_size(total_size)}")


@cloud.command('download')
@click.argument('backup_name')
def cloud_download(backup_name):
    """Download specific backup from cloud"""
    storage = CloudStorage()

    if not storage.is_configured():
        click.echo(f"{Fore.YELLOW}Cloud storage not configured. Run 'savior cloud setup' first.")
        return

    project_name = Path.cwd().name
    cloud_key = f"{project_name}/{backup_name}"

    savior = Savior(Path.cwd())
    destination = savior.backup_dir / backup_name

    click.echo(f"{Fore.CYAN}Downloading {backup_name}...")

    if storage.download_backup(cloud_key, destination):
        click.echo(f"{Fore.GREEN}✓ Downloaded to {destination}")
    else:
        click.echo(f"{Fore.RED}✗ Failed to download {backup_name}")


@cli.command()
@click.argument('filename', required=False)
def resurrect(filename):
    """Recover specific deleted files from all backups"""
    project_dir = Path.cwd()
    savior = Savior(project_dir)

    backups = savior.list_backups()
    if not backups:
        click.echo(f"{Fore.YELLOW}No backups found")
        return

    found_files = {}

    for backup in backups:
        temp_dir = Path(tempfile.mkdtemp(prefix='savior_resurrect_'))

        with tarfile.open(backup.path, 'r:gz') as tar:
            tar.extractall(temp_dir)

        for file_path in temp_dir.rglob('*'):
            if file_path.is_file():
                rel_path = file_path.relative_to(temp_dir)

                if filename:
                    if filename not in str(rel_path):
                        continue

                if str(rel_path) not in found_files:
                    found_files[str(rel_path)] = []

                found_files[str(rel_path)].append({
                    'backup': backup,
                    'path': file_path,
                    'temp_dir': temp_dir
                })

    if not found_files:
        click.echo(f"{Fore.YELLOW}No files found matching '{filename}'")
        return

    click.echo(f"{Fore.CYAN}Found {len(found_files)} unique file(s) across backups:\n")

    for i, (file_name, versions) in enumerate(found_files.items(), 1):
        current_exists = (project_dir / file_name).exists()
        status = f"{Fore.YELLOW}[EXISTS]" if current_exists else f"{Fore.RED}[DELETED]"

        click.echo(f"{i}. {status} {file_name}")
        click.echo(f"   Found in {len(versions)} backup(s):")

        for v in versions[:3]:
            click.echo(f"     - {format_time_ago(v['backup'].timestamp)}")

        if len(versions) > 3:
            click.echo(f"     ... and {len(versions) - 3} more")

    if click.confirm('\nRestore deleted files?'):
        restored = 0

        for file_name, versions in found_files.items():
            file_path = project_dir / file_name

            if not file_path.exists():
                latest = versions[0]
                file_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(latest['path'], file_path)
                restored += 1
                click.echo(f"{Fore.GREEN}✓ Restored {file_name}")

        click.echo(f"\n{Fore.GREEN}✓ Resurrected {restored} file(s) from the dead!")

    # Cleanup temp dirs
    for versions in found_files.values():
        for v in versions:
            try:
                shutil.rmtree(v['temp_dir'])
            except:
                pass


@cli.command()
@click.option('--restore', is_flag=True, help='Attempt to restore found files')
def pray(restore):
    """🙏 Hail Mary recovery attempt - tries EVERYTHING"""
    click.echo(f"{Fore.MAGENTA}🙏 Initiating deep recovery prayer sequence...")
    click.echo(f"{Fore.MAGENTA}   Searching for any traces of your lost work...\n")

    project_dir = Path.cwd()
    recovery = DeepRecovery(project_dir)

    results = recovery.attempt_recovery()

    click.echo(f"{Fore.CYAN}{'='*60}")
    click.echo(f"{Fore.CYAN}RECOVERY SCAN RESULTS:")
    click.echo(f"{Fore.CYAN}{'='*60}\n")

    # Swap files
    if results['swap_files']:
        click.echo(f"{Fore.GREEN}✓ Editor swap files found: {len(results['swap_files'])}")
        for item in results['swap_files'][:5]:
            click.echo(f"  - {item['path'].name} ({format_time_ago(item['modified'])})")
    else:
        click.echo(f"{Fore.YELLOW}✗ No editor swap files found")

    # Temp files
    if results['temp_files']:
        click.echo(f"\n{Fore.GREEN}✓ Temp files found: {len(results['temp_files'])}")
        for item in results['temp_files'][:5]:
            click.echo(f"  - {item['path'].name} ({format_size(item['size'])})")
    else:
        click.echo(f"\n{Fore.YELLOW}✗ No temp files found")

    # Trash
    if results['trash']:
        click.echo(f"\n{Fore.GREEN}✓ Items in trash: {len(results['trash'])}")
        for item in results['trash'][:5]:
            click.echo(f"  - {item['original_name']} ({format_time_ago(item['modified'])})")
    else:
        click.echo(f"\n{Fore.YELLOW}✗ Nothing found in trash")

    # Git stash
    if results['git_stash']:
        click.echo(f"\n{Fore.GREEN}✓ Git stashes found: {len(results['git_stash'])}")
        for item in results['git_stash'][:3]:
            click.echo(f"  - {item['description']}")
    else:
        click.echo(f"\n{Fore.YELLOW}✗ No git stashes found")

    # Git reflog
    if results['git_reflog']:
        click.echo(f"\n{Fore.GREEN}✓ Git reflog entries: {len(results['git_reflog'])}")
        for item in results['git_reflog'][:3]:
            click.echo(f"  - {item['commit']}: {item['description']}")

    # Open files
    if results['open_files']:
        click.echo(f"\n{Fore.GREEN}✓ Files open in processes: {len(results['open_files'])}")
        for item in results['open_files'][:5]:
            click.echo(f"  - {item['path'].name} (in {item['process']})")

    click.echo(f"\n{Fore.CYAN}{'='*60}")

    if results['total'] > 0:
        click.echo(f"{Fore.GREEN}✓ Total recoverable items: {results['total']}")

        if restore:
            click.echo(f"\n{Fore.YELLOW}⚠ Auto-restore is risky!")
            if click.confirm('Restore swap files and trash items?'):
                restored = 0

                for item in results['swap_files']:
                    if recovery.restore_from_swap(item['path']):
                        restored += 1

                for item in results['trash']:
                    if recovery.restore_from_trash(item['path']):
                        restored += 1

                click.echo(f"{Fore.GREEN}✓ Restored {restored} items")
        else:
            click.echo(f"\n{Fore.CYAN}Tip: Use --restore flag to attempt automatic restoration")
            click.echo(f"{Fore.CYAN}     Or manually recover files from the locations shown above")
    else:
        click.echo(f"{Fore.RED}✗ No recoverable items found")
        click.echo(f"{Fore.YELLOW}\nYour prayers were not answered this time... 😔")
        click.echo(f"{Fore.YELLOW}Maybe try 'savior restore' to check your Savior backups?")


@cli.group()
def daemon():
    """Manage Savior daemon for background operation"""
    pass


@daemon.command('start')
def daemon_start():
    """Start the Savior daemon"""
    try:
        from .daemon import SaviorDaemon
    except ImportError:
        from daemon import SaviorDaemon

    daemon = SaviorDaemon()
    if daemon.is_running():
        click.echo(f"{Fore.YELLOW}⚠ Daemon is already running")
        return

    if daemon.start():
        click.echo(f"{Fore.GREEN}✓ Savior daemon started")
        click.echo("  Run 'savior daemon status' to check watched projects")
    else:
        click.echo(f"{Fore.RED}✗ Failed to start daemon")


@daemon.command('stop')
def daemon_stop():
    """Stop the Savior daemon"""
    try:
        from .daemon import DaemonClient
    except ImportError:
        from daemon import DaemonClient

    client = DaemonClient()
    result = client.stop()

    if 'error' in result:
        click.echo(f"{Fore.RED}✗ {result['error']}")
    else:
        click.echo(f"{Fore.GREEN}✓ Savior daemon stopped")


@daemon.command('status')
def daemon_status():
    """Show daemon status and watched projects"""
    try:
        from .daemon import DaemonClient, SaviorDaemon
    except ImportError:
        from daemon import DaemonClient, SaviorDaemon

    daemon = SaviorDaemon()
    if not daemon.is_running():
        click.echo(f"{Fore.YELLOW}✗ Daemon is not running")
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
    """Add projects to daemon watch list"""
    try:
        from .daemon import DaemonClient, SaviorDaemon
    except ImportError:
        from daemon import DaemonClient, SaviorDaemon

    daemon = SaviorDaemon()
    if not daemon.is_running():
        click.echo(f"{Fore.YELLOW}Starting daemon first...")
        if not daemon.start():
            click.echo(f"{Fore.RED}✗ Failed to start daemon")
            return
        import time
        time.sleep(2)  # Give daemon time to start

    client = DaemonClient()

    for path_str in paths:
        path = Path(path_str).resolve()
        if not path.exists():
            click.echo(f"{Fore.RED}✗ Path does not exist: {path}")
            continue

        result = client.add_project(
            str(path),
            interval=interval,
            smart=not no_smart,  # Invert flag (smart is default)
            incremental=not full,  # Invert flag (incremental is default)
            exclude_git=exclude_git
        )

        if 'error' in result:
            click.echo(f"{Fore.RED}✗ {path}: {result['error']}")
        else:
            click.echo(f"{Fore.GREEN}✓ Added {path} (PID: {result['pid']})")


@daemon.command('remove')
@click.argument('paths', nargs=-1, required=True)
def daemon_remove(paths):
    """Remove projects from daemon watch list"""
    try:
        from .daemon import DaemonClient
    except ImportError:
        from daemon import DaemonClient

    client = DaemonClient()

    for path_str in paths:
        path = Path(path_str).resolve()

        result = client.remove_project(str(path))

        if 'error' in result:
            click.echo(f"{Fore.RED}✗ {path}: {result['error']}")
        else:
            click.echo(f"{Fore.GREEN}✓ Removed {path}")


@cli.group()
def autolaunch():
    """Manage auto-launch on system startup"""
    pass


@autolaunch.command('enable')
@click.option('--with-current', is_flag=True, help='Auto-launch with current directory')
@click.option('--with-projects', multiple=True, help='Auto-launch with specific projects')
def autolaunch_enable(with_current, with_projects):
    """Enable auto-launch on system startup"""
    try:
        from .autolaunch import AutoLauncher
        from .daemon import SaviorDaemon
    except ImportError:
        from autolaunch import AutoLauncher
        from daemon import SaviorDaemon

    launcher = AutoLauncher()

    # Prepare projects list
    projects = []

    if with_current:
        cwd = Path.cwd()
        click.echo(f"Adding current directory: {cwd}")
        projects.append({
            'path': str(cwd),
            'options': {'interval': 20, 'smart': True}
        })

    for project_path in with_projects:
        path = Path(project_path).resolve()
        if path.exists():
            click.echo(f"Adding project: {path}")
            projects.append({
                'path': str(path),
                'options': {'interval': 20, 'smart': True}
            })
        else:
            click.echo(f"{Fore.YELLOW}⚠ Path doesn't exist: {project_path}")

    # Enable auto-launch
    try:
        if launcher.enable(projects if projects else None):
            click.echo(f"{Fore.GREEN}✓ Auto-launch enabled")
            click.echo("  Savior daemon will start automatically on system startup")

            if projects:
                click.echo(f"\n  {len(projects)} project(s) will be auto-watched:")
                for p in projects:
                    click.echo(f"    • {p['path']}")

            # Start daemon now if not running
            daemon = SaviorDaemon()
            if not daemon.is_running():
                click.echo(f"\n{Fore.CYAN}Starting daemon now...")
                if daemon.start():
                    time.sleep(2)

                    # Add projects if specified
                    if projects:
                        try:
                            from .daemon import DaemonClient
                        except ImportError:
                            from daemon import DaemonClient
                        client = DaemonClient()
                        for project in projects:
                            client.add_project(project['path'], **project.get('options', {}))

                    click.echo(f"{Fore.GREEN}✓ Daemon started")
        else:
            click.echo(f"{Fore.RED}✗ Failed to enable auto-launch")
    except NotImplementedError as e:
        click.echo(f"{Fore.RED}✗ {e}")
    except Exception as e:
        click.echo(f"{Fore.RED}✗ Error: {e}")


@autolaunch.command('disable')
def autolaunch_disable():
    """Disable auto-launch on system startup"""
    try:
        from .autolaunch import AutoLauncher
    except ImportError:
        from autolaunch import AutoLauncher

    launcher = AutoLauncher()

    try:
        if launcher.disable():
            click.echo(f"{Fore.GREEN}✓ Auto-launch disabled")
            click.echo("  Savior daemon will no longer start automatically")
        else:
            click.echo(f"{Fore.RED}✗ Failed to disable auto-launch")
    except NotImplementedError as e:
        click.echo(f"{Fore.RED}✗ {e}")
    except Exception as e:
        click.echo(f"{Fore.RED}✗ Error: {e}")


@autolaunch.command('status')
def autolaunch_status():
    """Check auto-launch status"""
    try:
        from .autolaunch import AutoLauncher
    except ImportError:
        from autolaunch import AutoLauncher

    launcher = AutoLauncher()

    if launcher.is_enabled():
        click.echo(f"{Fore.GREEN}✓ Auto-launch is enabled")

        projects = launcher.get_auto_projects()
        if projects:
            click.echo(f"\n  Auto-watch projects:")
            for project in projects:
                click.echo(f"    • {project['path']}")
                options = project.get('options', {})
                if options:
                    click.echo(f"      Options: interval={options.get('interval', 20)}min, " +
                             f"smart={options.get('smart', False)}")
    else:
        click.echo(f"{Fore.YELLOW}○ Auto-launch is disabled")
        click.echo("  Run 'savior autolaunch enable' to enable")


@autolaunch.command('add-project')
@click.argument('path', type=click.Path(exists=True))
@click.option('--interval', '-i', default=20, help='Save interval in minutes')
@click.option('--smart', is_flag=True, help='Use smart activity detection')
def autolaunch_add_project(path, interval, smart):
    """Add a project to auto-launch watch list"""
    try:
        from .autolaunch import AutoLauncher
    except ImportError:
        from autolaunch import AutoLauncher

    launcher = AutoLauncher()
    project_path = Path(path).resolve()

    launcher.add_auto_project(str(project_path), {
        'interval': interval,
        'smart': smart
    })

    click.echo(f"{Fore.GREEN}✓ Added to auto-launch: {project_path}")
    click.echo("  This project will be watched when daemon starts")


@autolaunch.command('remove-project')
@click.argument('path', type=click.Path())
def autolaunch_remove_project(path):
    """Remove a project from auto-launch watch list"""
    try:
        from .autolaunch import AutoLauncher
    except ImportError:
        from autolaunch import AutoLauncher

    launcher = AutoLauncher()
    project_path = Path(path).resolve()

    launcher.remove_auto_project(str(project_path))

    click.echo(f"{Fore.GREEN}✓ Removed from auto-launch: {project_path}")


@cli.command()
@click.argument('paths', nargs=-1)
@click.option('--all', is_flag=True, help='List backups for all projects')
def projects(paths, all):
    """Manage multiple projects at once"""
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
            click.echo(f"{Fore.YELLOW}No Savior projects found")
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
                click.echo(f"{Fore.RED}✗ Path does not exist: {path}")
                continue

            click.echo(f"{Fore.GREEN}✓ Setting up Savior for {path}")

            # You can add logic here to set up watching for each path


@cli.group()
def zombie():
    """🧟 Dead code detection tools"""
    pass


@zombie.command('scan')
@click.option('--json', 'output_json', help='Output results as JSON file')
@click.option('--verbose', is_flag=True, help='Show detailed analysis')
@click.option('--enhanced', is_flag=True, help='Use enhanced detection with confidence scoring')
@click.option('--quarantine', is_flag=True, help='Move dead code to .zombie/ directory')
@click.option('--dry-run', is_flag=True, help='Preview quarantine without moving files')
def zombie_scan(output_json, verbose, enhanced, quarantine, dry_run):
    """Scan for dead code (functions, classes, variables never used)"""
    click.echo(f"{Fore.MAGENTA}🧟 Starting ZOMBIE scan...")
    click.echo(f"{Fore.MAGENTA}   Analyzing your codebase for dead code...\n")

    project_dir = Path.cwd()

    if enhanced:
        click.echo(f"{Fore.CYAN}Using enhanced detection with confidence scoring...\n")
        scanner = ZombieScanner(project_dir)
        zombies = scanner.scan_with_confidence()

        # Show confidence-based results
        if zombies.get('definite'):
            click.echo(f"{Fore.RED}🧟 DEFINITELY DEAD ({len(zombies['definite'])} items):")
            for item in zombies['definite'][:5]:
                click.echo(f"  • {item['name']} - {item['type']} ({item['confidence']:.0%} sure)")
                if item.get('dynamic_refs'):
                    click.echo("    ⚠️  But found in strings/dynamic calls")

        if zombies.get('probable'):
            click.echo(f"\n{Fore.YELLOW}🤔 PROBABLY DEAD ({len(zombies['probable'])} items):")
            for item in zombies['probable'][:3]:
                click.echo(f"  • {item['name']} - {item['type']} ({item['confidence']:.0%} sure)")

        if zombies.get('possible'):
            click.echo(f"\n{Fore.GREEN}❓ POSSIBLY DEAD ({len(zombies['possible'])} items):")
            click.echo(f"  {len(zombies['possible'])} items with low confidence (might be used dynamically)")
    else:
        scanner = ZombieScanner(project_dir)
        zombies = scanner.scan_project()

    # Generate report
    report = scanner.generate_report(zombies)
    click.echo("\n" + report)

    # Handle quarantine
    if quarantine or dry_run:
        quarantine_mgr = QuarantineManager(project_dir)

        if dry_run:
            click.echo(f"\n{Fore.CYAN}🔍 QUARANTINE PREVIEW (dry run):")
            preview = quarantine_mgr.quarantine_code(zombies, dry_run=True)
            click.echo(f"  Would quarantine: {preview['would_quarantine']['total_lines']} lines")
            click.echo(f"  Functions: {preview['would_quarantine']['functions']}")
            click.echo(f"  Classes: {preview['would_quarantine']['classes']}")
            click.echo(f"  Files affected: {len(preview['affected_files'])}")
        elif quarantine:
            click.echo(f"\n{Fore.YELLOW}⚠️  Moving dead code to .zombie/ directory")
            if click.confirm('Are you sure you want to quarantine dead code?'):
                manifest = quarantine_mgr.quarantine_code(zombies, dry_run=False)
                click.echo(f"{Fore.GREEN}✓ Quarantined {len(manifest['items'])} items")
                click.echo("  Saved to .zombie/ with manifest.json")

    # Save JSON if requested
    if output_json:
        output_path = Path(output_json)
        scanner.export_json(zombies, output_path)
        click.echo(f"\n{Fore.GREEN}✓ Results exported to {output_path}")

    # Summary
    total_zombies = (
        len(zombies['functions']) +
        len(zombies['classes']) +
        len(zombies['variables'])
    )

    if total_zombies > 0:
        click.echo(f"\n{Fore.YELLOW}⚠️  Found {total_zombies} potential zombie definitions")
        click.echo(f"{Fore.YELLOW}   {zombies['total_lines']} lines of potentially dead code")

        if verbose:
            click.echo(f"\n{Fore.CYAN}Detailed findings:")
            for func in zombies['functions'][:5]:
                click.echo(f"  • Function '{func['name']}' at {func['file']}:{func['line']}")
            if len(zombies['functions']) > 5:
                click.echo(f"    ... and {len(zombies['functions']) - 5} more functions")
    else:
        click.echo(f"\n{Fore.GREEN}✓ No dead code detected! Your codebase is clean! 🎉")


@zombie.command('check')
@click.argument('name')
def zombie_check(name):
    """Check if a specific function/class/variable is dead"""
    project_dir = Path.cwd()
    scanner = ZombieScanner(project_dir)

    click.echo(f"{Fore.CYAN}Checking '{name}'...")

    # Quick scan
    for file_path in project_dir.rglob('*.py'):
        if scanner.should_scan(file_path):
            scanner.analyzer.analyze_python_file(file_path)

    for file_path in project_dir.rglob('*.js'):
        if scanner.should_scan(file_path):
            scanner.analyzer.analyze_javascript_file(file_path)

    # Check if defined
    if name in scanner.analyzer.definitions:
        defined_in = scanner.analyzer.definitions[name]
        click.echo(f"\n{Fore.GREEN}✓ '{name}' is defined in:")
        for file in defined_in:
            rel_path = Path(file).relative_to(project_dir)
            click.echo(f"  • {rel_path}")

        # Check if referenced
        if name in scanner.analyzer.references:
            referenced_in = scanner.analyzer.references[name]
            click.echo(f"\n{Fore.GREEN}✓ '{name}' is referenced in:")
            for file in referenced_in:
                rel_path = Path(file).relative_to(project_dir)
                click.echo(f"  • {rel_path}")
        else:
            click.echo(f"\n{Fore.YELLOW}⚠️  '{name}' is never referenced - might be dead code!")
    else:
        click.echo(f"{Fore.RED}✗ '{name}' not found in codebase")


@zombie.command('trace')
@click.option('--start', is_flag=True, help='Start runtime tracing')
@click.option('--stop', is_flag=True, help='Stop runtime tracing')
@click.option('--show', is_flag=True, help='Show traced functions')
def zombie_trace(start, stop, show):
    """Runtime tracing to verify what actually gets called"""
    tracer = RuntimeTracer()

    if start:
        click.echo(f"{Fore.GREEN}✓ Starting runtime trace...")
        click.echo("  Functions called will be recorded to .savior/runtime_trace.json")
        tracer.start_tracing()
    elif stop:
        tracer.stop_tracing()
        click.echo(f"{Fore.YELLOW}✓ Runtime trace stopped")
        click.echo("  Results saved to .savior/runtime_trace.json")
    elif show:
        traced = tracer.load_trace()
        if traced:
            click.echo(f"{Fore.CYAN}Functions called during trace:")
            for func in sorted(traced)[:20]:
                click.echo(f"  • {func}")
            if len(traced) > 20:
                click.echo(f"  ... and {len(traced) - 20} more")
        else:
            click.echo(f"{Fore.YELLOW}No trace data found. Run with --start first.")
    else:
        click.echo(f"{Fore.YELLOW}Use --start, --stop, or --show")


@zombie.command('restore')
@click.argument('name', required=False)
def zombie_restore(name):
    """Restore quarantined code back to original files"""
    project_dir = Path.cwd()
    quarantine_mgr = QuarantineManager(project_dir)

    if name:
        result = quarantine_mgr.restore_from_quarantine(name)
        if 'error' in result:
            click.echo(f"{Fore.RED}✗ {result['error']}")
        else:
            click.echo(f"{Fore.GREEN}✓ Restored '{name}' from quarantine")
    else:
        if click.confirm('Restore ALL quarantined code?'):
            result = quarantine_mgr.restore_from_quarantine()
            if 'error' in result:
                click.echo(f"{Fore.RED}✗ {result['error']}")
            else:
                click.echo(f"{Fore.GREEN}✓ Restored {result['count']} items from quarantine")


@zombie.command('stats')
def zombie_stats():
    """Show codebase statistics"""
    project_dir = Path.cwd()

    py_files = list(project_dir.rglob('*.py'))
    js_files = list(project_dir.rglob('*.js')) + list(project_dir.rglob('*.jsx'))
    ts_files = list(project_dir.rglob('*.ts')) + list(project_dir.rglob('*.tsx'))

    total_lines = 0
    for files in [py_files, js_files, ts_files]:
        for file in files:
            try:
                with open(file, 'r') as f:
                    total_lines += len(f.readlines())
            except:
                pass

    click.echo(f"{Fore.CYAN}📊 Codebase Statistics:")
    click.echo(f"  Python files: {len(py_files)}")
    click.echo(f"  JavaScript files: {len(js_files)}")
    click.echo(f"  TypeScript files: {len(ts_files)}")
    click.echo(f"  Total lines: {total_lines:,}")

    # Quick zombie scan
    click.echo(f"\n{Fore.CYAN}Running quick zombie scan...")
    scanner = ZombieScanner(project_dir)
    zombies = scanner.scan_project()

    if zombies['total_lines'] > 0:
        percentage = (zombies['total_lines'] / total_lines) * 100
        click.echo(f"\n{Fore.YELLOW}🧟 Dead code: {zombies['total_lines']:,} lines ({percentage:.1f}%)")
        click.echo(f"  Dead functions: {len(zombies['functions'])}")
        click.echo(f"  Dead classes: {len(zombies['classes'])}")
        click.echo(f"  Dead variables: {len(zombies['variables'])}")
    else:
        click.echo(f"\n{Fore.GREEN}✓ No dead code detected!")


if __name__ == '__main__':
    cli()