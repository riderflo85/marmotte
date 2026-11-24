# Refonte du back — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** passer le back à une disposition à plat, des réglages découpés par thème chargés depuis un `.env`, et un premier module `base` organisé en dossiers ; puis documenter le back et le front.

**Architecture:** paquet `backend/marmotte/` (plus de `src/`), réglages `marmotte/settings/` (`base`, `dev`, `prod`, thèmes `django/` et `project/`), `.env` chargé par python-dotenv sans écraser l'environnement ; module `marmotte/base/` en `schemas/`, `views/`, `api_urls.py`, `tests/`, monté par `marmotte/api.py`.

**Tech Stack:** Python 3.14, uv, Django 6, django-ninja, python-dotenv, pytest, pytest-django, pytest-env, ruff, pyright.

**Spec:** `docs/plans/2026-11-24-refacto-back-design.md`

## Global Constraints

- Comportement visible inchangé : `GET /api/health` → `{"status": "ok", "version": "0.1.0"}` ; `/api/docs` → 200.
- Version définie une seule fois dans `marmotte/__version__.py` (`__version__ = "0.1.0"`), lue par hatchling.
- Variables : `DJANGO_SETTINGS_MODULE` (défaut `marmotte.settings.prod`), `DJANGO_SECRET_KEY` (obligatoire), `DJANGO_ALLOWED_HOSTS` (obligatoire, liste séparée par des virgules), `MARMOTTE_DATA_DIR` (facultative, défaut `backend/.data`). **Pas de `DJANGO_DEBUG`** : `dev.py` → `DEBUG = True`, `prod.py` → `DEBUG = False`.
- python-dotenv ne remplace **jamais** une variable déjà définie (`override=False`).
- `import *` permis seulement dans `marmotte/settings/` (ruff `F403`, `F405` ignorés pour ce dossier).
- Code typé, syntaxe moderne, `Any` évité ; aucun secret dans le dépôt ; rien de personnel dans le dépôt public.
- Commits : confirmation de l'auteur avant **chaque** commit.

## Review Focus

1. **Un `.env` du développeur avec d'autres valeurs** ne doit pas changer le résultat des tests : `test_load_env_keeps_existing_variables` (tâche 1).
2. **Variable vide** (`DJANGO_SECRET_KEY=` dans le `.env`) traitée comme absente : `test_empty_value_counts_as_missing` (tâche 1).
3. **Lancement sans aucune configuration** (ni `.env` ni variables) : mode `prod`, refus clair faute de clé : vérification manuelle à l'étape 6 de la tâche 1, **avant** de créer le `.env`.
4. **Liste avec espaces** (`127.0.0.1, localhost`) : `test_to_list_strips_spaces_and_empty_items` (tâche 1).
5. **Valeur impossible à convertir** : `ImproperlyConfigured` qui nomme la variable : `test_cast_error_names_the_variable` (tâche 1).

---

### Task 1: Back à plat, réglages découpés, `.env`, module `base`

**Files:**
- Move: `backend/src/marmotte/` → `backend/marmotte/` ; supprimer `backend/src/`, `backend/tests/`, `marmotte/config/`, `marmotte/web/`
- Create: `marmotte/__version__.py`, `marmotte/api.py`, `marmotte/urls.py`, `marmotte/asgi.py`, `marmotte/settings/{__init__,base,dev,prod}.py`, `marmotte/settings/django/{__init__,apps,core,internationalization,middlewares,paths,templates}.py`, `marmotte/settings/project/{__init__,data}.py`, `marmotte/base/{__init__,apps,api_urls}.py`, `marmotte/base/schemas/{__init__,health}.py`, `marmotte/base/views/{__init__,health}.py`, `backend/.env.example`
- Modify: `backend/manage.py`, `backend/pyproject.toml`, `backend/uv.lock`, `marmotte/__init__.py` (vide)
- Test: `marmotte/base/tests/__init__.py`, `marmotte/base/tests/test_settings.py`, `marmotte/base/tests/tests_views/__init__.py`, `marmotte/base/tests/tests_views/test_health.py`

(Chemins relatifs à `backend/` sauf mention.)

**Interfaces:**
- Produces, dans `marmotte/settings/__init__.py` :
  - `REQUIRED: Final` (sentinelle) ;
  - `get_config_value(name: str, default: str | _Required = REQUIRED) -> str` et, en surcharge, `get_config_value[T](name: str, default: str | _Required = REQUIRED, *, cast: Callable[[str], T]) -> T` : lit `os.environ[name]` ; valeur absente **ou vide** → `default` (converti lui aussi par `cast`) ; sans défaut → `ImproperlyConfigured` dont le message contient `name` ; erreur de `cast` → `ImproperlyConfigured` dont le message contient `name` ;
  - `to_bool(value: str) -> bool` (`"true"` / `"false"`, casse ignorée ; sinon `ValueError`) ;
  - `to_list(value: str, separator: str = ",") -> list[str]` (éléments débarrassés des espaces, éléments vides retirés) ;
  - `load_env(path: Path | None = None) -> None` : `load_dotenv(path or BACKEND_DIR / ".env", override=False)`.
