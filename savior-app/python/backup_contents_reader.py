#!/usr/bin/env python3

import os
import tarfile
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

def build_file_tree(path: Path, base_path: Path = None) -> Dict:
    """Build a file tree structure from a directory."""
    if base_path is None:
        base_path = path

    node = {
        'name': path.name or path.anchor,
        'path': str(path.relative_to(base_path) if base_path != path else '.'),
        'type': 'directory' if path.is_dir() else 'file'
    }

    if path.is_file():
        try:
            node['size'] = path.stat().st_size
        except:
            node['size'] = 0
    elif path.is_dir():
        children = []
        try:
            for item in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name)):
                # Skip .savior directory and common ignore patterns
                if item.name in ['.savior', '__pycache__', '.git', 'node_modules', '.DS_Store']:
                    continue
                children.append(build_file_tree(item, base_path))
            node['children'] = children
        except PermissionError:
            node['children'] = []

    return node

def get_backup_contents(backup_path: str) -> Dict:
    """
    Get the contents of a backup folder or tar file.

    Args:
        backup_path: Path to the backup folder or specific tar file

    Returns:
        Dictionary with file tree structure
    """
    try:
        backup_path = Path(backup_path)

        # Check if it's a directory (backup folder)
        if backup_path.is_dir():
            # Look for the most recent backup file in the directory
            backup_files = []

            # Check for folder structure backups: [HH:MM] [MM-DD-YYYY]
            for folder in backup_path.iterdir():
                if folder.is_dir() and folder.name.startswith('['):
                    for backup_file in folder.glob('*.tar*'):
                        backup_files.append(backup_file)

            # Also check for legacy format in root
            backup_files.extend(backup_path.glob('*.tar*'))

            if not backup_files:
                # If no backups, return the current directory structure
                # (for cases where user wants to see what would be backed up)
                project_path = backup_path.parent
                return {
                    'success': True,
                    'contents': build_file_tree(project_path, project_path)
                }

            # Get the most recent backup
            backup_file = max(backup_files, key=lambda f: f.stat().st_mtime)
        else:
            # It's a specific backup file
            backup_file = backup_path

            if not backup_file.exists():
                return {
                    'success': False,
                    'error': f'Backup file not found: {backup_file}'
                }

        # Extract and read the tar file
        if backup_file.suffix in ['.tar', '.gz']:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Extract the backup
                with tarfile.open(backup_file, 'r:*') as tar:
                    tar.extractall(temp_path)

                # Build the file tree
                contents = build_file_tree(temp_path, temp_path)

                return {
                    'success': True,
                    'contents': contents
                }
        else:
            return {
                'success': False,
                'error': f'Unsupported backup format: {backup_file.suffix}'
            }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def extract_file_from_backup(backup_path: str, file_path: str, destination: str = None) -> Dict:
    """
    Extract a specific file from a backup.

    Args:
        backup_path: Path to the backup tar file
        file_path: Path of the file within the backup to extract
        destination: Where to extract the file (defaults to Desktop)

    Returns:
        Dictionary with success status and extracted file path
    """
    try:
        backup_file = Path(backup_path)

        if not backup_file.exists():
            return {
                'success': False,
                'error': f'Backup file not found: {backup_file}'
            }

        # Default destination is Desktop
        if destination is None:
            destination = Path.home() / 'Desktop'
        else:
            destination = Path(destination)

        destination.mkdir(parents=True, exist_ok=True)

        # Extract the specific file
        with tarfile.open(backup_file, 'r:*') as tar:
            # Find the member
            member = None
            for m in tar.getmembers():
                if m.name == file_path or m.name.endswith(f'/{file_path}'):
                    member = m
                    break

            if not member:
                return {
                    'success': False,
                    'error': f'File not found in backup: {file_path}'
                }

            # Extract to destination
            tar.extract(member, destination)
            extracted_path = destination / member.name

            return {
                'success': True,
                'path': str(extracted_path)
            }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

# CLI interface for testing
if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python backup_contents_reader.py <backup_path> [file_to_extract]")
        sys.exit(1)

    backup_path = sys.argv[1]

    if len(sys.argv) > 2:
        # Extract specific file
        file_path = sys.argv[2]
        result = extract_file_from_backup(backup_path, file_path)
    else:
        # List contents
        result = get_backup_contents(backup_path)

    print(json.dumps(result, indent=2))