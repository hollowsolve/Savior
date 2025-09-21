import os
import sys
import json
import signal
import socket
import threading
import subprocess
import hashlib
import secrets
import stat
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import psutil


class SaviorDaemon:
    def __init__(self):
        self.config_dir = Path.home() / '.savior'
        self.config_dir.mkdir(exist_ok=True, mode=0o700)  # Restrict access
        self.pid_file = self.config_dir / 'daemon.pid'
        self.socket_file = self.config_dir / 'daemon.sock'
        self.projects_file = self.config_dir / 'projects.json'
        self.log_file = self.config_dir / 'daemon.log'
        self.auth_file = self.config_dir / 'daemon.auth'
        self.processes = {}
        self.running = False
        self.auth_token = self._get_or_create_auth_token()
        self.max_projects = 20  # Limit concurrent projects
        self.max_request_size = 1024 * 10  # 10KB max request
        self.client_threads = []

    def _load_projects(self) -> Dict:
        if self.projects_file.exists():
            with open(self.projects_file, 'r') as f:
                return json.load(f)
        return {}

    def _save_projects(self, projects: Dict):
        with open(self.projects_file, 'w') as f:
            json.dump(projects, f, indent=2)

    def _log(self, message: str):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(self.log_file, 'a') as f:
            f.write(f"[{timestamp}] {message}\n")

    def is_running(self) -> bool:
        if not self.pid_file.exists():
            return False

        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())

            # Check if process is running
            return psutil.pid_exists(pid)
        except:
            return False

    def start(self):
        if self.is_running():
            print("Daemon is already running")
            return False

        # Fork to background
        try:
            pid = os.fork()
            if pid > 0:
                # Parent process
                print(f"Daemon started with PID {pid}")
                return True
        except OSError as e:
            print(f"Fork failed: {e}")
            return False

        # Child process - become daemon
        os.setsid()

        # Fork again to prevent zombie
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError:
            sys.exit(1)

        # Redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()

        # Write PID
        with open(self.pid_file, 'w') as f:
            f.write(str(os.getpid()))

        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        self.running = True
        self._log("Daemon started")

        # Start socket server
        self._start_server()

    def _handle_signal(self, signum, frame):
        self._log(f"Received signal {signum}")
        self.stop()

    def _get_or_create_auth_token(self) -> str:
        """Get or create authentication token."""
        if self.auth_file.exists():
            try:
                with open(self.auth_file, 'r') as f:
                    return f.read().strip()
            except:
                pass

        # Generate new token
        token = secrets.token_hex(32)
        try:
            with open(self.auth_file, 'w') as f:
                f.write(token)
            # Restrict permissions
            os.chmod(self.auth_file, stat.S_IRUSR | stat.S_IWUSR)
        except:
            pass
        return token

    def _validate_project_path(self, path: str) -> bool:
        """Validate project path for safety."""
        try:
            project_path = Path(path).resolve()

            # Don't allow system directories
            forbidden = ['/etc', '/bin', '/sbin', '/usr', '/var', '/sys', '/proc']
            for forbidden_path in forbidden:
                if str(project_path).startswith(forbidden_path):
                    return False

            # Must be within user's home or current directory
            home = Path.home()
            cwd = Path.cwd()
            try:
                project_path.relative_to(home)
                return True
            except ValueError:
                try:
                    project_path.relative_to(cwd)
                    return True
                except ValueError:
                    return False
        except:
            return False

    def _start_server(self):
        # Clean up old socket
        if self.socket_file.exists():
            self.socket_file.unlink()

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(self.socket_file))
        # Restrict socket permissions
        os.chmod(self.socket_file, stat.S_IRUSR | stat.S_IWUSR)
        server.listen(5)

        self._log("Server listening on socket")

        while self.running:
            try:
                server.settimeout(1.0)
                client, addr = server.accept()

                # Limit concurrent client connections
                if len(self.client_threads) >= 10:
                    client.close()
                    continue

                thread = threading.Thread(
                    target=self._handle_client,
                    args=(client,),
                    daemon=True
                )
                thread.start()
                self.client_threads.append(thread)

                # Clean up finished threads
                self.client_threads = [t for t in self.client_threads if t.is_alive()]

            except socket.timeout:
                continue
            except Exception as e:
                self._log(f"Server error: {e}")

        server.close()
        if self.socket_file.exists():
            self.socket_file.unlink()

    def _handle_client(self, client: socket.socket):
        try:
            # Set timeout for client operations
            client.settimeout(5.0)

            # Receive data with size limit
            data = client.recv(self.max_request_size).decode('utf-8')
            command = json.loads(data)

            # Validate authentication
            if command.get('auth') != self.auth_token:
                response = {'error': 'Authentication failed'}
            else:
                response = self._process_command(command)

            client.send(json.dumps(response).encode('utf-8'))
        except socket.timeout:
            client.send(json.dumps({'error': 'Request timeout'}).encode('utf-8'))
        except json.JSONDecodeError:
            client.send(json.dumps({'error': 'Invalid JSON'}).encode('utf-8'))
        except Exception as e:
            self._log(f"Client error: {e}")
            client.send(json.dumps({'error': 'Internal error'}).encode('utf-8'))
        finally:
            client.close()

    def _process_command(self, command: Dict) -> Dict:
        cmd_type = command.get('type')

        if cmd_type == 'add_project':
            return self._add_project(command['path'], command.get('options', {}))
        elif cmd_type == 'remove_project':
            return self._remove_project(command['path'])
        elif cmd_type == 'list_projects':
            return self._list_projects()
        elif cmd_type == 'status':
            return self._get_status()
        elif cmd_type == 'stop':
            self.stop()
            return {'status': 'stopping'}
        else:
            return {'error': f'Unknown command: {cmd_type}'}

    def _add_project(self, path: str, options: Dict) -> Dict:
        # Validate project path
        if not self._validate_project_path(path):
            return {'error': 'Invalid or forbidden project path'}

        projects = self._load_projects()

        # Limit number of projects
        if len(projects) >= self.max_projects:
            return {'error': f'Maximum number of projects ({self.max_projects}) reached'}

        if path in projects:
            return {'error': 'Project already being watched'}

        # Start watching process with resource limits
        # Set resource limits for child process
        import resource
        def set_limits():
            # Limit memory (500MB)
            resource.setrlimit(resource.RLIMIT_AS, (500 * 1024 * 1024, 500 * 1024 * 1024))
            # Limit CPU time (1 hour)
            resource.setrlimit(resource.RLIMIT_CPU, (3600, 3600))

        cmd = [
            sys.executable, '-m', 'savior.cli', 'watch',
            '--interval', str(min(options.get('interval', 20), 1440))  # Max 1 day interval
        ]

        if options.get('smart'):
            cmd.append('--smart')
        if options.get('incremental'):
            cmd.append('--incremental')
        if options.get('exclude_git'):
            cmd.append('--exclude-git')

        try:
            process = subprocess.Popen(
                cmd,
                cwd=path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
                preexec_fn=None  # Temporarily disabled due to macOS compatibility issues
            )

            projects[path] = {
                'pid': process.pid,
                'started': datetime.now().isoformat(),
                'options': options
            }
            self._save_projects(projects)
            self.processes[path] = process

            self._log(f"Added project: {path} (PID: {process.pid})")
            return {'status': 'added', 'pid': process.pid}
        except Exception as e:
            return {'error': str(e)}

    def _remove_project(self, path: str) -> Dict:
        projects = self._load_projects()

        if path not in projects:
            return {'error': 'Project not being watched'}

        project = projects[path]

        # Kill the process
        try:
            os.kill(project['pid'], signal.SIGTERM)
        except:
            pass

        del projects[path]
        self._save_projects(projects)

        if path in self.processes:
            del self.processes[path]

        self._log(f"Removed project: {path}")
        return {'status': 'removed'}

    def _list_projects(self) -> Dict:
        projects = self._load_projects()

        # Check if processes are still running
        for path, info in list(projects.items()):
            if not psutil.pid_exists(info['pid']):
                del projects[path]
                self._save_projects(projects)

        return {'projects': projects}

    def _get_status(self) -> Dict:
        projects = self._load_projects()
        return {
            'daemon_pid': os.getpid(),
            'projects_count': len(projects),
            'running': True
        }

    def stop(self):
        self._log("Stopping daemon")
        self.running = False

        # Stop all project watchers
        projects = self._load_projects()
        for path, info in projects.items():
            try:
                os.kill(info['pid'], signal.SIGTERM)
            except:
                pass

        # Clean up
        if self.pid_file.exists():
            self.pid_file.unlink()

        sys.exit(0)