- Produces : `marmotte.settings.django.paths.PACKAGE_DIR`, `BACKEND_DIR: Path` ; `marmotte.settings.project.data.DATA_DIR: Path` ; `marmotte.api.api: NinjaAPI` ; `marmotte.base.api_urls.router: Router` ; `marmotte.base.views.health.router: Router` ; `marmotte.base.schemas.health.HealthOut`.

- [ ] **Step 1: Déplacer le paquet** avec `git mv backend/src/marmotte backend/marmotte`, puis retirer `backend/src/` et l'ancien `backend/tests/` (chemins absolus). `marmotte/__init__.py` devient vide ; `__version__ = "0.1.0"` passe dans `marmotte/__version__.py`.
- [ ] **Step 2: Mettre à jour `pyproject.toml`** : dépendance `python-dotenv>=1.0` ; `[tool.hatch.version] path = "marmotte/__version__.py"` ; `packages = ["marmotte"]` ; pytest : `DJANGO_SETTINGS_MODULE = "marmotte.settings.dev"`, `testpaths = ["marmotte"]`, `env = ["DJANGO_SECRET_KEY=test-only-secret-key", "DJANGO_ALLOWED_HOSTS=testserver,localhost"]` (plus de `MARMOTTE_DEBUG`) ; `[tool.ruff.lint.per-file-ignores] "marmotte/settings/**" = ["F403", "F405"]`. Puis `uv sync`.
- [ ] **Step 3: Écrire les tests qui échouent** dans `marmotte/base/tests/test_settings.py` :
  - `test_missing_required_value_names_the_variable` : `delenv("MARMOTTE_TEST_VAR")` → `ImproperlyConfigured` avec `"MARMOTTE_TEST_VAR"` dans le message ;
  - `test_empty_value_counts_as_missing` : `setenv("MARMOTTE_TEST_VAR", "")` → même erreur ; avec `default="x"` → `"x"` ;
  - `test_default_is_cast_too` : `get_config_value("MARMOTTE_TEST_VAR", default="a, b", cast=to_list) == ["a", "b"]` ;
  - `test_cast_error_names_the_variable` : `setenv(…, "maybe")`, `cast=to_bool` → `ImproperlyConfigured` avec le nom ;
  - `test_to_bool_accepts_true_and_false_any_case` (`"TRUE"` → `True`, `"false"` → `False`) ;
  - `test_to_list_strips_spaces_and_empty_items` : `to_list("127.0.0.1, localhost,") == ["127.0.0.1", "localhost"]` ; `to_list("") == []` ;
  - `test_load_env_reads_file` et `test_load_env_keeps_existing_variables` (fichier `.env` écrit dans `tmp_path`, variable absente → lue ; variable déjà définie → inchangée) ;
  - `test_prod_settings_disable_debug` : `importlib.import_module("marmotte.settings.prod").DEBUG is False` ; `test_dev_settings_enable_debug` (même chose, `True`) ;
  - `test_prod_refuses_to_start_without_secret_key` : sous-processus `[sys.executable, "-c", "import django; django.setup()"]` avec `DJANGO_SETTINGS_MODULE=marmotte.settings.prod` et `DJANGO_SECRET_KEY=""` → code de retour non nul, `"DJANGO_SECRET_KEY"` dans `stderr`.

  Et `marmotte/base/tests/tests_views/test_health.py` : les deux tests actuels (`test_health_returns_ok_and_version`, `test_api_docs_page_renders`), inchangés.

Run: `cd backend && uv run pytest -v`
Expected: FAIL (réglages `marmotte.settings.dev` introuvables).

- [ ] **Step 4: Implémenter** les réglages et le module, selon les Interfaces :
  - `settings/django/` : `paths.py` (`PACKAGE_DIR`, `BACKEND_DIR`) ; `apps.py` (`DJANGO_APPS = []`, `THIRD_PARTY_APPS = []`, `LOCAL_APPS = ["marmotte.base"]`, `INSTALLED_APPS`) ; `core.py` (`SECRET_KEY`, `ALLOWED_HOSTS` par `get_config_value`, `ROOT_URLCONF = "marmotte.urls"`, `ASGI_APPLICATION = "marmotte.asgi.application"`) ; `internationalization.py` (`fr-fr`, `Europe/Paris`, `USE_I18N`, `USE_TZ`) ; `middlewares.py` (`SecurityMiddleware`, `CommonMiddleware`) ; `templates.py` (`DjangoTemplates`, pour `/api/docs`).
  - `settings/project/data.py` : `DATA_DIR = get_config_value("MARMOTTE_DATA_DIR", default=str(BACKEND_DIR / ".data"), cast=Path)`.
  - `base.py` appelle `load_env()` puis importe les thèmes ; `dev.py` : `from .base import *` + `DEBUG = True` ; `prod.py` : `from .base import *` + `DEBUG = False` + cookies sécurisés.
  - `manage.py` et `asgi.py` : `load_env()` **puis** `os.environ.setdefault("DJANGO_SETTINGS_MODULE", "marmotte.settings.prod")`.
  - Module `base` : `apps.py` (`BaseConfig`, `name = "marmotte.base"`), `schemas/health.py`, `views/health.py` (`router` et `GET /health`), `api_urls.py` (assemble les routeurs de `views/`), `marmotte/api.py` (`NinjaAPI(title="Marmotte", version=__version__)` + routeur de `base`), `marmotte/urls.py` (`path("api/", api.urls)`).
