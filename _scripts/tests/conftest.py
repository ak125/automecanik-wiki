"""Pytest configuration for wiki _scripts tests."""
from __future__ import annotations

import sys
from pathlib import Path

# Make _scripts importable as modules
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))