class DaemonClient:
    def __init__(self):
        self.config_dir = Path.home() / '.savior'
        self.socket_file = self.config_dir / 'daemon.sock'
        self.auth_file = self.config_dir / 'daemon.auth'
        self.auth_token = self._load_auth_token()

    def _load_auth_token(self) -> Optional[str]:
        """Load authentication token."""
        if self.auth_file.exists():
            try:
                with open(self.auth_file, 'r') as f:
                    return f.read().strip()
            except:
                pass
        return None

    def send_command(self, command: Dict) -> Dict:
        if not self.socket_file.exists():
            return {'error': 'Daemon not running'}

        if not self.auth_token:
            return {'error': 'Authentication token not found'}

        # Add authentication to command
        command['auth'] = self.auth_token

        try:
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.settimeout(5.0)
            client.connect(str(self.socket_file))

            client.send(json.dumps(command).encode('utf-8'))
            response = client.recv(4096).decode('utf-8')
            client.close()

            return json.loads(response)
        except Exception as e:
            return {'error': str(e)}

    def add_project(self, path: str, **options) -> Dict:
        return self.send_command({
            'type': 'add_project',
            'path': path,
            'options': options
        })

    def remove_project(self, path: str) -> Dict:
        return self.send_command({
            'type': 'remove_project',
            'path': path
        })

    def list_projects(self) -> Dict:
        return self.send_command({'type': 'list_projects'})

    def status(self) -> Dict:
        return self.send_command({'type': 'status'})

    def stop(self) -> Dict:
        return self.send_command({'type': 'stop'})