- [ ] **Step 5: Vérifier**

Run: `cd backend && uv run pytest -v && uv run ruff check && uv run ruff format --check && uv run pyright`
Expected: tous les tests passent ; ruff et pyright sans erreur.

- [ ] **Step 6: Vérifier le démarrage sans configuration** (Review Focus 3), **avant** de créer le `.env` :

Run: `cd backend && env -u DJANGO_SETTINGS_MODULE -u DJANGO_SECRET_KEY uv run python manage.py check`
Expected: échec, message qui nomme `DJANGO_SECRET_KEY`.

- [ ] **Step 7: Écrire `.env.example`** (les quatre variables, commentées en français, valeur d'exemple de la clé `change-me` et la commande qui en génère une vraie), créer le `.env` local avec une clé générée, puis vérifier le vrai service :

Run: `cd backend && (timeout 10 uv run uvicorn marmotte.asgi:application --port 8765 &) ; curl -s --retry 15 --retry-connrefused --retry-delay 1 localhost:8765/api/health`
Expected: `{"status": "ok", "version": "0.1.0"}`.

- [ ] **Step 8: Commit**

```bash
git add backend
git commit -m "refactor(backend): split settings, load .env and organize the base module"
```

---

### Task 2: Docs, plans et commandes à jour

**Files:**
- Modify: `CLAUDE.md` (organisation, commandes, variables), `docs/plans/2026-11-19-lot-2-detection.md` (chemins), `docs/plans/2026-11-19-lot-1-fondations.md` (note datée en tête), `justfile` (`deploy` : `from marmotte.__version__ import __version__`)
- Add: `docs/plans/2026-11-24-refacto-back-design.md`, `docs/plans/2026-11-24-refacto-back.md`

- [ ] **Step 1: Mettre à jour les chemins du lot 2** : `backend/src/marmotte/` → `backend/marmotte/` ; `backend/tests/detection/` → `backend/marmotte/detection/tests/`.
- [ ] **Step 2: Mettre à jour `CLAUDE.md`** : ligne « Configurer » (`cp .env.example .env`, générer la clé) ; serveur de dev `uv run uvicorn marmotte.asgi:application --reload` ; variables du design ; organisation (`backend/marmotte/`, réglages, modules en dossiers, `schemas/` pour ninja, tests dans les modules).
- [ ] **Step 3: Ajouter la note datée** en tête du plan du lot 1 (organisation remplacée le 2026-11-24, renvoi au design).
- [ ] **Step 4: Vérifier**

Run: `git grep -n -E "src/marmotte|backend/tests|marmotte\.config|MARMOTTE_DEBUG|MARMOTTE_SECRET_KEY" -- . ':!docs/plans/2026-11-19-lot-1-fondations.md' ':!docs/plans/2026-11-24-*'` puis `just test`
Expected: aucune ligne ; tests back et front verts.

- [ ] **Step 5: Commit** (le `justfile`, encore non suivi, part avec la tâche 4 du lot 1)

```bash
git add CLAUDE.md docs/plans
git commit -m "docs: document the new backend layout and settings"
```

---

### Task 3: README du back et du front

**Files:**
- Create: `backend/README.md`, `frontend/README.md`
- Modify: `README.md` (section « Développement » : renvoi vers les deux README)

- [ ] **Step 1: Écrire `backend/README.md`** (français) : rôle du back ; prérequis (uv, Python 3.14 installé par uv) ; installation (`uv sync`) ; configuration (`.env` et tableau des variables) ; lancement en dev (Uvicorn, `/api/health`, `/api/docs`) ; tests et qualité ; organisation des dossiers.
- [ ] **Step 2: Écrire `frontend/README.md`** : rôle ; prérequis (Node 24 par nvm, `nvm use`) ; installation (`npm ci`) ; lancement en dev (`npm run dev`, adresse de Vite) ; tests et qualité ; build ; état (l'app n'appelle pas encore le back).
- [ ] **Step 3: Vérifier** en suivant chaque README depuis un terminal neuf : installation, lancement, tests.

Run: `uvx pre-commit run --all-files`
Expected: tous les hooks passent.

- [ ] **Step 4: Commit**

```bash
git add backend/README.md frontend/README.md README.md
git commit -m "docs: add backend and frontend READMEs"
```
