"""The one invariant the tooling foundation must already hold."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_the_env_file_cannot_be_committed() -> None:
    """No secret in the clear: `.env` must stay ignored by git."""
    gitignore = REPO_ROOT / ".gitignore"
    assert gitignore.is_file(), "missing .gitignore"
    assert re.search(r"^\.env$", gitignore.read_text(encoding="utf-8"), re.MULTILINE), (
        ".env is not ignored by git — a secret would end up in the history"
    )
