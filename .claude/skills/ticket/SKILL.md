---
name: ticket
description: Utiliser quand l'utilisateur demande "traite l'issue 4", "prends le lot 3", "liste les issues", "quelles issues sont ouvertes", "où en est l'issue X", "ticket <n>", ou veut commencer le travail d'une issue GitHub de Marmotte (lecture, branche, suivi).
---

# ticket

Traite une **issue GitHub** de Marmotte : la lire, en tirer le travail à faire, créer la branche qui porte son numéro, puis suivre son état jusqu'à la fusion. Une issue par lot du plan directeur (titre « Lot N : … », corps qui renvoie au plan du lot), plus les issues créées depuis `docs/backlog.md` (skill `ticket-create`).

Prérequis : `gh` authentifié (`gh auth status`) et dépôt GitHub existant (`gh repo view`). Sinon, le dire et s'arrêter : ne rien deviner du contenu d'une issue.

## Paramètres

- `ticket list` : issues ouvertes.
- `ticket <n>` (ou « traite l'issue <n> », « prends le lot N ») : lire l'issue et préparer son traitement.
- `ticket` seul, sur une branche `type/<n>-…` : l'issue de la branche courante.

## Procédé

### 1. Retrouver l'issue

```bash
gh issue list --state open --limit 50 --json number,title,labels,assignees
gh issue view <n> --json number,title,body,state,labels,assignees,url,comments
```

`ticket list` : un tableau court (numéro, titre, labels, assigné). « Prends le lot N » : chercher l'issue dont le titre commence par « Lot N : ». Introuvable : le dire, ne rien créer.

### 2. Lire et résumer

Restituer en français, sans recopier : le but, les critères d'acceptation (cases `- [ ]`), les contraintes, les dépendances (`#<n>` citées : les lire si elles conditionnent le travail). Pour un lot, lire aussi son plan (`docs/plans/*-lot-<N>-*.md`) : s'il manque, le dire (le plan du lot s'écrit au démarrage du lot, plan directeur § 3). Ce qui manque (pas de critère, périmètre flou) : le dire plutôt que combler.

Contrôler avant de commencer :
- issue fermée, ou assignée à quelqu'un d'autre : demander ;
- branche existante pour ce numéro : `git branch -a --list '*/<n>-*'` ;
- `git status --short` : des modifications non commitées sont à signaler avant de changer de branche.

### 3. Proposer la branche

Format `type/<n>-<slug>` (conventions de `CLAUDE.md`) :
- **type** : d'après le label de l'issue (`feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`) ; sans label, le proposer d'après le contenu (un lot du plan directeur est en général `feat`) ;
- **slug** : 2 à 5 mots **en anglais**, en minuscules, séparés par des tirets, tirés du titre.

Exemple : issue #3 « Lot 2 : détection des pleurs » → `feat/3-cry-detection`.

### 4. Confirmer, puis agir

```
Issue    : #<n> · <titre> (<url>)
Branche  : type/<n>-<slug>   depuis origin/main
Assigner l'issue à l'auteur : oui / non (marque le travail comme commencé)
```

Après confirmation :

```bash
git fetch origin
git switch -c "type/<n>-<slug>" origin/main
gh issue edit <n> --add-assignee @me   # seulement si accepté : action publique
```

### 5. Pendant le travail

Le travail suit le plan du lot ou les critères de l'issue. Un problème repéré hors du périmètre se note dans `docs/backlog.md` (section « Backlog » de `CLAUDE.md`), pas dans l'issue en cours.

### 6. Suivi de l'état

| Étape | Trace sur GitHub |
|---|---|
| Travail commencé | branche créée, issue assignée à l'auteur (si accepté) |
| PR ouverte (`pr-create`) | la PR contient `Closes #<n>` : l'issue y est reliée |
| PR fusionnée (`pr-create merge`) | GitHub ferme l'issue tout seul |

Après une fusion, vérifier : `gh issue view <n> --json state`. Issue encore ouverte : le signaler et proposer `gh issue close <n>` (à confirmer). Aucun autre statut n'est écrit.

### 7. Rendre compte

Résumé de l'issue, branche créée (ou non), assignation faite (ou non), prochaine étape.

## À éviter

- Créer une branche, assigner, commenter ou fermer une issue sans confirmation (actions publiques ou locales visibles).
- Inventer le contenu d'une issue ou d'un plan absent.
- Écrire dans l'issue des informations personnelles (règle « rien de personnel » de `CLAUDE.md`).
