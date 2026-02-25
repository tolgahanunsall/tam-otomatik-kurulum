"""Notion backup source using the Notion API.

Exports Notion pages and databases to Markdown or HTML format via the
official Notion API. Requires an integration token.
"""

import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger("note-backup")

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_API_VERSION = "2022-06-28"


class NotionBackup:
    """Handles backing up Notion pages and databases."""

    def __init__(self, config: Dict[str, Any]):
        self.api_token: str = config.get("api_token", "")
        self.page_ids: List[str] = config.get("page_ids", [])
        self.database_ids: List[str] = config.get("database_ids", [])
        self.export_format: str = config.get("export_format", "markdown")
        self._headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Notion-Version": NOTION_API_VERSION,
            "Content-Type": "application/json",
        }

    def backup(self, dest_dir: str) -> List[str]:
        """Back up Notion pages and databases.

        Args:
            dest_dir: Base destination directory for backups.

        Returns:
            List of paths where content was saved.
        """
        notion_dest = os.path.join(dest_dir, "notion")
        os.makedirs(notion_dest, exist_ok=True)
        saved_paths: List[str] = []

        # If no specific IDs given, search for all accessible pages
        if not self.page_ids and not self.database_ids:
            logger.info("No specific page/database IDs configured. Fetching all accessible content...")
            self._backup_all_pages(notion_dest, saved_paths)
            self._backup_all_databases(notion_dest, saved_paths)
        else:
            # Backup specific pages
            for page_id in self.page_ids:
                try:
                    path = self._backup_page(page_id, notion_dest)
                    if path:
                        saved_paths.append(path)
                except Exception as e:
                    logger.error("Failed to backup page %s: %s", page_id, e)

            # Backup specific databases
            for db_id in self.database_ids:
                try:
                    path = self._backup_database(db_id, notion_dest)
                    if path:
                        saved_paths.append(path)
                except Exception as e:
                    logger.error("Failed to backup database %s: %s", db_id, e)

        logger.info("Notion backup complete: %d items saved.", len(saved_paths))
        return saved_paths

    def _api_get(self, endpoint: str) -> Dict[str, Any]:
        """Make a GET request to the Notion API."""
        url = f"{NOTION_API_BASE}{endpoint}"
        response = requests.get(url, headers=self._headers, timeout=30)
        response.raise_for_status()
        return response.json()

    def _api_post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a POST request to the Notion API."""
        url = f"{NOTION_API_BASE}{endpoint}"
        response = requests.post(url, headers=self._headers, json=data or {}, timeout=30)
        response.raise_for_status()
        return response.json()

    def _get_block_children(self, block_id: str) -> List[Dict[str, Any]]:
        """Recursively get all child blocks of a block."""
        all_blocks: List[Dict[str, Any]] = []
        start_cursor: Optional[str] = None

        while True:
            endpoint = f"/blocks/{block_id}/children?page_size=100"
            if start_cursor:
                endpoint += f"&start_cursor={start_cursor}"

            result = self._api_get(endpoint)
            blocks = result.get("results", [])
            all_blocks.extend(blocks)

            # Recursively get children
            for block in blocks:
                if block.get("has_children", False):
                    children = self._get_block_children(block["id"])
                    block["children"] = children

            if not result.get("has_more", False):
                break
            start_cursor = result.get("next_cursor")

        return all_blocks

    def _block_to_markdown(self, block: Dict[str, Any], indent: int = 0) -> str:
        """Convert a Notion block to Markdown text."""
        block_type = block.get("type", "")
        prefix = "  " * indent
        text = ""

        rich_text_types = [
            "paragraph", "heading_1", "heading_2", "heading_3",
            "bulleted_list_item", "numbered_list_item", "to_do",
            "toggle", "quote", "callout",
        ]

        if block_type in rich_text_types:
            content = self._rich_text_to_string(
                block.get(block_type, {}).get("rich_text", [])
            )

            if block_type == "paragraph":
                text = f"{prefix}{content}\n\n"
            elif block_type == "heading_1":
                text = f"{prefix}# {content}\n\n"
            elif block_type == "heading_2":
                text = f"{prefix}## {content}\n\n"
            elif block_type == "heading_3":
                text = f"{prefix}### {content}\n\n"
            elif block_type == "bulleted_list_item":
                text = f"{prefix}- {content}\n"
            elif block_type == "numbered_list_item":
                text = f"{prefix}1. {content}\n"
            elif block_type == "to_do":
                checked = block.get(block_type, {}).get("checked", False)
                checkbox = "[x]" if checked else "[ ]"
                text = f"{prefix}- {checkbox} {content}\n"
            elif block_type == "toggle":
                text = f"{prefix}<details><summary>{content}</summary>\n\n"
            elif block_type == "quote":
                text = f"{prefix}> {content}\n\n"
            elif block_type == "callout":
                icon = block.get(block_type, {}).get("icon", {}).get("emoji", "")
                text = f"{prefix}> {icon} {content}\n\n"

        elif block_type == "code":
            code_content = self._rich_text_to_string(
                block.get("code", {}).get("rich_text", [])
            )
            language = block.get("code", {}).get("language", "")
            text = f"{prefix}```{language}\n{code_content}\n```\n\n"

        elif block_type == "divider":
            text = f"{prefix}---\n\n"

        elif block_type == "image":
            image_data = block.get("image", {})
            url = ""
            if image_data.get("type") == "external":
                url = image_data.get("external", {}).get("url", "")
            elif image_data.get("type") == "file":
                url = image_data.get("file", {}).get("url", "")
            caption = self._rich_text_to_string(image_data.get("caption", []))
            text = f"{prefix}![{caption}]({url})\n\n"

        elif block_type == "bookmark":
            url = block.get("bookmark", {}).get("url", "")
            text = f"{prefix}[Bookmark]({url})\n\n"

        elif block_type == "table":
            # Tables are handled through children
            pass

        elif block_type == "table_row":
            cells = block.get("table_row", {}).get("cells", [])
            row_text = " | ".join(
                self._rich_text_to_string(cell) for cell in cells
            )
            text = f"{prefix}| {row_text} |\n"

        # Process children
        children = block.get("children", [])
        if children:
            for child in children:
                text += self._block_to_markdown(child, indent + 1)
            if block_type == "toggle":
                text += f"{prefix}</details>\n\n"

        return text

    def _rich_text_to_string(self, rich_text: List[Dict[str, Any]]) -> str:
        """Convert Notion rich text array to a plain/markdown string."""
        parts: List[str] = []
        for segment in rich_text:
            plain = segment.get("plain_text", "")
            annotations = segment.get("annotations", {})

            if annotations.get("bold"):
                plain = f"**{plain}**"
            if annotations.get("italic"):
                plain = f"*{plain}*"
            if annotations.get("strikethrough"):
                plain = f"~~{plain}~~"
            if annotations.get("code"):
                plain = f"`{plain}`"

            href = segment.get("href")
            if href:
                plain = f"[{plain}]({href})"

            parts.append(plain)

        return "".join(parts)

    def _get_page_title(self, page: Dict[str, Any]) -> str:
        """Extract page title from a Notion page object."""
        properties = page.get("properties", {})
        for prop_name, prop_data in properties.items():
            if prop_data.get("type") == "title":
                title_parts = prop_data.get("title", [])
                return self._rich_text_to_string(title_parts) or "Untitled"
        return "Untitled"

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize a string for use as a filename."""
        name = re.sub(r'[<>:"/\\|?*]', "_", name)
        name = name.strip(". ")
        return name[:200] if name else "untitled"

    def _backup_page(self, page_id: str, dest_dir: str) -> Optional[str]:
        """Backup a single Notion page."""
        logger.info("Backing up Notion page: %s", page_id)

        # Get page metadata
        page = self._api_get(f"/pages/{page_id}")
        title = self._get_page_title(page)
        safe_title = self._sanitize_filename(title)

        # Get page content
        blocks = self._get_block_children(page_id)

        # Convert to markdown
        content = f"# {title}\n\n"
        for block in blocks:
            content += self._block_to_markdown(block)

        # Save to file
        ext = "md" if self.export_format == "markdown" else "html"
        filename = f"{safe_title}.{ext}"
        filepath = os.path.join(dest_dir, "pages", filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info("Saved page '%s' to %s", title, filepath)
        return filepath

    def _backup_database(self, db_id: str, dest_dir: str) -> Optional[str]:
        """Backup a Notion database and its entries."""
        logger.info("Backing up Notion database: %s", db_id)

        # Get database metadata
        db = self._api_get(f"/databases/{db_id}")
        db_title_parts = db.get("title", [])
        db_title = self._rich_text_to_string(db_title_parts) or "Untitled Database"
        safe_title = self._sanitize_filename(db_title)

        db_dest = os.path.join(dest_dir, "databases", safe_title)
        os.makedirs(db_dest, exist_ok=True)

        # Save database schema
        schema_path = os.path.join(db_dest, "_schema.json")
        with open(schema_path, "w", encoding="utf-8") as f:
            json.dump(db.get("properties", {}), f, indent=2, ensure_ascii=False)

        # Query all entries
        entries: List[Dict[str, Any]] = []
        start_cursor: Optional[str] = None

        while True:
            payload: Dict[str, Any] = {"page_size": 100}
            if start_cursor:
                payload["start_cursor"] = start_cursor

            result = self._api_post(f"/databases/{db_id}/query", payload)
            entries.extend(result.get("results", []))

            if not result.get("has_more", False):
                break
            start_cursor = result.get("next_cursor")

        # Backup each entry
        for entry in entries:
            try:
                self._backup_page(entry["id"], db_dest)
            except Exception as e:
                logger.error("Failed to backup database entry %s: %s", entry["id"], e)

        logger.info("Database '%s': %d entries backed up.", db_title, len(entries))
        return db_dest

    def _backup_all_pages(self, dest_dir: str, saved_paths: List[str]) -> None:
        """Search and backup all accessible pages."""
        logger.info("Searching for all accessible Notion pages...")
        start_cursor: Optional[str] = None

        while True:
            payload: Dict[str, Any] = {
                "filter": {"property": "object", "value": "page"},
                "page_size": 100,
            }
            if start_cursor:
                payload["start_cursor"] = start_cursor

            result = self._api_post("/search", payload)
            pages = result.get("results", [])

            for page in pages:
                if page.get("object") == "page":
                    try:
                        path = self._backup_page(page["id"], dest_dir)
                        if path:
                            saved_paths.append(path)
                    except Exception as e:
                        logger.error("Failed to backup page %s: %s", page["id"], e)
                    # Rate limiting
                    time.sleep(0.35)

            if not result.get("has_more", False):
                break
            start_cursor = result.get("next_cursor")

    def _backup_all_databases(self, dest_dir: str, saved_paths: List[str]) -> None:
        """Search and backup all accessible databases."""
        logger.info("Searching for all accessible Notion databases...")
        start_cursor: Optional[str] = None

        while True:
            payload: Dict[str, Any] = {
                "filter": {"property": "object", "value": "database"},
                "page_size": 100,
            }
            if start_cursor:
                payload["start_cursor"] = start_cursor

            result = self._api_post("/search", payload)
            databases = result.get("results", [])

            for db in databases:
                if db.get("object") == "database":
                    try:
                        path = self._backup_database(db["id"], dest_dir)
                        if path:
                            saved_paths.append(path)
                    except Exception as e:
                        logger.error("Failed to backup database %s: %s", db["id"], e)
                    time.sleep(0.35)

            if not result.get("has_more", False):
                break
            start_cursor = result.get("next_cursor")
