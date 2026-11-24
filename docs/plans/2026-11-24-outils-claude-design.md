# Outils de Claude Code pour Marmotte (skills, règles, permissions) — design

> **Statut** : validé par l'auteur le 2026-11-24. Plan d'exécution : `docs/plans/2026-11-24-outils-claude.md`.

## Intention

L'auteur travaille avec Claude Code au moyen de **skills** (procédures que Claude suit à la demande : commit, PR, relecture, tests, doc, tickets) et de **règles** chargées selon les fichiers touchés. Il en a déjà une série, écrite pour un autre projet. Il veut la même aide pour Marmotte, **adaptée à ses choix** : Conventional Commits, GitHub Flow et issues GitHub, uv, ruff, pyright, django-ninja, tests dans les modules.

## Objectifs, non-objectifs, anti-objectifs

- **Objectifs** : 8 skills et 3 règles dans `.claude/`, plus `.claude/settings.json` ; un `docs/backlog.md` local ; `CLAUDE.md` à jour (skills, backlog).
- **Non-objectifs** : nouveaux skills ; migration de la doc existante ; création du dépôt GitHub, des labels ou des issues (lot 1, tâche 5, avec l'accord de l'auteur).
- **Anti-objectifs** : une trace de l'autre projet (nom, chemins, kanban, personnes) dans le dépôt public ; une action publique (push, PR, issue, label, fusion) sans confirmation ; un skill qui renvoie à un fichier ou une commande qui n'existe pas dans Marmotte.

## Contraintes

- `.claude/` est **commité** : dépôt public, donc rien de personnel (`CLAUDE.md`, garde-fous).
- Conventions de `CLAUDE.md` : commits `type(module): description` en anglais ; branches `type/<numéro d'issue>-<slug>` ; squash ; **confirmation avant chaque commit et chaque fusion**.
- **L'auteur est le seul relecteur des PR** : aucune demande de relecture, PR assignée à l'auteur, relue par lui (avec `review-diff` s'il le souhaite), fusionnée après sa confirmation.
- Les issues GitHub sont publiques : leur texte suit la règle « rien de personnel ».

## Approches retenues par l'auteur

- **Transposer les 8 skills et les 3 règles en les adaptant** (plutôt que repartir de zéro ou les copier tels quels).
- **Tickets : tout adapter aux issues GitHub** (option A), plutôt que garder seulement la lecture d'issues (B) ou rien (C) :
  - `ticket` lit une issue par `gh`, la résume, propose la branche `type/<n>-<slug>`, renvoie au plan du lot s'il existe ; le suivi se fait par issue ouverte ou fermée et `Closes #<n>` dans la PR ;
  - `ticket-create` crée des issues à partir de `docs/backlog.md` (local, ignoré par Git), après recherche de doublons et une confirmation par issue, puis inscrit `#<n>` dans le backlog ; `ticket-create sync` passe en « Traité » les entrées dont l'issue est fermée **et** dont le correctif est vérifié dans le code.

## Ce que devient chaque élément

| Élément | Adaptation |
|---|---|
| `commit` | Format déjà utilisé par les commits du dépôt, `type(module): description` (précision de l'auteur : aucune autre convention), écrit en entier (pas de hook qui ajoute un préfixe) ; module d'après le chemin (`backend`, `frontend`, `system`, `hardware`, `docs`, `ci` ou un sous-module) ; hooks par `uvx pre-commit run` ; contrôle des fichiers sensibles (`.env`, `fichiers de travail/`, `docs/brainstorming/`) et de la règle « rien de personnel ». Sur `main` : refusé une fois le dépôt GitHub créé (avant, le plan du lot 1 commite sur `main`). |
| `pre-push` | Rebase, migrations, documentation, logs, lint, **typage vérifié par pyright**, tests (`just test`), hygiène des commits, **vie privée et secrets** (nouveau point). Pas de point « traductions » : l'interface est seulement en français (D51), sans fichiers de traduction. |
| `pr-create` | Synthèse en français regroupée par module, titre au format des commits (devient le commit de `main`), `Closes #<n>` d'après la branche, label de type, assignée à l'auteur, **aucun relecteur demandé** ; fusion par squash avec suppression de la branche, après confirmation. |
| `review-diff` | Règles de Marmotte (services séparés, matériel derrière une interface, file d'envoi, aucun secret, licences, typage, rien de personnel). |
| `write-test` | Conventions de Marmotte (ci-dessous), django-ninja, pytest-env, `monkeypatch`, sous-processus pour les points d'entrée. |
| `write-doc` | Inchangé sur le fond (gabarits feature et runbook, Mermaid, `docs/features/`, `docs/runbooks/`) ; chemins et exemples de Marmotte. |
| `ticket`, `ticket-create` | Issues GitHub (`gh issue …`), voir ci-dessus. Format d'une issue : user story, critères d'acceptation en cases à cocher, contraintes techniques, dépendances. |
| Règle `tests` | Chemins `backend/marmotte/**/tests/**`. |
| Règle `api` | `schemas/`, `views/` (un `Router` par fichier), `api_urls.py`, `marmotte/api.py`, erreurs explicites, documentation `/api/docs`. |
| Règle `migrations` | Migrations générées et relues, jamais modifiées une fois sur `main`, base SQLite dans `DATA_DIR`, même commit que le modèle. Peu utile avant le lot 4, mais prête. |
| `settings.json` | Autorise les lectures (`git status`, `git diff`, `git log`, `gh … view/list`) et les contrôles (`uv run pytest`, `uv run ruff check`, `uv run pyright`, `just lint`, `just test`) ; demande pour `git commit`, `git push`, `gh pr create/merge/edit`, `gh issue create/edit/close`, `gh label create`, `gh repo create` ; refuse `--force`, `--no-verify` et la lecture de `backend/.env`. |

## Décisions de Claude (à vérifier par l'auteur)

- **Conventions de test** : une docstring d'une ligne et les commentaires `# GIVEN`, `# WHEN`, `# THEN` ; tests groupés en classes par objet testé (`TestHealthView`, `TestGetConfigValue`). Les deux fichiers de tests existants sont convertis à ce format dans le même travail, pour que `write-test` ait un modèle dans le dépôt.
- **Labels GitHub de type** : `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci` (les types de commit), créés à la première PR avec l'accord de l'auteur.
- **Backlog** : `docs/backlog.md` local, une entrée par sujet (titre, type `bug` / `architecture` / `remarque`, user story, description, critères d'acceptation, fichiers, statut `À créer` → `Issue créée (#<n>)` → `Traité`). `CLAUDE.md` gagne une section « Backlog » : tout problème repéré hors du périmètre demandé y est noté au lieu d'être corrigé.
- Les skills renvoient aux conventions de `CLAUDE.md` (pas de document Git séparé).

## Laissé au constructeur

La formulation des skills, l'ordre de leurs étapes, les exemples, la liste exacte des permissions tant qu'elle respecte le tableau.
