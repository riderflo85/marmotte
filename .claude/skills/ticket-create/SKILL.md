---
name: ticket-create
description: Utiliser quand l'utilisateur demande "crée les issues du backlog", "envoie le backlog sur GitHub", "crée l'issue n°3 du backlog", "synchronise le backlog", "ticket-create", ou veut transformer des entrées de docs/backlog.md en issues GitHub de Marmotte.
---

# ticket-create

Transforme les entrées de `docs/backlog.md` au statut **« À créer »** en **issues GitHub**, après recherche de doublons et une confirmation par issue, puis inscrit le numéro dans le backlog. Sait aussi **synchroniser** le backlog avec les issues fermées.

`docs/backlog.md` est **local** (ignoré par Git) ; les issues sont **publiques** : leur texte suit la règle « rien de personnel » de `CLAUDE.md`.

Prérequis : `gh` authentifié et dépôt GitHub existant. Sinon, arrêter.

## Paramètres

- `ticket-create` : toutes les entrées « À créer ».
- `ticket-create <k>` : l'entrée n°`<k>` seulement.
- `ticket-create sync` : synchronisation (voir plus bas).

## Correspondance entrée → issue

| Backlog | Issue |
|---|---|
| Titre (`## <k>. …`) | Titre de l'issue, en français, sans balises de code |
| Type | Label, **à confirmer** : `bug` → `fix` ; `architecture` → `refactor` ; `remarque` → `feat`, `docs` ou `chore` selon le contenu |
| User story | Section `## User story`, en citation |
| Description | Section `## Contraintes techniques` : le constat, comment l'observer, puis « Fichiers concernés » |
| Critères d'acceptation | Section `## Critères d'acceptation`, une case `- [ ]` par critère |
| « Lié à » / « Dépend de » | Section `## Dépendances` : `#<n>` de l'issue liée si elle existe, sinon « entrée n°<k> du backlog » |

Une section vide dans le backlog est **omise** : ne rien inventer. Corps type :

```markdown
## User story
> En tant que …, je veux … afin de ….

## Contraintes techniques
Constat : …

Fichiers concernés : `backend/marmotte/…`

## Critères d'acceptation
- [ ] …

## Dépendances
- …
```

## Procédé

### 1. Lire le backlog

Lire `docs/backlog.md` en entier ; retenir les entrées « À créer » (ou l'entrée demandée). Aucune : le dire.

### 2. Chercher les doublons

```bash
gh issue list --state all --search "<mots du titre>" --json number,title,state
```

Une issue proche existe : la montrer et demander (lier l'entrée à cette issue, ou créer quand même).

### 3. Préparer et confirmer, issue par issue

Afficher le titre, le label proposé et le corps ; relire le texte (aucun prénom, aucune famille, aucune date de vie privée, aucun domaine réel, aucun secret). Un label absent du dépôt (`gh label list`) se crée avec l'accord de l'auteur, couleurs du skill `pr-create`. Attendre la confirmation **de cette issue**.

### 4. Créer

```bash
gh issue create --title "<titre>" --label "<label>" --body-file - <<'ISSUE_BODY'
<corps>
ISSUE_BODY
```

La commande renvoie l'URL ; le numéro est sa dernière partie.

### 5. Mettre à jour le backlog

Dans l'entrée : statut **« Issue créée (#<n>) »** et l'URL. Ne jamais deviner un numéro : le lire dans la sortie de `gh`.

## Synchroniser (`ticket-create sync`)

Pour chaque entrée « Issue créée (#<n>) » :

```bash
gh issue view <n> --json state,stateReason,closedAt
```

- **Fermée comme terminée** : vérifier **dans le code** que le problème est réglé (relire les fichiers cités, rejouer la vérification de l'entrée). Réglé : statut **« Traité (<date>, PR #<pr> ou commit <sha>) »**. Pas réglé : le dire, ne pas changer le statut.
- **Fermée comme non prévue** : le dire à l'auteur, qui décide.
- **Ouverte** : rien à faire.

Ne jamais supprimer une entrée du backlog.

## À éviter

- Créer une issue sans confirmation, ou plusieurs sur une seule confirmation.
- Créer un doublon sans l'avoir signalé.
- Publier une information personnelle ou un secret dans une issue.
- Passer une entrée à « Traité » sur la seule foi d'une issue fermée.
