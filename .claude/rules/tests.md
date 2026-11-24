---
paths:
  - "backend/marmotte/**/tests/**"
  - "backend/pyproject.toml"
---

# Tests du back

- pytest, pytest-django, pytest-env. Les tests ne lisent jamais le `.env` du développeur : pytest-env (`[tool.pytest.ini_options]` de `backend/pyproject.toml`) vide `MARMOTTE_ENV_FILE` et fixe `DJANGO_SETTINGS_MODULE`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`. Une variable lue par les réglages pendant les tests s'ajoute à cette liste `env`, jamais dans un `conftest.py` (trop tard : pytest-django charge les réglages avant).
- Emplacement : dans le module testé, `backend/marmotte/<module>/tests/` : `tests_models/`, `tests_schemas/`, `tests_views/`, ou `test_<sujet>.py` à la racine de `tests/`. Chaque dossier a son `__init__.py`. Un fichier porte le nom de l'objet testé (`test_health.py`).
- Format : une classe par objet testé (`TestHealthView`, `TestGetConfigValue`) ; chaque test a une docstring d'une ligne (en anglais), puis les commentaires `# GIVEN`, `# WHEN`, `# THEN` (`# WHEN / THEN` autour d'un `pytest.raises`). Modèle : `backend/marmotte/base/tests/test_settings.py`.
- Vues : la fixture `client` de pytest-django (`client.get("/api/…")`), en vérifiant le code HTTP et le JSON. Base de données (à partir du lot 4) : `@pytest.mark.django_db` sur la classe.
- Environnement : `monkeypatch` (`setenv`, `delenv`, `setattr`). Une variable posée par le code testé (pas par `monkeypatch`) se nettoie en la posant puis la retirant avec `monkeypatch` avant l'appel. Pas de `unittest.mock` sans raison.
- Points d'entrée (`manage.py`, `asgi.py`, services) : un sous-processus `subprocess.run([sys.executable, …])` avec un environnement explicite et `MARMOTTE_ENV_FILE=""`.
- Marqueurs : `hardware` (vrai matériel, sur le Pi seulement), `model` (fichier YAMNet requis), `bench` (banc d'essai complet). La CI lance `-m "not hardware and not model and not bench"`. Jamais de réseau ni de matériel réel hors de ces marqueurs : le matériel passe par sa version simulée (P63).
- Lancer : `cd backend && uv run pytest <chemin>::<Classe>::<test>`, la suite avec `uv run pytest`, tout le dépôt avec `just test`.
