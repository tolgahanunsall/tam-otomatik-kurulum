"""macOS launchd setup for automated backups."""

import logging
import os
import plistlib
import subprocess
import sys
from typing import Optional

logger = logging.getLogger("note-backup")

PLIST_LABEL = "com.note-backup-tool.daily"


class LaunchdSetup:
    """Manages launchd plist setup for macOS systems."""

    def __init__(self, backup_time: str = "03:00", frequency: str = "daily", weekly_day: int = 0):
        self.backup_time = backup_time
        self.frequency = frequency
        self.weekly_day = weekly_day

    def _get_plist_path(self) -> str:
        """Get the path for the launchd plist file."""
        return os.path.expanduser(f"~/Library/LaunchAgents/{PLIST_LABEL}.plist")

    def _get_script_path(self) -> str:
        """Get the absolute path to the backup script."""
        return os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "backup.py")
        )

    def _get_python_path(self) -> str:
        """Get the path to the current Python interpreter."""
        return sys.executable

    def _get_config_path(self) -> Optional[str]:
        """Try to find the config file path."""
        candidates = [
            os.path.abspath("config.yaml"),
            os.path.abspath("config.yml"),
            os.path.expanduser("~/.note-backup/config.yaml"),
        ]
        for path in candidates:
            if os.path.isfile(path):
                return path
        return None

    def _build_calendar_interval(self) -> dict:
        """Build the CalendarInterval dict for launchd."""
        parts = self.backup_time.split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0

        interval = {"Hour": hour, "Minute": minute}

        if self.frequency == "hourly":
            # Run every hour at the specified minute
            interval = {"Minute": minute}
        elif self.frequency == "weekly":
            # macOS: 0=Sunday, 1=Monday ... 6=Saturday
            # Our config: 0=Monday ... 6=Sunday
            macos_day = (self.weekly_day + 1) % 7
            interval["Weekday"] = macos_day

        return interval

    def install(self, config_path: Optional[str] = None) -> bool:
        """Install the launchd plist.

        Args:
            config_path: Optional path to config file.

        Returns:
            True if successful.
        """
        python_path = self._get_python_path()
        script_path = self._get_script_path()
        if not config_path:
            config_path = self._get_config_path()

        program_args = [python_path, script_path]
        if config_path:
            program_args.extend(["--config", config_path])

        log_dir = os.path.expanduser("~/Library/Logs/note-backup")
        os.makedirs(log_dir, exist_ok=True)

        plist_data = {
            "Label": PLIST_LABEL,
            "ProgramArguments": program_args,
            "StartCalendarInterval": self._build_calendar_interval(),
            "StandardOutPath": os.path.join(log_dir, "stdout.log"),
            "StandardErrorPath": os.path.join(log_dir, "stderr.log"),
            "RunAtLoad": False,
        }

        plist_path = self._get_plist_path()

        try:
            # Unload existing if present
            if os.path.exists(plist_path):
                subprocess.run(
                    ["launchctl", "unload", plist_path],
                    capture_output=True,
                )

            # Write plist
            os.makedirs(os.path.dirname(plist_path), exist_ok=True)
            with open(plist_path, "wb") as f:
                plistlib.dump(plist_data, f)

            # Load the plist
            result = subprocess.run(
                ["launchctl", "load", plist_path],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                logger.info("launchd job installed: %s", plist_path)
                print(f"\n[OK] macOS launchd job installed successfully!")
                print(f"  Plist: {plist_path}")
                print(f"  Logs:  {log_dir}/")
                return True
            else:
                logger.error("Failed to load plist: %s", result.stderr)
                return False

        except Exception as e:
            logger.error("Failed to set up launchd job: %s", e)
            return False

    def uninstall(self) -> bool:
        """Remove the launchd plist.

        Returns:
            True if successful.
        """
        plist_path = self._get_plist_path()

        try:
            if os.path.exists(plist_path):
                subprocess.run(
                    ["launchctl", "unload", plist_path],
                    capture_output=True,
                )
                os.remove(plist_path)
                logger.info("launchd job removed: %s", plist_path)
                print("[OK] macOS launchd job removed successfully!")
            else:
                print("[INFO] No launchd job found.")
            return True

        except Exception as e:
            logger.error("Failed to remove launchd job: %s", e)
            return False

    def status(self) -> bool:
        """Check if the launchd job is installed and loaded.

        Returns:
            True if the job exists and is loaded.
        """
        plist_path = self._get_plist_path()

        if not os.path.exists(plist_path):
            print("[INACTIVE] No launchd job found.")
            return False

        try:
            result = subprocess.run(
                ["launchctl", "list", PLIST_LABEL],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                print(f"[ACTIVE] launchd job is loaded: {PLIST_LABEL}")
                return True
            else:
                print(f"[INACTIVE] Plist exists but job is not loaded: {plist_path}")
                return False
        except Exception:
            print("[INACTIVE] Could not check launchd status.")
            return False
