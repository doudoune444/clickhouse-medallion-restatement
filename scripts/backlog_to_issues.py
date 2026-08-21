"""Publie le backlog sur GitHub Issues, une issue par story.

`Product-Engineer/backlog.md` reste la source redactionnelle : ce script en derive
les issues, puis reinjecte dans le fichier le numero de l'issue creee pour chaque
story. Relance sans risque : une story qui porte deja son numero est ignoree.

Usage :
    uv run python scripts/backlog_to_issues.py            # affiche le plan, ne cree rien
    uv run python scripts/backlog_to_issues.py --apply    # cree labels, jalons et issues
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
BACKLOG = RACINE / "Product-Engineer" / "backlog.md"

MOTIF_SESSION = re.compile(r"^# Session (\d+) — (.+)$")
MOTIF_STORY = re.compile(r"^## (S-\d+) · (.+)$")
MOTIF_TYPE = re.compile(r"^\*\*Type\*\* : (\S+)")
MOTIF_LIEN_ISSUE = re.compile(r"^\*\*Issue\*\* : #\d+$")

# Nom de label, couleur, description — pour les quatre types de story du backlog.
LABELS_TYPE = {
    "socle": ("type:socle", "5319e7", "Outillage, environnement, lisibilite"),
    "règle": ("type:regle", "0e8a16", "Transformation deterministe, testable sur fixture"),
    "flux": ("type:flux", "1d76db", "Deplacement de donnees, idempotence, rejeu"),
    "mesure": ("type:mesure", "fbca04", "Protocole de mesure, verdict sur chiffres"),
}

LABEL_BACKLOG = ("backlog", "c2e0c6", "Story issue du backlog produit")

# Qui bloque qui. Repris du plan d'execution en tete de backlog.md.
DEPENDANCES = {
    "S-02": ("S-01",),
    "S-03": ("S-02",),
    "S-04": ("S-03",),
    "S-05": ("S-04",),
    "S-06": ("S-05",),
    "S-07": ("S-06",),
    "S-08": ("S-06",),
    "S-09": ("S-03",),
    "S-10": ("S-07", "S-08", "S-09"),
}


@dataclass(frozen=True)
class Story:
    """Une carte du backlog, prete a devenir une issue."""

    cle: str
    titre: str
    type_: str
    session: str
    corps: str
    ligne_titre: int
    deja_publiee: bool


def lire_stories(lignes: list[str]) -> list[Story]:
    """Decoupe le backlog en stories, dans l'ordre du fichier."""
    stories: list[Story] = []
    session = ""
    for index, ligne in enumerate(lignes):
        session_trouvee = MOTIF_SESSION.match(ligne)
        if session_trouvee:
            session = f"Session {session_trouvee.group(1)} — {session_trouvee.group(2)}"
            continue
        story_trouvee = MOTIF_STORY.match(ligne)
        if not story_trouvee:
            continue
        fin = _fin_de_story(lignes, index)
        corps_lignes = lignes[index + 1 : fin]
        stories.append(
            Story(
                cle=story_trouvee.group(1),
                titre=story_trouvee.group(2).strip(),
                type_=_type_de_story(corps_lignes),
                session=session,
                corps="\n".join(_sans_separateur_final(corps_lignes)).strip(),
                ligne_titre=index,
                deja_publiee=any(MOTIF_LIEN_ISSUE.match(corps) for corps in corps_lignes),
            )
        )
    return stories


def _fin_de_story(lignes: list[str], debut: int) -> int:
    """Retourne l'index de la premiere ligne qui n'appartient plus a la story."""
    for index in range(debut + 1, len(lignes)):
        if lignes[index].startswith(("# ", "## ")):
            return index
    return len(lignes)


def _sans_separateur_final(corps: list[str]) -> list[str]:
    """Retire le `---` et les lignes vides qui closent une story."""
    fin = len(corps)
    while fin > 0 and corps[fin - 1].strip() in {"", "---"}:
        fin -= 1
    return corps[:fin]


def _type_de_story(corps: list[str]) -> str:
    for ligne in corps:
        trouve = MOTIF_TYPE.match(ligne)
        if trouve:
            return trouve.group(1)
    return "socle"


