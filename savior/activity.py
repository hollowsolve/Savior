import time
import threading
from pathlib import Path
from typing import Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class ActivityMonitor(FileSystemEventHandler):
    def __init__(self, idle_threshold: float = 2.0):
        self.idle_threshold = idle_threshold
        self.last_activity = time.time()
        self.is_active = False
        self._lock = threading.Lock()
        self._callbacks = []

    def on_any_event(self, event):
        """Called when any file system event occurs"""
        # Ignore events in .savior directory
        if '.savior' in event.src_path:
            return

        with self._lock:
            self.last_activity = time.time()
            self.is_active = True

    def get_idle_time(self) -> float:
        """Returns seconds since last activity"""
        with self._lock:
            return time.time() - self.last_activity

    def is_idle(self) -> bool:
        """Check if system has been idle for threshold time"""
        return self.get_idle_time() > self.idle_threshold

    def add_idle_callback(self, callback: Callable):
        """Add a callback to be called when system becomes idle"""
        self._callbacks.append(callback)

    def check_idle_state(self):
        """Check if system has become idle and trigger callbacks"""
        if self.is_idle() and self.is_active:
            self.is_active = False
            for callback in self._callbacks:
                try:
                    callback()
                except Exception:
                    pass


class SmartWatcher:
    def __init__(self, project_dir: Path, save_callback: Callable,
                 idle_time: float = 2.0, check_interval: float = 20 * 60):
        self.project_dir = project_dir
        self.save_callback = save_callback
        self.idle_time = idle_time
        self.check_interval = check_interval
        self.monitor = ActivityMonitor(idle_time)
        self.observer = Observer()
        self.watching = False
        self._watch_thread = None
        self._last_save = time.time()

    def _watch_loop(self):
        """Main watch loop that checks for idle state and triggers saves"""
        while self.watching:
            time.sleep(1)

            # Check if we should save
            time_since_save = time.time() - self._last_save

            if time_since_save >= self.check_interval:
                # Wait for idle state before saving
                if self.monitor.is_idle():
                    try:
                        self.save_callback()
                        self._last_save = time.time()
                    except Exception as e:
                        print(f"Error during auto-save: {e}")

    def start(self):
        """Start watching for changes and auto-saving"""
        if not self.watching:
            self.watching = True

            # Start file system observer
            self.observer.schedule(
                self.monitor,
                str(self.project_dir),
                recursive=True
            )
            self.observer.start()

            # Start watch thread
            self._watch_thread = threading.Thread(
                target=self._watch_loop,
                daemon=True
            )
            self._watch_thread.start()

    def stop(self):
        """Stop watching"""
        self.watching = False

        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join(timeout=5)

        if self._watch_thread:
            self._watch_thread.join(timeout=5)

    def force_save(self):
        """Force an immediate save"""
        self.save_callback()
        self._last_save = time.time()