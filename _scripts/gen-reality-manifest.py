#!/usr/bin/env python3
"""gen-reality-manifest — GÉNÉRATEUR du reality-manifest (ADR-088 §F, Phase 3.2).

⚠️ **OPS-ONLY — interroge la DB prod (SELECT read-only).** N'est PAS un gate, n'est PAS importé par
`promote.py`/`run_gates`, n'est PAS exécuté en CI. À lancer par l'owner (creds DB) pour (re)générer
`_meta/reality-manifest.json` que le gate lit ensuite **0-DB** (reality-check des `applies_to.engine_codes`
et `related_gammes` sans requête live). `import psycopg2` est LAZY (dans main) → importer ce module
sans psycopg installé ne casse rien (CI-safe).

Sortie : `_meta/reality-manifest.json` =
  { schema_version, generated, generated_at, source, counts, freshness_policy, engine_codes[], gamme_slugs[] }

Régénération (owner, sur une machine avec accès DB) :
    set -a; . backend/.env; set +a       # SUPABASE_DB_HOST / SUPABASE_DB_PASSWORD / SUPABASE_URL
    python3 _scripts/gen-reality-manifest.py --out _meta/reality-manifest.json
    git add _meta/reality-manifest.json && git commit -S -m "chore(manifest): refresh reality-manifest"

Cadence conseillée : ≤ 30 j (cf. freshness_policy ; le reader dégrade en 'stale' au-delà).
"""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

MANIFEST_SCHEMA_VERSION = "1.0.0"
DEFAULT_MAX_AGE_DAYS = 30


def _connect():
    import psycopg2  # lazy — pas requis pour importer ce module (CI-safe)

    host = os.environ["SUPABASE_DB_HOST"]
    pwd = os.environ["SUPABASE_DB_PASSWORD"]
    url = os.environ.get("SUPABASE_URL", "")
    ref = re.sub(r"^https?://", "", url).split(".")[0] if url else None
    user = os.environ.get("SUPABASE_DB_USER") or (f"postgres.{ref}" if ref else "postgres")
    port = os.environ.get("SUPABASE_DB_PORT", "6543")
    return psycopg2.connect(host=host, port=port, user=user, password=pwd,
                            dbname="postgres", sslmode="require", connect_timeout=20)


def build_manifest() -> dict:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT tmc_code FROM auto_type_motor_code "
                    "WHERE tmc_code IS NOT NULL AND tmc_code <> '' ORDER BY tmc_code")
        engine_codes = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT DISTINCT pg_alias FROM pieces_gamme "
                    "WHERE pg_alias IS NOT NULL AND pg_alias <> '' ORDER BY pg_alias")
        gamme_slugs = [r[0] for r in cur.fetchall()]
        cur.close()
    finally:
        conn.close()
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "generated": True,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {
            "engine_codes": "auto_type_motor_code.tmc_code (DISTINCT, non vide)",
            "gamme_slugs": "pieces_gamme.pg_alias (non null/vide)",
        },
        "counts": {"engine_codes": len(engine_codes), "gamme_slugs": len(gamme_slugs)},
        "freshness_policy": {"max_age_days": DEFAULT_MAX_AGE_DAYS,
                             "regen": "python3 _scripts/gen-reality-manifest.py (ops, DB creds)"},
        "engine_codes": engine_codes,
        "gamme_slugs": gamme_slugs,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Génère reality-manifest.json depuis la DB (OPS-ONLY).")
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "_meta" / "reality-manifest.json")
    args = ap.parse_args(argv)
    manifest = build_manifest()
    args.out.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"✓ {args.out} — {manifest['counts']['engine_codes']} codes moteur, "
          f"{manifest['counts']['gamme_slugs']} slugs gammes (généré {manifest['generated_at']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
