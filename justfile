# Commandes du projet Marmotte (https://just.systems) : `just --list` pour les voir toutes.

set shell := ["bash", "-euo", "pipefail", "-c"]

# Liste les commandes
default:
    @just --list

# Style et types : ruff, pyright, ESLint, tsc, Prettier
lint:
    cd backend && uv run ruff check --config pyproject.toml . ../scripts && uv run ruff format --check --config pyproject.toml . ../scripts && uv run pyright . ../scripts
    cd frontend && npm run lint && npm run typecheck && npm run format:check

# Tests sans le matériel, le modèle ni le banc complet (comme la CI)
test:
    cd backend && uv run pytest -m "not hardware and not model and not bench"
    cd backend && uv run pytest ../scripts
    cd frontend && npx vitest --run

# Arguments dans l'ordre : `just deploy <hôte> <clé ssh>`. Une clé absente est ignorée (avec un avertissement) : ssh essaie alors ses clés habituelles.
# Envoie le back sur le Pi de dev (sans le .env ni le modèle YAMNet du PC), installe ses dépendances et affiche la version
deploy host="marmotte-dev.local" key="~/.ssh/id_ed25519_raspi":
    #!/usr/bin/env bash
    set -euo pipefail
    # Les fichiers exclus ne sont ni envoyés ni effacés par --delete : le Pi garde son modèle téléchargé.
    rsync -a --delete --mkpath -e "ssh -i {{key}}" \
        --exclude .venv --exclude .data --exclude .env --exclude __pycache__ \
        --exclude .pytest_cache --exclude .ruff_cache \
        --exclude 'models/*.tflite' --exclude 'models/*.part' \
        backend/ "{{host}}:marmotte/backend/"
    # Shell de connexion (-l) : uv est dans ~/.local/bin, ajouté au PATH par ~/.profile.
    ssh -i "{{key}}" "{{host}}" bash -l -s <<'EOF'
    set -euo pipefail
    cd ~/marmotte/backend
    uv sync --locked
    uv run python -c "from marmotte.__version__ import __version__; print(__version__)"
    EOF
