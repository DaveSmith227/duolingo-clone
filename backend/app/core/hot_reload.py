"""
Configuration Hot-Reloading for Development

Provides hot-reloading capabilities for configuration changes in development
environment to improve developer experience.
"""

import os
import time
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Callable, List, Set
from threading import Thread, Event
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

from .environment import is_development, is_testing, Environment
from .config import reload_settings

logger = logging.getLogger(__name__)


class ConfigurationFileHandler(FileSystemEventHandler):
    """Handles configuration file change events."""
    
    def __init__(self, reload_callback: Callable[[], None], 
                 watched_files: Set[str]):
        self.reload_callback = reload_callback
        self.watched_files = watched_files
        self.last_reload_time = 0
        self.reload_debounce_seconds = 1.0  # Debounce multiple rapid changes
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path).resolve()
        
        # Check if this is a file we're watching
        if any(str(file_path).endswith(watched_file) for watched_file in self.watched_files):
            current_time = time.time()
            
            # Debounce rapid consecutive changes
            if current_time - self.last_reload_time < self.reload_debounce_seconds:
                return
            
            self.last_reload_time = current_time
            
            logger.info(f"Configuration file changed: {file_path}")
            
            try:
                self.reload_callback()
                logger.info("Configuration reloaded successfully")
            except Exception as e:
                logger.error(f"Failed to reload configuration: {e}")


class EnvironmentVariableWatcher:
    """Watches for environment variable changes."""
    
    def __init__(self, reload_callback: Callable[[], None],
                 watched_vars: Set[str]):
        self.reload_callback = reload_callback
        self.watched_vars = watched_vars
        self.last_values: Dict[str, Optional[str]] = {}
        self.check_interval = 2.0  # Check every 2 seconds
        self.running = False
        self.thread: Optional[Thread] = None
        
        # Initialize last known values
        for var in self.watched_vars:
            self.last_values[var] = os.environ.get(var)
    
    def start(self):
        """Start watching for environment variable changes."""
        if self.running:
            return
        
        self.running = True
        self.thread = Thread(target=self._watch_loop, daemon=True)
        self.thread.start()
        logger.info("Started environment variable watcher")
    
    def stop(self):
        """Stop watching for environment variable changes."""
        if not self.running:
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=5.0)
        logger.info("Stopped environment variable watcher")
    
    def _watch_loop(self):
        """Main watching loop."""
        while self.running:
            try:
                self._check_variables()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in environment variable watcher: {e}")
                time.sleep(self.check_interval)
    
    def _check_variables(self):
        """Check if any watched variables have changed."""
        changed_vars = []
        
        for var in self.watched_vars:
            current_value = os.environ.get(var)
            last_value = self.last_values.get(var)
            
            if current_value != last_value:
                changed_vars.append(var)
                self.last_values[var] = current_value
        
        if changed_vars:
            logger.info(f"Environment variables changed: {changed_vars}")
            try:
                self.reload_callback()
                logger.info("Configuration reloaded due to environment variable changes")
            except Exception as e:
                logger.error(f"Failed to reload configuration: {e}")


