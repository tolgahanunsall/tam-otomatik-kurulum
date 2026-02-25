"""Obsidian vault backup source.

Obsidian vaults are simply directories of Markdown files, so backing them up
is a straightforward file-system copy with optional exclude patterns.
"""

import fnmatch
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("note-backup")


class ObsidianBackup:
    """Handles backing up Obsidian vault directories."""

    def __init__(self, config: Dict[str, Any]):
        self.vaults: List[Dict[str, str]] = config.get("vaults", [])
        self.exclude_patterns: List[str] = config.get("exclude_patterns", [])

    def _should_exclude(self, relative_path: str) -> bool:
        """Check if a path matches any exclude pattern."""
        for pattern in self.exclude_patterns:
            # Normalize separators for cross-platform matching
            normalized_pattern = pattern.replace("\\", "/")
            normalized_path = relative_path.replace("\\", "/")
            if fnmatch.fnmatch(normalized_path, normalized_pattern):
                return True
            # Also check if the path starts with a directory pattern
            if normalized_pattern.endswith("/") and normalized_path.startswith(
                normalized_pattern
            ):
                return True
            if not normalized_pattern.endswith("/") and normalized_path.startswith(
                normalized_pattern + "/"
            ):
                return True
        return False

    def backup(self, dest_dir: str) -> List[str]:
        """Back up all configured Obsidian vaults to the destination directory.

        Args:
            dest_dir: Base destination directory for backups.

        Returns:
            List of backed-up vault paths.
        """
        backed_up_paths: List[str] = []

        for vault in self.vaults:
            vault_name = vault["name"]
            vault_path = os.path.expanduser(vault["path"])

            if not os.path.isdir(vault_path):
                logger.warning(
                    "Obsidian vault not found, skipping: %s (%s)",
                    vault_name,
                    vault_path,
                )
                continue

            vault_dest = os.path.join(dest_dir, "obsidian", vault_name)
            logger.info(
                "Backing up Obsidian vault '%s': %s -> %s",
                vault_name,
                vault_path,
                vault_dest,
            )

            file_count = self._copy_vault(vault_path, vault_dest)
            logger.info(
                "Obsidian vault '%s': %d files backed up.", vault_name, file_count
            )
            backed_up_paths.append(vault_dest)

        return backed_up_paths

    def _copy_vault(self, source: str, dest: str) -> int:
        """Copy vault files to destination, respecting exclude patterns.

        Args:
            source: Source vault directory.
            dest: Destination directory.

        Returns:
            Number of files copied.
        """
        file_count = 0
        source_path = Path(source)

        for root, dirs, files in os.walk(source):
            rel_root = os.path.relpath(root, source)
            if rel_root == ".":
                rel_root = ""

            # Filter excluded directories (modify in-place to skip them)
            filtered_dirs = []
            for d in dirs:
                rel_dir = os.path.join(rel_root, d) if rel_root else d
                if not self._should_exclude(rel_dir):
                    filtered_dirs.append(d)
            dirs[:] = filtered_dirs

            for filename in files:
                rel_file = os.path.join(rel_root, filename) if rel_root else filename
                if self._should_exclude(rel_file):
                    continue

                src_file = os.path.join(root, filename)
                dest_file = os.path.join(dest, rel_file)

                dest_file_dir = os.path.dirname(dest_file)
                os.makedirs(dest_file_dir, exist_ok=True)

                shutil.copy2(src_file, dest_file)
                file_count += 1

        return file_count
