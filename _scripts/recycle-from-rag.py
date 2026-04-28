#!/usr/bin/env python3
"""
recycle-from-rag.py — 0-LLM transformer that reads automecanik-rag/knowledge/<cat>/<file>.md
and emits automecanik-wiki/proposals/<slug>.md with valid frontmatter v1.0.

Phase F tooling for ADR-031 (D15bis mapping). Supports the "1 source → 1 proposal" flow
for gammes/vehicles/constructeurs/policies/faq/faqs. The "absorption" flow (D15bis:
guides/ + reference/ → enriched gamme fiches) is handled by a sister mode `--mode enrich`,
not implemented in this initial version (Phase F.1 scope).

Determinism:
  - sha256 of source body included in source_refs
  - lineage_id generated as UUIDv7 (timestamp-prefixed, stable)
  - content_hash computed on body of proposal (without frontmatter)
  - idempotent: skip if proposals/<slug>.md exists with matching content_hash

Usage:
  ./recycle-from-rag.py --source automecanik-rag/knowledge/gammes/plaquette-de-frein.md \\
                       --rag-repo /opt/automecanik-rag             # default automecanik-rag clone path
  ./recycle-from-rag.py --source automecanik-rag/knowledge/gammes/ \\
                       --apply                                      # write to proposals/
  ./recycle-from-rag.py --source ... --dry-run                      # default: just print to stdout
  ./recycle-from-rag.py --source ... --validate-only                # parse + skip output

Exit codes:
  0 — success
  1 — input/output validation error
  2 — schema mismatch / category unsupported
"""
from __future__ import annotations

import argparse
import hashlib
import re
import secrets
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("pip install pyyaml", file=sys.stderr)
    sys.exit(2)


WIKI_REPO = Path(__file__).resolve().parent.parent
PROPOSALS_DIR = WIKI_REPO / "proposals"
SCHEMA_DIR = WIKI_REPO / "_meta" / "schema"

FRONTMATTER_RE = re.compile(r"^---\n([\s\S]*?)\n---\n([\s\S]*)$", re.MULTILINE)

# rag/knowledge/<cat>/ → entity_type
CATEGORY_TO_ENTITY = {
    "gammes": "gamme",
    "vehicles": "vehicle",
    "constructeurs": "constructeur",
    "policies": "support",
    "faq": "support",
    "faqs": "support",
    "diagnostic": "diagnostic",
}

SUPPORT_CATEGORY_ENUM = {
    "livraison", "retour", "garantie", "compatibilite", "remboursement",
    "paiement", "compte", "service-client", "seo-strategy",
}


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def gen_uuidv7() -> str:
    """RFC 9562 UUIDv7: 48-bit Unix-ms timestamp || 4-bit version=7 || 12-bit rand_a ||
    2-bit variant=10 || 62-bit rand_b. Returns canonical hyphenated string."""
    ts_ms = int(time.time() * 1000)
    rand_a = secrets.randbits(12)
    rand_b = secrets.randbits(62)
    # 128 bits assembly
    ts_hex = f"{ts_ms:012x}"  # 48 bits = 12 hex chars
    rand_a_hex = f"{0x7000 | rand_a:04x}"  # version 7 + 12-bit rand
    rand_b_with_variant = (0x8000_0000_0000_0000 | rand_b)
    rand_b_hex = f"{rand_b_with_variant:016x}"
    return f"{ts_hex[0:8]}-{ts_hex[8:12]}-{rand_a_hex}-{rand_b_hex[0:4]}-{rand_b_hex[4:16]}"


