# ClickHouse vs PostgreSQL vs non-relationnel — note de compréhension

*Document de montée en compétence. Objectif : comprendre les enjeux avant de coder.*
*Date : 2026-08-20*

---

## 1. Le point de départ : OLTP vs OLAP

- **OLTP** — Charge de travail faite de nombreuses petites opérations qui lisent ou modifient quelques lignes précises (créer un compte, valider une commande).
- **OLAP** — Charge de travail faite de peu de requêtes qui balayent des millions de lignes pour produire des agrégats (CA par campagne sur 90 jours).
- **Le vrai clivage** — Ce n'est pas « quelle base est la meilleure » mais « quelle forme de charge de travail », et une base optimisée pour l'une est structurellement mauvaise pour l'autre.
- **Pourquoi on entend souvent que ClickHouse est « mieux »** — Sur une charge de travail publicitaire (volumes massifs, append-only, agrégations lourdes) ClickHouse est effectivement 10 à 100× plus rapide que Postgres, mais l'affirmation n'est pas universelle.
- **La formulation juste** — « ClickHouse est meilleur *pour ce workload* », et savoir dire ça est exactement ce qui distingue un ingénieur data d'un suiveur de mode.

---

## 2. Pourquoi ClickHouse est rapide (les 6 mécanismes)

- **Stockage colonne** — Les valeurs d'une même colonne sont contiguës sur disque, donc une requête qui lit 3 colonnes sur 50 ne lit que 6 % des données.
- **Compression forte** — Une colonne ne contient qu'un seul type de valeurs très similaires entre elles, ce qui permet des ratios de compression de 10× à 100× (LZ4 par défaut, ZSTD si on privilégie la taille).
- **Codecs spécialisés** — `Delta`, `DoubleDelta`, `Gorilla` et `T64` encodent l'écart entre valeurs successives, ce qui écrase les colonnes de dates, compteurs et métriques.
- **Exécution vectorisée** — Le moteur traite les données par blocs de milliers de valeurs avec des instructions SIMD du CPU, au lieu de traiter ligne par ligne.
- **Index primaire épars** — ClickHouse n'indexe pas chaque ligne mais une ligne sur 8192 (un « granule »), ce qui rend l'index minuscule et permet de sauter des blocs entiers au lieu de les lire.
- **Parallélisme natif** — Une seule requête utilise tous les cœurs de la machine, et se répartit sur tous les shards en cluster.

---

## 3. ClickHouse — les POUR

- **Débit d'agrégation** — Des milliards de lignes par seconde scannées sur une seule machine, ce qui rend interactives des requêtes qui prendraient des minutes ailleurs.
- **Coût de stockage** — La compression divise la facture disque par 10 ou plus, ce qui compte quand on garde 3 ans d'historique publicitaire.
- **Ingestion massive** — Conçu pour avaler des millions de lignes par seconde en insertions par lots, sans WAL par ligne ni verrous.
- **Lecture directe de S3** — La fonction table `s3()` lit du Parquet/CSV/JSON directement sur l'object store, ce qui supprime une étape d'ETL entre le lac et la base.
- **Vues matérialisées incrémentales** — Une MV se déclenche à chaque insertion et pré-agrège la donnée, donc la couche Gold est calculée à l'écriture et non à la lecture.
- **Moteurs de table spécialisés** — `MergeTree`, `ReplacingMergeTree`, `AggregatingMergeTree`, `SummingMergeTree` et `CollapsingMergeTree` encodent la sémantique métier directement dans le stockage.
- **Manipulation de partitions** — `REPLACE PARTITION`, `DROP PARTITION` et `MOVE PARTITION` permettent des backfills atomiques et rejouables, ce qui est la clé de l'idempotence d'un pipeline.
- **SQL riche** — Des centaines de fonctions analytiques (fonctions de fenêtre, `argMax`, `uniqExact`, `windowFunnel`, `sequenceMatch`) évitent d'exporter les données ailleurs pour les analyser.
- **Simplicité opérationnelle relative** — Un seul binaire et un seul type de nœud, là où Druid ou Pinot demandent 5 à 6 types de composants plus ZooKeeper.
- **Écosystème mûr** — Connecteurs Kafka, S3, Postgres/MySQL (y compris CDC), support dbt, drivers Python/Go/Java officiels.

---

## 4. ClickHouse — les CONTRE

