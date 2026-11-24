---
name: write-test
description: Utiliser quand l'utilisateur demande "écris les tests de X", "ajoute des tests", "teste ce réglage / cette vue / ce schéma / ce service", "write-test", "couvre ce changement par des tests" ou "reproduis ce bug par un test", dans le back de Marmotte.
---

# write-test

Écrit des tests qui ressemblent à ceux du dépôt, les lance et dit ce qui est couvert ou non. Les conventions sont dans `.claude/rules/tests.md` (et `api.md`, `migrations.md`) : les **lire** avant d'écrire. Modèle : `backend/marmotte/base/tests/test_settings.py`.

Ce skill écrit des tests ; il **ne modifie pas le code testé**. Un test qui révèle un bug se rapporte (étape 5).

## Procédé

### 0. Cibler

L'objet ou le comportement nommé par l'utilisateur ; sinon le changement de la branche (`git diff $(git merge-base origin/main HEAD)...HEAD`), en ne gardant que le code qui porte du comportement. Lire le code testé **en entier** : branches, erreurs, effets de bord (base, fichier, sous-processus, réseau, matériel).

### 1. Lire l'existant

- Les tests du module : `backend/marmotte/<module>/tests/` (`tests_models/`, `tests_schemas/`, `tests_views/`, `test_<sujet>.py`). Ne pas dupliquer : compléter.
- Modèles à suivre : réglages et variables d'environnement (`backend/marmotte/base/tests/test_settings.py`), vue (`backend/marmotte/base/tests/tests_views/test_health.py`), point d'entrée lancé en sous-processus (`TestEntryPoints`, dans le premier).
- La configuration de pytest (`[tool.pytest.ini_options]` de `backend/pyproject.toml`) : variables fixées par pytest-env, marqueurs.

### 2. Choisir quoi couvrir

Un test par comportement observable :

- **Vue django-ninja** : code HTTP et JSON de chaque réponse déclarée (`client.get("/api/…")`), entrée refusée (422), erreur attendue (`HttpError`) ; plus tard, accès refusé à un téléphone non appairé (lot 8).
- **Schéma** : champs requis, valeurs refusées, sérialisation.
- **Réglage** : variable absente, vide, invalide, valeur par défaut, conversion (`monkeypatch`).
- **Matériel** (caméra, micro, capteur, bouton) : la version **simulée** sur PC ; la vraie seulement dans un test marqué `@pytest.mark.hardware`.
- **Détection** : fichiers du banc d'essai ; un test qui charge YAMNet porte `@pytest.mark.model`, le banc complet `@pytest.mark.bench`.
- **Programme** (`manage.py`, `asgi.py`, service) : sous-processus avec un environnement explicite et `MARMOTTE_ENV_FILE=""`.
- **Base de données** (à partir du lot 4) : `@pytest.mark.django_db` sur la classe.

Cas limites à chercher dans le code lu : valeur absente, vide ou faite d'espaces, liste vide, doublon, erreur de conversion, service arrêté, fichier manquant.

### 3. Écrire

- une **classe par objet testé** (`Test<Objet>`), dans le fichier de l'objet s'il existe ;
- chaque test : une docstring d'une ligne en anglais, puis `# GIVEN`, `# WHEN`, `# THEN` (`# WHEN / THEN` autour d'un `pytest.raises`) ;
- `monkeypatch` pour l'environnement et les remplacements ; une variable posée par le code testé se nettoie en la posant puis la retirant avec `monkeypatch` avant l'appel ;
- `tmp_path` pour les fichiers ; jamais de réseau ni de matériel réel hors des marqueurs ;
- une assertion utile en cas d'échec : `assert result.stdout.strip() == "…", result.stderr` ;
- aucune valeur réelle (domaine, adresse, clé, identifiant d'appareil) : des valeurs manifestement fictives ;
- les tests sont typés comme le reste du code (paramètres et `-> None`).

### 4. Exécuter

```bash
cd backend && uv run pytest marmotte/<module>/tests/<fichier>.py::<Classe>::<test> -v
uv run pytest
uv run ruff check && uv run ruff format --check && uv run pyright
```

- **Nouveau comportement** : les tests passent.
- **Reproduction d'un bug** : le test **échoue avant le correctif**, pour la bonne raison (l'assertion qui décrit le bug, pas une erreur d'import). Le montrer ; le correctif est une décision distincte.
- Un test qui protège un comportement critique et passe du premier coup : vérifier qu'il échoue quand on casse volontairement le code (puis tout remettre).

### 5. Restituer

En français : fichiers créés ou modifiés ; **ce qui est couvert** (comportements) et **ce qui ne l'est pas** (et pourquoi : vrai matériel, service externe, hors périmètre) ; commande lancée et résultat réel. Un bug découvert se note dans `docs/backlog.md` (après recherche de doublon), sans le corriger. Les tests se commitent avec le skill `commit`.

## À éviter

- Modifier le code testé pour faire passer un test.
- Refaire le calcul du code dans le test au lieu de vérifier le résultat.
- Un `conftest.py` pour des variables lues par les réglages (trop tard : pytest-env).
- Des tests qui dépendent de l'ordre d'exécution ou de l'heure réelle.
- Annoncer « tests OK » sans les avoir lancés.
