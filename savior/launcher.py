#!/usr/bin/env python3
"""
Universal launcher for Savior that works regardless of how it's invoked.
This script can be called directly and will properly set up the Python path.
"""

import sys
import os
from pathlib import Path

def setup_path():
    """Setup Python path to ensure imports work correctly."""
    # Get the directory containing this script
    script_dir = Path(__file__).parent.absolute()

    # Add parent directory to path if not already there
    parent_dir = script_dir.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))

    # Also add the script directory itself
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))

    return script_dir

def main():
    """Main entry point that sets up environment and runs CLI."""
    setup_path()

    # Now we can import the CLI
    try:
        # Try importing as a package first
        from savior.cli import cli
    except ImportError:
        try:
            # Try importing from current directory
            from cli import cli
        except ImportError:
            # Last resort - try to import after adding to path
            import cli
            cli = cli.cli

    # Run the CLI
    cli()

if __name__ == '__main__':
    main()