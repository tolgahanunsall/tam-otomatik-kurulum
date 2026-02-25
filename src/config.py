"""Configuration loader and validator."""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from src.tier import TierManager, TierError


DEFAULT_CONFIG_PATHS = [
    "config.yaml",
    "config.yml",
    os.path.expanduser("~/.note-backup/config.yaml"),
    os.path.expanduser("~/.note-backup/config.yml"),
]


class ConfigError(Exception):
    """Configuration error."""
    pass


class Config:
    """Loads and validates the backup configuration."""

    def __init__(self, config_path: Optional[str] = None):
        self._data: Dict[str, Any] = {}
        self._config_path = config_path
        self._load()
        self._tier_manager = TierManager(self._data)

    def _find_config_file(self) -> str:
        """Find the configuration file."""
        if self._config_path:
            path = os.path.expanduser(self._config_path)
            if os.path.isfile(path):
                return path
            raise ConfigError(f"Config file not found: {self._config_path}")

        for path in DEFAULT_CONFIG_PATHS:
            expanded = os.path.expanduser(path)
            if os.path.isfile(expanded):
                return expanded

        raise ConfigError(
            "No configuration file found. Please create 'config.yaml' "
            "from 'config.example.yaml'.\n"
            "  cp config.example.yaml config.yaml"
        )

    def _load(self) -> None:
        """Load and parse the YAML configuration."""
        config_file = self._find_config_file()
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                self._data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid YAML in config file: {e}")
        except OSError as e:
            raise ConfigError(f"Cannot read config file: {e}")

        self._validate()

    def _validate(self) -> None:
        """Validate required configuration sections."""
        if "sources" not in self._data:
            raise ConfigError("Config must have a 'sources' section.")
        if "targets" not in self._data:
            raise ConfigError("Config must have a 'targets' section.")

        sources = self._data["sources"]
        targets = self._data["targets"]

        # At least one source must be enabled
        any_source = False
        if sources.get("obsidian", {}).get("enabled", False):
            any_source = True
            self._validate_obsidian(sources["obsidian"])
        if sources.get("notion", {}).get("enabled", False):
            any_source = True
            self._validate_notion(sources["notion"])

        if not any_source:
            raise ConfigError("At least one source (obsidian or notion) must be enabled.")

        # At least one target must be enabled
        any_target = False
        if targets.get("github", {}).get("enabled", False):
            any_target = True
            self._validate_github(targets["github"])
        if targets.get("dropbox", {}).get("enabled", False):
            any_target = True
            self._validate_dropbox(targets["dropbox"])

        if not any_target:
            raise ConfigError("At least one target (github or dropbox) must be enabled.")

    def validate_tier_restrictions(self) -> None:
        """Validate configuration against tier restrictions.

        Called after tier manager is initialized to enforce limits.

        Raises:
            TierError: If any tier restriction is violated.
        """
        tier = self._tier_manager

        # Check vault limit
        obsidian_cfg = self.sources.get("obsidian", {})
        if obsidian_cfg.get("enabled", False):
            vault_count = len(obsidian_cfg.get("vaults", []))
            tier.enforce_vault_limit(vault_count)

        # Check Notion access
        notion_cfg = self.sources.get("notion", {})
        if notion_cfg.get("enabled", False):
            tier.enforce_notion_access()

        # Check target limit
        enabled_targets = 0
        if self.targets.get("github", {}).get("enabled", False):
            enabled_targets += 1
        if self.targets.get("dropbox", {}).get("enabled", False):
            enabled_targets += 1
        tier.enforce_target_limit(enabled_targets)

        # Check schedule frequency
        frequency = self.schedule.get("frequency", "daily")
        tier.enforce_frequency(frequency)

    def _validate_obsidian(self, cfg: Dict[str, Any]) -> None:
        """Validate Obsidian configuration."""
        vaults = cfg.get("vaults", [])
        if not vaults:
            raise ConfigError("Obsidian is enabled but no vaults are configured.")
        for vault in vaults:
            if "path" not in vault:
                raise ConfigError("Each Obsidian vault must have a 'path'.")
            if "name" not in vault:
                raise ConfigError("Each Obsidian vault must have a 'name'.")
            expanded_path = os.path.expanduser(vault["path"])
            if not os.path.isdir(expanded_path):
                print(
                    f"[WARNING] Obsidian vault path does not exist: {expanded_path}",
                    file=sys.stderr,
                )

    def _validate_notion(self, cfg: Dict[str, Any]) -> None:
        """Validate Notion configuration."""
        token = cfg.get("api_token", "")
        if not token or token == "YOUR_NOTION_API_TOKEN":
            raise ConfigError(
                "Notion is enabled but no valid API token is provided. "
                "Get one from https://www.notion.so/my-integrations"
            )

    def _validate_github(self, cfg: Dict[str, Any]) -> None:
        """Validate GitHub configuration."""
        token = cfg.get("token", "")
        if not token or token == "YOUR_GITHUB_TOKEN":
            raise ConfigError(
                "GitHub target is enabled but no valid token is provided."
            )
        repo = cfg.get("repository", "")
        if not repo or repo == "YOUR_USERNAME/obsidian-backup":
            raise ConfigError(
                "GitHub target is enabled but no valid repository is configured."
            )

    def _validate_dropbox(self, cfg: Dict[str, Any]) -> None:
        """Validate Dropbox configuration."""
        access_token = cfg.get("access_token", "")
        refresh_token = cfg.get("refresh_token", "")
        if (not access_token or access_token == "YOUR_DROPBOX_ACCESS_TOKEN") and not refresh_token:
            raise ConfigError(
                "Dropbox target is enabled but no valid access/refresh token is provided."
            )

    @property
    def general(self) -> Dict[str, Any]:
        """Get general settings."""
        defaults = {
            "backup_dir": "~/note-backups",
            "log_level": "INFO",
            "log_file": "",
        }
        general = self._data.get("general", {})
        defaults.update(general)
        return defaults

    @property
    def backup_dir(self) -> str:
        """Get the expanded backup directory path."""
        return os.path.expanduser(self.general["backup_dir"])

    @property
    def sources(self) -> Dict[str, Any]:
        """Get sources configuration."""
        return self._data.get("sources", {})

    @property
    def targets(self) -> Dict[str, Any]:
        """Get targets configuration."""
        return self._data.get("targets", {})

    @property
    def schedule(self) -> Dict[str, Any]:
        """Get schedule configuration."""
        defaults = {
            "time": "03:00",
            "frequency": "daily",
            "weekly_day": 0,
        }
        schedule = self._data.get("schedule", {})
        defaults.update(schedule)
        return defaults

    @property
    def obsidian_config(self) -> Optional[Dict[str, Any]]:
        """Get Obsidian source config if enabled."""
        cfg = self.sources.get("obsidian", {})
        return cfg if cfg.get("enabled", False) else None

    @property
    def notion_config(self) -> Optional[Dict[str, Any]]:
        """Get Notion source config if enabled."""
        cfg = self.sources.get("notion", {})
        return cfg if cfg.get("enabled", False) else None

    @property
    def github_config(self) -> Optional[Dict[str, Any]]:
        """Get GitHub target config if enabled."""
        cfg = self.targets.get("github", {})
        return cfg if cfg.get("enabled", False) else None

    @property
    def dropbox_config(self) -> Optional[Dict[str, Any]]:
        """Get Dropbox target config if enabled."""
        cfg = self.targets.get("dropbox", {})
        return cfg if cfg.get("enabled", False) else None

    @property
    def tier_manager(self) -> TierManager:
        """Get the tier manager instance."""
        return self._tier_manager
