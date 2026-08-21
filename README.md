# Pipeline médaillon ClickHouse — absorber la révision tardive des chiffres publicitaires

Les régies publicitaires révisent leurs chiffres jusqu'à trente jours après coup :
une conversion attribuée tardivement modifie un rapport déjà ingéré. Un pipeline naïf
ré-ingère le fichier corrigé et compte la dépense deux fois. C'est ce que ce projet résout.

**État : S-00 — socle d'outillage.** Le pipeline n'existe pas encore. Les dix stories qui
le livrent sont ouvertes en [issues](../../issues) ; ce README grandit avec elles.

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
docs/                           décisions techniques argumentées
scripts/                        outillage du dépôt
tests/                          suite de tests
```

## Méthode de travail

Une story = une issue = une branche = une PR. Chaque issue porte son contrat d'exécution :
les critères d'acceptation, les arbitrages et leur motif, et la condition de « fini ».
Chaque PR ouvre sa description par `Closes #N` — la CI la refuse sinon.
