# Marmotte

Babyphone vidéo fait maison sur Raspberry Pi 4 : live image et son sur le réseau local, détection des pleurs par IA (YAMNet), notifications Web Push vers une app PWA.
L'image et le son du bébé ne quittent jamais le réseau local ; aucun enregistrement, aucun cloud, aucun compte.
Back : Python 3.14, Django 6 + django-ninja, Uvicorn, SQLite. Front : React 19, TypeScript, Vite. Dépôt public sur GitHub.

## Commandes

Python est installé et géré par **uv** (version figée dans `backend/.python-version`) ; Node.js 24 par **nvm** (`nvm use` dans `frontend/`, qui lit `.nvmrc`).

| Besoin | Commande |
|---|---|
| Installer le back | `cd backend && uv sync` |
| Configurer le back | `cd backend && cp .env.example .env`, puis y mettre une clé générée (commande dans le fichier) |
| Tests back (comme la CI) | `cd backend && uv run pytest -m "not hardware and not model and not bench"` |
| Style et types du back | `uv run ruff check`, `uv run ruff format`, `uv run pyright` (dans `backend/`) |
| Serveur de dev | `cd backend && uv run uvicorn marmotte.asgi:application --reload` (`/api/health`, `/api/docs`) |
| Installer le front | `cd frontend && npm ci` |
| Front | `npm run dev`, `npm run lint`, `npm run typecheck`, `npm run format:check`, `npx vitest --run`, `npm run build` (dans `frontend/`) |
| Tout le lint, tous les tests | `just lint`, `just test` |
| Hooks pre-commit | `uvx pre-commit install` (une fois : contrôles avant le commit, pré-remplissage et contrôle du message), `uvx pre-commit run --all-files` |
| Déployer sur le Pi de dev | `just deploy` (par défaut `marmotte-dev.local`, clé `~/.ssh/id_ed25519_raspi`), `just deploy <hôte>`, `just deploy <hôte> <clé ssh>` : arguments dans l'ordre, sans `nom=` (`host=x` serait pris comme nom d'hôte) |

