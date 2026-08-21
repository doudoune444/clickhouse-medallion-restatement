# Pipeline médaillon ClickHouse — absorber la révision tardive des chiffres publicitaires

Une régie publicitaire publie le rapport du 3 juin, puis le corrige. Une conversion
attribuée trois semaines plus tard change le chiffre d'une journée déjà ingérée. Il faut
donc recharger le 3 juin. Un pipeline qui se contente d'insérer les lignes du nouveau
fichier se retrouve avec les deux versions de la journée empilées, et une dépense comptée
deux fois.

Ce projet construit le pipeline qui encaisse ces corrections. Recharger une extraction,
une fois ou dix fois, laisse la donnée exactement dans l'état que décrit le dernier fichier
reçu.

Les données sont synthétiques, le jeu se base sur deux régies aux conventions volontairement divergentes,
publiant du Parquet sur S3.

## Pourquoi ce Repo existe

C'est un projet d'apprentissage. Le but est de maîtriser les deux éléments ci-dessous. Le reste n'est qu'un prétexte
crédible pour les exercer :

- **L'architecture médaillon** — comprendre le but et l'utilisation des couches bronze, silver et gold pour un projet de données analytiques
- **ClickHouse** — comprendre ce système de gestion de base de données, et dans quel cas il surpasse un moteur transactionnel comme PostgreSQL sur le traitement analytique.

## Méthode de travail

Le backlog est découpé en issues GitHub, chaque issue est suivie d'une branche, puis d'une PR.
