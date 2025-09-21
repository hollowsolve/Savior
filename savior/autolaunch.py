import os
import sys
import platform
import subprocess
import json
from pathlib import Path
from typing import Optional, Dict, List


class AutoLauncher:
    def __init__(self):
        self.system = platform.system()
        self.config_dir = Path.home() / '.savior'
        self.config_dir.mkdir(exist_ok=True)
        self.autolaunch_config = self.config_dir / 'autolaunch.json'

    def _load_config(self) -> Dict:
        if self.autolaunch_config.exists():
            with open(self.autolaunch_config, 'r') as f:
                return json.load(f)
        return {'enabled': False, 'projects': []}

    def _save_config(self, config: Dict):
        with open(self.autolaunch_config, 'w') as f:
            json.dump(config, f, indent=2)

    def is_enabled(self) -> bool:
        config = self._load_config()
        return config.get('enabled', False)

    def get_auto_projects(self) -> List[Dict]:
        config = self._load_config()
        return config.get('projects', [])

    def add_auto_project(self, path: str, options: Dict = None):
        config = self._load_config()
        projects = config.get('projects', [])

        # Check if project already exists
        for p in projects:
            if p['path'] == path:
                p['options'] = options or {}
                self._save_config(config)
                return

        projects.append({
            'path': path,
            'options': options or {}
        })
        config['projects'] = projects
        self._save_config(config)

    def remove_auto_project(self, path: str):
        config = self._load_config()
        projects = config.get('projects', [])
        config['projects'] = [p for p in projects if p['path'] != path]
        self._save_config(config)

    def enable(self, with_projects: List[Dict] = None) -> bool:
        if self.system == 'Darwin':
            return self._enable_macos(with_projects)
        elif self.system == 'Linux':
            return self._enable_linux(with_projects)
        elif self.system == 'Windows':
            return self._enable_windows(with_projects)
        else:
            raise NotImplementedError(f"Auto-launch not supported on {self.system}")

    def disable(self) -> bool:
        if self.system == 'Darwin':
            return self._disable_macos()
        elif self.system == 'Linux':
            return self._disable_linux()
        elif self.system == 'Windows':
            return self._disable_windows()
        else:
            raise NotImplementedError(f"Auto-launch not supported on {self.system}")

    def _enable_macos(self, with_projects: List[Dict] = None) -> bool:
        # Create launchd plist
        plist_path = Path.home() / 'Library' / 'LaunchAgents' / 'com.savior.daemon.plist'
        plist_path.parent.mkdir(exist_ok=True, parents=True)

        # Get Python executable path
        python_path = sys.executable

        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.savior.daemon</string>

    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>-m</string>
        <string>savior.autolaunch</string>
        <string>--start-daemon</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>

    <key>StandardOutPath</key>
    <string>{str(self.config_dir)}/autolaunch.log</string>

    <key>StandardErrorPath</key>
    <string>{str(self.config_dir)}/autolaunch_error.log</string>

    <key>WorkingDirectory</key>
    <string>{str(Path.home())}</string>
</dict>
</plist>"""

        with open(plist_path, 'w') as f:
            f.write(plist_content)

        # Load the launch agent
        try:
            subprocess.run(['launchctl', 'unload', str(plist_path)],
                         capture_output=True, check=False)
            subprocess.run(['launchctl', 'load', str(plist_path)],
                         capture_output=True, check=True)

            # Save config
            config = self._load_config()
            config['enabled'] = True
            if with_projects:
                config['projects'] = with_projects
            self._save_config(config)

            return True
        except subprocess.CalledProcessError:
            return False

    def _disable_macos(self) -> bool:
        plist_path = Path.home() / 'Library' / 'LaunchAgents' / 'com.savior.daemon.plist'

        if plist_path.exists():
            try:
                subprocess.run(['launchctl', 'unload', str(plist_path)],
                             capture_output=True, check=False)
                plist_path.unlink()
            except:
                pass

        config = self._load_config()
        config['enabled'] = False
        self._save_config(config)

        return True

    def _enable_linux(self, with_projects: List[Dict] = None) -> bool:
        # Create systemd user service
        service_dir = Path.home() / '.config' / 'systemd' / 'user'
        service_dir.mkdir(exist_ok=True, parents=True)
        service_path = service_dir / 'savior-daemon.service'

        python_path = sys.executable

        service_content = f"""[Unit]
