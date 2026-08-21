# Pourquoi Bronze se recharge par reconstruction de partition

## La décision

Bronze est partitionné par `(_source, _extracted_at)`. Recharger une extraction ne
touche jamais un objet isolé : la procédure relit **tous** les objets présents sous le
préfixe de l'extraction (`extracted_at=<jour>/*.parquet`) vers une table de staging, puis
échange la partition d'un bloc (`ALTER TABLE … REPLACE PARTITION … FROM …`).

L'échange n'a lieu qu'après une reconstruction complète et réussie : si la lecture S3
échoue, `scripts/ingest-extraction.sh` s'arrête avant le swap et Bronze garde l'état
précédent. C'est ce qui interdit qu'un rechargement de `part-0001` fasse disparaître
`part-0002`.

## Pourquoi pas `insert_deduplication_token`

C'est le mécanisme natif de ClickHouse pour l'idempotence d'ingestion, et il est écarté
en connaissance de cause : il garantit qu'un **même** lot inséré deux fois ne compte
qu'une fois. Or un objet corrigé porte un contenu différent — soit il change de jeton et
s'ajoute en doublon, soit il garde le même jeton et sa correction est rejetée. Le jeton
répond au rejeu, pas à la révision. Ce projet existe précisément pour absorber des
chiffres révisés par les régies : la rechargeabilité n'est pas négociable.

## Pourquoi pas un journal d'ingestion

Une table `bronze.ingestion_log` qui note les objets déjà vus est plus simple, mais elle
rend un objet **corrigé** définitivement non rechargeable — même impasse, pour la même
raison.

## Limite connue

Une partition par source et par jour d'extraction : deux régies sur un an font environ
730 partitions. C'est tenable à cette échelle, et c'est le prix de la rechargeabilité.
Une volumétrie plus large demanderait de regrouper les jours d'extraction (au mois, par
exemple), au prix d'une reconstruction plus lourde à chaque rechargement.
