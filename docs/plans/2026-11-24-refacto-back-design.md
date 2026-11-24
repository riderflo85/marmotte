# Refonte du back : réglages découpés, fichier `.env`, modules en dossiers — design

> **Statut** : validé par l'auteur le 2026-11-24. Plan d'exécution : `docs/plans/2026-11-24-refacto-back.md`.

## Intention

Le squelette du back (lot 1, tâche 2) tient ses réglages dans un seul fichier et ne propose aucun fichier pour les variables d'environnement. L'auteur veut une organisation qu'il connaît et qui grandira bien avec les lots suivants :

- des **réglages découpés par thème**, rassemblés par un `base`, avec un `dev` et un `prod` par-dessus ;
- une **fonction de lecture des variables** qui échoue clairement quand une variable obligatoire manque ;
- un **fichier `.env`** local (ignoré par Git) et un **`.env.example`** versionné ;
- des **modules Django découpés en dossiers** (un fichier par objet), **avec leurs tests à l'intérieur**.

## Objectifs, non-objectifs, anti-objectifs

- **Objectifs** : la structure ci-dessous ; même comportement visible qu'avant (`GET /api/health`, `/api/docs`) ; démarrage refusé sans clé secrète ; CI et `just` inchangés pour l'utilisateur ; docs à jour ; un README pour le back et un pour le front.
- **Non-objectifs** : base de données, authentification, nouveaux points d'API (lots 4 et 8).
- **Anti-objectifs** : un secret dans le dépôt ; des tests qui dépendent du `.env` du développeur ; le mode debug activable par erreur sur le Pi.

## Contraintes

- Python 3.14, uv, Django 6, django-ninja, pytest, ruff, pyright `standard` (inchangés).
- Sur le Pi, les secrets viennent d'un fichier de la partie données lu par systemd (`EnvironmentFile=`, specs techniques § 12.3), pas d'un `.env` dans le code.
- Code typé en syntaxe moderne (`X | None`, `list[str]`).

## Approches pour charger le `.env`

| | Principe | Pour | Contre |
|---|---|---|---|
| **A. python-dotenv** (retenue) | Le `.env` est chargé au démarrage de `manage.py`, de `asgi.py` et des réglages | Marche partout (uv, pytest, Uvicorn, VS Code) sans rien taper ; ne remplace jamais une variable déjà définie (systemd, CI, pytest gardent la main) ; déjà installé avec pytest-env | Une dépendance de plus (BSD) |
| B. `uv run --env-file .env` | uv charge le fichier à chaque commande | Rien dans le code | À taper à chaque fois ; pytest ou VS Code lancés autrement ne voient rien |
| C. django-environ | Lecture et conversion des types | Conversions toutes faites | Remplace la fonction de lecture voulue par l'auteur |

**Choix de l'auteur : A.**

## Structure

Plus de dossier `src/` : uv ne l'exige pas (`uv init` crée un projet à plat, seul `uv init --package` crée `src/`). Cette disposition protège surtout les bibliothèques publiées ; Marmotte est une application installée par `uv sync`, et Django range d'habitude son paquet à côté de `manage.py`.

```
backend/
  .env.example          versionné : toutes les variables, valeurs d'exemple
  .env                  local, ignoré par Git
  manage.py, pyproject.toml, uv.lock, .python-version, README.md
  marmotte/
    __init__.py         vide
    __version__.py      __version__ = "0.1.0" : source unique, lue par hatchling
    asgi.py             point d'entrée d'Uvicorn
    urls.py             path("api/", api.urls)
    api.py              NinjaAPI du projet, monte le routeur de chaque module
    settings/
      __init__.py       get_config_value, to_bool, to_list, load_env
      base.py           rassemble django/* et project/*
      dev.py            base + DEBUG = True
      prod.py           base + DEBUG = False + options de sécurité
      django/           apps, core, internationalization, middlewares, paths, templates
      project/          data.py (DATA_DIR)
    base/               premier module (application Django)
      apps.py
      api_urls.py       routeur ninja du module, assemble ceux de views/
      schemas/          un fichier par objet (health.py : HealthOut)
      views/            un fichier par objet (health.py : son routeur et GET /health)
      tests/            tests_views/, test_<sujet>.py (dont test_settings.py)
```

### Réglages

