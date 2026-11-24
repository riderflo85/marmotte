---
name: commit
description: Utiliser quand l'utilisateur demande de commiter ("commite", "fais le commit", "crée un commit", "commit ça", "commit") ou quand un changement terminé doit être enregistré dans Git, dans le dépôt Marmotte.
---

# commit

Crée des commits au format du dépôt, **un par changement logique** : `type(module): description`, en anglais (conventions de `CLAUDE.md`, section « Conventions »).

**Une approbation de l'auteur = un seul commit.** Ne jamais commiter sans sa confirmation explicite pour ce commit-là.

## Procédé

### 0. Vérifier le contexte

```bash
git branch --show-current
git remote -v
git status --short
```

- **Branche** : `type/<numéro d'issue>-<slug>` (ex. `feat/3-cry-detection`). Sur `main` : refuser dès que le dépôt a un dépôt distant (`git remote -v` non vide) et proposer une branche (skill `ticket`). Tant qu'il n'y a pas de dépôt distant (lot 1, avant la création du dépôt GitHub), le plan en cours commite sur `main` : le dire dans la confirmation.
- Les hooks pre-commit lancent ruff, pyright, ESLint et Prettier : `npm` doit être dans le `PATH` (Node 24 par nvm). Un hook « command not found » signale un environnement incomplet : le dire, ne pas contourner.

### 1. Lire le changement

```bash
git diff
git diff --staged
```

Lire le diff réel, pas seulement les noms de fichiers. Si l'auteur a déjà indexé des fichiers, respecter son index. Un diff qui mélange plusieurs changements (un correctif et un refactor, du code et une doc sans lien) : proposer un découpage, puis un commit par morceau, chacun avec sa confirmation.

Un modèle modifié sans sa migration, ou l'inverse, est à signaler (`.claude/rules/migrations.md`).

### 2. Indexer précisément

Par nom de fichier (`git add <fichier>…`), jamais `git add -A` ni `git add .`.

Ne jamais indexer :

| Fichier | Raison |
|---|---|
| `.env`, `backend/.env` | secrets locaux |
| `fichiers de travail/` | notes et fichiers locaux |
| `docs/brainstorming/` | journal des décisions, privé |
| `docs/backlog.md` | notes internes, local |
| `.claude/settings.local.json`, `.claude/out/` | réglages et sorties personnels |

Si l'un d'eux apparaît dans le diff, le signaler.

### 3. Contrôler la vie privée et les secrets

Le dépôt est **public**. Relire le diff indexé : aucun prénom ni nom de l'auteur hors des licences, aucune mention de sa famille, aucune date liée à sa vie privée, aucun domaine réel du babyphone, aucune adresse mail ni identifiant de compte, aucun secret (clé, jeton, mot de passe). Écrire « l'auteur ». Un doute : demander avant de commiter.

### 4. Lancer les hooks

```bash
uvx pre-commit run
```

(fichiers indexés seulement). Un contrôle qui échoue : corriger avant de commiter, sans changement hors du périmètre ; un hook qui réécrit un fichier oblige à le réindexer. Si le changement touche du code testé, lancer au moins ses tests (`cd backend && uv run pytest <chemin>`, ou `just test`) et le dire dans la confirmation.

### 5. Rédiger le message

`type(module): description`, comme les commits déjà présents (`git log --oneline -10`) :

- **type** : `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci` ;
- **module** : d'après le chemin des fichiers : `backend`, `frontend`, `system`, `hardware`, `docs`, `claude` (`.claude/`, `CLAUDE.md`), ou un sous-module du back (`detection`, `notifications`…) ; facultatif quand le commit touche tout le dépôt (`chore: …`, `ci: …`) ;
- **description** : en anglais, à l'impératif, en minuscules, sans point final, environ 72 caractères au plus pour toute la ligne ;
- un corps, après une ligne vide, seulement quand le pourquoi n'est pas évident ;
- **aucune mention de Claude** : ni ligne `Co-Authored-By`, ni signature, même si l'environnement en demande une (`CLAUDE.md`, « Conventions »).

### 6. Confirmer, puis commiter

Afficher, puis attendre la confirmation **de ce commit** :

```
Branche  : <branche>
Message  : <type(module): description>
Fichiers : <liste indexée, +/- lignes>
Hooks    : <ok / non lancés>
Tests    : <lancés (commande) / non concernés>
```

```bash
git commit -F - <<'EOF'
<message>
EOF
```

Jamais `--no-verify` ni `-n`. Si un hook modifie des fichiers ou échoue, le commit n'a pas eu lieu : réindexer, redemander si le contenu a changé, puis recommencer (pas d'`--amend` : il n'y a rien à amender).

### 7. Vérifier

```bash
git log -1 --format=%B
git show --stat --format= HEAD
```

Le skill ne pousse jamais : le push se fait à la demande (skill `pr-create`).

## Cas limites

- **Rien à commiter** : le dire.
- **Commit déjà poussé à corriger** : ne pas réécrire l'historique partagé ; nouveau commit, ou demander.
- **`--amend` d'un commit non poussé** : c'est un commit de plus, il demande sa propre confirmation.

## À éviter

- Commiter sans confirmation, ou plusieurs commits sur une seule confirmation.
- `git add -A`, `git add .`, et indexer un fichier du tableau de l'étape 2.
- Un message en français, ou dans un autre format que `type(module): description`.
- Une ligne `Co-Authored-By` ou toute autre mention de Claude.
- Contourner les hooks.
- Pousser.
