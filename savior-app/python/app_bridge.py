#!/usr/bin/env python3
"""
Python bridge for Savior desktop app.
Interfaces with the existing Savior CLI/core functionality.
"""

import sys
import os
import json
import time
import threading
import queue
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

# Add parent directory to path to import savior modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from savior.core import SaviorCore
    from savior.daemon import SaviorDaemon
    from savior.cloud import CloudStorage
    from savior.conflicts import ConflictDetector
except ImportError as e:
    print(json.dumps({
        'type': 'error',
        'message': f'Failed to import Savior modules: {e}'
    }))
    sys.exit(1)


class SaviorAppBridge:
    def __init__(self):
        self.daemon = SaviorDaemon()
        self.config_dir = Path.home() / '.savior'
        self.config_dir.mkdir(exist_ok=True)
        self.projects_file = self.config_dir / 'projects.json'
        self.running = True
        self.command_queue = queue.Queue()
        self.watchers = {}  # Store active watcher threads

        # Send ready signal
        self.send_message({
            'type': 'ready',
            'timestamp': time.time()
        })

    def send_message(self, message: Dict[str, Any]):
        """Send JSON message to Electron process via stdout"""
        try:
            print(json.dumps(message), flush=True)
        except Exception as e:
            sys.stderr.write(f"Failed to send message: {e}\n")

    def send_event(self, name: str, data: Any):
        """Send event to Electron process"""
        self.send_message({
            'type': 'event',
            'name': name,
            'data': data,
            'timestamp': time.time()
        })

    def send_response(self, command_id: str, success: bool, data: Any = None, error: str = None):
        """Send command response to Electron process"""
        self.send_message({
            'type': 'response',
            'id': command_id,
            'success': success,
            'data': data,
            'error': error,
            'timestamp': time.time()
        })

    def load_projects(self) -> List[Dict[str, Any]]:
        """Load projects from config file"""
        if self.projects_file.exists():
            try:
                with open(self.projects_file, 'r') as f:
                    projects_data = json.load(f)

                # Convert to list format with status
                projects = []
                for path, info in projects_data.items():
                    project = {
                        'path': path,
                        'name': Path(path).name,
                        'active': self.daemon.is_watching(path) if self.daemon.is_running() else False,
                        'lastBackup': info.get('last_backup'),
                        'backupCount': info.get('backup_count', 0),
                        'size': info.get('total_size', 0)
                    }
                    projects.append(project)

                return projects
            except Exception as e:
                self.send_event('error', {'message': f'Failed to load projects: {e}'})

        return []

    def handle_command(self, command: Dict[str, Any]):
        """Handle command from Electron process"""
        try:
            action = command.get('action')
            params = command.get('params', {})
            command_id = command.get('id')

            if action == 'get_projects':
                projects = self.load_projects()
                self.send_response(command_id, True, projects)

            elif action == 'watch':
                self.start_watching(params.get('path'), params, command_id)

            elif action == 'stop':
                self.stop_watching(params.get('path'), command_id)

            elif action == 'save':
                self.force_backup(params.get('path'), params.get('description', ''), command_id)

            elif action == 'get_backups':
                backups = self.get_backups(params.get('path'))
                self.send_response(command_id, True, backups)

            elif action == 'restore':
                self.restore_backup(
                    params.get('path'),
                    params.get('backup_id'),
                    params,
                    command_id
                )

            elif action == 'daemon_status':
                status = self.get_daemon_status()
                self.send_response(command_id, True, status)

            elif action == 'daemon_start':
                success = self.daemon.start()
                self.send_response(command_id, success)
                if success:
                    self.send_event('daemon_status', {'running': True})

            elif action == 'daemon_stop':
                success = self.daemon.stop()
                self.send_response(command_id, success)
                if success:
                    self.send_event('daemon_status', {'running': False})

            elif action == 'daemon_add':
                self.add_to_daemon(params.get('path'), command_id)

            elif action == 'daemon_remove':
                self.remove_from_daemon(params.get('path'), command_id)

            elif action == 'cloud_status':
                cloud_status = self.get_cloud_status()
                self.send_response(command_id, True, cloud_status)

            elif action == 'cloud_setup':
                self.setup_cloud(params, command_id)

            elif action == 'cloud_sync':
                self.sync_cloud(params.get('path'), command_id)

            elif action == 'refresh_status':
                # Refresh and send current status
                projects = self.load_projects()
                self.send_event('projects_updated', projects)
                self.send_response(command_id, True)

            elif action == 'shutdown':
                self.running = False
                self.send_response(command_id, True)

            else:
                self.send_response(command_id, False, error=f'Unknown action: {action}')

        except Exception as e:
            self.send_response(
                command.get('id'),
                False,
                error=str(e)
            )
            self.send_event('error', {'message': str(e)})

    def start_watching(self, project_path: str, options: Dict[str, Any], command_id: str):
        """Start watching a project"""
        try:
            # Create a SaviorCore instance for this project
            core = SaviorCore(
                Path(project_path),
                exclude_git=options.get('exclude_git', False),
                compression_level=options.get('compression', 6)
            )

            # Start watching in a separate thread
            def watch_thread():
                try:
                    # Send started event
                    self.send_event('backup_started', {
                        'path': project_path,
                        'timestamp': time.time()
                    })

                    # Perform the backup
                    core.save_backup(
                        description=options.get('description', 'Auto-backup from Savior app'),
                        incremental=options.get('incremental', True)
                    )

                    # Send completed event
                    self.send_event('backup_completed', {
                        'path': project_path,
                        'timestamp': time.time()
                    })

                except Exception as e:
                    self.send_event('error', {
                        'message': f'Backup failed for {project_path}: {e}',
                        'path': project_path
                    })

            # Store the watcher thread
            if project_path not in self.watchers:
                thread = threading.Thread(target=watch_thread)
                thread.daemon = True
                thread.start()
                self.watchers[project_path] = thread

            self.send_response(command_id, True)

            # Update projects list
            projects = self.load_projects()
            self.send_event('projects_updated', projects)

        except Exception as e:
            self.send_response(command_id, False, error=str(e))

    def stop_watching(self, project_path: str, command_id: str):
        """Stop watching a project"""
        try:
            # Remove from watchers
            if project_path in self.watchers:
                del self.watchers[project_path]

            self.send_response(command_id, True)

            # Update projects list
            projects = self.load_projects()
            self.send_event('projects_updated', projects)

        except Exception as e:
            self.send_response(command_id, False, error=str(e))

    def force_backup(self, project_path: str, description: str, command_id: str):
        """Force an immediate backup"""
        try:
            core = SaviorCore(Path(project_path))

            # Send started event
            self.send_event('backup_started', {
                'path': project_path,
                'timestamp': time.time()
            })

            # Perform backup
            backup_path = core.save_backup(description=description)

            # Send completed event
            self.send_event('backup_completed', {
                'path': project_path,
                'backup_path': str(backup_path),
                'timestamp': time.time()
            })

            self.send_response(command_id, True, {'backup_path': str(backup_path)})

        except Exception as e:
            self.send_response(command_id, False, error=str(e))

    def get_backups(self, project_path: str) -> List[Dict[str, Any]]:
        """Get list of backups for a project"""
        try:
            core = SaviorCore(Path(project_path))
            backups_dir = core.backup_dir

            backups = []
            if backups_dir.exists():
                for backup_file in sorted(backups_dir.glob('*.tar.gz'), reverse=True):
                    # Parse backup filename
                    name = backup_file.stem.replace('.tar', '')
                    parts = name.split('_', 2)

                    backup_info = {
                        'id': backup_file.name,
                        'name': name,
                        'path': str(backup_file),
                        'size': backup_file.stat().st_size,
                        'timestamp': backup_file.stat().st_mtime,
                        'date': datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat()
                    }

                    # Extract description if available
                    if len(parts) > 2:
                        backup_info['description'] = parts[2].replace('_', ' ')

                    backups.append(backup_info)

            return backups

        except Exception as e:
            self.send_event('error', {'message': f'Failed to get backups: {e}'})
            return []

    def restore_backup(self, project_path: str, backup_id: str, options: Dict[str, Any], command_id: str):
        """Restore a backup"""
        try:
            core = SaviorCore(Path(project_path))

            # Check for conflicts if requested
            if options.get('check_conflicts', True):
                detector = ConflictDetector(Path(project_path))
                conflicts = detector.detect_conflicts()

                if conflicts.uncommitted_files:
                    self.send_response(command_id, False, error='Uncommitted changes detected')
                    return

            # Perform restore
            backup_file = core.backup_dir / backup_id
            core.restore_backup(backup_file, force=options.get('force', False))

            self.send_response(command_id, True)
            self.send_event('restore_completed', {
                'path': project_path,
                'backup_id': backup_id
            })

        except Exception as e:
            self.send_response(command_id, False, error=str(e))

    def get_daemon_status(self) -> Dict[str, Any]:
        """Get daemon status"""
        return {
            'running': self.daemon.is_running(),
            'pid': self.daemon.get_pid() if self.daemon.is_running() else None,
            'projects': len(self.load_projects())
        }

    def add_to_daemon(self, project_path: str, command_id: str):
        """Add project to daemon watching"""
        try:
            if not self.daemon.is_running():
                self.daemon.start()

            success = self.daemon.add_project(Path(project_path))
            self.send_response(command_id, success)

            # Update projects list
            projects = self.load_projects()
            self.send_event('projects_updated', projects)

        except Exception as e:
            self.send_response(command_id, False, error=str(e))

    def remove_from_daemon(self, project_path: str, command_id: str):
        """Remove project from daemon watching"""
        try:
            success = self.daemon.remove_project(Path(project_path))
            self.send_response(command_id, success)

            # Update projects list
            projects = self.load_projects()
            self.send_event('projects_updated', projects)

        except Exception as e:
            self.send_response(command_id, False, error=str(e))

    def get_cloud_status(self) -> Dict[str, Any]:
        """Get cloud storage status"""
        try:
            cloud = CloudStorage()
            return {
                'configured': cloud.is_configured(),
                'provider': cloud.provider if cloud.is_configured() else None,
                'last_sync': cloud.get_last_sync_time()
            }
        except:
            return {'configured': False}

    def setup_cloud(self, config: Dict[str, Any], command_id: str):
        """Setup cloud storage configuration"""
        try:
            cloud = CloudStorage()
            cloud.configure(config)
            self.send_response(command_id, True)
        except Exception as e:
            self.send_response(command_id, False, error=str(e))

    def sync_cloud(self, project_path: Optional[str], command_id: str):
        """Sync with cloud storage"""
        try:
            cloud = CloudStorage()

            if project_path:
                cloud.sync_project(Path(project_path))
            else:
                cloud.sync_all()

            self.send_response(command_id, True)
            self.send_event('cloud_sync_completed', {
                'timestamp': time.time()
            })

        except Exception as e:
            self.send_response(command_id, False, error=str(e))

    def run(self):
        """Main loop to process commands from stdin"""
        try:
            while self.running:
                # Read command from stdin
                line = sys.stdin.readline()
                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    command = json.loads(line)
                    # Process command in a separate thread to avoid blocking
                    threading.Thread(
                        target=self.handle_command,
                        args=(command,),
                        daemon=True
                    ).start()

                except json.JSONDecodeError as e:
                    self.send_event('error', {'message': f'Invalid JSON: {e}'})

        except KeyboardInterrupt:
            pass
        except Exception as e:
            self.send_event('error', {'message': f'Bridge error: {e}'})
        finally:
            sys.exit(0)


if __name__ == '__main__':
    bridge = SaviorAppBridge()
    bridge.run()