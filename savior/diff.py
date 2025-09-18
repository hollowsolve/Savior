import difflib
import tarfile
import tempfile
import shutil
from pathlib import Path
from typing import List, Tuple
from colorama import Fore, Style
import fnmatch


class BackupDiffer:
    def __init__(self):
        self.ignore_patterns = ['.git/', '__pycache__/', '*.pyc', '.DS_Store']

    def extract_backup(self, backup_path: Path) -> Path:
        temp_dir = Path(tempfile.mkdtemp(prefix='savior_diff_'))
        with tarfile.open(backup_path, 'r:gz') as tar:
            tar.extractall(temp_dir)
        return temp_dir

    def should_compare(self, path: str) -> bool:
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(path, pattern):
                return False
        return True

    def compare_files(self, file1: Path, file2: Path) -> List[str]:
        try:
            with open(file1, 'r', encoding='utf-8', errors='ignore') as f1:
                lines1 = f1.readlines()
            with open(file2, 'r', encoding='utf-8', errors='ignore') as f2:
                lines2 = f2.readlines()

            diff = difflib.unified_diff(
                lines1, lines2,
                fromfile=str(file1),
                tofile=str(file2),
                lineterm=''
            )
            return list(diff)
        except:
            return []

    def colorize_diff(self, diff_lines: List[str]) -> str:
        output = []
        for line in diff_lines:
            if line.startswith('+++') or line.startswith('---'):
                output.append(f"{Fore.CYAN}{line}{Style.RESET_ALL}")
            elif line.startswith('+'):
                output.append(f"{Fore.GREEN}{line}{Style.RESET_ALL}")
            elif line.startswith('-'):
                output.append(f"{Fore.RED}{line}{Style.RESET_ALL}")
            elif line.startswith('@'):
                output.append(f"{Fore.YELLOW}{line}{Style.RESET_ALL}")
            else:
                output.append(line)
        return '\n'.join(output)

    def diff_backups(self, backup1_path: Path, backup2_path: Path) -> Tuple[List[str], List[str], List[str], List[Tuple[str, str]]]:
        temp1 = self.extract_backup(backup1_path)
        temp2 = self.extract_backup(backup2_path)

        files1 = set()
        files2 = set()

        for path in temp1.rglob('*'):
            if path.is_file():
                rel_path = path.relative_to(temp1)
                if self.should_compare(str(rel_path)):
                    files1.add(str(rel_path))

        for path in temp2.rglob('*'):
            if path.is_file():
                rel_path = path.relative_to(temp2)
                if self.should_compare(str(rel_path)):
                    files2.add(str(rel_path))

        added = list(files2 - files1)
        deleted = list(files1 - files2)
        modified = []
        diffs = []

        for file in files1 & files2:
            file1 = temp1 / file
            file2 = temp2 / file

            diff = self.compare_files(file1, file2)
            if diff:
                modified.append(file)
                diffs.append((file, self.colorize_diff(diff)))

        shutil.rmtree(temp1)
        shutil.rmtree(temp2)

        return added, deleted, modified, diffs

    def diff_backup_with_current(self, backup_path: Path, project_dir: Path) -> Tuple[List[str], List[str], List[str], List[Tuple[str, str]]]:
        temp = self.extract_backup(backup_path)

        files_backup = set()
        files_current = set()

        for path in temp.rglob('*'):
            if path.is_file():
                rel_path = path.relative_to(temp)
                if self.should_compare(str(rel_path)):
                    files_backup.add(str(rel_path))

        for path in project_dir.rglob('*'):
            if path.is_file():
                try:
                    rel_path = path.relative_to(project_dir)
                    if self.should_compare(str(rel_path)) and '.savior' not in str(rel_path):
                        files_current.add(str(rel_path))
                except:
                    pass

        added = list(files_current - files_backup)
        deleted = list(files_backup - files_current)
        modified = []
        diffs = []

        for file in files_backup & files_current:
            file_backup = temp / file
            file_current = project_dir / file

            diff = self.compare_files(file_backup, file_current)
            if diff:
                modified.append(file)
                diffs.append((file, self.colorize_diff(diff)))

        shutil.rmtree(temp)

        return added, deleted, modified, diffs