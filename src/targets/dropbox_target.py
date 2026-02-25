"""Dropbox backup target.

Uploads backup files to Dropbox using the Dropbox API v2.
Supports both short-lived access tokens and long-lived refresh tokens.
"""

import logging
import os
from typing import Any, Dict

import dropbox
from dropbox.exceptions import ApiError, AuthError
from dropbox.files import WriteMode

logger = logging.getLogger("note-backup")

# Dropbox API has a 150 MB limit for simple uploads
UPLOAD_SIZE_LIMIT = 150 * 1024 * 1024  # 150 MB
CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB for chunked uploads


class DropboxBackup:
    """Handles uploading backup files to Dropbox."""

    def __init__(self, config: Dict[str, Any]):
        self.access_token: str = config.get("access_token", "")
        self.refresh_token: str = config.get("refresh_token", "")
        self.app_key: str = config.get("app_key", "")
        self.app_secret: str = config.get("app_secret", "")
        self.remote_path: str = config.get("remote_path", "/NoteBackups")
        self._dbx: dropbox.Dropbox = self._create_client()

    def _create_client(self) -> dropbox.Dropbox:
        """Create and return a Dropbox client."""
        if self.refresh_token and self.app_key:
            return dropbox.Dropbox(
                oauth2_refresh_token=self.refresh_token,
                app_key=self.app_key,
                app_secret=self.app_secret if self.app_secret else None,
            )
        return dropbox.Dropbox(self.access_token)

    def upload(self, source_dir: str) -> bool:
        """Upload backup files to Dropbox.

        Args:
            source_dir: Directory containing the backed-up files.

        Returns:
            True if upload succeeded, False otherwise.
        """
        try:
            # Verify connection
            account = self._dbx.users_get_current_account()
            logger.info("Dropbox: Connected as %s", account.name.display_name)
        except AuthError as e:
            logger.error("Dropbox authentication failed: %s", e)
            return False

        try:
            file_count = self._upload_directory(source_dir, self.remote_path)
            logger.info(
                "Dropbox: Successfully uploaded %d files to %s",
                file_count,
                self.remote_path,
            )
            return True
        except Exception as e:
            logger.error("Dropbox backup failed: %s", e)
            return False

    def _upload_directory(self, local_dir: str, remote_dir: str) -> int:
        """Recursively upload a directory to Dropbox.

        Args:
            local_dir: Local directory path.
            remote_dir: Remote Dropbox directory path.

        Returns:
            Number of files uploaded.
        """
        file_count = 0

        for root, dirs, files in os.walk(local_dir):
            rel_root = os.path.relpath(root, local_dir)
            if rel_root == ".":
                rel_root = ""

            for filename in files:
                local_path = os.path.join(root, filename)
                if rel_root:
                    remote_file_path = f"{remote_dir}/{rel_root}/{filename}"
                else:
                    remote_file_path = f"{remote_dir}/{filename}"

                # Normalize path separators for Dropbox (always use /)
                remote_file_path = remote_file_path.replace("\\", "/")

                try:
                    self._upload_file(local_path, remote_file_path)
                    file_count += 1
                except Exception as e:
                    logger.error(
                        "Failed to upload %s to %s: %s",
                        local_path,
                        remote_file_path,
                        e,
                    )

        return file_count

    def _upload_file(self, local_path: str, remote_path: str) -> None:
        """Upload a single file to Dropbox.

        Uses chunked upload for files larger than UPLOAD_SIZE_LIMIT.

        Args:
            local_path: Path to the local file.
            remote_path: Destination path on Dropbox.
        """
        file_size = os.path.getsize(local_path)

        with open(local_path, "rb") as f:
            if file_size <= UPLOAD_SIZE_LIMIT:
                # Simple upload
                self._dbx.files_upload(
                    f.read(),
                    remote_path,
                    mode=WriteMode.overwrite,
                )
            else:
                # Chunked upload for large files
                self._chunked_upload(f, remote_path, file_size)

        logger.debug("Uploaded: %s -> %s", local_path, remote_path)

    def _chunked_upload(self, file_obj: Any, remote_path: str, file_size: int) -> None:
        """Perform a chunked upload for large files.

        Args:
            file_obj: Open file object.
            remote_path: Destination path on Dropbox.
            file_size: Total file size in bytes.
        """
        # Start upload session
        chunk = file_obj.read(CHUNK_SIZE)
        session = self._dbx.files_upload_session_start(chunk)
        cursor = dropbox.files.UploadSessionCursor(
            session_id=session.session_id,
            offset=file_obj.tell(),
        )
        commit = dropbox.files.CommitInfo(
            path=remote_path,
            mode=WriteMode.overwrite,
        )

        # Upload remaining chunks
        while file_obj.tell() < file_size:
            remaining = file_size - file_obj.tell()
            if remaining <= CHUNK_SIZE:
                # Last chunk — finish the session
                chunk = file_obj.read(CHUNK_SIZE)
                self._dbx.files_upload_session_finish(chunk, cursor, commit)
            else:
                chunk = file_obj.read(CHUNK_SIZE)
                self._dbx.files_upload_session_append_v2(chunk, cursor)
                cursor.offset = file_obj.tell()
