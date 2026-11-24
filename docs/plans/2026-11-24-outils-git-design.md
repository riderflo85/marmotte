# Messages de commit, hooks dans la CI et Dependabot — design et plan

> **Statut** : validé par l'auteur le 2026-11-24.

## Intention

Ne plus pouvoir commiter un message hors convention, n'avoir à écrire que la description, rejouer les contrôles légers dans la CI, et tenir les dépendances à jour sans y penser.

## Décisions

- **Script versionné** `scripts/git_hooks/commit_message.py` (bibliothèque standard, Python 3.12 ou plus), branché sur pre-commit pour deux étapes de Git ; `default_install_hook_types` fait installer les trois crochets par `uvx pre-commit install` ; `default_stages: [pre-commit]` garde les autres hooks à leur étape.
- **Pré-remplissage** (`prepare-commit-msg`) : branche `type/<n>-<slug>` ou `type/<slug>` → en-tête `type(module): ` ; module deviné d'après les fichiers indexés (`backend/marmotte/<paquet>/…` → `<paquet>` ; `backend/`, `frontend/`, `system/`, `hardware/`, `docs/` → ce dossier ; `.claude/`, `CLAUDE.md` → `claude` ; `.github/` → `ci` ; `README.md` → `docs` ; fichiers mélangés → pas de module ; module égal au type → pas de module). Un message déjà au format, une fusion, un squash, un amend ou un revert ne sont jamais modifiés ; rien sur `main`.
- **Contrôle** (`commit-msg`, et dans la CI pour le titre des PR) : refus si le titre n'est pas `type(module): description` ; type hors de `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci` ; description vide, commençant par une majuscule suivie d'une minuscule (`Add`), ou finissant par un point ; titre de plus de 72 caractères ; pas de ligne vide entre titre et corps ; mention de Claude (`Co-Authored-By: Claude`, « Generated with Claude Code »). Messages produits par Git (`Merge …`, `Revert "…"`, `fixup! …`, `squash! …`, `amend! …`) acceptés. Messages d'erreur en français.
- **CI** : job `hooks` obligatoire : contrôles légers de pre-commit (ruff, pyright, ESLint et Prettier tournent déjà ailleurs), tests du script, titre de la PR (sauf PR de Dependabot, au format garanti) ; le job `backend` vérifie aussi `scripts/` avec ruff et pyright.
- **Dependabot** : actions GitHub, npm (`frontend/`), uv (`backend/`), chaque lundi ; mises à jour mineures regroupées par écosystème ; messages `chore(deps): …` ; module `deps` ajouté au `CLAUDE.md`. Alertes et correctifs de sécurité automatiques activés dans les réglages du dépôt.

## Plan

1. Tests du script (rouges), puis le script (verts) ; ruff et pyright sur `scripts/`.
2. `.pre-commit-config.yaml` (étapes, deux crochets locaux) ; réinstallation ; essai réel d'un commit refusé et d'un commit pré-rempli.
3. Job `hooks` et contrôles de `scripts/` dans la CI ; `justfile` (`lint`, `test`).
4. `.github/dependabot.yml`.
5. `CLAUDE.md`, skill `commit`, README (crochets).
6. PR ; après fusion : alertes de sécurité, job `hooks` ajouté aux contrôles obligatoires.