Marqueurs pytest : `hardware` (vrai matériel, sur le Pi seulement), `model` (fichier YAMNet requis), `bench` (banc d'essai complet). La CI de base les exclut.

Réglages lus dans l'environnement, ou dans `backend/.env` (chargé par python-dotenv, qui ne remplace jamais une variable déjà définie) : `DJANGO_SETTINGS_MODULE` (`marmotte.settings.dev` sur le PC, `marmotte.settings.prod` sur le Pi et par défaut), `DJANGO_SECRET_KEY` (obligatoire), `DJANGO_ALLOWED_HOSTS` (obligatoire, séparés par des virgules), `MARMOTTE_DATA_DIR` (par défaut `backend/.data/`). `MARMOTTE_ENV_FILE` désigne un autre fichier que `backend/.env` ; vide, aucun fichier n'est lu. Les tests ne lisent jamais le `.env` du développeur : pytest-env vide `MARMOTTE_ENV_FILE` et fixe leurs valeurs, `DJANGO_SETTINGS_MODULE` compris (`backend/pyproject.toml`).

## Organisation

- `backend/` : paquet Python `marmotte` à plat (`backend/marmotte/`, à côté de `manage.py`). Détail et commandes : `backend/README.md`.
  - `marmotte/settings/` : `base.py` assemble les thèmes `django/` (un fichier par sujet) et `project/` (réglages propres à Marmotte) ; `dev.py` et `prod.py` par-dessus (`DEBUG` fixé là, pas de variable). Chaque valeur se lit avec `get_config_value` (`marmotte/settings/__init__.py`), qui arrête le démarrage si une variable obligatoire manque. `import *` seulement dans ce dossier.
  - Un module par domaine (`marmotte/base/`, puis `detection`, `notifications`…) : `apps.py`, `models/`, `schemas/` (schémas django-ninja, l'équivalent des serializers), `views/` (un fichier par objet, chacun avec son `Router` ninja), `api_urls.py` (assemble les routeurs du module), `admin.py`, `utils/`, `management/commands/`, `tests/` (`tests_models/`, `tests_schemas/`, `tests_views/`, `test_<sujet>.py`). Un fichier par objet dans chaque dossier.
  - `marmotte/api.py` monte le routeur de chaque module ; `marmotte/urls.py` le sert sous `/api/` ; `marmotte/asgi.py` est le point d'entrée d'Uvicorn.
- `frontend/` : l'app PWA. `system/` : préparation du Pi, services, go2rtc, image A/B. `hardware/` : modèles 3D en code, câblage. `docs/` : documentation.
- Version SemVer définie une seule fois dans `backend/marmotte/__version__.py` (`__version__`) ; la version de l'image est celle de l'app.

## Règles d'architecture

- **Services séparés** (D82) : `marmotte-web` (app, API, SSE), `marmotte-detection`, `marmotte-notifications`, plus go2rtc pour le live. Ils partagent la base SQLite (mode WAL).
- **Matériel derrière une interface Python** avec une version réelle et une version simulée (P63) : tout se développe et se teste sur PC ; les tests du vrai matériel sont marqués `hardware`.
- **File d'envoi et filet des notifications** (P73) : chaque notification est écrite en base avec un identifiant unique avant l'envoi ; si une alerte de pleur n'est pas envoyée en ~2 s, la détection l'envoie elle-même.
- **Aucun secret dans le dépôt** (clés VAPID, jeton Infomaniak, mots de passe, clés d'appareil, clé de signature) : ils sont générés ou stockés sur le Pi, ou dans les secrets de GitHub Actions.
- **Aucune dépendance sous licence non commerciale** ; du code **GPL** seulement comme programme séparé, jamais importé ni intégré.
- **Typage** : toute fonction écrite ou modifiée a ses paramètres et son retour typés (`-> None` compris), en syntaxe moderne (`list[str]`, `X | None`). pyright (mode `standard`) tourne dans la CI ; la règle `ANN` de ruff refuse une fonction non annotée.
- **Style** : ruff pour le back (`backend/pyproject.toml` : 120 colonnes, un import par ligne, règles `E`, `W`, `F`, `I`, `UP`, `B`, `SIM`, `C4`, `PTH`, `RUF`, `N`, `PT`, `DJ`, `LOG`, `ANN`, `TID`, `ERA`), Prettier pour le front (120 colonnes). Pas de black, isort ni flake8 : ruff les remplace. Exception ponctuelle : `# pyright: ignore[<règle>]`, jamais un `ignore` nu.
- **Commentaires** : une constante de module ou un champ de dataclass se décrit par une docstring placée juste en dessous (`"""…"""`), que l'éditeur affiche au survol partout où il est utilisé ; `#` explique le code (le pourquoi d'une ligne ou d'un choix) et décrit ce qui ne peut pas porter de docstring (entrée de dictionnaire, ligne d'une liste).

## Conventions

- Code, identifiants et messages de commit **en anglais** ; interface et documentation **en français**.
- Commits au format Conventional Commits : `type(module): description`, types `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci` ; module = `backend`, `frontend`, `system`, `hardware`, `docs`, `claude` (`.claude/`, `CLAUDE.md`), `deps` (Dependabot) ou un sous-module (`detection`, `notifications`…) ; facultatif pour un changement de tout le dépôt.
- Les crochets Git (`scripts/git_hooks/commit_message.py`) **pré-remplissent** `type(module): ` d'après la branche et les fichiers indexés quand le message n'a pas d'en-tête, et **refusent** un message hors format (type inconnu, description en majuscule ou avec un point final, titre de plus de 72 caractères, mention de Claude). La CI applique le même contrôle au titre des PR. Exemple : `feat(backend): add Django project with health endpoint`.
- **Aucune mention de Claude** dans les commits et les pull requests : ni ligne `Co-Authored-By`, ni « Generated with Claude Code », ni signature (`attribution` vide dans `.claude/settings.json`).
- GitHub Flow : branches courtes `type/<numéro d'issue>-<slug>` (ex. `feat/3-cry-detection`) ; une petite tâche sans issue (doc, dépendance, réglage d'outil) se fait sur `type/<slug>` (ex. `docs/fix-readme-typo`) ; pull request, fusion par **squash** (le titre de la PR devient le commit sur `main` : il suit le même format).
- Suivi des tâches dans les **issues GitHub** (D83), une par lot du plan directeur.

## Skills et règles

Les skills (`.claude/skills/`) se lancent à la demande ; les règles (`.claude/rules/`) se chargent selon les fichiers touchés.

| Skill | Pour |
|---|---|
| `commit` | un commit par changement logique, au format `type(module): description`, après confirmation |
| `pre-push` | la checklist avant de pousser une branche, sans pousser |
| `pr-create` | créer la pull request (synthèse en français, `Closes #<n>`, assignée à l'auteur, seul relecteur) et la fusionner par squash |
| `review-diff` | relire une PR, une branche ou un diff, avec un verdict |
| `ticket` | lire une issue GitHub, créer sa branche, suivre son état |
| `ticket-create` | créer les issues à partir de `docs/backlog.md`, puis synchroniser |
| `write-test` | écrire des tests au format du dépôt et les lancer |
| `write-doc` | écrire une doc de fonction (`docs/features/`) ou une procédure (`docs/runbooks/`) |

Règles : `tests.md` (tests du back), `api.md` (django-ninja), `migrations.md`.

## Garde-fous

- **Confirmation de l'auteur avant chaque commit** (une approbation = un commit) et **avant toute fusion de PR**.
- **Rien de personnel dans le dépôt public** : ni prénom, ni famille, ni date liée à la vie privée, ni domaine réel, ni identifiant de compte ; le nom de l'auteur n'apparaît que dans les licences. Écrire « l'auteur ».
- Accord explicite avant toute action publique : push, création ou modification du dépôt GitHub, issues, publications.
- Ne jamais contourner les hooks (`--no-verify`).

## Backlog

Tout bug, problème d'architecture ou remarque repéré en passant et **hors du périmètre demandé** se note dans `docs/backlog.md` au lieu d'être corrigé. Ce fichier est **local** (ignoré par Git) ; il sert à créer les issues GitHub (skill `ticket-create`).

- Une entrée par sujet, au format décrit en tête du fichier : titre, type (`bug`, `architecture`, `remarque`), statut, user story, description, critères d'acceptation, fichiers.
- Vérifier le constat avant de l'écrire (lire le code, lancer un test) et dire ce qui n'a pas été reproduit. Chercher d'abord si le sujet existe déjà : pas de doublon.
- Ne pas corriger sans demande : l'ajout au backlog ne remplace pas la décision de l'auteur.
- Relire le backlog avant de créer une PR, au début d'un travail sur un sujet proche, et à la demande : une entrée réglée passe à « Traité » avec la date et la PR ou le commit, après vérification dans le code (une issue fermée ne suffit pas). Ne jamais supprimer une entrée ; ne jamais deviner un numéro d'issue.

## Documentation

- Specs : `docs/fonctionnel/specs-fonctionnelles.md` (exigences F-xx, NF-xx), `docs/technique/choix-techniques-et-architecture.md` (architecture, raison des choix), `docs/technique/modelisation-3d.md`.
- Décisions (D*) et propositions (P*) : `docs/brainstorming/notes-brainstorming.md`, journal des décisions, **privé** (ignoré par Git, jamais publié). Pour corriger une décision, demander d'abord à l'auteur, puis ajouter une mention datée « Amendé le … » plutôt que réécrire.
- Plans : `docs/plans/` (plan directeur en 15 lots, un plan détaillé par lot). Résultats des tests sur le vrai matériel et pièges connus (go2rtc, micro, filtre IR-Cut) : `docs/plans/resultats-tests-prealables.md`.

## Pièges connus

- Une variable lue par les réglages pendant les tests se fixe dans `env` de pytest-env (`backend/pyproject.toml`), pas dans un `conftest.py` : pytest-django charge les réglages avant les `conftest.py`.
- uv ne charge pas le `.env` tout seul : c'est `load_env()` (`marmotte/settings/__init__.py`) qui le fait, appelé par `settings/base.py` et par `prepare_environment()`. Tout programme Marmotte (`manage.py`, `asgi.py`, futurs services) appelle `prepare_environment()` avant Django : elle charge le `.env` puis choisit `marmotte.settings.prod` si aucun mode n'est donné.
- Un serveur lancé en arrière-plan pour un essai : `curl --max-time`, et un port libre (le 8000 peut être pris par un autre programme, `curl` attend alors sans fin).

## Faire évoluer ce fichier

Chaque piège rencontré devient une ligne ici, courte et précise.
