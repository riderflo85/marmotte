# Marmotte

Babyphone vidéo fait maison sur Raspberry Pi 4 : live image et son sur le réseau local, détection des pleurs par IA (YAMNet), notifications Web Push vers une app PWA.
L'image et le son du bébé ne quittent jamais le réseau local ; aucun enregistrement, aucun cloud, aucun compte.
Back : Python 3.14, Django 6 + django-ninja, Uvicorn, SQLite. Front : React 19, TypeScript, Vite. Dépôt public sur GitHub.

## Commandes

Python est installé et géré par **uv** (version figée dans `backend/.python-version`) ; Node.js 24 par **nvm** (`nvm use` dans `frontend/`, qui lit `.nvmrc`).

| Besoin | Commande |
|---|---|
| Installer le back | `cd backend && uv sync` |
| Tests back (comme la CI) | `cd backend && uv run pytest -m "not hardware and not model and not bench"` |
| Style et types du back | `uv run ruff check`, `uv run ruff format`, `uv run pyright` (dans `backend/`) |
| Serveur de dev | `cd backend && MARMOTTE_DEBUG=1 uv run uvicorn marmotte.config.asgi:application --reload` |
| Installer le front | `cd frontend && npm ci` |
| Front | `npm run dev`, `npm run lint`, `npm run typecheck`, `npm run format:check`, `npx vitest --run`, `npm run build` (dans `frontend/`) |
| Tout le lint, tous les tests | `just lint`, `just test` |
| Hooks pre-commit | `uvx pre-commit install` (une fois), `uvx pre-commit run --all-files` |
| Déployer sur le Pi de dev | `just deploy` (par défaut `marmotte-dev.local`), `just deploy host=<nom>` |

Marqueurs pytest : `hardware` (vrai matériel, sur le Pi seulement), `model` (fichier YAMNet requis), `bench` (banc d'essai complet). La CI de base les exclut.

Réglages lus dans l'environnement : `MARMOTTE_SECRET_KEY` (obligatoire hors développement), `MARMOTTE_DEBUG` (`1` = développement), `MARMOTTE_DATA_DIR` (par défaut `backend/.data/`).

## Organisation

- `backend/` : paquet Python `marmotte` en disposition `src/` (`backend/src/marmotte/`), réglages Django `marmotte.config.settings`, tests dans `backend/tests/` (même arborescence que le paquet).
- `frontend/` : l'app PWA. `system/` : préparation du Pi, services, go2rtc, image A/B. `hardware/` : modèles 3D en code, câblage. `docs/` : documentation.
- Version SemVer définie une seule fois dans `backend/src/marmotte/__init__.py` (`__version__`) ; la version de l'image est celle de l'app.

## Règles d'architecture

- **Services séparés** (D82) : `marmotte-web` (app, API, SSE), `marmotte-detection`, `marmotte-notifications`, plus go2rtc pour le live. Ils partagent la base SQLite (mode WAL).
- **Matériel derrière une interface Python** avec une version réelle et une version simulée (P63) : tout se développe et se teste sur PC ; les tests du vrai matériel sont marqués `hardware`.
- **File d'envoi et filet des notifications** (P73) : chaque notification est écrite en base avec un identifiant unique avant l'envoi ; si une alerte de pleur n'est pas envoyée en ~2 s, la détection l'envoie elle-même.
- **Aucun secret dans le dépôt** (clés VAPID, jeton Infomaniak, mots de passe, clés d'appareil, clé de signature) : ils sont générés ou stockés sur le Pi, ou dans les secrets de GitHub Actions.
- **Aucune dépendance sous licence non commerciale** ; du code **GPL** seulement comme programme séparé, jamais importé ni intégré.
- **Typage** : toute fonction écrite ou modifiée a ses paramètres et son retour typés (`-> None` compris), en syntaxe moderne (`list[str]`, `X | None`). pyright (mode `standard`) tourne dans la CI. Exception ponctuelle : `# pyright: ignore[<règle>]`, jamais un `ignore` nu.

## Conventions

- Code, identifiants et messages de commit **en anglais** ; interface et documentation **en français**.
- Commits au format Conventional Commits : `type(module): description`, types `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci` ; module = `backend`, `frontend`, `system`, `hardware`, `docs` ou un sous-module (`detection`, `notifications`…). Exemple : `feat(backend): add Django project with health endpoint`.
- GitHub Flow : branches courtes `type/<numéro d'issue>-<slug>` (ex. `feat/3-cry-detection`), pull request, fusion par **squash** (le titre de la PR devient le commit sur `main` : il suit le même format).
- Suivi des tâches dans les **issues GitHub** (D83), une par lot du plan directeur.

## Garde-fous

- **Confirmation de l'auteur avant chaque commit** (une approbation = un commit) et **avant toute fusion de PR**.
- **Rien de personnel dans le dépôt public** : ni prénom, ni famille, ni date liée à la vie privée, ni domaine réel, ni identifiant de compte ; le nom de l'auteur n'apparaît que dans les licences. Écrire « l'auteur ».
- Accord explicite avant toute action publique : push, création ou modification du dépôt GitHub, issues, publications.
- Ne jamais contourner les hooks (`--no-verify`).

## Documentation

- Specs : `docs/fonctionnel/specs-fonctionnelles.md` (exigences F-xx, NF-xx), `docs/technique/choix-techniques-et-architecture.md` (architecture, raison des choix), `docs/technique/modelisation-3d.md`.
- Décisions (D*) et propositions (P*) : `docs/brainstorming/notes-brainstorming.md`, journal des décisions, **privé** (ignoré par Git, jamais publié). Pour corriger une décision, demander d'abord à l'auteur, puis ajouter une mention datée « Amendé le … » plutôt que réécrire.
- Plans : `docs/plans/` (plan directeur en 15 lots, un plan détaillé par lot). Résultats des tests sur le vrai matériel et pièges connus (go2rtc, micro, filtre IR-Cut) : `docs/plans/resultats-tests-prealables.md`.

## Faire évoluer ce fichier

Chaque piège rencontré devient une ligne ici, courte et précise.
