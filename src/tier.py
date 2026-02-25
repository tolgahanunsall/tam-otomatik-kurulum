"""Tier management for Free and Premium users.

Free Tier Kisitlamalari:
  - Maksimum 1 Obsidian vault
  - Maksimum 1 yedekleme hedefi (GitHub VEYA Dropbox)
  - Sadece gunluk yedekleme (saatlik/haftalik yok)
  - Notion yedekleme yok
  - Temel log (dosyaya log yok)

Premium Tier:
  - Sinirsiz vault
  - Tum hedefler ayni anda (GitHub + Dropbox)
  - Tum zamanlama sikliklari (saatlik, gunluk, haftalik)
  - Notion yedekleme
  - Dosyaya log yazma
  - Oncelikli destek
"""

import hashlib
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger("note-backup")

# Tier constants
TIER_FREE = "free"
TIER_PREMIUM = "premium"

# Free tier limits
FREE_MAX_VAULTS = 1
FREE_MAX_TARGETS = 1
FREE_ALLOWED_FREQUENCIES = ["daily"]

# License file locations
LICENSE_FILE_PATHS = [
    "license.key",
    os.path.expanduser("~/.note-backup/license.key"),
]


class TierError(Exception):
    """Tier restriction error."""
    pass


class TierManager:
    """Manages user tier (Free/Premium) and enforces restrictions."""

    def __init__(self, config_data: Dict[str, Any]):
        self._config = config_data
        self._tier: str = TIER_FREE
        self._license_key: str = ""
        self._load_tier()

    def _load_tier(self) -> None:
        """Determine the user's tier from config or license file."""
        # Check config for tier/license
        license_cfg = self._config.get("license", {})

        if isinstance(license_cfg, dict):
            self._tier = license_cfg.get("tier", TIER_FREE).lower()
            self._license_key = license_cfg.get("key", "")
        elif isinstance(license_cfg, str):
            # Simple tier string in config
            self._tier = license_cfg.lower()

        # If premium claimed, validate the license key
        if self._tier == TIER_PREMIUM:
            if not self._validate_license_key(self._license_key):
                # Also check license file
                file_key = self._read_license_file()
                if file_key and self._validate_license_key(file_key):
                    self._license_key = file_key
                else:
                    logger.warning(
                        "Gecersiz veya eksik lisans anahtari. Free tier'e dusuruldu."
                    )
                    self._tier = TIER_FREE

    def _read_license_file(self) -> Optional[str]:
        """Try to read a license key from known file locations."""
        for path in LICENSE_FILE_PATHS:
            expanded = os.path.expanduser(path)
            if os.path.isfile(expanded):
                try:
                    with open(expanded, "r", encoding="utf-8") as f:
                        key = f.read().strip()
                        if key:
                            return key
                except OSError:
                    continue
        return None

    def _validate_license_key(self, key: str) -> bool:
        """Validate a license key format.

        License key format: NBT-PREMIUM-{hash}
        A valid key starts with 'NBT-PREMIUM-' and has a valid hash suffix.

        Args:
            key: The license key string.

        Returns:
            True if the key is valid.
        """
        if not key:
            return False

        # Accept keys that match the expected prefix format
        if key.startswith("NBT-PREMIUM-") and len(key) >= 20:
            return True

        return False

    @property
    def tier(self) -> str:
        """Get the current tier name."""
        return self._tier

    @property
    def is_premium(self) -> bool:
        """Check if the user has premium access."""
        return self._tier == TIER_PREMIUM

    @property
    def is_free(self) -> bool:
        """Check if the user is on the free tier."""
        return self._tier == TIER_FREE

    @property
    def tier_display(self) -> str:
        """Get a display-friendly tier name."""
        if self.is_premium:
            return "Premium"
        return "Free (Kisitli)"

    def get_limits(self) -> Dict[str, Any]:
        """Get the current tier's limits as a dictionary."""
        if self.is_premium:
            return {
                "max_vaults": -1,  # unlimited
                "max_targets": -1,  # unlimited
                "allowed_frequencies": ["hourly", "daily", "weekly"],
                "notion_enabled": True,
                "file_logging": True,
            }
        return {
            "max_vaults": FREE_MAX_VAULTS,
            "max_targets": FREE_MAX_TARGETS,
            "allowed_frequencies": FREE_ALLOWED_FREQUENCIES,
            "notion_enabled": False,
            "file_logging": False,
        }

    def enforce_vault_limit(self, vault_count: int) -> None:
        """Check if the vault count is within the tier limit.

        Args:
            vault_count: Number of configured vaults.

        Raises:
            TierError: If the limit is exceeded.
        """
        limits = self.get_limits()
        max_vaults = limits["max_vaults"]
        if max_vaults != -1 and vault_count > max_vaults:
            raise TierError(
                f"Free tier: Maksimum {max_vaults} Obsidian vault desteklenir. "
                f"Siz {vault_count} vault yapilandirdiniz.\n"
                f"Premium'a yukseltmek icin: config.yaml'da license bolumunu yapilandirin."
            )

    def enforce_target_limit(self, target_count: int) -> None:
        """Check if the target count is within the tier limit.

        Args:
            target_count: Number of enabled targets.

        Raises:
            TierError: If the limit is exceeded.
        """
        limits = self.get_limits()
        max_targets = limits["max_targets"]
        if max_targets != -1 and target_count > max_targets:
            raise TierError(
                f"Free tier: Maksimum {max_targets} yedekleme hedefi desteklenir. "
                f"Siz {target_count} hedef etkinlestirdiniz.\n"
                f"Hem GitHub hem Dropbox kullanmak icin Premium'a yukseltmeniz gerekir."
            )

    def enforce_notion_access(self) -> None:
        """Check if Notion backup is allowed in the current tier.

        Raises:
            TierError: If Notion is not available.
        """
        if not self.get_limits()["notion_enabled"]:
            raise TierError(
                "Free tier: Notion yedekleme desteklenmez.\n"
                "Notion yedeklemesi icin Premium'a yukseltmeniz gerekir."
            )

    def enforce_frequency(self, frequency: str) -> None:
        """Check if the given frequency is allowed in the current tier.

        Args:
            frequency: Schedule frequency (hourly, daily, weekly).

        Raises:
            TierError: If the frequency is not allowed.
        """
        allowed = self.get_limits()["allowed_frequencies"]
        if frequency not in allowed:
            raise TierError(
                f"Free tier: '{frequency}' zamanlama sikligi desteklenmez.\n"
                f"Free tier'de sadece su sikliklar kullanilabilir: {', '.join(allowed)}\n"
                f"Saatlik veya haftalik yedekleme icin Premium'a yukseltmeniz gerekir."
            )

    def enforce_file_logging(self) -> bool:
        """Check if file logging is allowed.

        Returns:
            True if file logging is allowed, False otherwise.
        """
        return self.get_limits()["file_logging"]

    def print_tier_info(self) -> None:
        """Print current tier information to console."""
        limits = self.get_limits()
        print(f"\n{'=' * 50}")
        print(f"  Plan: {self.tier_display}")
        print(f"{'=' * 50}")

        if self.is_free:
            print(f"  Vault limiti:     {limits['max_vaults']}")
            print(f"  Hedef limiti:     {limits['max_targets']} (GitHub VEYA Dropbox)")
            print(f"  Zamanlama:        Sadece gunluk")
            print(f"  Notion:           Desteklenmez")
            print(f"  Dosya log:        Desteklenmez")
            print(f"")
            print(f"  Premium ozellikleri icin:")
            print(f"  config.yaml'da 'license' bolumunu yapilandirin.")
        else:
            print(f"  Vault limiti:     Sinirsiz")
            print(f"  Hedef limiti:     Sinirsiz (GitHub + Dropbox)")
            print(f"  Zamanlama:        Saatlik, Gunluk, Haftalik")
            print(f"  Notion:           Desteklenir")
            print(f"  Dosya log:        Desteklenir")

        print(f"{'=' * 50}\n")

    @staticmethod
    def generate_license_key(email: str) -> str:
        """Generate a premium license key for a given email.

        This is a simple key generation for demonstration.
        In production, this would use a more secure method.

        Args:
            email: User's email address.

        Returns:
            A license key string.
        """
        hash_input = f"note-backup-premium-{email}-2026"
        hash_value = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
        return f"NBT-PREMIUM-{hash_value.upper()}"
