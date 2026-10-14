#!/usr/bin/env python3
"""check-coverage-map.py — validateur coverage-map (livrable différé ADR-089).

Backing de gouvernance : ADR-089 (Content Coverage-Map Canon), encore `proposed`
au vault. Ce validateur est le « `check-coverage-map.py` » que le schéma
(`_meta/schema/coverage-map.schema.json`) et ADR-089 §Invariant nomment mais qui
n'avait jamais été construit — d'où une structure coverage-map produite ad-hoc et
incohérente (6/15 fiches sans coverage-map, dim A du score ADR-088 à 0 pour elles).

REPORT-ONLY par défaut (exit 0, observabilité). L'ENFORCEMENT (`--strict`, exit 1)
et le câblage CI restent GELÉS jusqu'à la ratification d'ADR-089 (owner G3) —
cohérent avec ADR-089 §Séquence « owner-sponsorisé après acceptation ». Aucun repli
silencieux : un trou est toujours rapporté, jamais masqué.

Invariants (ADR-089 §5) : 0 LLM, 0 DB. Reality-check via `_meta/source-catalog.yaml`
commité (FK strict), jamais de requête DB.

Vérifie, par fiche `proposals/<slug>.md` :
  1. Présence d'une coverage-map `proposals/_coverage/<slug>.coverage.yaml`
     (WARN si la fiche porte des sections H2 sourçables mais n'a pas de coverage-map).
  2. Conformité au schéma `_meta/schema/coverage-map.schema.json`.
  3. FK strict : chaque `coverage_entries[].source_slug` existe dans
     `_meta/source-catalog.yaml` (FAIL sinon — anti-gonflement du score, ADR-089 §3).
  4. Ancrage : chaque `coverage_entries[].section` correspond à un H2 OU H3 réel de la fiche
     (les fiches structurent en sous-sections ; H4+ = niveau-item, hors ancrage).
  5. Quand text_anchor est déclaré, son texte doit apparaître dans un bloc de prose
     de cette section unique. Markdown analysé, pas de correspondance floue : les
     exemples de code, commentaires et URL de lien ne constituent pas une preuve.
     Cette présence ne valide ni la vérité du claim ni son appui par la source.
  La promotion appelle require_source_proof=True : carte non vide, ancre explicite,
  source capturée/active et empreinte exigées. Le mode de préparation conserve les
  sources en attente. L'intégrité RAW reste contrôlée par quality-gates.py.

Usage:
  python3 _scripts/check-coverage-map.py --all
  python3 _scripts/check-coverage-map.py proposals/disque-de-frein.md
  python3 _scripts/check-coverage-map.py --all --strict        # enforcement (post-ADR-089)
  python3 _scripts/check-coverage-map.py --all --format json
"""
from __future__ import annotations

import argparse
import functools
import html
import importlib.util
import json
import re
import sys
import unicodedata

from markdown_it import MarkdownIt
from pathlib import Path

import yaml

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover
    Draft202012Validator = None

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)


def _repo_root(start: Path) -> Path:
    """Remonte jusqu'au repo wiki (présence _meta/source-catalog.yaml)."""
    cur = start.resolve()
    for cand in [cur, *cur.parents]:
        if (cand / "_meta" / "source-catalog.yaml").is_file():
            return cand
    return start


def _load_catalog(root: Path) -> dict[str, dict]:
    """Read the selected checkout, rejecting ambiguous source identifiers."""
    cat = root / "_meta" / "source-catalog.yaml"
    data = yaml.safe_load(cat.read_text(encoding="utf-8")) or {}
    entries = {}
    for source in data.get("sources") or []:
        if not isinstance(source, dict) or not source.get("slug"):
            continue
        slug = source["slug"]
        if slug in entries:
            raise ValueError(f"duplicate_source_slug:{slug}")
        entries[slug] = source
    return entries


def _load_catalog_slugs(root: Path) -> set[str]:
    return set(_load_catalog(root))


def referenced_source_slugs(md_path: Path, root: Path) -> set[str]:
    """Scope of archive inputs; malformed maps are rejected by check_fiche."""
    path = root / "proposals" / "_coverage" / f"{md_path.stem}.coverage.yaml"
    if not path.is_file():
        return set()
    coverage = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {entry["source_slug"] for entry in coverage.get("coverage_entries") or []
            if isinstance(entry, dict) and isinstance(entry.get("source_slug"), str)}


def _load_schema(root: Path):
    sp = root / "_meta" / "schema" / "coverage-map.schema.json"
    if not sp.is_file():
        return None
    return json.loads(sp.read_text(encoding="utf-8"))


