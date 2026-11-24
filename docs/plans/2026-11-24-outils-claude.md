# Outils de Claude Code pour Marmotte — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** doter Marmotte de 8 skills, 3 règles et de permissions Claude Code adaptés à ses conventions, avec un backlog local relié aux issues GitHub.

**Architecture:** `.claude/skills/<nom>/SKILL.md`, `.claude/rules/<sujet>.md` (chargées selon les chemins touchés), `.claude/settings.json` ; `docs/backlog.md` local (ignoré par Git) ; `CLAUDE.md` décrit skills et backlog. Les modèles de départ sont dans un dossier local de `fichiers de travail/` (jamais cité dans le dépôt).

**Tech Stack:** Claude Code (skills, règles, permissions), git, gh, uv, pre-commit, just, pytest.

**Spec:** `docs/plans/2026-11-24-outils-claude-design.md`

## Global Constraints

- Tout le contenu est en **français**, sauf messages de commit et code (anglais).
- **Aucune trace de l'autre projet** dans le dépôt : ni son nom, ni ses chemins, ni son kanban, ni ses personnes, ni son format de commit.
- Format des commits : **celui déjà utilisé dans le dépôt**, `type(module): description` (Conventional Commits).
- Branches `type/<numéro d'issue>-<slug>` ; squash ; **confirmation avant chaque commit et chaque fusion** ; accord explicite avant toute action publique (push, PR, issue, label, fusion, création de dépôt).
- L'auteur est **le seul relecteur** des PR : aucune demande de relecture.
- Description de chaque skill : commence par « Utiliser quand », donne les déclencheurs, **sans résumer la procédure** ; 1 024 caractères au plus.
- Chaque chemin, fichier ou commande cité par un skill ou une règle existe dans Marmotte (ou est explicitement marqué « à venir » avec son lot).

## Review Focus

