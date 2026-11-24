---
name: pre-push
description: Utiliser quand l'utilisateur demande "pre-push", "je peux pousser ?", "checklist avant push", "prépare le push", "vérifie avant de pousser", ou avant de créer une pull request (skill pr-create) dans le dépôt Marmotte.
---

# pre-push

Porte de contrôle avant de pousser une branche : diagnostique, propose des corrections, rend un bilan point par point. **Ne pousse jamais** (le push et la PR passent par `pr-create`, à la demande).

Tout ce qui réécrit l'historique (rebase) ou modifie du code est **proposé puis confirmé**. Un point non vérifié est marqué « non vérifié », jamais « OK ».

## Procédé

### 0. Contexte

```bash
git branch --show-current
git fetch origin
git status --short
```

- Arrêter sur `main` ou sur une branche qui ne suit ni `type/<numéro d'issue>-<slug>` ni `type/<slug>` (petite tâche sans issue).
- Arbre de travail non propre : le signaler (tests et lint tournent sur l'arbre, pas sur les commits).
- **Cible** : la base de la PR si elle existe (`gh pr view --json baseRefName -q .baseRefName`), sinon `main` ; notée `<cible>` ci-dessous.
- Commits concernés : `git log origin/<cible>..HEAD --oneline`. Aucun : rien à pousser.

### 1. Rebase sur la cible (en premier)

`git rev-list --count HEAD..origin/<cible>` : 0, à jour ; sinon proposer `git rebase origin/<cible>`. Branche jamais poussée : rebaser après confirmation. Branche déjà poussée : un rebase forcerait le push (refusé par `.claude/settings.json`) ; expliquer et laisser l'auteur décider.

### 2. Migrations

```bash
git diff --name-status origin/<cible>...HEAD -- 'backend/marmotte/*/migrations/*.py'
cd backend && uv run python manage.py makemigrations --check --dry-run
```

Migration modifiée (`M`) ou supprimée (`D`) : **bloquant**, demander. Modèle changé sans migration : bloquant, proposer de la générer. Plusieurs migrations ajoutées dans un même module : proposer de les fusionner (`.claude/rules/migrations.md`). Aucun modèle dans le diff : « non concerné ».

### 3. Documentation

Un comportement visible change (fonction, réglage, commande, procédure) : la doc correspondante (`docs/features/`, `docs/runbooks/`, `backend/README.md`, `frontend/README.md`, specs) doit suivre ; proposer le skill `write-doc`. Une règle ou une commande de `CLAUDE.md` ou de `.claude/rules/` modifiée : vérifier que ces fichiers restent justes. Refactor sans effet visible : « non concerné ».

### 4. Logs

Lire le code **ajouté** : un chemin qui a des effets de bord ou peut échouer (matériel, réseau, envoi de notification, sous-processus, erreur attendue) sans aucune trace est à signaler, avec une proposition de `logger = logging.getLogger(__name__)` et du bon niveau. Rien à ajouter sans accord.

### 5. Lint et typage

```bash
just lint
```

(ruff, `ruff format --check`, pyright, ESLint, `tsc`, Prettier : comme la CI). Corriger ce qui relève de la branche. **Typage** : pyright vérifie la cohérence des types ; il ne signale pas une fonction **sans** annotation. Relire le code ajouté : fonction sans paramètres ou retour typés, `typing.Optional`/`List`/`Dict`, `Any` évitable, `# pyright: ignore` sans règle précise : à signaler (⚠️).

### 6. Vie privée et secrets

Le dépôt est public. Sur `git diff origin/<cible>...HEAD` : aucun prénom ni nom de l'auteur hors des licences, ni famille, ni date liée à sa vie privée, ni domaine réel du babyphone, ni adresse mail, ni identifiant de compte, ni secret (clé, jeton, mot de passe, valeur d'un `.env`). Aucun fichier local dans le diff : `.env`, `backend/.env`, `fichiers de travail/`, `docs/brainstorming/`, `docs/backlog.md`, `.claude/settings.local.json`, `.claude/out/`. Une trace trouvée : **bloquant**.

### 7. Tests (en dernier)

```bash
just test
```

(back sans `hardware`, `model`, `bench`, puis front). Échec : donner le test et l'erreur. Un périmètre réduit se dit dans le bilan.

### 8. Hygiène des commits

```bash
git log origin/<cible>..HEAD --format='%h %s'
```

Chaque titre suit `type(module): description`, en anglais. Pas de `fixup`, `WIP`. Une migration est dans le même commit que son modèle. Les commits sont squashés **à la fusion de la PR** (le titre de la PR devient le commit de `main`) : ne pas les squasher avant.

### 9. Backlog

Relire `docs/backlog.md` (section « Backlog » de `CLAUDE.md`) : une entrée que la branche règle reçoit la mention « réglée par la branche <branche> » ; elle ne passera à « Traité » qu'après la fusion et une vérification dans le code (`pr-create merge`, `ticket-create sync`). Un problème repéré pendant cette checklist et hors périmètre s'y note.

### 10. Bilan

| Point | Statut | Détail |
|---|---|---|
| Rebase sur `<cible>` | ✅ / ⚠️ / ❌ / ➖ non concerné / ⏭️ non vérifié | … |
| Migrations | | |
| Documentation | | |
| Logs | | |
| Lint | | |
| Typage | | |
| Vie privée et secrets | | |
| Tests | | commande, nombre de tests |
| Commits | | |
| Backlog | | |

Verdict : **prêt à pousser**, **à corriger avant** (liste des ❌) ou **non vérifié** (ce qui n'a pas pu l'être). Les fichiers produits par la checklist se commitent avec le skill `commit`.

## À éviter

- Pousser, ou forcer un push.
- Rebaser une branche déjà poussée sans accord.
- Modifier une migration déjà sur `main`, ou en écrire une à la main.
- Annoncer « tests OK » sans les avoir lancés.
- Embarquer des changements sans rapport avec la branche.
