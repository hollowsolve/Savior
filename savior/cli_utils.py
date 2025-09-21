"""Utility functions for CLI operations."""

import sys
import select
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict
import click
from colorama import Fore, Style


def format_time_ago(timestamp: datetime) -> str:
    """Format timestamp as human-readable time ago."""
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
    """Format bytes as human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def check_keyboard_input():
    """Check if a key has been pressed (non-blocking)."""
    if sys.platform == 'win32':
        import msvcrt
        return msvcrt.kbhit()
    else:
        return select.select([sys.stdin], [], [], 0)[0] != []


def print_success(message: str):
    """Print a success message with green checkmark."""
    click.echo(f"{Fore.GREEN}✓ {message}")


def print_error(message: str):
    """Print an error message with red X."""
    click.echo(f"{Fore.RED}✗ {message}")


def print_warning(message: str):
    """Print a warning message with yellow warning sign."""
    click.echo(f"{Fore.YELLOW}⚠ {message}")


def print_info(message: str):
    """Print an info message with cyan color."""
    click.echo(f"{Fore.CYAN}{message}")


def print_header(title: str):
    """Print a styled header."""
    click.echo(f"\n{Fore.CYAN}{'=' * 40}")
    click.echo(f"{Fore.WHITE}{title}")
    click.echo(f"{Fore.CYAN}{'=' * 40}\n")


def confirm_action(message: str, default: bool = False) -> bool:
    """Ask user for confirmation with colored prompt."""
    return click.confirm(f"{Fore.YELLOW}{message}", default=default)


def select_from_list(items: List, prompt: str, formatter=None) -> Optional[int]:
    """Present a numbered list for user selection."""
    if not items:
        return None

    click.echo(f"{Fore.CYAN}{prompt}:")
    for i, item in enumerate(items, 1):
        if formatter:
            click.echo(f"{Fore.WHITE}{i}. {formatter(item)}")
        else:
            click.echo(f"{Fore.WHITE}{i}. {item}")

    click.echo()
    choice = click.prompt('Which one?', type=int)

    if 1 <= choice <= len(items):
        return choice - 1
    return None


def display_stats(stats: Dict):
    """Display statistics in a formatted way."""
    for key, value in stats.items():
        if isinstance(value, (int, float)):
            if 'size' in key.lower() or 'bytes' in key.lower():
                value = format_size(value)
            elif isinstance(value, float):
                value = f"{value:.2%}" if value < 1 else f"{value:.2f}"

        key_display = key.replace('_', ' ').title()
        click.echo(f"{Fore.CYAN}{key_display}: {Fore.WHITE}{value}")


def create_progress_callback(description: str):
    """Create a callback for progress reporting."""
    def callback(current: int, total: int):
        percent = (current / total * 100) if total > 0 else 0
        click.echo(f"\r{description}: {percent:.1f}%", nl=False)
        if current >= total:
            click.echo()  # New line at completion
    return callback