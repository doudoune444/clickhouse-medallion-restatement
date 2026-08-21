"""Le seul invariant que le socle d'outillage doit tenir des maintenant."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_le_fichier_env_n_est_pas_versionnable() -> None:
    """Aucun secret en clair : `.env` doit rester ignore par git."""
    gitignore = REPO_ROOT / ".gitignore"
    assert gitignore.is_file(), ".gitignore absent"
    assert re.search(r"^\.env$", gitignore.read_text(encoding="utf-8"), re.MULTILINE), (
        ".env n'est pas ignore par git — un secret finirait dans l'historique"
    )
