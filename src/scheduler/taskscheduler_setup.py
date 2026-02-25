"""Windows Task Scheduler setup for automated backups."""

import logging
import os
import subprocess
import sys
from typing import Optional

logger = logging.getLogger("note-backup")

TASK_NAME = "NoteBackupTool"


class TaskSchedulerSetup:
    """Manages Windows Task Scheduler setup for automated backups."""

    def __init__(self, backup_time: str = "03:00", frequency: str = "daily", weekly_day: int = 0):
        self.backup_time = backup_time
        self.frequency = frequency
        self.weekly_day = weekly_day

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

    def _get_schedule_args(self) -> list:
        """Build the schtasks schedule arguments."""
        parts = self.backup_time.split(":")
        time_str = f"{parts[0]}:{parts[1] if len(parts) > 1 else '00'}"

        if self.frequency == "hourly":
            return ["/SC", "HOURLY", "/ST", time_str]
        elif self.frequency == "weekly":
            days_map = {
                0: "MON",
                1: "TUE",
                2: "WED",
                3: "THU",
                4: "FRI",
                5: "SAT",
                6: "SUN",
            }
            day = days_map.get(self.weekly_day, "MON")
            return ["/SC", "WEEKLY", "/D", day, "/ST", time_str]
        else:  # daily
            return ["/SC", "DAILY", "/ST", time_str]

    def install(self, config_path: Optional[str] = None) -> bool:
        """Install a Windows scheduled task.

        Args:
            config_path: Optional path to config file.

        Returns:
            True if successful.
        """
        if sys.platform != "win32":
            logger.error("Task Scheduler is only available on Windows.")
            print("[ERROR] This command is only available on Windows.")
            return False

        python_path = self._get_python_path()
        script_path = self._get_script_path()
        if not config_path:
            config_path = self._get_config_path()

        args = f'"{script_path}"'
        if config_path:
            args += f' --config "{config_path}"'

        schedule_args = self._get_schedule_args()

        cmd = [
            "schtasks",
            "/Create",
            "/TN", TASK_NAME,
            "/TR", f'"{python_path}" {args}',
            *schedule_args,
            "/F",  # Force overwrite if exists
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                shell=True,
            )

            if result.returncode == 0:
                logger.info("Windows scheduled task created: %s", TASK_NAME)
                print(f"\n[OK] Windows scheduled task created successfully!")
                print(f"  Task Name: {TASK_NAME}")
                print(f"  Schedule:  {' '.join(schedule_args)}")
                print(f"\n  To view:   schtasks /Query /TN {TASK_NAME}")
                print(f"  To run now: schtasks /Run /TN {TASK_NAME}")
                return True
            else:
                logger.error(
                    "Failed to create scheduled task: %s", result.stderr
                )
                print(f"[ERROR] Failed to create task: {result.stderr}")
                return False

        except Exception as e:
            logger.error("Failed to set up scheduled task: %s", e)
            return False

    def uninstall(self) -> bool:
        """Remove the Windows scheduled task.

        Returns:
            True if successful.
        """
        if sys.platform != "win32":
            logger.error("Task Scheduler is only available on Windows.")
            return False

        try:
            result = subprocess.run(
                ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
                capture_output=True,
                text=True,
                shell=True,
            )

            if result.returncode == 0:
                logger.info("Windows scheduled task removed: %s", TASK_NAME)
                print("[OK] Windows scheduled task removed successfully!")
            else:
                print("[INFO] No scheduled task found or already removed.")
            return True

        except Exception as e:
            logger.error("Failed to remove scheduled task: %s", e)
            return False

    def status(self) -> bool:
        """Check if the Windows scheduled task exists.

        Returns:
            True if the task exists.
        """
        if sys.platform != "win32":
            print("[INFO] Task Scheduler is only available on Windows.")
            return False

        try:
            result = subprocess.run(
                ["schtasks", "/Query", "/TN", TASK_NAME],
                capture_output=True,
                text=True,
                shell=True,
            )

            if result.returncode == 0:
                print(f"[ACTIVE] Scheduled task '{TASK_NAME}' is configured.")
                print(result.stdout)
                return True
            else:
                print(f"[INACTIVE] No scheduled task '{TASK_NAME}' found.")
                return False

        except Exception:
            print("[INACTIVE] Could not check Task Scheduler status.")
            return False
