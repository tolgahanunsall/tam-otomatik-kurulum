"""GitHub backup target.

Pushes backup files to a GitHub repository using GitPython.
"""

import logging
import os
import shutil
from datetime import datetime
from typing import Any, Dict, Optional

from git import Repo, InvalidGitRepositoryError

logger = logging.getLogger("note-backup")


class GitHubBackup:
    """Handles pushing backup files to a GitHub repository."""

    def __init__(self, config: Dict[str, Any]):
        self.token: str = config.get("token", "")
        self.repository: str = config.get("repository", "")
        self.branch: str = config.get("branch", "main")
        self.commit_message_template: str = config.get(
            "commit_message", "Otomatik yedekleme: {date}"
        )

    def _get_remote_url(self) -> str:
        """Build the authenticated remote URL."""
        return f"https://x-access-token:{self.token}@github.com/{self.repository}.git"

    def upload(self, source_dir: str, work_dir: str) -> bool:
        """Upload backup files to GitHub.

        Args:
            source_dir: Directory containing the backed-up files.
            work_dir: Working directory for git operations.

        Returns:
            True if upload succeeded, False otherwise.
        """
        repo_dir = os.path.join(work_dir, "github_repo")
        remote_url = self._get_remote_url()

        try:
            # Clone or open existing repo
            repo = self._prepare_repo(repo_dir, remote_url)

            # Ensure we're on the correct branch
            self._ensure_branch(repo)

            # Clear existing content (except .git)
            self._clear_repo_content(repo_dir)

            # Copy backup files to repo
            self._copy_backup_files(source_dir, repo_dir)

            # Check if there are changes
            if not repo.is_dirty(untracked_files=True):
                logger.info("GitHub: No changes detected, skipping commit.")
                return True

            # Stage all changes
            repo.git.add(A=True)

            # Commit
            commit_msg = self.commit_message_template.format(
                date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            repo.index.commit(commit_msg)
            logger.info("GitHub: Committed changes: %s", commit_msg)

            # Push
            origin = repo.remote("origin")
            origin.push(self.branch)
            logger.info(
                "GitHub: Successfully pushed to %s/%s",
                self.repository,
                self.branch,
            )
            return True

        except Exception as e:
            logger.error("GitHub backup failed: %s", e)
            return False

    def _prepare_repo(self, repo_dir: str, remote_url: str) -> Repo:
        """Clone or open the git repository."""
        if os.path.isdir(os.path.join(repo_dir, ".git")):
            try:
                repo = Repo(repo_dir)
                # Update remote URL (in case token changed)
                if "origin" in [r.name for r in repo.remotes]:
                    repo.remote("origin").set_url(remote_url)
                # Pull latest changes
                try:
                    repo.remote("origin").pull(self.branch)
                except Exception:
                    logger.debug("Pull failed, continuing with local state.")
                return repo
            except InvalidGitRepositoryError:
                shutil.rmtree(repo_dir, ignore_errors=True)

        # Clone fresh
        logger.info("GitHub: Cloning repository %s...", self.repository)
        os.makedirs(repo_dir, exist_ok=True)

        try:
            repo = Repo.clone_from(remote_url, repo_dir, branch=self.branch)
        except Exception:
            # If branch doesn't exist yet, clone default and create branch
            repo = Repo.clone_from(remote_url, repo_dir)
            if self.branch not in [ref.name for ref in repo.references]:
                repo.git.checkout("-b", self.branch)

        return repo

    def _ensure_branch(self, repo: Repo) -> None:
        """Ensure we're on the correct branch."""
        current = repo.active_branch.name
        if current != self.branch:
            if self.branch in [ref.name for ref in repo.heads]:
                repo.git.checkout(self.branch)
            else:
                repo.git.checkout("-b", self.branch)

    def _clear_repo_content(self, repo_dir: str) -> None:
        """Remove all files from repo directory except .git."""
        for item in os.listdir(repo_dir):
            if item == ".git":
                continue
            item_path = os.path.join(repo_dir, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)

    def _copy_backup_files(self, source: str, dest: str) -> None:
        """Copy all backup files from source to destination."""
        for item in os.listdir(source):
            src_path = os.path.join(source, item)
            dst_path = os.path.join(dest, item)
            if os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
            else:
                shutil.copy2(src_path, dst_path)
