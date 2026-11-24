# Lot 1 : fondations du dépôt — plan détaillé

> **Amendé le 2026-11-24** : l'organisation du back décrite ici (disposition `src/`, réglages `marmotte.config.settings`, tests dans `backend/tests/`, variables `MARMOTTE_SECRET_KEY` et `MARMOTTE_DEBUG`) a été remplacée par celle de `docs/plans/2026-11-24-refacto-back-design.md` : paquet à plat `backend/marmotte/`, réglages `marmotte.settings.dev` / `prod`, fichier `.env`, tests dans chaque module. La suite du lot (tâches 4 et 5) suit la nouvelle organisation.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** un dépôt public propre, avec le squelette du back et du front, les outils de qualité et une intégration continue verte sur x86 et ARM.

**Architecture:** un seul dépôt (P69) : `backend/` (paquet Python `marmotte`, projet Django), `frontend/` (Vite, React, TypeScript), `system/`, `hardware/`, `docs/`. Le back expose un premier point d'API, `GET /api/health`, pour prouver toute la chaîne.

**Tech Stack:** Git, GitHub (`gh`), uv, Python 3.14, Django 6, django-ninja, Uvicorn, pytest, pytest-django, ruff, pyright ; Node.js 24, npm, Vite, React 19, TypeScript, Vitest, Testing Library, ESLint, Prettier ; pre-commit ; just ; GitHub Actions.

**Spec:** `docs/technique/choix-techniques-et-architecture.md` § 18 (process de développement), § 12.3 (secrets) ; `docs/brainstorming/notes-brainstorming.md` § 10.13 (P63 à P72), § 6.12 (licences).

## Global Constraints

- Voir `docs/plans/2026-11-19-plan-directeur-v1.md`, « Global Constraints ».
- Paquet Python : **`marmotte`**, en disposition `backend/src/marmotte/` ; module de réglages Django : **`marmotte.config.settings`**.
- Version initiale : **`0.1.0`** (SemVer, P71), définie une seule fois dans `marmotte/__init__.py` (`__version__`).
- Python **`>=3.14,<3.15`** (D94), version figée dans `backend/.python-version` (`3.14`) pour uv, en local, sur le Pi et dans la CI ; Node.js **24** (`frontend/.nvmrc`).
- Marqueurs pytest : **`hardware`** (vrai matériel, Pi seulement), **`model`** (fichier YAMNet requis), **`bench`** (banc d'essai complet). La CI de base les exclut.
- Licences : **PolyForm Noncommercial 1.0.0** pour le code (fichier `LICENSE` à la racine) ; **CC BY-NC-SA 4.0** pour `hardware/` et `docs/` (D55, D56).
- Réglages sensibles lus dans l'environnement : `MARMOTTE_SECRET_KEY`, `MARMOTTE_DATA_DIR`, `MARMOTTE_DEBUG`. Aucun secret dans le dépôt.

## Review Focus

1. **Fichiers hérités d'un autre projet** (`CLAUDE.md`, `.claude/`) publiés par erreur dans le dépôt public : le premier commit ne doit pas les contenir (tâche 1).
2. **Réglages Django sans `MARMOTTE_SECRET_KEY`** hors mode développement : le démarrage doit échouer clairement, pas tourner avec une clé connue (tâche 2).
3. **Différence x86 / ARM** : les tests passent sur les deux architectures (matrice de la CI, tâche 5).
4. **Fichier de verrouillage désynchronisé** (`uv.lock`, `package-lock.json`) : la CI échoue au lieu d'installer d'autres versions (`uv sync --locked`, `npm ci`, tâche 5).
5. **Dossiers locaux de données** (`.data/`, bancs locaux) committés par erreur : ignorés par Git (tâche 1).

---

### Task 1: Initialiser le dépôt, les licences et le `CLAUDE.md`

**Files:**
- Create: `.gitignore`, `LICENSE`, `hardware/LICENSE`, `docs/LICENSE`, `CLAUDE.md` (remplace la copie héritée)
- Move (avec l'accord de l'auteur) : `CLAUDE.md` et `.claude/` hérités d'un autre projet → un sous-dossier de `fichiers de travail/`

- [ ] **Step 1: Demander à l'auteur**, en une fois : (a) son accord pour déplacer `CLAUDE.md` et `.claude/` (hérités d'un autre projet) dans un sous-dossier de `fichiers de travail/` ; (b) le **nom du titulaire des droits** pour la licence ; (c) s'il veut garder la règle « confirmation avant chaque commit et avant toute fusion de PR » de l'autre projet dans le `CLAUDE.md` de Marmotte.
- [ ] **Step 2: Déplacer les fichiers hérités** selon la réponse, puis vérifier

