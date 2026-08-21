# Pipeline médaillon ClickHouse — absorber la révision tardive des chiffres publicitaires

Les régies publicitaires révisent leurs chiffres jusqu'à trente jours après coup :
une conversion attribuée tardivement modifie un rapport déjà ingéré. Un pipeline naïf
ré-ingère le fichier corrigé et compte la dépense deux fois. C'est ce que ce projet résout.

**État : S-01 — socle exécutable.** ClickHouse et MinIO démarrent en une commande ; le
pipeline lui-même n'existe pas encore. Les stories qui le livrent sont ouvertes en
[issues](../../issues) ; ce README grandit avec elles.

## Démarrer

| Outil | Version | Note |
|---|---|---|
| WSL2 + Ubuntu 24.04 | — | le dépôt vit dans le FS Linux, pas sur `/mnt/c` |
| `uv` | ≥ 0.12 | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| GNU Make | ≥ 4.3 | fourni par Ubuntu |
| Docker Engine / Desktop | ≥ 24 | intégration WSL activée, 8 Go de mémoire |

```bash
make install     # dépendances + hooks pre-commit
make up          # ClickHouse + MinIO + DDL — relançable sans dérive
make seed        # jeu de référence déterministe dans bronze.ads_raw
make scenarios   # rejoue scenarios/*.sh
make test        # pytest
make down        # détruit la stack ET ses volumes
```

`make up` copie `.env.example` en `.env` s'il est absent. Les identifiants MinIO ne vivent
que là : `docker-compose.yml` et la configuration ClickHouse ne les lisent que par
variable d'environnement (`from_env`).

| Service | Adresse | Usage |
|---|---|---|
| ClickHouse HTTP | `127.0.0.1:8123` | requêtes |
| ClickHouse natif | `127.0.0.1:9000` | `clickhouse-client` |
| MinIO S3 | `127.0.0.1:10000` | buckets `lake` (fichiers des régies) et `medallion` (données ClickHouse) |
| MinIO console | `127.0.0.1:10001` | inspection |

## Structure

```text
docker/clickhouse/config.d/     configuration ClickHouse — le lac de données sur MinIO
docs/                           décisions techniques argumentées
scenarios/                      scénarios exécutables, un par story
scripts/                        outillage du dépôt
sql/ddl/                        DDL versionné, appliqué par `make up`
sql/seed/                       jeu de référence déterministe
tests/                          suite de tests
```

Le disque ClickHouse s'appelle `data_lake` et sa politique de stockage
`store_on_data_lake` : une table créée avec
`SETTINGS storage_policy = 'store_on_data_lake'` range ses données sur MinIO plutôt que
sur le disque local.

**Langue** : tout ce qui est nommé dans le code est en anglais — fichiers, identifiants,
cibles `make`, services et volumes Docker, commentaires. Le français est réservé à la
documentation destinée au lecteur : ce README, `docs/`, et les descriptions d'issues.

## Le socle

`docker-compose.yml` est **dérivé** de la recette officielle
[`ClickHouse/examples` · `docker-compose-recipes/recipes/ch-and-minio-S3`](https://github.com/ClickHouse/examples/tree/main/docker-compose-recipes/recipes/ch-and-minio-S3),
qui câble déjà un disque ClickHouse de type S3 pointant vers MinIO. Les adaptations sont
les versions épinglées, les buckets du projet, et les secrets sortis du fichier.

**MinIO plutôt qu'un vrai bucket AWS** : MinIO expose une API S3 compatible, donc le code
d'ingestion sera identique face à un vrai bucket — seules l'URL et l'authentification
changent. Ce que ce choix **ne prouve pas** : l'infrastructure cloud réelle, l'IaC, les
politiques IAM, les coûts et latences d'un S3 distant. S-09 rejoue les mesures depuis un
vrai bucket S3 public pour combler une partie de cet écart.

`make down` supprime les volumes : c'est délibéré, `make up && make seed` doit redonner
exactement les mêmes checksums, et c'est ce que vérifie le test `S-01/R2`.

## Méthode de travail

Une story = une issue = une branche = une PR. Chaque issue porte son contrat d'exécution :
les critères d'acceptation, les arbitrages et leur motif, et la condition de « fini ».
Chaque PR ouvre sa description par `Closes #N` — la CI la refuse sinon.
