---
paths:
  - "backend/marmotte/*/migrations/**"
  - "backend/marmotte/**/models/**"
---

# Migrations (à partir du lot 4)

- Une migration se génère (`cd backend && uv run python manage.py makemigrations <module>`), jamais à la main ; la relire avant de la garder.
- Ne jamais modifier ni supprimer une migration déjà présente sur `main` : elle tourne peut-être déjà sur un babyphone. En cas de doute, demander à l'auteur.
- La migration fait partie du même commit que le changement de modèle. Avant de pousser : `uv run python manage.py makemigrations --check --dry-run`.
- Plusieurs migrations créées dans un même module sur une branche : les fusionner en une seule avant de pousser, **uniquement celles de la branche**, avec l'accord de l'auteur.
- La base est un fichier SQLite en mode WAL dans `DATA_DIR`, partagé par les trois services (D82) : une migration doit rester compatible avec un service qui tourne encore sur l'ancien schéma pendant une mise à jour (ajouter avant de retirer).
- Sur le Pi, le moment où les migrations s'appliquent se décide au lot 11 (mises à jour) ; dans tous les cas, une migration qui échoue doit laisser la base intacte pour le retour arrière.
- Les tests construisent leur base à partir des migrations : une migration cassée fait échouer toute la suite.