- `settings/__init__.py` fournit `get_config_value(name, default=…, cast=…)` : lit la variable, renvoie la valeur par défaut, ou lève `ImproperlyConfigured` si la variable est obligatoire et absente ; `to_bool`, `to_list` pour les conversions ; `load_env()` charge `backend/.env` avec python-dotenv **sans remplacer** les variables déjà définies.
- `base.py` assemble les fichiers thématiques par `from … import *` ; ruff accepte ces imports **seulement dans `settings/`** (exception `F403`, `F405` limitée à ce dossier).
- **Pas de variable `DJANGO_DEBUG`** : `dev.py` et `prod.py` fixent `DEBUG`. Un seul réglage choisit le mode (`DJANGO_SETTINGS_MODULE`) ; le mode debug ne peut pas s'allumer par erreur sur le Pi.
- Les fichiers sans contenu aujourd'hui (`databases.py`, `third_party/`…) arrivent avec les lots qui en ont besoin (lot 4 pour la base).

### Variables

| Variable | Rôle | Sur le PC (`.env`) | Sur le Pi |
|---|---|---|---|
| `DJANGO_SETTINGS_MODULE` | Mode : développement ou production | `marmotte.settings.dev` | `marmotte.settings.prod` (aussi la valeur par défaut de `manage.py` et `asgi.py`) |
| `DJANGO_SECRET_KEY` | Clé secrète de Django | Obligatoire, générée localement | Obligatoire, générée sur le Pi (lot 11) |
| `DJANGO_ALLOWED_HOSTS` | Noms acceptés, séparés par des virgules | `127.0.0.1,localhost` | Nom du babyphone (lot 7) |
| `MARMOTTE_DATA_DIR` | Données du babyphone | Facultative (`backend/.data/`) | Partie données |

`manage.py` et `asgi.py` chargent le `.env` **avant** de lire `DJANGO_SETTINGS_MODULE`. Sans aucune variable, le mode par défaut est `prod`, qui refuse de démarrer sans clé secrète.

### Modules et django-ninja

django-ninja n'a ni serializers ni routeurs à la DRF. Équivalences retenues : **`schemas/`** (schémas ninja) à la place de `serializers/` ; chaque fichier de **`views/`** déclare un `Router` ninja et ses routes ; **`api_urls.py`** du module assemble ces routeurs ; **`marmotte/api.py`** monte le routeur de chaque module. Les autres noms restent ceux de l'organisation voulue : `models/`, `admin.py`, `utils/`, `management/commands/`, `tests/tests_models/`, `tests/tests_schemas/`, `tests/tests_views/`.

### Tests

- Rangés dans chaque module (`marmotte/<module>/tests/`) ; `testpaths = ["marmotte"]`.
- **Indépendants du `.env`** : pytest-env fournit `DJANGO_SECRET_KEY` et `DJANGO_ALLOWED_HOSTS` de test, et `DJANGO_SETTINGS_MODULE = marmotte.settings.dev` dans la configuration de pytest. Comme python-dotenv ne remplace jamais une variable déjà définie, les valeurs de test l'emportent. La CI n'a besoin ni de `.env` ni de secrets GitHub.
- *Précisé après la relecture du 2026-11-24* : pytest-env vide aussi `MARMOTTE_ENV_FILE`, ce qui coupe la lecture du `.env` pendant les tests (sinon ses autres variables, comme `MARMOTTE_DATA_DIR`, s'appliquaient), et fixe `DJANGO_SETTINGS_MODULE`. `load_env` lit le fichier nommé par `MARMOTTE_ENV_FILE`, ou `backend/.env` si elle n'est pas définie.

## Docs à mettre à jour

- `CLAUDE.md` : organisation, commandes (copie du `.env`), variables.
- `docs/plans/2026-11-19-lot-2-detection.md` : chemins (`backend/marmotte/…`, tests dans les modules).
- `docs/plans/2026-11-19-lot-1-fondations.md` : une note datée en tête, sans réécrire le plan exécuté.
- `justfile` (`deploy`) : lecture de la version dans `marmotte.__version__`.
- Nouveaux `backend/README.md` et `frontend/README.md` : présentation, installation, lancement en développement.

## Laissé au constructeur

Le texte des messages d'erreur, les options de sécurité exactes de `prod.py`, le découpage des tests de réglages, le contenu des README.
