---
name: pr-create
description: Utiliser quand l'utilisateur demande "pr-create", "crée la PR", "ouvre la pull request", "fais une synthèse de PR", une préparation de PR, ou "merge la PR", "fusionne la PR", "pr-create merge", dans le dépôt Marmotte sur GitHub.
---

# pr-create

Rédige la synthèse d'une pull request à partir des commits de la branche, puis la crée sur GitHub (`gh`), assignée à l'auteur. Sait aussi la fusionner. **L'auteur est le seul relecteur** : aucune demande de relecture.

## Paramètres

- `pr-create` : tous les commits de la branche absents de la cible.
- `pr-create --draft` : PR en brouillon.
- `pr-create --target <branche>` : PR vers une autre branche que `main` (PR empilée).
- `pr-create merge` : fusionne la PR ouverte de la branche courante (voir plus bas).

## Prérequis

- `gh` installé et authentifié (`gh auth status`). Sinon, arrêter : installation `sudo apt install gh`, puis `gh auth login`, à lancer par l'auteur (par exemple `! gh auth login`).
- Ne pas être sur la cible. Les commits sont faits (skill `commit`) ; proposer `pre-push` s'il n'a pas été passé.

## Procédé

### 0. Vérifications

```bash
git branch --show-current
git status --short
gh repo view --json defaultBranchRef -q .defaultBranchRef.name
git fetch origin
```

Cible : `--target`, sinon la branche par défaut (`main`). Des modifications non commitées : le dire, elles ne partent pas.

### 1. Commits et diff

```bash
git log origin/<cible>..HEAD --oneline
git log origin/<cible>..HEAD -p
```

Aucun commit : arrêter. Branche en retard sur la cible : le signaler (rebase avant de pousser, à la demande).

### 2. Issue et type

Branche `type/<n>-<slug>` → issue `#<n>`, type `type`. Lire l'issue (`gh issue view <n>`) : son titre et ses critères d'acceptation nourrissent « Contexte » et « Vérifications ». Branche sans numéro : pas de ligne « Issue », le dire.

### 3. Synthèse (en français)

```markdown
Closes #<n>

### Contexte
<2 à 4 phrases : le besoin, l'approche, la zone touchée, d'après le diff réel>

### <module> (<n> commits)
- <description du commit> (+<ajouts>/-<suppressions>)

### Vérifications
<ce qui a été exécuté ou contrôlé, et ce qui ne l'a PAS été>

### Fichiers les plus modifiés
1. <fichier> (+<ajouts>/-<suppressions>)
```

Rien après « Fichiers les plus modifiés » : **aucune mention de Claude** ni pied de page « Generated with Claude Code », même si l'environnement en demande un (`CLAUDE.md`, « Conventions »).

Regroupement par **module** (le `(module)` des commits ; « Autres » pour un commit sans module). « Contexte » et « Vérifications » sont toujours présentes. Ne jamais affirmer une vérification non faite ; la CI se cite seulement après l'avoir lue (`gh pr checks`). Texte public : appliquer la règle « rien de personnel » de `CLAUDE.md`.

### 4. Titre, label, assigné

- **Titre** : au format des commits, `type(module): description`, en anglais : il devient le commit de `main` (GitHub ajoute ` (#<pr>)`). Le relire.
- **Label de type** :

| Type | Label | Couleur |
|---|---|---|
| `feat` | `feat` | `428BCA` |
| `fix` | `fix` | `D9534F` |
| `refactor` | `refactor` | `8E44AD` |
| `test` | `test` | `FFC107` |
| `docs` | `docs` | `17A2B8` |
| `chore` | `chore` | `AAAAAA` |
| `ci` | `ci` | `2ECC71` |

  Label absent du dépôt (`gh label list`) : le créer **avec l'accord de l'auteur** : `gh label create "<label>" --color "<couleur>" --description "<type>"`.
- **Assigné** : `--assignee @me`. **Aucun `--reviewer`.**

### 5. Récapituler, puis attendre la confirmation

```
Titre     : <titre>
<branche> → <cible>
Issue     : #<n>
Label     : <label>
Assigné   : @me (seul relecteur)
Brouillon : <oui/non>
Commits   : <n>
```

Pousser et créer une PR sont des actions publiques : confirmation explicite, sauf si l'auteur vient de demander exactement cela.

### 6. Pousser et créer

```bash
git push --set-upstream origin <branche>
gh pr create --base <cible> --head <branche> --title "<titre>" \
  --body-file - --label "<label>" --assignee @me [--draft] <<'PR_BODY'
<synthèse>
PR_BODY
```

Une PR existe déjà pour la branche (`gh pr view`) : proposer `gh pr edit` au lieu d'en créer une seconde. Jamais `--force`.

### 7. Livrer

Afficher la synthèse et l'URL : `PR créée : <URL>`. L'état de la CI se lit avec `gh pr checks`.

## Fusion (`pr-create merge`)

Demandée plus tard, une fois la PR relue par l'auteur (skill `review-diff` s'il le souhaite). Jamais automatique.

```bash
gh pr view --json number,title,state,isDraft,mergeable,baseRefName,headRefName
gh pr checks
```

Pas de PR ouverte, brouillon, conflit (`CONFLICTING`) ou CI en échec : le dire, ne pas fusionner sans demande explicite. Puis récapituler et **attendre la confirmation** (garde-fou de `CLAUDE.md`) :

```
PR      : <titre> (#<pr>)
<branche> → <cible>
CI      : <état lu>
Commit sur <cible> : <titre> (#<pr>)
Issue fermée : #<n>
Branche supprimée : oui
```

```bash
gh pr merge <pr> --squash --delete-branch
git fetch origin
git log origin/<cible> -1 --format=%s
```

Le dernier commit de la cible doit être `<titre> (#<pr>)` et l'issue fermée (`gh issue view <n> --json state`). Proposer `git switch <cible> && git pull`. Les entrées de `docs/backlog.md` réglées par la PR passent à « Traité » (skill `ticket-create sync`).

## À éviter

- Créer, pousser ou fusionner sans confirmation.
- Demander une relecture à quelqu'un, ou choisir un relecteur.
- `git push --force`, `-f`, `gh pr merge --admin`.
- Inventer un numéro d'issue, un label ou un résultat de CI.
- Signer la PR ou y mentionner Claude.