class ConfigurationHotReloader:
    """
    Manages hot-reloading of configuration in development environment.
    """
    
    def __init__(self):
        self.file_observer: Optional[Observer] = None
        self.env_watcher: Optional[EnvironmentVariableWatcher] = None
        self.running = False
        self.reload_callbacks: List[Callable[[], None]] = []
        
        # Default files to watch
        self.watched_files = {
            ".env",
            ".env.local",
            ".env.development",
            "config.py",
            "settings.py",
        }
        
        # Default environment variables to watch
        self.watched_env_vars = {
            "ENVIRONMENT",
            "NODE_ENV",
            "DEBUG",
            "SECRET_KEY",
            "DATABASE_URL",
            "REDIS_URL",
            "SUPABASE_URL",
            "SUPABASE_ANON_KEY",
            "OPENAI_API_KEY",
        }
    
    def add_reload_callback(self, callback: Callable[[], None]):
        """Add a callback to be called when configuration reloads."""
        self.reload_callbacks.append(callback)
        logger.debug("Added configuration reload callback")
    
    def remove_reload_callback(self, callback: Callable[[], None]):
        """Remove a reload callback."""
        if callback in self.reload_callbacks:
            self.reload_callbacks.remove(callback)
            logger.debug("Removed configuration reload callback")
    
    def add_watched_file(self, filename: str):
        """Add a file to watch for changes."""
        self.watched_files.add(filename)
        logger.debug(f"Added watched file: {filename}")
    
    def add_watched_env_var(self, var_name: str):
        """Add an environment variable to watch for changes."""
        self.watched_env_vars.add(var_name)
        logger.debug(f"Added watched environment variable: {var_name}")
    
    def start(self, watch_directory: Optional[Path] = None):
        """
        Start hot-reloading.
        
        Args:
            watch_directory: Directory to watch for file changes (default: current directory)
        """
        if not (is_development() or is_testing()):
            logger.info("Hot-reloading is only enabled in development and test environments")
            return
        
        if self.running:
            logger.warning("Hot-reloader is already running")
            return
        
        watch_dir = watch_directory or Path.cwd()
        
        try:
            # Setup file watcher
            self._start_file_watcher(watch_dir)
            
            # Setup environment variable watcher
            self._start_env_watcher()
            
            self.running = True
            logger.info(f"Started configuration hot-reloading for directory: {watch_dir}")
            
        except Exception as e:
            logger.error(f"Failed to start hot-reloading: {e}")
            self.stop()
            raise
    
    def stop(self):
        """Stop hot-reloading."""
        if not self.running:
            return
        
        # Stop file watcher
        if self.file_observer:
            self.file_observer.stop()
            self.file_observer.join()
            self.file_observer = None
        
        # Stop environment watcher
        if self.env_watcher:
            self.env_watcher.stop()
            self.env_watcher = None
        
        self.running = False
        logger.info("Stopped configuration hot-reloading")
    
    def _start_file_watcher(self, watch_directory: Path):
        """Start the file system watcher."""
        handler = ConfigurationFileHandler(
            reload_callback=self._handle_reload,
            watched_files=self.watched_files
        )
        
        self.file_observer = Observer()
        self.file_observer.schedule(handler, str(watch_directory), recursive=False)
        self.file_observer.start()
        
        logger.debug(f"Started file watcher for: {watch_directory}")
    
    def _start_env_watcher(self):
        """Start the environment variable watcher."""
        self.env_watcher = EnvironmentVariableWatcher(
            reload_callback=self._handle_reload,
            watched_vars=self.watched_env_vars
        )
        self.env_watcher.start()
        
        logger.debug("Started environment variable watcher")
    
    def _handle_reload(self):
        """Handle configuration reload."""
        logger.info("Reloading configuration...")
        
        try:
            # Reload the main settings
            reload_settings()
            
            # Call any registered callbacks
            for callback in self.reload_callbacks:
                try:
                    callback()
                except Exception as e:
                    logger.error(f"Error in reload callback: {e}")
            
            logger.info("Configuration reload completed")
            
        except Exception as e:
            logger.error(f"Configuration reload failed: {e}")
            raise
    
    def is_running(self) -> bool:
        """Check if hot-reloading is currently running."""
        return self.running
    
    def get_status(self) -> Dict[str, Any]:
        """Get hot-reloader status information."""
        return {
            "running": self.running,
            "watched_files": list(self.watched_files),
            "watched_env_vars": list(self.watched_env_vars),
            "file_observer_active": self.file_observer is not None and self.file_observer.is_alive(),
            "env_watcher_active": self.env_watcher is not None and self.env_watcher.running,
            "callback_count": len(self.reload_callbacks),
        }


# Global hot-reloader instance
_hot_reloader: Optional[ConfigurationHotReloader] = None


def get_hot_reloader() -> ConfigurationHotReloader:
    """Get or create the global hot-reloader instance."""
    global _hot_reloader
    
    if _hot_reloader is None:
        _hot_reloader = ConfigurationHotReloader()
    
    return _hot_reloader


def start_hot_reloading(watch_directory: Optional[Path] = None):
    """Start configuration hot-reloading."""
    reloader = get_hot_reloader()
    reloader.start(watch_directory)


def stop_hot_reloading():
    """Stop configuration hot-reloading."""
    reloader = get_hot_reloader()
    reloader.stop()


def add_reload_callback(callback: Callable[[], None]):
    """Add a callback to be called when configuration reloads."""
    reloader = get_hot_reloader()
    reloader.add_reload_callback(callback)


def remove_reload_callback(callback: Callable[[], None]):
    """Remove a reload callback."""
    reloader = get_hot_reloader()
    reloader.remove_reload_callback(callback)


def get_hot_reload_status() -> Dict[str, Any]:
    """Get hot-reloader status."""
    reloader = get_hot_reloader()
    return reloader.get_status()


# Auto-start hot-reloading in development if enabled by environment variable
if is_development() and os.environ.get("AUTO_START_HOT_RELOAD", "true").lower() == "true":
    import atexit
    
    def auto_start_hot_reload():
        """Auto-start hot-reloading in development."""
        try:
            start_hot_reloading()
            # Register cleanup on exit
            atexit.register(stop_hot_reloading)
        except Exception as e:
            logger.warning(f"Could not auto-start hot-reloading: {e}")
    
    # Start in a separate thread to avoid blocking module import
    auto_thread = Thread(target=auto_start_hot_reload, daemon=True)
    auto_thread.start()