Description=Savior Daemon - Automatic backup service
After=graphical-session.target

[Service]
Type=forking
ExecStart={python_path} -m savior.autolaunch --start-daemon
ExecStop={python_path} -m savior.cli daemon stop
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target"""

        with open(service_path, 'w') as f:
            f.write(service_content)

        try:
            # Reload systemd
            subprocess.run(['systemctl', '--user', 'daemon-reload'],
                         capture_output=True, check=True)
            # Enable and start service
            subprocess.run(['systemctl', '--user', 'enable', 'savior-daemon.service'],
                         capture_output=True, check=True)
            subprocess.run(['systemctl', '--user', 'start', 'savior-daemon.service'],
                         capture_output=True, check=True)

            config = self._load_config()
            config['enabled'] = True
            if with_projects:
                config['projects'] = with_projects
            self._save_config(config)

            return True
        except subprocess.CalledProcessError:
            return False

    def _disable_linux(self) -> bool:
        try:
            subprocess.run(['systemctl', '--user', 'stop', 'savior-daemon.service'],
                         capture_output=True, check=False)
            subprocess.run(['systemctl', '--user', 'disable', 'savior-daemon.service'],
                         capture_output=True, check=False)
        except:
            pass

        service_path = Path.home() / '.config' / 'systemd' / 'user' / 'savior-daemon.service'
        if service_path.exists():
            service_path.unlink()

        config = self._load_config()
        config['enabled'] = False
        self._save_config(config)

        return True

    def _enable_windows(self, with_projects: List[Dict] = None) -> bool:
        # Use Windows Task Scheduler
        python_path = sys.executable.replace('\\', '\\\\')

        # Create VBS script to run hidden
        vbs_path = self.config_dir / 'start_savior.vbs'
        vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """{python_path}"" -m savior.autolaunch --start-daemon", 0
Set WshShell = Nothing'''

        with open(vbs_path, 'w') as f:
            f.write(vbs_content)

        # Create scheduled task
        task_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>wscript.exe</Command>
      <Arguments>"{str(vbs_path)}"</Arguments>
    </Exec>
  </Actions>
</Task>"""

        xml_path = self.config_dir / 'savior_task.xml'
        with open(xml_path, 'w', encoding='utf-16') as f:
            f.write(task_xml)

        try:
            # Delete existing task if it exists
            subprocess.run(['schtasks', '/delete', '/tn', 'SaviorDaemon', '/f'],
                         capture_output=True, check=False)
            # Create new task
            subprocess.run(['schtasks', '/create', '/xml', str(xml_path), '/tn', 'SaviorDaemon'],
                         capture_output=True, check=True)

            config = self._load_config()
            config['enabled'] = True
            if with_projects:
                config['projects'] = with_projects
            self._save_config(config)

            return True
        except subprocess.CalledProcessError:
            return False

    def _disable_windows(self) -> bool:
        try:
            subprocess.run(['schtasks', '/delete', '/tn', 'SaviorDaemon', '/f'],
                         capture_output=True, check=False)
        except:
            pass

        config = self._load_config()
        config['enabled'] = False
        self._save_config(config)

        return True


def start_daemon_with_projects():
    """Start daemon and add auto-launch projects"""
    from .daemon import SaviorDaemon, DaemonClient

    launcher = AutoLauncher()
    config = launcher._load_config()

    # Start daemon if not running
    daemon = SaviorDaemon()
    if not daemon.is_running():
        daemon.start()
        import time
        time.sleep(2)  # Give daemon time to start

    # Add auto-launch projects
    client = DaemonClient()
    for project in config.get('projects', []):
        result = client.add_project(project['path'], **project.get('options', {}))
        if 'error' not in result:
            print(f"Auto-started watching: {project['path']}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--start-daemon', action='store_true', help='Start daemon with auto projects')
    args = parser.parse_args()

    if args.start_daemon:
        start_daemon_with_projects()