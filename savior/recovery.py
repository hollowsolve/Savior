import os
import tempfile
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import psutil


class DeepRecovery:
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.recovered_files = []

    def find_editor_swap_files(self) -> List[Dict]:
        recovered = []

        swap_patterns = [
            '.*.swp',  # Vim swap files
            '.*.swo',
            '.*.swn',
            '*~',      # Emacs/general backup
            '.#*',     # Emacs lock files
            '#*#',     # Emacs autosave
            '*.tmp',   # Temp files
            '.*.kate-swp',  # Kate editor
            '.~lock.*#',    # LibreOffice
        ]

        for pattern in swap_patterns:
            for file in self.project_dir.rglob(pattern):
                try:
                    stat = file.stat()
                    recovered.append({
                        'path': file,
                        'type': 'swap_file',
                        'modified': datetime.fromtimestamp(stat.st_mtime),
                        'size': stat.st_size,
                        'pattern': pattern
                    })
                except:
                    pass

        return recovered

    def find_temp_files(self) -> List[Dict]:
        recovered = []
        temp_dirs = [
            Path('/tmp'),
            Path('/var/tmp'),
            Path(tempfile.gettempdir()),
            Path.home() / 'Library' / 'Caches' if os.name == 'darwin' else None,
            Path.home() / '.cache' if os.name == 'posix' else None,
        ]

        project_name = self.project_dir.name

        for temp_dir in filter(None, temp_dirs):
            if not temp_dir.exists():
                continue

            for file in temp_dir.rglob('*'):
                if file.is_file() and project_name.lower() in str(file).lower():
                    try:
                        stat = file.stat()
                        recovered.append({
                            'path': file,
                            'type': 'temp_file',
                            'modified': datetime.fromtimestamp(stat.st_mtime),
                            'size': stat.st_size,
                            'location': str(temp_dir)
                        })
                    except:
                        pass

        return recovered

    def check_trash(self) -> List[Dict]:
        recovered = []

        trash_paths = []
        if os.name == 'darwin':  # macOS
            trash_paths.append(Path.home() / '.Trash')
        elif os.name == 'posix':  # Linux
            trash_paths.extend([
                Path.home() / '.local' / 'share' / 'Trash' / 'files',
                Path.home() / '.trash'
            ])

        project_name = self.project_dir.name

        for trash in trash_paths:
            if not trash.exists():
                continue

            for item in trash.iterdir():
                if project_name.lower() in item.name.lower():
                    try:
                        stat = item.stat()
                        recovered.append({
                            'path': item,
                            'type': 'trash',
                            'modified': datetime.fromtimestamp(stat.st_mtime),
                            'size': stat.st_size if item.is_file() else 0,
                            'original_name': item.name
                        })
                    except:
                        pass

        return recovered

    def find_process_files(self) -> List[Dict]:
        recovered = []

        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] in ['python', 'node', 'vim', 'emacs', 'code', 'sublime']:
                        for file in proc.open_files():
                            if str(self.project_dir) in file.path:
                                recovered.append({
                                    'path': Path(file.path),
                                    'type': 'open_in_process',
                                    'process': proc.info['name'],
                                    'pid': proc.info['pid']
                                })
                except:
                    pass
        except:
            pass

        return recovered

    def check_git_stash(self) -> List[Dict]:
        recovered = []

        if (self.project_dir / '.git').exists():
            try:
                result = subprocess.run(
                    ['git', 'stash', 'list'],
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True
                )

                if result.returncode == 0 and result.stdout:
                    stashes = result.stdout.strip().split('\n')
                    for i, stash in enumerate(stashes):
                        recovered.append({
                            'type': 'git_stash',
                            'index': i,
                            'description': stash
                        })
            except:
                pass

        return recovered

    def check_git_reflog(self) -> List[Dict]:
        recovered = []

        if (self.project_dir / '.git').exists():
            try:
                result = subprocess.run(
                    ['git', 'reflog', '--format=%h %gd %gs', '-n', '20'],
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True
                )

                if result.returncode == 0 and result.stdout:
                    refs = result.stdout.strip().split('\n')
                    for ref in refs[:10]:  # Last 10 refs
                        parts = ref.split(' ', 2)
                        if len(parts) >= 3:
                            recovered.append({
                                'type': 'git_reflog',
                                'commit': parts[0],
                                'ref': parts[1],
                                'description': parts[2]
                            })
            except:
                pass

        return recovered

    def attempt_recovery(self) -> Dict:
        results = {
            'swap_files': self.find_editor_swap_files(),
            'temp_files': self.find_temp_files(),
            'trash': self.check_trash(),
            'open_files': self.find_process_files(),
            'git_stash': self.check_git_stash(),
            'git_reflog': self.check_git_reflog(),
        }

        # Count total recoverable items
        total = sum(len(v) for v in results.values())
        results['total'] = total

        return results

    def restore_from_swap(self, swap_file: Path, target: Optional[Path] = None) -> bool:
        if not target:
            # Try to determine original name
            name = swap_file.name
            if name.startswith('.') and name.endswith('.swp'):
                original_name = name[1:-4]
            else:
                original_name = name.replace('.swp', '').replace('.swo', '')

            target = swap_file.parent / original_name

        try:
            shutil.copy2(swap_file, target)
            return True
        except Exception as e:
            print(f"Failed to restore {swap_file}: {e}")
            return False

    def restore_from_trash(self, trash_item: Path, target: Optional[Path] = None) -> bool:
        if not target:
            target = self.project_dir / trash_item.name

        try:
            if trash_item.is_dir():
                shutil.copytree(trash_item, target)
            else:
                shutil.copy2(trash_item, target)
            return True
        except Exception as e:
            print(f"Failed to restore {trash_item}: {e}")
            return False