Run: `ls -a . .claude 2>/dev/null; ls "fichiers de travail/<sous-dossier>"`
Expected: plus de `.claude/` hérité ni d'ancien `CLAUDE.md` à la racine ; ils sont dans le sous-dossier de `fichiers de travail/`.

- [ ] **Step 3: Écrire `.gitignore`** : `fichiers de travail/`, `.data/`, `.env`, `.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.ruff_cache/`, `node_modules/`, `frontend/dist/`, `backend/models/*.tflite`, `backend/bench/local/`, `.claude/settings.local.json`.
- [ ] **Step 4: Ajouter les licences** : `LICENSE` = texte officiel de PolyForm Noncommercial 1.0.0 (<https://polyformproject.org/licenses/noncommercial/1.0.0/>), suivi de la ligne `Required Notice: Copyright <année> <titulaire>` ; `hardware/LICENSE` et `docs/LICENSE` = texte officiel CC BY-NC-SA 4.0 (`legalcode.txt` de <https://creativecommons.org/licenses/by-nc-sa/4.0/>).
- [ ] **Step 5: Écrire le `CLAUDE.md` de Marmotte** (P72), en français, court : présentation en trois lignes ; tableau des commandes (celles des tâches 2 à 4) ; règles d'architecture (services séparés D82, matériel derrière une interface réelle/simulée P63, file d'envoi et filet P73, aucun secret dans le dépôt, aucune dépendance non commerciale, GPL seulement en programme séparé) ; conventions (code et commits en anglais, Conventional Commits `type(module): description`, branches `type/<issue>-<slug>`, squash) ; garde-fous (réponse de l'étape 1 c) ; renvoi vers `docs/` et vers les notes de brainstorming pour les décisions D/P.
- [ ] **Step 6: Initialiser Git et vérifier le contenu**

Run: `git init -b main && git add -A && git status --short`
Expected: `README.md`, `CLAUDE.md`, `LICENSE`, `.gitignore`, `docs/…`, `hardware/LICENSE` ; **aucun** fichier de `fichiers de travail/` ni de `.claude/`.

- [ ] **Step 7: Commit**

```bash
git commit -m "chore: initialize repository with docs, licenses and CLAUDE.md"
```

---

### Task 2: Projet back et point d'API `/api/health`

**Files:**
- Create: `backend/pyproject.toml`, `backend/manage.py`, `backend/src/marmotte/__init__.py`, `backend/src/marmotte/config/__init__.py`, `backend/src/marmotte/config/settings.py`, `backend/src/marmotte/config/urls.py`, `backend/src/marmotte/config/asgi.py`, `backend/src/marmotte/web/__init__.py`, `backend/src/marmotte/web/api.py`
- Test: `backend/tests/conftest.py`, `backend/tests/web/test_health.py`, `backend/tests/config/test_settings.py`

**Interfaces:**
- Produces: `marmotte.__version__: str = "0.1.0"` ; `marmotte.web.api.api: NinjaAPI` (titre `"Marmotte"`, version `__version__`), monté sous `/api/` ; `marmotte.config.asgi.application` (point d'entrée Uvicorn) ; `marmotte.config.settings.DATA_DIR: Path`.

- [ ] **Step 1: Créer le projet uv** : `pyproject.toml` avec `name = "marmotte"`, `version = "0.1.0"`, `requires-python = ">=3.14,<3.15"` (et un fichier `backend/.python-version` contenant `3.14`), dépendances `django>=6.0,<7`, `django-ninja>=1.8`, `uvicorn>=0.30` ; groupe `dev` : `pytest`, `pytest-django`, `ruff`, `pyright` ; construction `hatchling` sur `src/marmotte` ; `[tool.pytest.ini_options]` : `DJANGO_SETTINGS_MODULE = "marmotte.config.settings"`, `testpaths = ["tests"]`, marqueurs `hardware`, `model`, `bench` ; `[tool.ruff]` : `target-version = "py314"`, `line-length = 100`, règles `E`, `F`, `I`, `UP`, `B`, `SIM` ; `[tool.pyright]` : `pythonVersion = "3.14"`, `typeCheckingMode = "standard"`.

Run: `cd backend && uv sync`
Expected: environnement créé, `uv.lock` écrit.

- [ ] **Step 2: Écrire les tests qui échouent**

```python
# backend/tests/web/test_health.py
def test_health_returns_ok_and_version(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}
```

```python
# backend/tests/config/test_settings.py
def test_settings_refuse_missing_secret_key_outside_debug(monkeypatch):
    monkeypatch.delenv("MARMOTTE_SECRET_KEY", raising=False)
    monkeypatch.setenv("MARMOTTE_DEBUG", "0")
    with pytest.raises(ImproperlyConfigured):
        load_secret_key()
```

- [ ] **Step 3: Vérifier qu'ils échouent**

Run: `cd backend && uv run pytest -v`
Expected: FAIL (module ou URL introuvable).

- [ ] **Step 4: Implémenter**
  - `marmotte/config/settings.py` : `load_secret_key() -> str` lit `MARMOTTE_SECRET_KEY` ; si absente et `MARMOTTE_DEBUG` ne vaut pas `"1"`, lève `ImproperlyConfigured` ; en mode développement, renvoie une clé fixe marquée « dev only ». `DEBUG` vient de `MARMOTTE_DEBUG`. `DATA_DIR = Path(os.environ.get("MARMOTTE_DATA_DIR", "<racine du back>/.data"))`. `INSTALLED_APPS = []` pour l'instant (les modèles arrivent au lot 4). `ROOT_URLCONF = "marmotte.config.urls"`. `LANGUAGE_CODE = "fr-fr"`, `TIME_ZONE = "Europe/Paris"`, `USE_TZ = True`.
  - `marmotte/web/api.py` : `api = NinjaAPI(title="Marmotte", version=__version__)` ; `@api.get("/health")` renvoie `{"status": "ok", "version": __version__}` avec un schéma `HealthOut`.
  - `marmotte/config/urls.py` : `path("api/", api.urls)`.
  - `tests/conftest.py` : force `MARMOTTE_DEBUG=1` pour la session de tests.
- [ ] **Step 5: Vérifier que tout passe**

Run: `cd backend && uv run pytest -v && uv run ruff check && uv run ruff format --check && uv run pyright`
Expected: 2 tests PASS ; ruff et pyright sans erreur.

- [ ] **Step 6: Vérifier le service réel**

Run: `cd backend && MARMOTTE_DEBUG=1 uv run uvicorn marmotte.config.asgi:application --port 8000 & sleep 2; curl -s localhost:8000/api/health; kill %1`
Expected: `{"status": "ok", "version": "0.1.0"}`.

- [ ] **Step 7: Commit**

```bash
git add backend
git commit -m "feat(backend): add Django project with health endpoint"
```

---

### Task 3: Projet front

**Files:**
- Create: `frontend/` (gabarit Vite `react-ts`), `frontend/.nvmrc` (`24`), `frontend/.prettierrc`, `frontend/src/App.tsx`, `frontend/src/App.test.tsx`, `frontend/vitest.setup.ts`
- Modify: `frontend/package.json` (scripts), `frontend/vite.config.ts` (configuration Vitest)

**Interfaces:**
- Produces: scripts npm `dev`, `build`, `lint`, `typecheck` (`tsc -b`), `format:check` (`prettier --check .`), `test` (`vitest`).

- [ ] **Step 1: Créer le projet** : `npm create vite@latest frontend -- --template react-ts`, puis `npm i -D vitest @testing-library/react @testing-library/jest-dom jsdom prettier`.
- [ ] **Step 2: Écrire le test qui échoue**

```tsx
// frontend/src/App.test.tsx
it("affiche le nom de l'app", () => {
  render(<App />);
  expect(screen.getByRole("heading", { name: "Marmotte" })).toBeInTheDocument();
});
```

- [ ] **Step 3: Vérifier qu'il échoue**

Run: `cd frontend && npx vitest --run`
Expected: FAIL (le gabarit n'affiche pas « Marmotte »).

- [ ] **Step 4: Implémenter** : `App.tsx` réduit à un titre `<h1>Marmotte</h1>` ; Vitest en environnement `jsdom` avec `vitest.setup.ts` qui importe `@testing-library/jest-dom/vitest` ; scripts npm de l'interface ci-dessus ; `<html lang="fr">` dans `index.html`.
- [ ] **Step 5: Vérifier**

Run: `cd frontend && npm run lint && npm run typecheck && npm run format:check && npx vitest --run && npm run build`
Expected: tout passe ; `dist/` produit.

- [ ] **Step 6: Commit**

```bash
git add frontend
git commit -m "feat(frontend): add React TypeScript app skeleton"
```

---

### Task 4: pre-commit, commandes `just` et déploiement sur le Pi de dev

**Files:**
- Create: `.pre-commit-config.yaml`, `justfile`

**Interfaces:**
- Produces: recettes `just lint`, `just test`, `just deploy host="marmotte-dev.local"` (utilisées par les lots suivants ; le lot 5 y ajoutera le redémarrage des services).

- [ ] **Step 1: Écrire `.pre-commit-config.yaml`** : `pre-commit-hooks` (`end-of-file-fixer`, `trailing-whitespace`, `check-yaml`, `check-toml`, `check-json`) ; `ruff-pre-commit` (`ruff` avec `--fix`, `ruff-format`) sur `backend/` ; hooks locaux : `uv run --directory backend pyright`, `npm --prefix frontend run lint`, `npm --prefix frontend run format:check` (limités à leurs dossiers par `files:`).
- [ ] **Step 2: Installer et vérifier**

Run: `uvx pre-commit install && uvx pre-commit run --all-files`
Expected: tous les hooks passent.

- [ ] **Step 3: Écrire le `justfile`** : `lint` (ruff, pyright, ESLint, Prettier) ; `test` (`pytest -m "not hardware and not model and not bench"` puis `vitest --run`) ; `deploy host` : `rsync -a --delete --exclude .venv --exclude .data --exclude .env backend/ {{host}}:~/marmotte/backend/` (le `.env` du PC ne part jamais sur le Pi), puis `ssh {{host}} 'cd ~/marmotte/backend && uv sync --locked && uv run python -c "import marmotte; print(marmotte.__version__)"'`.
- [ ] **Step 4: Vérifier le déploiement** (Pi de dev du lot 0 allumé, uv installé dessus)

Run: `just deploy`
Expected: la dernière ligne affiche `0.1.0`.

- [ ] **Step 5: Commit**

```bash
git add .pre-commit-config.yaml justfile
git commit -m "chore: add pre-commit hooks and just recipes"
```

---

### Task 5: Intégration continue et dépôt GitHub

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Écrire `ci.yml`** : déclenché sur `pull_request` et `push` vers `main`.
  - Job `backend`, matrice `runs-on: [ubuntu-24.04, ubuntu-24.04-arm]` : `actions/checkout`, `astral-sh/setup-uv`, `uv sync --locked`, `uv run ruff check`, `uv run ruff format --check`, `uv run pyright`, `uv run pytest -m "not hardware and not model and not bench"` (dans `backend/`).
  - Job `frontend`, `ubuntu-24.04` : `actions/setup-node` avec `node-version-file: frontend/.nvmrc` et le cache npm, `npm ci`, `npm run lint`, `npm run typecheck`, `npm run format:check`, `npx vitest --run`, `npm run build` (dans `frontend/`).
  - Versions des actions **figées** sur une version majeure.
- [ ] **Step 2: Vérifier la syntaxe en local**

Run: `uvx pre-commit run check-yaml --files .github/workflows/ci.yml`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add backend and frontend checks on x86 and arm64"
```

- [ ] **Step 4: Créer le dépôt GitHub public — avec l'accord explicite de l'auteur** (action publique). Vérifier d'abord que le nom `marmotte` est libre sur son compte, puis :

Run: `gh repo create marmotte --public --source . --description "Babyphone vidéo fait maison, qui garde tout à la maison" --push`
Expected: dépôt créé, branche `main` poussée.

- [ ] **Step 5: Vérifier la CI**

Run: `gh run watch --exit-status`
Expected: les jobs `backend` (x86 et ARM) et `frontend` sont verts.

- [ ] **Step 6: Créer les issues des lots** dans GitHub Issues (D83) : une issue par lot du plan directeur, titre « Lot N : … », corps = lien vers le plan du lot. Avec l'accord de l'auteur (action publique).
