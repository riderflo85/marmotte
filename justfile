# Commandes du projet Marmotte (https://just.systems) : `just --list` pour les voir toutes.

set shell := ["bash", "-euo", "pipefail", "-c"]

# Liste les commandes
default:
    @just --list

# Style et types : ruff, pyright, ESLint, tsc, Prettier
lint:
    cd backend && uv run ruff check && uv run ruff format --check && uv run pyright
    cd frontend && npm run lint && npm run typecheck && npm run format:check

# Tests sans le matériel, le modèle ni le banc complet (comme la CI)
test:
    cd backend && uv run pytest -m "not hardware and not model and not bench"
    cd frontend && npx vitest --run

# Envoie le back sur le Pi de dev (sans le .env du PC), installe ses dépendances et affiche la version
deploy host="marmotte-dev.local" key="~/.ssh/id_ed25519_raspi":
    #!/usr/bin/env bash
    set -euo pipefail
    rsync -a --delete --mkpath -e "ssh -i {{key}}" \
        --exclude .venv --exclude .data --exclude .env --exclude __pycache__ \
        --exclude .pytest_cache --exclude .ruff_cache \
        backend/ "{{host}}:marmotte/backend/"
    # Shell de connexion (-l) : uv est dans ~/.local/bin, ajouté au PATH par ~/.profile.
    ssh -i "{{key}}" "{{host}}" bash -l -s <<'EOF'
    set -euo pipefail
    cd ~/marmotte/backend
    uv sync --locked
    uv run python -c "from marmotte.__version__ import __version__; print(__version__)"
    EOF
