# Pipeline médaillon ClickHouse — absorber la révision tardive des chiffres publicitaires

Les régies publicitaires révisent leurs chiffres jusqu'à trente jours après coup :
une conversion attribuée tardivement modifie un rapport déjà ingéré. Un pipeline naïf
ré-ingère le fichier corrigé et compte la dépense deux fois. C'est ce que ce projet résout.

**État : S-00 — socle d'outillage.** Le pipeline n'existe pas encore. Les dix cartes qui
le livrent sont dans `Product-Engineer/backlog.md` ; ce README grandit avec elles.

## Démarrer

| Outil | Version | Note |
|---|---|---|
| WSL2 + Ubuntu 24.04 | — | le dépôt vit dans le FS Linux, pas sur `/mnt/c` |
| `uv` | ≥ 0.12 | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| GNU Make | ≥ 4.3 | fourni par Ubuntu |

```bash
make install   # dépendances + hooks pre-commit
make help      # liste des cibles
make lint      # ruff, ruff format, mypy strict, yamllint, actionlint, gitleaks
make test      # pytest
```

## Structure

```text
Product-Engineer/backlog.md     les dix cartes, contrats d'exécution
docs/                           décisions techniques argumentées
tests/                          suite de tests
```
