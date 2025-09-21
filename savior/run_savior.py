#!/usr/bin/env python3
"""
Cross-platform runner for Savior CLI.
This script automatically detects the best way to run Savior on any system.
"""

import sys
import os
import subprocess
from pathlib import Path

def find_python():
    """Find the best Python interpreter to use."""
    # Try different Python commands in order of preference
    python_commands = ['python3', 'python', sys.executable]

    for cmd in python_commands:
        try:
            result = subprocess.run(
                [cmd, '--version'],
                capture_output=True,
                text=True,
                timeout=1
            )
            if result.returncode == 0:
                return cmd
        except (subprocess.SubprocessError, FileNotFoundError):
            continue

    # Fallback to current interpreter
    return sys.executable

def run_as_module():
    """Try to run savior as a module."""
    python = find_python()
    script_dir = Path(__file__).parent.absolute()
    parent_dir = script_dir.parent

    # Set up environment
    env = os.environ.copy()
    if 'PYTHONPATH' in env:
        env['PYTHONPATH'] = f"{parent_dir}{os.pathsep}{env['PYTHONPATH']}"
    else:
        env['PYTHONPATH'] = str(parent_dir)

    # Try running as module
    cmd = [python, '-m', 'savior.cli'] + sys.argv[1:]

    try:
        result = subprocess.run(cmd, env=env)
        return result.returncode
    except subprocess.SubprocessError:
        return None

def run_launcher():
    """Run using the launcher script."""
    python = find_python()
    launcher = Path(__file__).parent / 'launcher.py'

    if launcher.exists():
        cmd = [python, str(launcher)] + sys.argv[1:]
        try:
            result = subprocess.run(cmd)
            return result.returncode
        except subprocess.SubprocessError:
            return None
    return None

def run_direct():
    """Run CLI script directly with proper path setup."""
    # Setup path
    script_dir = Path(__file__).parent.absolute()
    parent_dir = script_dir.parent

    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))

    # Import and run
    try:
        from savior.cli import cli
        cli()
        return 0
    except ImportError:
        try:
            from cli import cli
            cli()
            return 0
        except ImportError:
            return None

def main():
    """Main entry point that tries different methods."""
    # Try methods in order of preference
    methods = [
        ('module', run_as_module),
        ('launcher', run_launcher),
        ('direct', run_direct)
    ]

    for name, method in methods:
        try:
            result = method()
            if result is not None:
                sys.exit(result)
        except Exception as e:
            # Continue to next method
            continue

    # If all methods failed
    print("Error: Could not run Savior CLI. Please check your installation.", file=sys.stderr)
    sys.exit(1)

if __name__ == '__main__':
    main()