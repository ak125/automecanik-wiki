"""reality_manifest — reader **0-DB** du reality-manifest (ADR-088 §F, Phase 3.2).

Le scorer/gate importe CECI (jamais le générateur `gen-reality-manifest.py`). Aucune dépendance DB.

**Dégradation sûre (ADR-088 #3)** : si le manifest est absent / non généré / vide / périmé → `status() != 'ready'`
→ le reality-check des `applies_to.engine_codes` / `related_gammes` doit être **SKIPPÉ** (advisory), JAMAIS un
faux rejet. Le rejet n'est légitime que sur **absence confirmée** dans un manifest **frais**.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_MAX_AGE_DAYS = 30


def load_manifest(path) -> dict | None:
    p = Path(path)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def status(manifest: dict | None, max_age_days: int = DEFAULT_MAX_AGE_DAYS, now: datetime | None = None) -> str:
    """'absent' | 'ungenerated' | 'empty' | 'stale' | 'ready'. Seul 'ready' autorise un rejet reality-check."""
    if manifest is None:
        return "absent"
    if not manifest.get("generated"):
        return "ungenerated"
    if not (manifest.get("engine_codes") or manifest.get("gamme_slugs")):
        return "empty"
    ga = manifest.get("generated_at")
    if ga:
        try:
            ts = datetime.fromisoformat(ga)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            now = now or datetime.now(timezone.utc)
            if (now - ts).days > max_age_days:
                return "stale"
        except ValueError:
            return "stale"
    return "ready"


def is_ready(manifest: dict | None, **kw) -> bool:
    return status(manifest, **kw) == "ready"


def engine_code_set(manifest: dict | None) -> set[str]:
    return set((manifest or {}).get("engine_codes") or [])


def gamme_slug_set(manifest: dict | None) -> set[str]:
    return set((manifest or {}).get("gamme_slugs") or [])


def unknown_engine_codes(manifest: dict | None, codes) -> list[str]:
    """Codes ABSENTS du manifest — significatif UNIQUEMENT si is_ready(manifest) (sinon skip, pas de rejet)."""
    valid = engine_code_set(manifest)
    return [c for c in (codes or []) if c not in valid]


def unknown_gamme_slugs(manifest: dict | None, slugs) -> list[str]:
    valid = gamme_slug_set(manifest)
    return [s for s in (slugs or []) if s not in valid]
