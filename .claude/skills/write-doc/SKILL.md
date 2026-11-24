---
name: write-doc
description: Utiliser quand l'utilisateur demande "documente cette fonction", "écris la doc de X", "fais la doc technique de ce qu'on vient de faire", "génère un runbook pour Y", "documente cette procédure", une fois une fonction de Marmotte construite ou une procédure en place.
---

# write-doc

Une doc de référence se rouvre six mois plus tard par quelqu'un qui veut savoir « comment ça marche » ou « quelles sont les étapes exactes », sans l'auteur sous la main. Dense, structurée, facile à parcourir, **en français** (code, chemins, clés de configuration et commandes tels quels).

**Où elle vit** : `docs/features/` (fonctions) et `docs/runbooks/` (procédures), en Markdown avec diagrammes Mermaid (rendus par GitHub) ; créer le dossier au premier usage. Les autres documents de `docs/` (specs fonctionnelles et techniques, modélisation 3D, plans, pistes) ne suivent pas ces gabarits et ne sont pas régénérés ici ; une doc les cite plutôt que de les répéter.

**Ce que ce skill n'est pas** : ni un cours (pas de glossaire), ni une relecture (pas de sévérités ni de verdict), ni un document de conception écrit avant le travail : il décrit ce qui existe.

## Deux gabarits

| | **Fonction** | **Procédure** |
|---|---|---|
| Documente | Du code, une capacité | Un processus qu'un humain exécutera |
| Sections | Résumé → Contexte → Architecture → Flux / Comportement → Configuration & Utilisation → Points d'attention → Tests & Vérification → Fichiers clés → Références | Résumé → Prérequis → Vue d'ensemble → Étapes → Vérification → Rollback / Annulation → Points d'attention → Références |
| Dossier | `docs/features/` | `docs/runbooks/` |
| Le lecteur | comprend et maintient | exécute, pas à pas |

Demande ambiguë (« documente le micro ») : demander le gabarit avant de travailler.

## Étapes

### 0. Résoudre la cible

Un diff, une branche ou une PR (`git diff $(git merge-base origin/main HEAD)...HEAD`, `gh pr view <N>`, `gh pr diff <N>`, fichiers lus au SHA, jamais `gh pr checkout`) ; le travail de la conversation ; ou l'existant à explorer depuis la description de l'auteur (points d'entrée, réglages, scripts de `system/`, `justfile`, `.github/workflows/`, `.pre-commit-config.yaml`).

### 1. Lire pour de vrai

Les fichiers actuels, pas seulement le diff ni le souvenir de la conversation : **vérifier chaque affirmation concrète** (variable, chemin, option, comportement). Pour Marmotte, penser aux services séparés (web, détection, notifications, go2rtc), au matériel réel ou simulé, aux réglages lus par `get_config_value` (`.env` en développement, systemd sur le Pi), à la base SQLite dans `DATA_DIR`, aux résultats du vrai matériel (`docs/plans/resultats-tests-prealables.md`). Pour une procédure : ce qui se passe si une étape est sautée ou rejouée.

### 2. Rassembler

**Fonction** : le problème résolu ; le module qui la porte ; chaque réglage avec sa **valeur par défaut actuelle** ; le plus petit exemple réel (requête d'API, commande) ; limites et cas limites ; comment vérifier (`cd backend && uv run pytest marmotte/<module>/tests/…`, ou recette manuelle).

**Procédure** : ce qui la déclenche ; les prérequis ; les étapes ordonnées, chacune = **action** + **résultat attendu** (+ commande) ; la vérification de bout en bout ; comment annuler. Une commande non exécutée se dit « non rejouée ici », jamais présentée comme vérifiée.

### 3. Diagrammes : au moins deux

- **Fonction** : architecture (`flowchart TD`, un `subgraph` par service ou composant, 6 à 10 nœuds) ; flux (`sequenceDiagram`, ou `stateDiagram-v2` pour un cycle de vie comme les modes Sieste et Surveillance).
- **Procédure** : vue d'ensemble (`flowchart TD` : Pi, PC, téléphones, services touchés) ; étapes en flux (`flowchart TD` avec décisions en losanges, ou `sequenceDiagram` s'il y a plusieurs acteurs), en plus de la liste numérotée.

Une légende d'une ligne par figure. Syntaxe Mermaid vérifiée : pas de parenthèses ni de guillemets non échappés dans les libellés, identifiants uniques. Un doute sur le rendu : le dire.

### 4. Rédiger

Blocs de 2 à 4 phrases, tableaux et listes quand ils servent mieux ; pas de transition creuse ; un fait énoncé une fois.

**Fonction**, titres exacts : `## Résumé` (2 à 4 phrases), `## Contexte`, `## Architecture`, `## Flux / Comportement`, `## Configuration & Utilisation` (tableau réglage → défaut → effet, puis un exemple), `## Points d'attention` (une ligne s'il n'y a rien), `## Tests & Vérification`, `## Fichiers clés` (tableau `chemin → rôle`, un index), `## Références` (PR `#<n>`, issue `#<n>`, décisions `D…`/`P…`, et « Voir aussi » vers des docs qui existent vraiment).

**Procédure**, titres exacts : `## Résumé`, `## Prérequis` (cases `- [ ]`), `## Vue d'ensemble`, `## Étapes` (diagramme puis liste numérotée : action, commande, résultat attendu), `## Vérification`, `## Rollback / Annulation` (dire franchement si une étape n'est pas réversible), `## Points d'attention`, `## Références`.

### 5. Livrer

Écrire `docs/features/<slug>.md` ou `docs/runbooks/<slug>.md` (`<slug>` en kebab-case, sans date) ; un fichier existant se **met à jour**. Il s'ouvre par `# <Fonction|Procédure> : <nom>` et `Dernière vérification : <date> · <sha court de HEAD>`.

Dans le chat : le chemin, les sections, et ce que l'auteur doit trancher ou vérifier. Ne pas commiter : skill `commit` (une doc seule prend le type `docs`, par exemple `docs(detection): describe the cry alert flow`).

**Le dépôt est public** : aucun secret, aucune valeur réelle (domaine, adresse IP réelle, clé, identifiant d'appareil), rien de personnel ; des valeurs manifestement fictives dans les exemples.

## Cas limites

- **Procédure sans code** (réglage d'un compte, manipulation sur le Pi) : la source est la conversation et la vérification directe des outils nommés.
- **Défaut découvert en écrivant** : le décrire dans « Points d'attention » s'il touche le lecteur, le noter dans `docs/backlog.md` ; ne pas le corriger ici.

## À éviter

- Mélanger les gabarits, ou passer sous deux diagrammes.
- Se fier à la mémoire de la conversation plutôt qu'aux fichiers.
- Présenter comme vérifiée une commande non exécutée.
- Inventer un lien « Voir aussi ».
- Créer un second fichier quand un existe déjà pour la cible.
