"""Safety utilities for preventing data loss and resource exhaustion."""

import os
import sys
import stat
import fcntl
import signal
import psutil
import hashlib
import tempfile
from pathlib import Path
from typing import Optional, Set, Dict, Tuple
from contextlib import contextmanager
import threading
import time


class FileLock:
    """Cross-platform file locking to prevent concurrent operations."""

    def __init__(self, lockfile: Path, timeout: int = 30):
        self.lockfile = lockfile
        self.timeout = timeout
        self.fd = None
        self.acquired = False

    def acquire(self) -> bool:
        """Acquire lock with timeout."""
        self.lockfile.parent.mkdir(parents=True, exist_ok=True)
        start_time = time.time()

        while time.time() - start_time < self.timeout:
            try:
                # Open file for exclusive access
                self.fd = os.open(str(self.lockfile),
                                 os.O_CREAT | os.O_EXCL | os.O_RDWR)

                # Write PID for debugging
                os.write(self.fd, str(os.getpid()).encode())

                # Try to lock (Unix)
                if hasattr(fcntl, 'flock'):
                    fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

                self.acquired = True
                return True

            except (OSError, IOError):
                if self.fd is not None:
                    try:
                        os.close(self.fd)
                    except:
                        pass
                    self.fd = None

                # Check if lock holder is still alive
                if self.lockfile.exists():
                    try:
                        with open(self.lockfile, 'r') as f:
                            pid = int(f.read().strip())
                        if not psutil.pid_exists(pid):
                            # Stale lock, remove it
                            self.lockfile.unlink()
                    except:
                        pass

                time.sleep(0.5)

        return False

    def release(self):
        """Release the lock."""
        if self.acquired and self.fd is not None:
            try:
                # Unlock (Unix)
                if hasattr(fcntl, 'flock'):
                    fcntl.flock(self.fd, fcntl.LOCK_UN)
                os.close(self.fd)
            except:
                pass
            finally:
                self.fd = None

            try:
                if self.lockfile.exists():
                    self.lockfile.unlink()
            except:
                pass

            self.acquired = False

    def __enter__(self):
        if not self.acquire():
            raise RuntimeError(f"Could not acquire lock on {self.lockfile}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


class SymlinkValidator:
    """Validates symlinks to prevent security issues."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir.resolve()
        self.visited_inodes: Set[Tuple[int, int]] = set()

    def is_safe_symlink(self, symlink_path: Path) -> bool:
        """Check if symlink is safe to follow."""
        try:
            # Resolve the symlink target
            target = symlink_path.resolve()

            # Check if target is within project directory
            try:
                target.relative_to(self.project_dir)
            except ValueError:
                # Target is outside project directory
                return False

            # Check for symlink loops
            stat_info = target.stat()
            inode_key = (stat_info.st_dev, stat_info.st_ino)

            if inode_key in self.visited_inodes:
                # Loop detected
                return False

            return True

        except (OSError, IOError):
            # Broken symlink or permission issue
            return False

    def validate_path(self, path: Path) -> bool:
        """Validate a path for safety."""
        try:
            # Check if path escapes project directory
            resolved = path.resolve()
            try:
                resolved.relative_to(self.project_dir)
            except ValueError:
                return False

            # Check all parent directories for symlinks
            current = path
            while current != self.project_dir and current.parent != current:
                if current.is_symlink():
                    if not self.is_safe_symlink(current):
                        return False
                current = current.parent

            return True

        except (OSError, IOError):
            return False


class ResourceMonitor:
    """Monitors system resources to prevent exhaustion."""

    def __init__(self):
        self.max_memory_percent = 80  # Max memory usage
        self.min_disk_space_mb = 500  # Min free disk space
        self.max_file_descriptors_percent = 80  # Max FD usage

    def check_memory(self) -> Tuple[bool, str]:
        """Check if memory usage is safe."""
        memory = psutil.virtual_memory()
        if memory.percent > self.max_memory_percent:
            return False, f"Memory usage too high: {memory.percent:.1f}%"
        return True, ""

    def check_disk_space(self, path: Path, required_mb: int = None) -> Tuple[bool, str]:
        """Check if enough disk space is available."""
        if required_mb is None:
            required_mb = self.min_disk_space_mb

        try:
            stat = os.statvfs(path)
            free_mb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)

            if free_mb < required_mb:
                return False, f"Insufficient disk space: {free_mb:.1f}MB free, {required_mb}MB required"

            return True, ""
        except (OSError, IOError) as e:
            return False, f"Cannot check disk space: {e}"

    def check_file_descriptors(self) -> Tuple[bool, str]:
        """Check file descriptor usage."""
        try:
            import resource
            soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)

            # Count open file descriptors
            open_fds = len(os.listdir('/proc/%d/fd' % os.getpid()))

            if open_fds > soft * (self.max_file_descriptors_percent / 100):
                return False, f"Too many open files: {open_fds}/{soft}"

            return True, ""
        except:
            # Can't check on this platform
            return True, ""

    def check_all(self, path: Path = None) -> Tuple[bool, str]:
        """Run all resource checks."""
        checks = [
            self.check_memory(),
            self.check_file_descriptors()
        ]

        if path:
            checks.append(self.check_disk_space(path))

        for ok, msg in checks:
            if not ok:
                return False, msg

        return True, ""


class SafeFileOperations:
    """Safe file operations with atomic writes and rollback."""

    @staticmethod
    def atomic_write(filepath: Path, content: bytes, mode: int = 0o644) -> bool:
        """Atomically write to a file using rename."""
        temp_fd = None
        temp_path = None

        try:
            # Create temp file in same directory (for atomic rename)
            dir_path = filepath.parent
            dir_path.mkdir(parents=True, exist_ok=True)

            temp_fd, temp_path = tempfile.mkstemp(
                dir=str(dir_path),
                prefix='.tmp_',
                suffix=filepath.suffix
            )

            # Write content
            os.write(temp_fd, content)
            os.fsync(temp_fd)  # Ensure data is on disk
            os.close(temp_fd)
            temp_fd = None

            # Set permissions
            os.chmod(temp_path, mode)

            # Atomic rename
            os.rename(temp_path, str(filepath))

            return True

        except Exception:
            # Clean up on error
            if temp_fd is not None:
                try:
                    os.close(temp_fd)
                except:
                    pass
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass
            return False

    @staticmethod
    def safe_extract(archive_path: Path, extract_to: Path,
                    max_size_mb: int = 10000) -> Tuple[bool, str]:
        """Safely extract archive with size limits."""
        import tarfile

        total_size = 0
        max_size = max_size_mb * 1024 * 1024

        try:
            with tarfile.open(archive_path, 'r:gz') as tar:
                # Check total extracted size first
                for member in tar.getmembers():
                    total_size += member.size

                    # Check for path traversal
                    if member.name.startswith('/') or '..' in member.name:
                        return False, f"Unsafe path in archive: {member.name}"

                    # Check for symlink escape
                    if member.issym() or member.islnk():
                        if member.linkname.startswith('/') or '..' in member.linkname:
                            return False, f"Unsafe link in archive: {member.linkname}"

                    if total_size > max_size:
                        return False, f"Archive too large: {total_size / (1024*1024):.1f}MB"

                # Safe to extract
                tar.extractall(extract_to, filter='data')
                return True, ""

        except Exception as e:
            return False, f"Extraction failed: {e}"


class BackupIntegrityChecker:
    """Verifies backup integrity to prevent corruption."""

    @staticmethod
    def calculate_checksum(filepath: Path) -> str:
        """Calculate SHA256 checksum of a file."""
        hasher = hashlib.sha256()

        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                hasher.update(chunk)

        return hasher.hexdigest()

    @staticmethod
    def verify_archive(archive_path: Path) -> Tuple[bool, str]:
        """Verify tar.gz archive integrity."""
        import tarfile

        try:
            with tarfile.open(archive_path, 'r:gz') as tar:
                # Try to read all members
                for member in tar.getmembers():
                    if member.isfile():
                        # Try to extract to memory to verify
                        try:
                            tar.extractfile(member).read(1)  # Read 1 byte
                        except:
                            return False, f"Corrupt member: {member.name}"

            return True, ""

        except Exception as e:
            return False, f"Archive verification failed: {e}"

    @staticmethod
    def create_checksum_file(archive_path: Path) -> bool:
        """Create a checksum file for an archive."""
        try:
            checksum = BackupIntegrityChecker.calculate_checksum(archive_path)
            checksum_path = archive_path.with_suffix('.sha256')

            with open(checksum_path, 'w') as f:
                f.write(f"{checksum}  {archive_path.name}\n")

            return True
        except:
            return False

    @staticmethod
    def verify_checksum(archive_path: Path) -> bool:
        """Verify archive against its checksum file."""
        checksum_path = archive_path.with_suffix('.sha256')

        if not checksum_path.exists():
            return True  # No checksum to verify

        try:
            with open(checksum_path, 'r') as f:
                expected_checksum = f.read().split()[0]

            actual_checksum = BackupIntegrityChecker.calculate_checksum(archive_path)

            return expected_checksum == actual_checksum
        except:
            return False


class ProcessLimiter:
    """Limits process resources to prevent system exhaustion."""

    @staticmethod
    def set_limits():
        """Set resource limits for the current process."""
        try:
            import resource

            # Limit memory usage (2GB soft, 4GB hard)
            resource.setrlimit(resource.RLIMIT_AS,
                             (2 * 1024 * 1024 * 1024, 4 * 1024 * 1024 * 1024))

            # Limit CPU time (30 minutes soft, 1 hour hard)
            resource.setrlimit(resource.RLIMIT_CPU, (1800, 3600))

            # Limit file size (10GB)
            resource.setrlimit(resource.RLIMIT_FSIZE,
                             (10 * 1024 * 1024 * 1024, 10 * 1024 * 1024 * 1024))

        except:
            # Resource limits not available on this platform
            pass

    @staticmethod
    def set_timeout(seconds: int):
        """Set a timeout for the entire process."""
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Process timed out after {seconds} seconds")

        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(seconds)


@contextmanager
def safe_backup_operation(project_dir: Path, operation: str = "backup"):
    """Context manager for safe backup operations."""
    lock_file = project_dir / '.savior' / f'.{operation}.lock'
    lock = FileLock(lock_file)
    monitor = ResourceMonitor()

    # Check resources before starting
    ok, msg = monitor.check_all(project_dir)
    if not ok:
        raise RuntimeError(f"Cannot start {operation}: {msg}")

    # Acquire lock
    if not lock.acquire():
        raise RuntimeError(f"Another {operation} operation is in progress")

    try:
        yield
    finally:
        lock.release()