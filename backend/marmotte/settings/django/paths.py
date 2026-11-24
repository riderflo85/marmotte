"""Settings for paths."""

from pathlib import Path

# backend/marmotte/
PACKAGE_DIR = Path(__file__).resolve().parents[2]
# backend/
BACKEND_DIR = PACKAGE_DIR.parent
