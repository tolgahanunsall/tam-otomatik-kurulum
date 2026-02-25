#!/usr/bin/env python3
"""
Note Backup Tool - Notion/Obsidian Otomatik Yedekleme Araci
============================================================

Obsidian vault'larinizi ve Notion sayfalarinizi otomatik olarak
GitHub ve/veya Dropbox'a yedekler.

Kullanim:
    python backup.py                    # Yedeklemeyi calistir
    python backup.py --config path.yaml # Ozel config dosyasi
    python backup.py schedule install   # Otomatik zamanlama kur
    python backup.py schedule remove    # Zamanlamayi kaldir
    python backup.py schedule status    # Zamanlama durumu
"""

import argparse
import os
import platform
import shutil
import sys
import tempfile
from datetime import datetime
from typing import List, Optional

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import Config, ConfigError
from src.logger import setup_logger


def run_backup(config: Config) -> bool:
    """Execute the backup process.

    Args:
        config: Validated configuration object.

    Returns:
        True if all backups succeeded.
    """
    logger = setup_logger(
        log_level=config.general.get("log_level", "INFO"),
        log_file=config.general.get("log_file", ""),
    )

    logger.info("=" * 60)
    logger.info("Note Backup Tool - Yedekleme baslatiliyor...")
    logger.info("Tarih: %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("Platform: %s", platform.system())
    logger.info("=" * 60)

    # Create temporary backup directory
    backup_base = config.backup_dir
    os.makedirs(backup_base, exist_ok=True)

    temp_dir = tempfile.mkdtemp(
        prefix="note-backup-",
        dir=backup_base,
    )

    success = True
    backed_up_paths: List[str] = []

    try:
        # === SOURCES ===

        # Obsidian Backup
        obsidian_cfg = config.obsidian_config
        if obsidian_cfg:
            logger.info("-" * 40)
            logger.info("Obsidian vault yedekleniyor...")
            from src.sources.obsidian import ObsidianBackup

            obsidian = ObsidianBackup(obsidian_cfg)
            paths = obsidian.backup(temp_dir)
            backed_up_paths.extend(paths)
            if not paths:
                logger.warning("Obsidian: Hicbir vault yedeklenmedi.")

        # Notion Backup
        notion_cfg = config.notion_config
        if notion_cfg:
            logger.info("-" * 40)
            logger.info("Notion sayfalari yedekleniyor...")
            from src.sources.notion import NotionBackup

            notion = NotionBackup(notion_cfg)
            paths = notion.backup(temp_dir)
            backed_up_paths.extend(paths)
            if not paths:
                logger.warning("Notion: Hicbir icerik yedeklenmedi.")

        if not backed_up_paths:
            logger.error("Hicbir kaynak yedeklenemedi. Islem durduruluyor.")
            return False

        # Add a timestamp file
        timestamp_file = os.path.join(temp_dir, ".backup-timestamp")
        with open(timestamp_file, "w") as f:
            f.write(f"Last backup: {datetime.now().isoformat()}\n")
            f.write(f"Platform: {platform.system()} {platform.release()}\n")
            f.write(f"Python: {sys.version}\n")

        # === TARGETS ===

        # GitHub
        github_cfg = config.github_config
        if github_cfg:
            logger.info("-" * 40)
            logger.info("GitHub'a yukleniyor...")
            from src.targets.github_target import GitHubBackup

            github = GitHubBackup(github_cfg)
            work_dir = os.path.join(backup_base, ".git_work")
            os.makedirs(work_dir, exist_ok=True)
            if not github.upload(temp_dir, work_dir):
                logger.error("GitHub yedekleme basarisiz!")
                success = False
            else:
                logger.info("GitHub yedekleme basarili!")

        # Dropbox
        dropbox_cfg = config.dropbox_config
        if dropbox_cfg:
            logger.info("-" * 40)
            logger.info("Dropbox'a yukleniyor...")
            from src.targets.dropbox_target import DropboxBackup

            dbx = DropboxBackup(dropbox_cfg)
            if not dbx.upload(temp_dir):
                logger.error("Dropbox yedekleme basarisiz!")
                success = False
            else:
                logger.info("Dropbox yedekleme basarili!")

    except Exception as e:
        logger.error("Beklenmeyen hata: %s", e, exc_info=True)
        success = False

    finally:
        # Clean up temporary directory
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass

    logger.info("=" * 60)
    if success:
        logger.info("Yedekleme basariyla tamamlandi!")
    else:
        logger.error("Yedekleme hatalarla tamamlandi. Logları kontrol edin.")
    logger.info("=" * 60)

    return success


def handle_schedule(args: argparse.Namespace, config: Config) -> None:
    """Handle schedule subcommands.

    Args:
        args: Parsed command-line arguments.
        config: Configuration object.
    """
    schedule_cfg = config.schedule
    backup_time = schedule_cfg.get("time", "03:00")
    frequency = schedule_cfg.get("frequency", "daily")
    weekly_day = schedule_cfg.get("weekly_day", 0)

    system = platform.system()

    if system == "Linux":
        from src.scheduler.cron_setup import CronSetup

        scheduler = CronSetup(backup_time, frequency, weekly_day)
    elif system == "Darwin":
        from src.scheduler.launchd_setup import LaunchdSetup

        scheduler = LaunchdSetup(backup_time, frequency, weekly_day)
    elif system == "Windows":
        from src.scheduler.taskscheduler_setup import TaskSchedulerSetup

        scheduler = TaskSchedulerSetup(backup_time, frequency, weekly_day)
    else:
        print(f"[ERROR] Desteklenmeyen platform: {system}")
        sys.exit(1)

    action = args.schedule_action
    config_path = args.config if hasattr(args, "config") else None

    if action == "install":
        print(f"\nPlatform: {system}")
        print(f"Zamanlama: {frequency} @ {backup_time}")
        scheduler.install(config_path)
    elif action == "remove":
        scheduler.uninstall()
    elif action == "status":
        scheduler.status()
    else:
        print(f"[ERROR] Bilinmeyen zamanlama islemi: {action}")
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Note Backup Tool - Notion/Obsidian Otomatik Yedekleme",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ornekler:
  python backup.py                        Yedeklemeyi calistir
  python backup.py --config my.yaml       Ozel config ile calistir
  python backup.py schedule install       Otomatik yedekleme kur
  python backup.py schedule remove        Zamanlamayi kaldir
  python backup.py schedule status        Zamanlama durumunu goster
        """,
    )

    parser.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help="Yapilandirma dosyasi yolu (varsayilan: config.yaml)",
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Ayrintili log ciktisi",
    )

    # Schedule subcommand
    subparsers = parser.add_subparsers(dest="command")
    schedule_parser = subparsers.add_parser(
        "schedule",
        help="Otomatik zamanlama yonetimi",
    )
    schedule_parser.add_argument(
        "schedule_action",
        choices=["install", "remove", "status"],
        help="Zamanlama islemi: install, remove, status",
    )

    args = parser.parse_args()

    # Load configuration
    try:
        config = Config(args.config)
    except ConfigError as e:
        print(f"\n[HATA] Yapilandirma hatasi: {e}", file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        config._data.setdefault("general", {})["log_level"] = "DEBUG"

    # Route to appropriate handler
    if args.command == "schedule":
        handle_schedule(args, config)
    else:
        success = run_backup(config)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