def parse_frontmatter(text: str) -> tuple[dict, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm = yaml.safe_load(m.group(1)) or {}
    body = m.group(2)
    return fm, body


def detect_category(source_path: Path, rag_repo: Path) -> str:
    """rag/knowledge/<category>/<file>.md → category"""
    rel = source_path.relative_to(rag_repo / "knowledge")
    parts = rel.parts
    if len(parts) < 2:
        raise ValueError(f"unexpected path layout: {source_path}")
    return parts[0]


def derive_slug(source_path: Path, fm: dict) -> str:
    """Prefer fm.slug, fallback to filename stem."""
    slug = fm.get("slug")
    if not slug:
        slug = source_path.stem
    if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$", slug):
        raise ValueError(f"derived slug invalid: {slug!r}")
    return slug


def build_entity_data(category: str, source_fm: dict, slug: str) -> dict:
    """Return entity_data block per the matching entity_data/*.schema.json."""
    if category == "gammes":
        return {
            "pg_id": int(source_fm.get("pg_id") or 0) or _missing("pg_id", source_fm),
            "family": str(source_fm.get("category") or _missing("category(=family)", source_fm)),
            "intents": _coerce_intents(source_fm.get("intent_targets", [])),
            **({"vlevel": source_fm["vlevel"]} if source_fm.get("vlevel") in {"V1", "V2", "V3", "V4", "V5", "V6"} else {}),
        }
    if category == "vehicles":
        # slug = make-modeleparts ; first segment = make, rest = model (kebab-case)
        if "-" not in slug:
            raise ValueError(f"vehicle slug missing make-model split: {slug!r}")
        make, _, model = slug.partition("-")
        return {
            "make": make,
            "model": model,
        }
    if category == "constructeurs":
        return {
            "name": str(source_fm.get("brand_name") or source_fm.get("title") or slug.title()),
        }
    if category in {"policies", "faq", "faqs"}:
        cat = str(source_fm.get("category") or _missing("category", source_fm))
        if cat not in SUPPORT_CATEGORY_ENUM:
            # faq/faqs default to service-client when source category is non-enum
            if category in {"faq", "faqs"}:
                cat = "service-client"
            else:
                raise ValueError(f"support.category {cat!r} not in enum {SUPPORT_CATEGORY_ENUM}")
        return {
            "category": cat,
            "audience": "client",
        }
    if category == "diagnostic":
        # Minimal mapping; reviewer fills the rest in proposals.
        return {}
    raise ValueError(f"unsupported category: {category}")


def _missing(field: str, fm: dict) -> Any:
    raise ValueError(f"source frontmatter missing required field {field!r} (have keys: {sorted(fm.keys())})")


def _coerce_intents(raw: list) -> list[str]:
    enum = {"diagnostic", "achat", "comparatif", "compatibilite", "remplacement", "entretien", "guide"}
    return [i for i in raw if i in enum]


def build_proposal(source_path: Path, rag_repo: Path) -> tuple[str, dict]:
    """Read source .md, derive proposal frontmatter + body. Returns (slug, payload_dict)."""
    text = source_path.read_text(encoding="utf-8")
    source_fm, source_body = parse_frontmatter(text)

    category = detect_category(source_path, rag_repo)
    if category not in CATEGORY_TO_ENTITY:
        raise ValueError(f"category {category!r} not in CATEGORY_TO_ENTITY mapping (D15bis scope)")
    entity_type = CATEGORY_TO_ENTITY[category]

    slug = derive_slug(source_path, source_fm)
    today = date.today().isoformat()
    src_body_sha = sha256_hex(source_body.encode("utf-8"))
    title = str(source_fm.get("title") or slug.replace("-", " ").title())
    aliases = source_fm.get("aliases") or []
    if isinstance(aliases, str):
        aliases = [aliases]

    fm: dict[str, Any] = {
        "schema_version": "1.0.0",
        "id": f"{entity_type}:{slug}",
        "entity_type": entity_type,
        "slug": slug,
        "title": title,
        "aliases": aliases,
        "lang": "fr",
        "created_at": today,
        "updated_at": today,
        "truth_level": "L3",
        "source_refs": [
            {
                "kind": "recycled",
                "origin_repo": "automecanik-rag",
                "origin_path": str(source_path.relative_to(rag_repo)),
                "captured_at": today,
            }
        ],
        "provenance": {
            "ingested_by": "skill:recycle-from-rag@v0.1",
            "promoted_from": None,
        },
        "lineage_id": gen_uuidv7(),
        "review_status": "proposed",
        "reviewed_by": None,
        "reviewed_at": None,
        "review_notes": (
            f"Phase F batch ADR-031. Recyclé depuis automecanik-rag par recycle-from-rag.py. "
            f"Source body sha256={src_body_sha}. À reviewer humainement avant promotion vers wiki/{entity_type}/."
        ),
        "no_disputed_claims": True,
        "exportable": {"rag": False, "seo": False, "support": False},
        "target_classes": [],
        "entity_data": build_entity_data(category, source_fm, slug),
    }

    body_lines = [
        f"# {title}",
        "",
        f"> 📥 **Proposition Phase F** — extraite par `recycle-from-rag.py` depuis `{fm['source_refs'][0]['origin_path']}`.",
        f"> source body sha256 : `{src_body_sha}`",
        f"> À reviewer manuellement avant promotion vers `wiki/{entity_type}/{slug}.md`.",
        "",
        "## Faits extraits (source body brut, à structurer)",
        "",
        source_body.strip(),
        "",
        "## Points de review",
        "",
        f"- [ ] Vérifier `entity_data` complet et aligné DB monorepo (`{entity_type}`)",
        "- [ ] Compléter ou corriger les `aliases`",
        "- [ ] Décider promotion vers `wiki/" + entity_type + "/" + slug + ".md` ou ajustement",
        "- [ ] Si promotion : `review_status: approved`, `reviewed_by: <email>`, `reviewed_at: <ISO>`",
        "",
    ]
    body = "\n".join(body_lines)

    fm["content_hash"] = "sha256:" + sha256_hex(body.encode("utf-8"))

    return slug, {"frontmatter": fm, "body": body}


def render(payload: dict) -> str:
    fm_yaml = yaml.safe_dump(payload["frontmatter"], allow_unicode=True, sort_keys=False, default_flow_style=False)
    return f"---\n{fm_yaml}---\n\n{payload['body']}"


def process_one(source: Path, rag_repo: Path, apply: bool, validate_only: bool) -> int:
    try:
        slug, payload = build_proposal(source, rag_repo)
    except (ValueError, KeyError, yaml.YAMLError) as e:
        # Single-line FAIL summary; full traceback omitted by design (one bad file should not
        # mask the batch — reviewer fixes the source frontmatter, re-runs).
        first_line = str(e).split("\n", 1)[0]
        print(f"FAIL  {source}: {first_line}", file=sys.stderr)
        return 1
    rendered = render(payload)

    if validate_only:
        print(f"OK    {source} → proposals/{slug}.md (validate-only)")
        return 0

    target = PROPOSALS_DIR / f"{slug}.md"
    if apply:
        if target.exists():
            existing = target.read_text(encoding="utf-8")
            existing_fm, _ = parse_frontmatter(existing)
            if existing_fm.get("content_hash") == payload["frontmatter"]["content_hash"]:
                print(f"SKIP  {target} (content_hash unchanged)")
                return 0
            print(f"WRITE {target} (content_hash drift, overwriting)")
        else:
            print(f"WRITE {target} (new)")
        PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
        return 0

    print(f"DRY   {source} → {target}")
    print(rendered)
    return 0


def iter_sources(source: Path) -> list[Path]:
    if source.is_file():
        return [source] if source.suffix == ".md" else []
    if source.is_dir():
        out: list[Path] = []
        for p in source.rglob("*.md"):
            if p.name.startswith("_"):
                continue
            # Skip dotted backup/working dirs (e.g. .backup-pre-enrich/, .backup-v1/) — those
            # are not canonical sources (they are local working copies under rag/knowledge/).
            if any(part.startswith(".") for part in p.relative_to(source).parts[:-1]):
                continue
            out.append(p)
        return sorted(out)
    raise FileNotFoundError(source)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--source", required=True, help="Source .md file or directory under <rag-repo>/knowledge/")
    ap.add_argument("--rag-repo", default="/opt/automecanik-rag",
                    help="Local clone path of automecanik-rag (default: /opt/automecanik-rag)")
    ap.add_argument("--apply", action="store_true", help="Write proposals to disk (default: dry-run)")
    ap.add_argument("--dry-run", action="store_true", help="Print rendered proposals without writing (default behavior)")
    ap.add_argument("--validate-only", action="store_true", help="Validate input + output schema only, no rendered output")
    args = ap.parse_args()

    rag_repo = Path(args.rag_repo).resolve()
    source = Path(args.source).resolve()
    if args.apply and args.validate_only:
        print("--apply and --validate-only are mutually exclusive", file=sys.stderr)
        return 2

    sources = iter_sources(source)
    if not sources:
        print(f"no .md files under {source}", file=sys.stderr)
        return 1

    failed = 0
    for s in sources:
        rc = process_one(s, rag_repo, args.apply, args.validate_only)
        if rc != 0:
            failed += 1
    if failed:
        print(f"\n{failed}/{len(sources)} sources failed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
