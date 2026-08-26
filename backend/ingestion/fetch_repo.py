"""
ingestion/fetch_repo.py

Shallow git clone or pull of the lennys-podcast-transcripts repository.
Returns the current HEAD commit SHA so it can be recorded in ingestion_runs.
"""

import os
from pathlib import Path

import git

from core.logging import get_logger

logger = get_logger(__name__)


def fetch_transcripts_repo(repo_url: str, local_path: str) -> str:
    """
    Clone the repo if it doesn't exist locally; otherwise pull latest changes.

    Args:
        repo_url:    Remote URL (e.g. https://github.com/ChatPRD/lennys-podcast-transcripts.git)
        local_path:  Local filesystem path to clone/pull into.

    Returns:
        The HEAD commit SHA string.
    """
    path = Path(local_path)

    if path.exists() and (path / ".git").exists():
        # Repository already exists — pull latest
        logger.info("git_pull_start", path=str(path))
        repo = git.Repo(str(path))
        origin = repo.remotes.origin
        origin.pull()
        sha = repo.head.commit.hexsha
        logger.info("git_pull_done", sha=sha[:8])
    else:
        # Fresh clone
        path.mkdir(parents=True, exist_ok=True)
        logger.info("git_clone_start", url=repo_url, path=str(path))
        repo = git.Repo.clone_from(
            url=repo_url,
            to_path=str(path),
            depth=1,  # shallow clone — we only need current state
        )
        sha = repo.head.commit.hexsha
        logger.info("git_clone_done", sha=sha[:8])

    return sha