def corps_issue(story: Story, numeros: dict[str, int]) -> str:
    """Compose le corps de l'issue : entete de contexte, puis la story telle quelle."""
    bloquants = [f"#{numeros[cle]}" for cle in DEPENDANCES.get(story.cle, ()) if cle in numeros]
    entete = [f"**Session** : {story.session}"]
    if bloquants:
        entete.append(f"**Bloquee par** : {', '.join(bloquants)}")
    return "\n".join(entete) + "\n\n---\n\n" + story.corps + "\n"


def gh(*arguments: str, entree: str | None = None) -> str:
    """Appelle la CLI GitHub et retourne sa sortie standard."""
    resultat = subprocess.run(  # noqa: S603
        ["gh", *arguments],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
        input=entree,
    )
    return resultat.stdout.strip()


def creer_labels() -> None:
    """Cree les labels de type et le label `backlog`, sans echouer s'ils existent."""
    for nom, couleur, description in [*LABELS_TYPE.values(), LABEL_BACKLOG]:
        gh("label", "create", nom, "--color", couleur, "--description", description, "--force")
        print(f"  label  {nom}")


def creer_jalon(titre: str) -> None:
    """Cree un jalon GitHub, ou le laisse tel quel s'il existe deja."""
    try:
        gh("api", "--method", "POST", "repos/{owner}/{repo}/milestones", "-f", f"title={titre}")
    except subprocess.CalledProcessError as erreur:
        if "already_exists" not in (erreur.stderr or ""):
            raise
        print(f"  jalon  {titre} (existe deja)")
        return
    print(f"  jalon  {titre}")


def creer_issue(story: Story, numeros: dict[str, int]) -> int:
    """Cree l'issue de la story et retourne son numero."""
    label_type = LABELS_TYPE[story.type_][0]
    url = gh(
        "issue",
        "create",
        "--title",
        f"{story.cle} · {story.titre}",
        "--body-file",
        "-",
        "--label",
        label_type,
        "--label",
        LABEL_BACKLOG[0],
        "--milestone",
        story.session,
        entree=corps_issue(story, numeros),
    )
    return int(url.rstrip("/").rsplit("/", 1)[-1])


def injecter_numeros(lignes: list[str], numeros_par_ligne: dict[int, int]) -> list[str]:
    """Insere `**Issue** : #N` juste sous le titre de chaque story publiee."""
    resultat: list[str] = []
    for index, ligne in enumerate(lignes):
        resultat.append(ligne)
        numero = numeros_par_ligne.get(index)
        if numero is not None:
            resultat.extend(["", f"**Issue** : #{numero}"])
    return resultat


def main() -> int:
    """Point d'entree."""
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument(
        "--apply",
        action="store_true",
        help="cree reellement les labels, jalons et issues (sinon, affiche le plan)",
    )
    options = analyseur.parse_args()

    lignes = BACKLOG.read_text(encoding="utf-8").splitlines()
    stories = lire_stories(lignes)
    a_publier = [story for story in stories if not story.deja_publiee]

    print(f"{len(stories)} stories lues, {len(a_publier)} a publier.")
    for story in stories:
        etat = "deja publiee" if story.deja_publiee else "a creer"
        print(f"  {story.cle}  {story.type_:<7} {etat:<13} {story.titre}")

    if not options.apply:
        print("\nPlan uniquement. Relancer avec --apply pour creer les issues.")
        return 0

    if shutil.which("gh") is None:
        print("\nLa CLI GitHub (`gh`) est introuvable. Installer gh puis `gh auth login`.")
        return 1

    print("\nLabels et jalons :")
    creer_labels()
    for titre in dict.fromkeys(story.session for story in a_publier):
        creer_jalon(titre)

    print("\nIssues :")
    numeros: dict[str, int] = {}
    numeros_par_ligne: dict[int, int] = {}
    for story in a_publier:
        numero = creer_issue(story, numeros)
        numeros[story.cle] = numero
        numeros_par_ligne[story.ligne_titre] = numero
        print(f"  #{numero:<4} {story.cle} · {story.titre}")

    BACKLOG.write_text("\n".join(injecter_numeros(lignes, numeros_par_ligne)) + "\n", "utf-8")
    print(f"\n{BACKLOG.relative_to(RACINE)} met a jour avec les numeros d'issue.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
