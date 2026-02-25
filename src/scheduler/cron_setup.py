"""Linux cron job setup for automated backups."""

import logging
import os
import subprocess
import sys
from typing import Optional

logger = logging.getLogger("note-backup")


class CronSetup:
    """Manages cron job setup for Linux systems."""

    def __init__(self, backup_time: str = "03:00", frequency: str = "daily", weekly_day: int = 0):
        self.backup_time = backup_time
        self.frequency = frequency
        self.weekly_day = weekly_day

    def _get_cron_expression(self) -> str:
        """Generate the cron schedule expression."""
        parts = self.backup_time.split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0

        if self.frequency == "hourly":
            return f"{minute} * * * *"
        elif self.frequency == "weekly":
            # cron uses 0=Sunday, our config uses 0=Monday
            cron_day = (self.weekly_day + 1) % 7
            return f"{minute} {hour} * * {cron_day}"
        else:  # daily
            return f"{minute} {hour} * * *"

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

    def _build_cron_command(self, config_path: Optional[str] = None) -> str:
        """Build the full cron command."""
        python = self._get_python_path()
        script = self._get_script_path()
        cmd = f"{python} {script}"
        if config_path:
            cmd += f" --config {config_path}"
        return cmd

    def install(self, config_path: Optional[str] = None) -> bool:
        """Install the cron job.

        Args:
            config_path: Optional path to config file.

        Returns:
            True if successful.
        """
        cron_expr = self._get_cron_expression()
        if not config_path:
            config_path = self._get_config_path()
        command = self._build_cron_command(config_path)
        cron_line = f"{cron_expr} {command}"
        marker = "# note-backup-tool"

        try:
            # Get existing crontab
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True,
                text=True,
            )
            existing = result.stdout if result.returncode == 0 else ""

            # Remove old entry if exists
            lines = [
                line
                for line in existing.strip().split("\n")
                if line.strip() and marker not in line
            ]

            # Add new entry
            lines.append(f"{cron_line} {marker}")

            # Install new crontab
            new_crontab = "\n".join(lines) + "\n"
            proc = subprocess.run(
                ["crontab", "-"],
                input=new_crontab,
                capture_output=True,
                text=True,
            )

            if proc.returncode == 0:
                logger.info("Cron job installed: %s", cron_line)
                print(f"\n[OK] Cron job installed successfully!")
                print(f"  Schedule: {cron_expr}")
                print(f"  Command:  {command}")
                return True
            else:
                logger.error("Failed to install cron job: %s", proc.stderr)
                return False

        except FileNotFoundError:
            logger.error("crontab command not found. Is cron installed?")
            return False
        except Exception as e:
            logger.error("Failed to set up cron job: %s", e)
            return False

    def uninstall(self) -> bool:
        """Remove the cron job.

        Returns:
            True if successful.
        """
        marker = "# note-backup-tool"

        try:
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                logger.info("No crontab found.")
                return True

            lines = [
                line
                for line in result.stdout.strip().split("\n")
                if line.strip() and marker not in line
            ]

            if lines:
                new_crontab = "\n".join(lines) + "\n"
                subprocess.run(["crontab", "-"], input=new_crontab, text=True)
            else:
                subprocess.run(["crontab", "-r"], capture_output=True)

            logger.info("Cron job removed.")
            print("[OK] Cron job removed successfully!")
            return True

        except Exception as e:
            logger.error("Failed to remove cron job: %s", e)
            return False

    def status(self) -> bool:
        """Check if the cron job is installed.

        Returns:
            True if the cron job exists.
        """
        marker = "# note-backup-tool"
        try:
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and marker in result.stdout:
                for line in result.stdout.split("\n"):
                    if marker in line:
                        print(f"[ACTIVE] {line.replace(marker, '').strip()}")
                return True
            else:
                print("[INACTIVE] No backup cron job found.")
                return False
        except Exception:
            print("[INACTIVE] Could not check cron status.")
            return False
