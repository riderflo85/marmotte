---
name: review-diff
description: Utiliser quand l'utilisateur demande "review cette PR", "relis ce diff", "fais une code review", "review cette branche", "donne-moi ton avis sur ce diff", "review-diff", ou veut un avis de relecture avant de fusionner une pull request de Marmotte.
---

# review-diff

Relire un diff comme un développeur senior : raconter ce que le changement cherche à faire, ce qui ne va pas (avec un **scénario d'échec concret**, pas une impression), ce qu'il faudrait à la place, et s'il est prêt à fusionner. Rapport en **français** ; code, chemins et identifiants tels quels.

**Périmètre** : la **correction** (bugs, cas limites, comportement erroné), la **réutilisation / simplification / efficacité**, et le **respect des règles** de `CLAUDE.md` et de `.claude/rules/`. Pas de chasse au style : ruff et Prettier s'en chargent (`just lint`).

**Ce que ce skill ne fait pas** : il n'applique aucune correction (chaque constat a une piste, jamais appliquée) ; il ne poste rien sur GitHub (`gh pr comment`, `gh pr review`) sans demande explicite ; il n'invente pas de constat pour remplir un axe vide.

## Cible

1. **Numéro de PR** (`review-diff 14`) :
   ```bash
   gh pr view <N> --json number,title,url,headRefName,headRefOid,baseRefName,body
   git fetch origin pull/<N>/head
   gh pr diff <N>
   ```
   Lire les fichiers au commit `headRefOid` (`git show <sha>:<chemin>`). Jamais `gh pr checkout` (il change l'arbre de travail).
2. **Branche ou ref donnée** : `git rev-parse` ; base `origin/main` sauf indication.
3. **Sinon, branche courante** : `git diff $(git merge-base origin/main HEAD)...HEAD`, plus `git diff HEAD` s'il y a des changements non commités (le dire). Sans dépôt distant : base `main` locale.

## Étapes

### 1. Lire tout le diff, puis enquêter

Pour chaque fichier modifié, lire assez de code autour : appelants, tests existants, code voisin qui fait déjà la même chose, règles de `.claude/rules/` (`api.md`, `tests.md`, `migrations.md`) pour les fichiers touchés. Si la branche porte une issue (`type/<n>-…`), lire ses critères d'acceptation (`gh issue view <n>`) : un critère non couvert est un constat 🟡 (🔴 pour le comportement principal).

### 2. Identifier les constats

- **Correction** : un bug n'existe que si l'on énonce l'entrée ou l'état qui le déclenche et le résultat faux (plantage, valeur fausse, rien ne se passe, course, fuite). Sinon, abandonner.
- **Réutilisation / simplification** : logique déjà présente (`get_config_value`, `prepare_environment`, interfaces matérielles, bibliothèque partagée d'envoi), complexité inutile, requête en boucle (N+1).
- **Règles de Marmotte** :
  - l'image et le son ne quittent jamais le réseau local ; rien n'est enregistré (un envoi vers un tiers ou un fichier audio/vidéo écrit est 🔴) ;
  - services séparés (`marmotte-web`, `marmotte-detection`, `marmotte-notifications`, go2rtc) : une panne de l'un n'emporte pas les autres ;
  - le matériel passe par une interface avec une version réelle et une simulée ; un test qui touche le vrai matériel porte le marqueur `hardware` ;
  - une notification est écrite en base avant l'envoi, avec un identifiant unique ; le filet de la détection reste possible (P73) ;
  - aucun secret dans le dépôt ; un réglage se lit par `get_config_value` dans `marmotte/settings/` ; un nouveau programme appelle `prepare_environment()` ;
  - aucune dépendance sous licence non commerciale ; du code GPL seulement comme programme séparé ;
  - rien de personnel dans le dépôt public (`CLAUDE.md`, « Garde-fous ») ;
  - API : `.claude/rules/api.md` ; tests : `.claude/rules/tests.md` ; migrations : `.claude/rules/migrations.md`.
- **Typage** : fonction écrite ou modifiée sans paramètres ou retour typés, `typing.Optional`/`List`/`Dict`, `Any` évitable, `# pyright: ignore` sans règle précise (pyright ne signale pas une annotation absente).
- Titre de PR ou commit hors du format `type(module): description` : 🟢 au plus.
- Défaut déjà noté dans `docs/backlog.md` : pas un nouveau constat, sauf si le diff l'aggrave.

Sévérité : 🔴 **bloquant** (vrai bug, règle enfreinte, faille, fuite de données) ; 🟡 **à surveiller** (vrai problème, non bloquant seul) ; 🟢 **suggestion**.

### 3. Rédiger le rapport

- **`## Vue d'ensemble`** : 1 à 3 phrases : ce que fait le diff (d'après la PR et les commits), son périmètre, un avis global ; dire ici si un axe n'a rien donné.
- **`## Constats`** : 🔴, puis 🟡, puis 🟢. Chacun : `#### <emoji> <résumé> — <fichier>:<ligne>`, 1 à 3 phrases avec le scénario concret, puis **`Piste de correction :`** (extrait court ou description), jamais appliquée.
- **`## Points positifs`** : seulement s'il y a un choix notablement bon.
- **`## Synthèse`** : **Prêt à fusionner**, **À corriger avant fusion** (liste des 🔴) ou **Bloquant** ; puis 1 à 3 priorités s'il y a plusieurs constats.

### 4. Livrer

Dans le chat, en entier. Première ligne : `[**PR #<N> · <titre>**](<url>) — relu à <sha court>` (ou, en local, la branche et le SHA court, « changements non commités inclus » s'il y a lieu). Puis les sections, puis :

```
---
*review-diff · <cible> · marmotte · <sha court>*
```

Garder la review sur demande seulement : `.claude/out/reviews/<slug>-<sha court>.md`, après avoir vérifié que le dossier est ignoré par Git (`git check-ignore -q .claude/out/reviews/x.md`).

## Cas limites

- **Gros diff** : concentrer les constats sur les fichiers à risque ; citer le reste comme « relu, rien à signaler ».
- **Doc, dépendances ou configuration seulement** : « Rien à signaler », sauf erreur factuelle (commande, chemin, nom).
- **Fichiers de `.claude/`, `CLAUDE.md`, `docs/`** : vérifier leur exactitude par rapport au code, comme du code.

## À éviter

- Inventer un constat, ou relire seulement les morceaux du diff sans le code autour.
- Appliquer une correction, ou poster sur la PR sans demande.
- Recopier un secret vu dans le diff.
- Oublier le verdict.