- **Pas de transactions multi-tables** — Il n'y a pas de `BEGIN … COMMIT` couvrant plusieurs tables, donc toute logique métier transactionnelle est à exclure.
- **Contraintes non garanties** — Pas de clé étrangère, pas de contrainte d'unicité réellement appliquée, et la « clé primaire » sert au tri et au saut de blocs, pas à l'unicité.
- **Déduplication différée** — `ReplacingMergeTree` ne déduplique qu'au moment des fusions en arrière-plan, à un instant non déterministe, donc il faut lire avec `FINAL` ou avec un `argMax(...) GROUP BY` pour un résultat correct.
- **Coût du `FINAL`** — Forcer la déduplication à la lecture annule une partie du gain de performance, ce qui pousse à concevoir des tables où la dédup est rarement nécessaire.
- **UPDATE/DELETE coûteux** — Historiquement des mutations qui réécrivent des parts entières ; les `DELETE` légers (2022) puis les `UPDATE` légers via *patch parts* (2025) ont beaucoup amélioré la situation, mais le modèle reste append-first.
- **JOINs délicats** — La table de droite est chargée en mémoire pour la plupart des algorithmes de jointure, donc l'ordre des tables compte et les gros joins peuvent saturer la RAM.
- **Dénormalisation attendue** — Le modèle idiomatique est la grande table plate plutôt que le schéma normalisé, ce qui va à l'encontre des réflexes appris sur Postgres.
- **Piège des petites insertions** — Chaque `INSERT` crée une *part* sur disque, donc insérer ligne par ligne provoque l'erreur `Too many parts` (remède : lots de dizaines de milliers de lignes ou `async_insert`).
- **Choix de l'`ORDER BY` irréversible en pratique** — La clé de tri détermine toute la performance de la table et la changer implique de reconstruire les données.
- **Faible concurrence transactionnelle** — Optimisé pour peu de grosses requêtes, pas pour des dizaines de milliers de petites requêtes concurrentes par seconde.
- **Courbe d'apprentissage** — Le SQL est familier mais les moteurs, les parts, les merges et les MV imposent un modèle mental spécifique qu'il faut acquérir.
- **Sécurité fine plus pauvre** — Le contrôle d'accès par ligne et les outils de gouvernance sont moins mûrs que dans l'écosystème Postgres.

---

## 5. PostgreSQL — les POUR

- **ACID complet** — Transactions, isolation MVCC, rollback fiable, ce qui est indispensable dès qu'une écriture engage plusieurs tables.
- **Intégrité garantie par la base** — Clés étrangères, contraintes `UNIQUE`, `CHECK` et `NOT NULL` empêchent les données incohérentes d'exister.
- **UPDATE/DELETE naturels** — Modifier une ligne est une opération de premier ordre, rapide et sans effet de bord sur le reste de la table.
- **Forte concurrence de petites requêtes** — Des milliers de connexions applicatives lisant et écrivant quelques lignes chacune, c'est le cas d'usage nominal.
- **Jointures excellentes** — Le planificateur gère les schémas normalisés complexes avec plusieurs algorithmes de jointure et des statistiques fines.
- **Écosystème d'extensions** — PostGIS, `pgvector`, TimescaleDB, Citus, `pg_duckdb` étendent la base sans changer de technologie.
- **Ubiquité** — Tout le monde le connaît, tout outil s'y connecte, et le recrutement comme l'exploitation en sont simplifiés.
- **Suffisant très longtemps** — Jusqu'à quelques dizaines de millions de lignes avec de bons index, l'analytique sur Postgres reste parfaitement acceptable.

---

## 6. PostgreSQL — les CONTRE (en contexte analytique)

- **Stockage ligne** — Lire une seule colonne oblige à traverser toutes les autres colonnes de chaque ligne, donc à lire beaucoup de données inutiles.
- **Compression faible** — Une ligne mélange des types hétérogènes qui compressent mal, et TOAST ne compresse que les grandes valeurs individuelles.
- **Exécution ligne à ligne** — Pas d'exécution vectorisée SIMD, donc un coût CPU par ligne bien supérieur sur les scans massifs.
- **Parallélisme limité** — Le parallélisme de requête existe mais reste modeste comparé au modèle « tous les cœurs par défaut » de ClickHouse.
- **VACUUM et bloat** — Le MVCC laisse des versions mortes qu'il faut nettoyer, ce qui devient une charge d'exploitation sur les tables à fort taux de modification.
- **Index coûteux en écriture** — Les index B-tree qui accélèrent l'analytique ralentissent l'ingestion et occupent beaucoup de disque.
- **Scaling horizontal non natif** — Répartir la donnée sur plusieurs nœuds demande Citus ou un sharding applicatif, alors que c'est intégré dans ClickHouse.
- **Mur des gros volumes** — Au-delà de ~100 millions de lignes, les agrégations sur larges plages de dates passent typiquement de secondes à minutes.

---

## 7. Le non-relationnel — est-ce pertinent ici ?

