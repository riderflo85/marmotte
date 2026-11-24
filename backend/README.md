# Marmotte : le back

Les services Python de Marmotte, qui tournent sur le Raspberry Pi. Aujourd'hui, le **service web** : Django et django-ninja, servis par Uvicorn, avec un premier point d'API, `GET /api/health`. La détection des pleurs, les notifications et le reste de l'API arrivent avec les lots suivants (`docs/plans/`).

## Prérequis

- [uv](https://docs.astral.sh/uv/getting-started/installation/). Il installe lui-même **Python 3.14** (version figée dans `.python-version`) : rien d'autre à installer.

## Installation

```bash
cd backend
uv sync
```

`uv sync` crée l'environnement `.venv/` et y installe les dépendances, outils de développement compris, aux versions exactes de `uv.lock`.

## Configuration

Les réglages viennent de variables d'environnement. Sur le PC, on les écrit dans un fichier `.env` (ignoré par Git), lu au démarrage :

```bash
cp .env.example .env
```

Puis remplacer `change-me` par une vraie clé, générée avec :

```bash
uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

| Variable | Rôle | Valeur sur le PC |
|---|---|---|
| `DJANGO_SETTINGS_MODULE` | Mode : développement ou production | `marmotte.settings.dev` |
| `DJANGO_SECRET_KEY` | Clé secrète de Django (obligatoire) | Une clé générée |
| `DJANGO_ALLOWED_HOSTS` | Noms acceptés par le serveur, séparés par des virgules | `127.0.0.1,localhost` |
| `MARMOTTE_DATA_DIR` | Dossier des données du babyphone (facultatif) | `backend/.data/` par défaut |

Une variable déjà définie dans le terminal l'emporte sur le `.env`. Sans `.env` ni variables, le back démarre en mode production et s'arrête aussitôt, faute de clé secrète. Sur le Pi, c'est systemd qui fournit les variables.

## Lancer en développement

```bash
uv run uvicorn marmotte.asgi:application --reload
```

- <http://127.0.0.1:8000/api/health> : répond `{"status": "ok", "version": "0.1.0"}` ;
- <http://127.0.0.1:8000/api/docs> : documentation interactive de l'API.

Si le port 8000 est déjà pris par un autre programme, ajouter `--port 8001` (et changer l'adresse en conséquence).

Les commandes de Django passent par `manage.py`, par exemple `uv run python manage.py check`.

## Tests et qualité

```bash
uv run pytest -m "not hardware and not model and not bench"   # comme la CI
uv run ruff check          # style
uv run ruff format         # mise en forme
uv run pyright             # types
```

Les tests ne lisent pas votre `.env` : pytest leur fournit leurs propres valeurs (`pyproject.toml`). Les marqueurs `hardware` (vrai matériel, sur le Pi), `model` (fichier YAMNet) et `bench` (banc d'essai complet) désignent les tests exclus de la CI de base. Depuis la racine du dépôt, `just lint` et `just test` lancent tout, back et front.

## Organisation

```
backend/
  .env.example        modèle du fichier .env
  manage.py
  pyproject.toml      dépendances et réglages des outils ; uv.lock fige les versions
  marmotte/
    __version__.py    version de Marmotte (SemVer)
    asgi.py           point d'entrée d'Uvicorn
    urls.py           sert l'API sous /api/
    api.py            l'API django-ninja, qui monte le routeur de chaque module
    settings/         réglages : base.py, dev.py, prod.py, thèmes django/ et project/
    base/             premier module
      schemas/        schémas des données de l'API (un fichier par objet)
      views/          points d'API (un fichier par objet, chacun avec son routeur)
      api_urls.py     assemble les routeurs du module
      tests/          tests du module (tests_views/, test_<sujet>.py…)
```

Pour ajouter un point d'API à un module : son schéma dans `schemas/<objet>.py`, ses routes dans `views/<objet>.py` (un `Router` django-ninja), puis le routeur ajouté dans `api_urls.py`, et les tests dans `tests/tests_views/`.
