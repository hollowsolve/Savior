#!/usr/bin/env python3
"""
Main entry point for the savior package.
This allows the package to be run as: python -m savior
"""

from .cli import cli

if __name__ == '__main__':
    cli()