1. **Un skill cite un chemin ou une commande absents de Marmotte** (héritage de l'autre projet) : contrôle de la tâche 5, étape 2.
2. **Une trace de l'autre projet** dans un fichier versionné : contrôle de la tâche 5, étape 3.
3. **Une action publique sans confirmation** (`gh issue create`, `gh pr create`, `git push`) : rangée en `ask` dans `settings.json` (tâche 5) et exigée par les skills.
4. **`docs/backlog.md` commité par erreur** (notes internes) : ignoré par Git (tâche 3, contrôle `git check-ignore`).
5. **Commit sur `main` une fois le dépôt GitHub créé** : refusé par `commit` (tâche 2) ; avant la création du dépôt, le plan du lot 1 commite sur `main`.

Vérification des skills (décision de Claude, voir la ligne « Ruling » du journal) : ce sont des adaptations de skills déjà éprouvés ; chacun est vérifié par la tâche 5 (chemins, commandes, descriptions), puis par son premier usage réel (`commit` dès ce plan, `write-test` à la tâche 1, `ticket`, `ticket-create` et `pr-create` à la tâche 5 du lot 1).

---

### Task 1: Conventions de test et règles

**Files:**
- Create: `.claude/rules/tests.md` (chemins `backend/marmotte/**/tests/**`), `.claude/rules/api.md` (`backend/marmotte/**/views/**`, `schemas/**`, `api_urls.py`, `backend/marmotte/api.py`), `.claude/rules/migrations.md` (`backend/marmotte/*/migrations/**`)
- Modify: `backend/marmotte/base/tests/test_settings.py`, `backend/marmotte/base/tests/tests_views/test_health.py`

- [ ] **Step 1: Convertir les tests existants** au format retenu : classes par objet testé (`TestGetConfigValue`, `TestToBool`, `TestToList`, `TestLoadEnv`, `TestSettingsModes`, `TestPrepareEnvironment`, `TestEntryPoints`, `TestHealthView`, `TestApiDocs`), une docstring d'une ligne par test, commentaires `# GIVEN`, `# WHEN`, `# THEN` ; mêmes assertions, aucun test retiré.

Run: `cd backend && uv run pytest -q`
Expected: `25 passed` (le même nombre qu'avant).

- [ ] **Step 2: Écrire les trois règles** à partir des modèles, adaptées : `tests.md` (pytest, pytest-django, pytest-env et `MARMOTTE_ENV_FILE` vide, marqueurs, format de la tâche 1, `monkeypatch`, sous-processus pour les points d'entrée, pas de réseau ni de matériel réel hors `hardware`) ; `api.md` (`schemas/`, un `Router` par fichier de `views/`, `api_urls.py`, `marmotte/api.py`, types de réponse déclarés, erreurs explicites, `/api/docs`, accès protégé à venir au lot 8) ; `migrations.md` (générées par `uv run python manage.py makemigrations`, relues, jamais modifiées une fois sur `main`, même commit que le modèle, `makemigrations --check --dry-run`, base SQLite dans `DATA_DIR`, à venir au lot 4).
- [ ] **Step 3: Commit** — `test(backend): group tests by object with given/when/then` puis `chore(claude): add rules for tests, api and migrations` (deux commits, deux confirmations).

### Task 2: Skills de travail Git et GitHub

**Files:**
- Create: `.claude/skills/commit/SKILL.md`, `.claude/skills/pre-push/SKILL.md`, `.claude/skills/pr-create/SKILL.md`, `.claude/skills/review-diff/SKILL.md`

- [ ] **Step 1: `commit`** : contexte (branche ; sur `main`, refus dès qu'un dépôt distant existe), lecture du diff, un commit par changement logique, indexation par nom de fichier, fichiers interdits (`.env`, `backend/.env`, `fichiers de travail/`, `docs/brainstorming/`, `docs/backlog.md`, `.claude/settings.local.json`), contrôle « rien de personnel », `uvx pre-commit run`, message `type(module): description` en anglais écrit en entier, confirmation par commit, jamais `--no-verify`, jamais de push.
- [ ] **Step 2: `pre-push`** : rebase sur la cible, migrations, documentation, logs, lint (`just lint`), **typage par pyright**, tests (`just test`), hygiène des commits, **vie privée et secrets** ; bilan en tableau ; ne pousse jamais.
- [ ] **Step 3: `pr-create`** : synthèse en français par module, titre au format des commits, `Closes #<n>` tiré de la branche, label de type (créé avec accord s'il manque), assignée à l'auteur (`--assignee @me`), aucun relecteur ; fusion `gh pr merge --squash --delete-branch` après confirmation.
- [ ] **Step 4: `review-diff`** : constats appuyés sur un scénario d'échec, réutilisation et simplification, règles de `CLAUDE.md` (services séparés, matériel derrière une interface, file d'envoi, aucun secret, licences, typage, rien de personnel), rapport en français, verdict ; ne corrige rien.
- [ ] **Step 5: Commit** — `chore(claude): add commit, pre-push, pr-create and review-diff skills`.

### Task 3: Tickets sur les issues GitHub et backlog

**Files:**
- Create: `.claude/skills/ticket/SKILL.md`, `.claude/skills/ticket-create/SKILL.md`, `docs/backlog.md` (local)
- Modify: `.gitignore` (`docs/backlog.md`), `CLAUDE.md` (sections « Skills » et « Backlog »)

- [ ] **Step 1: `ticket`** : `ticket list` (`gh issue list --state open`), `ticket <n>` (`gh issue view <n>`, résumé, plan du lot s'il existe, branche `type/<n>-<slug>` d'après les labels ou le titre, création de branche après confirmation), `ticket` seul sur une branche `type/<n>-…` ; le suivi passe par l'état de l'issue et `Closes #<n>`.
- [ ] **Step 2: `ticket-create`** : entrées « À créer » de `docs/backlog.md` → issues (`gh issue create`), format user story, critères d'acceptation en cases à cocher, contraintes techniques, dépendances ; recherche de doublons (`gh issue list --search`) ; confirmation par issue ; contrôle « rien de personnel » du texte ; `#<n>` et statut « Issue créée » écrits dans le backlog ; `ticket-create sync` (issue fermée **et** correctif vérifié dans le code → « Traité »).
- [ ] **Step 3: Créer `docs/backlog.md`** (format des entrées, aucune entrée) et l'ignorer.

Run: `git check-ignore -v docs/backlog.md`
Expected: la règle de `.gitignore` est affichée.

- [ ] **Step 4: Mettre à jour `CLAUDE.md`** : liste des skills (une ligne chacun) ; section « Backlog » (noter au lieu de corriger hors périmètre, vérifier avant d'écrire, pas de doublon, relire avant une PR, ne jamais supprimer une entrée).
- [ ] **Step 5: Commit** — `chore(claude): add ticket skills based on GitHub issues and a local backlog`.

### Task 4: Skills de tests et de documentation

**Files:**
- Create: `.claude/skills/write-test/SKILL.md`, `.claude/skills/write-doc/SKILL.md`

- [ ] **Step 1: `write-test`** : cibler, lire l'existant, choisir quoi couvrir, écrire au format de la tâche 1 (modèle : `backend/marmotte/base/tests/test_settings.py`), exécuter (`uv run pytest <fichier>` puis la suite), rendre compte de ce qui est couvert ou non.
- [ ] **Step 2: `write-doc`** : deux gabarits (feature dans `docs/features/`, runbook dans `docs/runbooks/`), Mermaid systématique, lecture du code avant d'écrire, français, « rien de personnel ».
- [ ] **Step 3: Commit** — `chore(claude): add write-test and write-doc skills`.

### Task 5: Permissions et contrôles d'ensemble

**Files:**
- Create: `.claude/settings.json`

- [ ] **Step 1: Écrire `settings.json`** selon le tableau du design (allow, ask, deny) ; `enabledPlugins` : `pyright-lsp@claude-plugins-official`.

Run: `python3 -c "import json; json.load(open('.claude/settings.json'))"`
Expected: aucune erreur.

- [ ] **Step 2: Contrôler les références** : chaque chemin entre accents graves des skills et règles qui ressemble à un fichier du dépôt existe, ou est marqué « à venir » ; chaque description commence par « Utiliser quand » et fait 1 024 caractères au plus.
- [ ] **Step 3: Contrôler les traces** : rechercher dans `.claude/`, `CLAUDE.md` et les deux documents de ce plan les noms, outils et termes propres à l'autre projet (liste tenue dans le journal d'exécution local, pas dans le dépôt).
Expected: aucune trace (faux positifs justifiés un par un).

- [ ] **Step 4: Commit** — `chore(claude): add Claude Code permissions`.