- **Document (MongoDB, DocumentDB)** — Utile pour absorber des payloads d'API hétérogènes sans schéma fixe, mais faible et coûteux sur les agrégations analytiques massives.
- **Clé-valeur (DynamoDB, Redis)** — Excellent pour servir un objet connu par sa clé en quelques millisecondes, inutilisable pour de l'analytique ad hoc.
- **Colonne large (Cassandra, ScyllaDB)** — Débit d'écriture énorme et haute disponibilité, mais on ne peut interroger que selon les clés prévues à la conception.
- **Recherche (Elasticsearch, OpenSearch)** — Imbattable sur la recherche plein texte et les logs, mais les agrégations sur gros volumes y sont plus lentes et bien plus chères en RAM que sur ClickHouse.
- **OLAP temps réel (Druid, Pinot)** — Conçus pour des latences p99 de quelques millisecondes sur des dashboards exposés aux utilisateurs finaux, au prix d'une complexité opérationnelle très supérieure.
- **OLAP embarqué (DuckDB)** — Parfait pour l'analyse locale, les tests et le prototypage sur des fichiers Parquet, mais mono-processus et non conçu comme base de service.
- **Lac de données (S3 + Parquet + Iceberg/Delta)** — Stockage très bon marché et découplé du calcul, utilisé *en amont* de ClickHouse plutôt qu'à sa place.
- **Conclusion pour un cas e-commerce/publicité** — Le besoin est de l'agrégation SQL sur des événements append-only massifs, donc aucun modèle non relationnel n'apporte d'avantage décisif face à ClickHouse.
- **La nuance qui compte** — Un document store peut malgré tout servir de couche Bronze si les payloads d'API sont très instables, mais ClickHouse gère aussi le JSON brut avec son type `JSON`.

---

## 8. L'architecture qui gagne en 2026

- **Deux moteurs, pas un** — Postgres (ou MySQL) sert les écritures applicatives, ClickHouse sert les lectures analytiques, chacun sur son terrain.
- **Reliés par CDC ou par le lac** — La donnée circule de l'OLTP vers l'OLAP via change data capture ou via des fichiers déposés sur S3.
- **Le prix à payer** — La cohérence devient éventuelle, donc une ligne validée dans Postgres peut n'apparaître dans ClickHouse que quelques secondes plus tard.
- **Architecture médaillon** — Bronze (brut immuable), Silver (typé, dédupliqué, conforme), Gold (agrégats métier), chaque couche étant reconstructible depuis la précédente.
- **Règle d'or du médaillon** — Si Bronze est intact et le code versionné, tout le reste doit pouvoir être détruit et régénéré à l'identique.

---

## 9. Ce que je dois vérifier moi-même (à tester dans le projet)

- **Le ratio de compression réel** — Comparer la taille sur disque avec et sans `LowCardinality` + `CODEC(Delta, ZSTD)` sur les mêmes données.
- **L'impact de l'`ORDER BY`** — Mesurer la même requête sur deux tables identiques dont seule la clé de tri diffère.
- **Le gain des vues matérialisées** — Comparer l'agrégation à la volée sur Bronze et la lecture de la table Gold pré-agrégée.
- **Le coût du `FINAL`** — Mesurer la même requête sur `ReplacingMergeTree` avec et sans `FINAL`.
- **L'idempotence** — Rejouer trois fois le même jour via `REPLACE PARTITION` et vérifier que le nombre de lignes ne bouge pas.
- **Le piège des parts** — Insérer volontairement en petits lots pour observer l'accumulation de parts et le comportement des merges.

---

## 10. Ce que je retiens en une phrase

- **Ce qu'il faut retenir** — ClickHouse et Postgres ne sont pas concurrents mais complémentaires, et le choix se déduit de la forme de la charge de travail : append-only et agrégations lourdes pour ClickHouse, transactions et intégrité pour Postgres.

---

## Sources

- https://www.tinybird.co/blog/clickhouse-vs-postgresql-with-extensions
- https://clickhouse.com/docs/concepts/features/operations/update/replacing-merge-tree
- https://clickhouse.com/blog/handling-updates-and-deletes-in-clickhouse
- https://clickhouse.com/blog/updates-in-clickhouse-1-purpose-built-engines
- https://www.glassflow.dev/blog/replacingmergetree
- https://github.com/nielsreijers/clickhouse-gotchas
- https://startree.ai/resources/a-tale-of-three-real-time-olap-databases/
- https://clickhouse.com/resources/engineering/how-to-choose-a-database-for-real-time-analytics-in-2026
- https://bigdataboutique.com/blog/oltp-vs-olap-2026