def _split_md(text: str) -> tuple[dict, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm = yaml.safe_load(m.group(1)) or {}
    return (fm if isinstance(fm, dict) else {}), m.group(2)


def _normalize_anchor(text: str) -> str:
    # Keep negations, numbers, punctuation and accents: this is an excerpt check,
    # never a semantic similarity score. NFC accepts equivalent Unicode spelling.
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


def _prose_sections(body: str) -> dict[str, list[list[str]]]:
    """H2/H3 label -> occurrences -> prose blocks (children included).

    CommonMark parsing avoids treating headings inside fenced code or comments
    as actual sections. Matching within one block prevents assembling a claim
    from unrelated paragraphs. Repeated headings remain ambiguous, not merged.
    """
    tokens = MarkdownIt("commonmark").enable("table").parse(body)
    headings = [(i, int(t.tag[1:]), "#" * int(t.tag[1:]) + " " + tokens[i + 1].content.strip())
                for i, t in enumerate(tokens)
                if t.type == "heading_open" and t.level == 0]
    sections: dict[str, list[list[str]]] = {}
    for pos, (index, depth, label) in enumerate(headings):
        if depth not in (2, 3):
            continue
        end = next((j for j, d, _ in headings[pos + 1:] if d <= depth), len(tokens))
        blocks = []
        for j in range(index + 3, end):
            token = tokens[j]
            if token.type != "inline" or tokens[j - 1].type == "heading_open":
                continue
            children = token.children or []
            # Raw inline HTML may contain hidden content. Conservatively require
            # an excerpt in ordinary Markdown prose instead of interpreting CSS.
            if any(c.type == "html_inline" for c in children):
                continue
            visible = "".join(c.content if c.type in ("text", "code_inline") else
                              " " if c.type in ("softbreak", "hardbreak") else ""
                              for c in children)
            if visible.strip():
                blocks.append(_normalize_anchor(visible))
        sections.setdefault(label, []).append(blocks)
    return sections


# Lecture par un lecteur qui ignore le balisage (rendu permissif, texte brut) : un lien ou une
# image se réduit à son libellé quelle que soit sa destination ; un autolien `<https://…>` n'est
# pas une balise.
_HTML_TAG = re.compile(r"<!--.*?-->|</?[A-Za-z][A-Za-z0-9-]*(?:\s[^>]*)?/?>", re.S)
_INLINE_LINK = re.compile(r"!?\[([^\[\]]*)\]\([^)]*\)")
_MARKUP_CHARS = re.compile(r"[`*_~\\\[\]]")
# Default_Ignorable_Code_Point (Unicode 15.0, DerivedCoreProperties.txt), absente d'`unicodedata` :
# points de code qu'un rendu n'affiche pas quelle que soit leur catégorie (sélecteurs de
# variation, remplisseurs hangûl, étiquettes ; réservés compris).
_DEFAULT_IGNORABLE = ((0x00AD, 0x00AD), (0x034F, 0x034F), (0x061C, 0x061C), (0x115F, 0x1160),
                      (0x17B4, 0x17B5), (0x180B, 0x180F), (0x200B, 0x200F), (0x202A, 0x202E),
                      (0x2060, 0x206F), (0x3164, 0x3164), (0xFE00, 0xFE0F), (0xFEFF, 0xFEFF),
                      (0xFFA0, 0xFFA0), (0xFFF0, 0xFFF8), (0x1BCA0, 0x1BCA3), (0x1D173, 0x1D17A),
                      (0xE0000, 0xE0FFF))
# Glyphes vides : caractères visibles pour Unicode (ni espace, ni invisibles) qu'un rendu dessine
# sans encre, lus comme un espace (`25` + blanc braille + `Nm` s'affiche `25 Nm`) : blanc braille,
# blancs hiéroglyphiques plein et demi, remplisseur khitan, tête de note nulle.
_BLANK_GLYPHS = frozenset({0x2800, 0x13441, 0x13442, 0x16FE4, 0x1D159})
# Blocs feuilles : leurs lignes source sont lues par leurs jetons. Une ligne hors de tous
# (définition de lien, y compris répétée ou imbriquée dans une citation ou une liste) n'a pas de
# jeton : elle est lue telle qu'écrite.
_LEAF_BLOCKS = frozenset({"paragraph_open", "heading_open", "fence", "code_block", "html_block",
                          "hr", "table_open"})


def invisible(ch: str) -> bool:
    """Vrai pour un caractère qu'aucun rendu n'affiche : caractère de format (catégorie Cf :
    espace sans chasse, trait d'union conditionnel, marques de direction) ou ignorable par
    défaut (`_DEFAULT_IGNORABLE` : sélecteur de variation, remplisseur hangûl…)."""
    cp = ord(ch)
    return unicodedata.category(ch) == "Cf" or any(lo <= cp <= hi for lo, hi in _DEFAULT_IGNORABLE)


@functools.lru_cache(maxsize=None)
def _script(ch: str) -> bool:
    """Vrai pour un exposant ou un indice (décomposition `<super>` ou `<sub>`)."""
    return unicodedata.decomposition(ch).startswith(("<super>", "<sub>"))


@functools.lru_cache(maxsize=None)
def _compat_char(ch: str) -> str:
    """Décomposition de compatibilité de `ch` (celle de NFKD), exposants et indices gardés pour
    que `_compat` les lise dans leur contexte (`㎟` → `mm²`)."""
    decomposition = unicodedata.decomposition(ch)
    if _script(ch):
        return ch
    if decomposition.startswith("<"):
        return "".join(_compat_char(chr(int(cp, 16))) for cp in decomposition.split()[1:])
    canonical = unicodedata.normalize("NFD", ch)
    return ch if canonical == ch else "".join(_compat_char(c) for c in canonical)


def _compat(text: str) -> str:
    """Texte à l'équivalence de compatibilité Unicode près : NFKC (`℃` → `°C`, `㎜` → `mm`,
    pleine chasse → ASCII, exposant ou indice → chiffre ou lettre : `10²` → `102`, `₁₂₀` → `120`),
    sauf le `²` d'une unité `mm²` (`㎟` → `mm²`, jamais `mm2` : l'unité lue changerait),
    caractères invisibles retirés (`invisible`), glyphes vides lus comme un espace (`_BLANK_GLYPHS`),
    espaces réduits."""
    text = unicodedata.normalize("NFC", "".join(_compat_char(ch) for ch in text))
    text = "".join(" " if ord(ch) in _BLANK_GLYPHS else ch for ch in text if not invisible(ch))
    read = ""
    for i, ch in enumerate(text):
        unit_square = (ch == "\u00b2" and read.endswith("mm")
                       and not (i + 1 < len(text) and _script(text[i + 1])))
        read += ch if unit_square or not _script(ch) else unicodedata.normalize("NFKC", ch)
    return " ".join(unicodedata.normalize("NFC", read).split())


def markup_blind_text(source: str) -> str:
    """`source` lu sans balisage : entités décodées, lien ou image réduit à son libellé, balises
    et commentaires HTML retirés, caractères de balisage Markdown retirés. Sur-approximation des
    rendus CommonMark et HTML : un nombre et son unité séparés seulement par du balisage se
    lisent côte à côte. Un renvoi de note (`25[^a] Nm`) n'est pas du balisage : le rendu affiche
    son numéro entre le nombre et l'unité."""
    text = html.unescape(source)
    while (reduced := _INLINE_LINK.sub(r"\1", text)) != text:
        text = reduced
    text = _HTML_TAG.sub("", text)
    return _compat(_MARKUP_CHARS.sub("", text))


def form_text(text: str, form: str) -> str:
    """`text` normalisé comme un bloc dérivé de la forme `form` de `visible_text_blocks`."""
    if form == "sans balisage":
        return markup_blind_text(text)
    return _compat(text)


def _shown_inline(children) -> str:
    """Texte affiché d'une suite de jetons inline, HTML brut exclu, texte alternatif d'image en
    place (récursivement, entités comprises)."""
    parts = []
    for c in children:
        if c.type in ("text", "text_special", "code_inline"):
            parts.append(c.content)
        elif c.type in ("softbreak", "hardbreak"):
            parts.append(" ")
        elif c.type == "image":
            parts.append(_shown_inline(c.children or []))
    return "".join(parts)


def _link_attributes(md: MarkdownIt, children):
    """Titre et destination de chaque lien et image (texte alternatif compris). La destination
    est lue échappements d'URL décodés (`normalizeLinkText`) : l'attribut `href`/`src` est la
    forme que l'analyseur ré-encode (`é` → `%C3%A9`), écrite par personne. Telle qu'écrite,
    elle est relevée à l'analyse (`visible_text_blocks`)."""
    for c in children:
        if c.type in ("link_open", "image"):
            for name in ("title", "href", "src"):
                value = c.attrGet(name)
                if isinstance(value, str) and value:
                    yield value if name == "title" else md.normalizeLinkText(value)
        if c.type == "image":
            yield from _link_attributes(md, c.children or [])


def visible_text_blocks(body: str) -> list[dict]:
    """Every published text block of the body, each with the form it is read in.

    Same parse and section ranges as `_prose_sections`, which keeps only the anchorable prose:
    `anchorable` marks exactly those blocks (NFC, collapsed whitespace, case kept since units
    such as `mm`/`MPa` are case-sensitive), so an anchor can be located in its section.
    Everything else in the body is returned too, so that a value scan of the published text has
    nothing outside its reach. Forms (`form`):
    - `rendue`: as a CommonMark/HTML renderer shows it: prose, headings, code, HTML text with
      tags removed and entities decoded, image alt text in place;
    - `écrite`: as written in the file: inline and block HTML (tags, attributes, comments, also
      with entities decoded), link and image titles, link and image destinations (inline,
      reference or autolink: as written, and with URL escapes decoded), fence info strings, and
      every source line no block token covers (link reference definitions, used or not,
      repeated or nested);
    - `sans balisage`: each block's source read by a reader that ignores markup
      (`markup_blind_text`), so that `[25](x y) Nm` or ``25``Nm`` also read `25 Nm`.
    Blocks other than the anchorable prose are read up to Unicode compatibility, invisible
    characters removed (`_compat`). `origin` is the index of the anchorable block a block was
    derived from (the same source, read in another way: shown, with image alt text in place and
    `_compat`; or without markup), else None: an anchored excerpt is located in
    its block, then masked in its derived blocks too, where its text may read differently."""
    md = MarkdownIt("commonmark").enable("table")
    # Chaque destination de lien, d'image, d'autolien ou de définition, telle qu'écrite (échappements
    # Markdown résolus, échappements d'URL gardés) : l'analyseur la passe à `normalizeLink`.
    destinations: list[str] = []
    normalize_link = md.normalizeLink

    def recorded(url: str) -> str:
        destinations.append(url)
        return normalize_link(url)

    md.normalizeLink = recorded
    env: dict = {}
    tokens = md.parse(body, env)
    headings = [(i, int(t.tag[1:]), "#" * int(t.tag[1:]) + " " + tokens[i + 1].content.strip())
                for i, t in enumerate(tokens)
                if t.type == "heading_open" and t.level == 0]
    ranges = []
    for pos, (index, depth, label) in enumerate(headings):
        if depth in (2, 3):
            end = next((j for j, d, _ in headings[pos + 1:] if d <= depth), len(tokens))
            ranges.append((index + 3, end, label))

    blocks: list[dict] = []
    seen: set[tuple] = set()

    def add(j, text: str, form: str, anchorable: bool = False, origin=None):
        if not text.strip() or (j, form, text) in seen:
            return None
        seen.add((j, form, text))
        blocks.append({"text": text, "form": form, "anchorable": anchorable, "origin": origin,
                       "sections": {label for start, end, label in ranges
                                    if j is not None and start <= j < end}})
        return len(blocks) - 1

    def add_blind(j, source: str, origin=None):
        add(j, markup_blind_text(source), "sans balisage", origin=origin)

    for j, token in enumerate(tokens):
        if token.type == "inline":
            children = token.children or []
            hidden = any(c.type == "html_inline" for c in children)
            visible = "".join(c.content if c.type in ("text", "code_inline", "html_inline") else
                              " " if c.type in ("softbreak", "hardbreak") else ""
                              for c in children)
            k = add(j, " ".join(unicodedata.normalize("NFC", visible).split()), "rendue",
                    anchorable=tokens[j - 1].type != "heading_open" and not hidden)
            add(j, _compat(_shown_inline(children)), "rendue", origin=k)
            if hidden:
                add(j, _compat(visible), "écrite")
                add(j, _compat(html.unescape(visible)), "écrite")
            for value in _link_attributes(md, children):
                add(j, _compat(value), "écrite")
            add_blind(j, token.content, origin=k)
        elif token.type in ("fence", "code_block", "html_block"):
            if token.type == "html_block":
                add(j, _compat(token.content), "écrite")
                add(j, _compat(html.unescape(token.content)), "écrite")
                add(j, _compat(html.unescape(re.sub(r"<[^>]*>", "", token.content))), "rendue")
            else:
                add(j, _compat(token.content), "rendue")
                add(j, _compat(token.info), "écrite")
            add_blind(j, token.content)

    covered = {n for t in tokens if t.map and t.type in _LEAF_BLOCKS for n in range(*t.map)}
    # Lignes comptées comme l'analyseur les compte (`\r\n` et `\r` lus `\n`, et seulement eux) :
    # `splitlines` couperait aussi à U+2028, NEL ou saut de page, et décalerait chaque ligne suivante.
    lines = re.sub(r"\r\n?", "\n", body).split("\n")
    run: list[str] = []
    for n, line in enumerate([*lines, ""]):
        if n < len(lines) and n not in covered and line.strip():
            run.append(line)
            continue
        if run:
            source = "\n".join(run)
            add(None, _compat(source), "écrite")
            add(None, _compat(html.unescape(source)), "écrite")
            add_blind(None, source)
            run = []
    for ref in [*env.get("references", {}).values(), *env.get("duplicate_refs", [])]:
        if isinstance(ref.get("title"), str) and ref["title"]:
            add(None, _compat(ref["title"]), "écrite")
        if isinstance(ref.get("href"), str) and ref["href"]:
            add(None, _compat(md.normalizeLinkText(ref["href"])), "écrite")
    # Destination telle qu'écrite, quand elle ne se lit pas déjà ainsi (sans échappement d'URL)
    written = {b["text"] for b in blocks if b["form"] == "écrite"}
    for destination in destinations:
        if _compat(destination) not in written:
            add(None, _compat(destination), "écrite")
    return blocks


def check_fiche(md_path: Path, root: Path, catalog: set[str] | dict[str, dict], schema, *, require_source_proof: bool = False) -> dict:
    """Retourne {slug, status (PASS|WARN|FAIL), fails[], warns[]}."""
    if require_source_proof:
        if not isinstance(catalog, dict):
            raise ValueError("source proof requires the full source catalog")
        if schema is None or Draft202012Validator is None:
            raise RuntimeError("source proof schema validation unavailable")
        spec = importlib.util.spec_from_file_location(
            "_coverage_page_proof", Path(__file__).with_name("gen_coverage_map.py"))
        page_proof = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(page_proof)
    slug = md_path.stem
    fails: list[str] = []
    warns: list[str] = []
    fm, body = _split_md(md_path.read_text(encoding="utf-8"))
    sections = _prose_sections(body)
    h2 = {s for s in sections if s.startswith("## ")}
    valid_sections = set(sections)
    cov_path = root / "proposals" / "_coverage" / f"{slug}.coverage.yaml"

    if not cov_path.is_file():
        # Une fiche sans claim H2 (rare) n'a rien à couvrir ; sinon trou de structure.
        if h2:
            warns.append(
                f"coverage_map_absente: aucune {cov_path.relative_to(root)} "
                f"(la fiche a {len(h2)} sections H2 sourçables → dim A du score = 0)"
            )
        if require_source_proof:
            fails.append("proof_coverage_missing: no claim-to-source evidence available for promotion")
        status = "FAIL" if fails else ("WARN" if warns else "PASS")
        return {"slug": slug, "status": status, "fails": fails, "warns": warns,
                "coverage_entries": 0, "h2_sections": len(h2)}

    try:
        cov = yaml.safe_load(cov_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        fails.append(f"coverage_yaml_invalide: {e}")
        return {"slug": slug, "status": "FAIL", "fails": fails, "warns": warns,
                "coverage_entries": 0, "h2_sections": len(h2)}

    # 2. Schéma
    if schema is not None and Draft202012Validator is not None:
        for err in Draft202012Validator(schema).iter_errors(cov):
            loc = "/".join(str(p) for p in err.path) or "(racine)"
            fails.append(f"schema:{loc}: {err.message}")

    entries = cov.get("coverage_entries") or []

    if cov.get("fiche") and cov["fiche"] != slug:
        fails.append(f"fiche_mismatch: coverage.fiche='{cov['fiche']}' ≠ slug '{slug}'")

    if not entries and require_source_proof:
        fails.append("proof_coverage_empty: no claim-to-source evidence available for promotion")
    if not entries:
        warns.append("coverage_entries_vide: aucune preuve claim↔source (suspect, schéma §coverage_entries)")

    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            fails.append(f"entry[{i}]: entrée non-objet")
            continue
        # 3. FK strict source-catalog
        sslug = e.get("source_slug")
        if sslug and sslug not in catalog:
            fails.append(f"entry[{i}].source_slug='{sslug}' absent de _meta/source-catalog.yaml (FK, ADR-089 §3)")
        if require_source_proof:
            reasons = []
            if e.get("source_status") not in {"captured", "verified"}:
                reasons.append("source_pending")
            source = catalog.get(sslug) or {}
            if source.get("status") != "active" or not page_proof.is_page_proven(source):
                reasons.append("page_not_archived")
            raw_ref = source.get("raw_ref") or {}
            digest = raw_ref.get("expected_sha256")
            if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
                reasons.append("archive_hash_missing_or_invalid")
            anchor = e.get("text_anchor")
            if not isinstance(anchor, str) or not _normalize_anchor(anchor):
                reasons.append("claim_anchor_missing")
            if reasons:
                fails.append(
                    f"proof_unavailable:claim_id={e.get('claim_id')}:source_slug={sslug}:"
                    + ",".join(reasons))
        # 4. Ancrage section ↔ H2 réel
        sec = e.get("section")
        if sec and sec not in valid_sections:
            fails.append(f"entry[{i}].section='{sec}' ne correspond à aucun H2/H3 de la fiche")
        elif sec and len(sections[sec]) != 1:
            fails.append(f"entry[{i}].section='{sec}' ambiguë: titre répété")
        elif "text_anchor" in e and sec in sections:
            anchor = e["text_anchor"]
            normalized = _normalize_anchor(anchor) if isinstance(anchor, str) else ""
            if not normalized or not any(normalized in block for block in sections[sec][0]):
                fails.append(
                    f"entry[{i}].text_anchor absent de la prose de '{sec}' "
                    f"(claim_id={e.get('claim_id')})"
                )

    status = "FAIL" if fails else ("WARN" if warns else "PASS")
    return {"slug": slug, "status": status, "fails": fails, "warns": warns,
            "coverage_entries": len(entries), "h2_sections": len(h2)}


def collect_targets(args, root: Path) -> list[Path]:
    if args.all:
        return sorted(p for p in (root / "proposals").glob("*.md") if not p.name.startswith("_"))
    out = []
    for f in args.files:
        p = Path(f)
        if not p.is_absolute():
            p = root / f
        out.append(p)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Validateur coverage-map (ADR-089, report-only par défaut).")
    ap.add_argument("files", nargs="*", help="proposals/<slug>.md à vérifier")
    ap.add_argument("--all", action="store_true", help="scanner toutes les proposals/*.md")
    ap.add_argument("--wiki-root", default=None, help="racine repo wiki (auto-détectée sinon)")
    ap.add_argument("--strict", action="store_true",
                    help="ENFORCEMENT : exit 1 si FAIL (gelé jusqu'à ratification ADR-089).")
    ap.add_argument("--warn-as-fail", action="store_true", help="traiter les WARN comme des FAIL (--strict).")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    args = ap.parse_args()

    if not args.all and not args.files:
        ap.error("préciser --all ou des fichiers")

    root = Path(args.wiki_root).resolve() if args.wiki_root else _repo_root(Path(args.files[0]) if args.files else Path.cwd())
    if not (root / "_meta" / "source-catalog.yaml").is_file():
        print(f"ERREUR: racine wiki introuvable depuis {root}", file=sys.stderr)
        return 2

    catalog = _load_catalog_slugs(root)
    schema = _load_schema(root)
    if schema is None or Draft202012Validator is None:
        print("WARN: schéma coverage-map ou jsonschema absent — validation schéma désactivée (dégradé, non silencieux)",
              file=sys.stderr)

    results = [check_fiche(p, root, catalog, schema) for p in collect_targets(args, root) if p.is_file()]

    n_pass = sum(1 for r in results if r["status"] == "PASS")
    n_warn = sum(1 for r in results if r["status"] == "WARN")
    n_fail = sum(1 for r in results if r["status"] == "FAIL")

    if args.format == "json":
        print(json.dumps({"pass": n_pass, "warn": n_warn, "fail": n_fail, "results": results},
                         ensure_ascii=False, indent=2))
    else:
        for r in results:
            for f in r["fails"]:
                print(f"FAIL {r['slug']}: {f}")
            for w in r["warns"]:
                print(f"WARN {r['slug']}: {w}")
            if r["status"] == "PASS":
                print(f"PASS {r['slug']} ({r['coverage_entries']} entries / {r['h2_sections']} H2)")
        print(f"\n{n_pass} PASS — {n_fail} FAIL — {n_warn} WARN  (report-only ; enforcement gelé jusqu'à ADR-089)")

    enforce = args.strict or args.warn_as_fail
    if enforce and (n_fail or (args.warn_as_fail and n_warn)):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
