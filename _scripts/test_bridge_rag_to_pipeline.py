"""
Tests bridge_rag_to_pipeline — garde-fous ultra-minimal adapter.

Conformément à ADR-059 Phase B PR-3b : le bridge n'a aucune logique
d'extraction propre. Les tests vérifient :
- mapping category → entity_type canon ADR-031
- garde-fou : aucun import LLM / DB dans le bridge
- garde-fou : aucune extraction parallèle (subprocess invocation only)
- parsing frontmatter rag correct
- conversion markdown → HTML synthétique préserve le contenu littéral
"""
from __future__ import annotations

from pathlib import Path

import pytest

from bridge_rag_to_pipeline import (
    CATEGORY_TO_ENTITY_TYPE,
    _category_from_path_or_frontmatter,
    _markdown_body_to_synthetic_html,
    _parse_rag_frontmatter,
)


SCRIPT_PATH = Path(__file__).parent / "bridge_rag_to_pipeline.py"


def test_category_mapping_canonical_singular() -> None:
    """CATEGORY_TO_ENTITY_TYPE doit produire les 5 entity_types canon."""
    assert CATEGORY_TO_ENTITY_TYPE["gammes"] == "gamme"
    assert CATEGORY_TO_ENTITY_TYPE["vehicles"] == "vehicle"
    assert CATEGORY_TO_ENTITY_TYPE["constructeurs"] == "constructeur"
    assert CATEGORY_TO_ENTITY_TYPE["diagnostic"] == "diagnostic"
    canon = set(CATEGORY_TO_ENTITY_TYPE.values())
    assert canon == {"gamme", "vehicle", "constructeur", "support", "diagnostic"}


def test_no_llm_inference_imports() -> None:
    """Garde-fou statique : aucun import LLM dans le bridge."""
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    forbidden = ["anthropic", "openai", "groq", "cohere", "mistralai", "google.generativeai"]
    for needle in forbidden:
        assert needle not in text, f"LLM SDK '{needle}' must not appear in bridge"


def test_no_db_imports() -> None:
    """Garde-fou statique : aucun import DB dans le bridge."""
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    forbidden_db = ["psycopg", "asyncpg", "supabase", "sqlalchemy", "django"]
    for needle in forbidden_db:
        assert needle not in text, f"DB SDK '{needle}' must not appear in bridge"


def test_no_parallel_extraction_logic() -> None:
    """
    Garde-fou architectural : le bridge ne ré-implémente PAS Readability,
    Trafilatura, JSON-LD direct lift, ou DOM selectors. Il invoque le
    pipeline PR-3a via subprocess uniquement.
    """
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    # The bridge MUST NOT import these extraction tools — only the PR-3a pipeline does.
    parallel_extractors = ["from readability", "import readability", "import trafilatura"]
    for needle in parallel_extractors:
        assert needle not in text, (
            f"parallel extractor '{needle}' detected in bridge — "
            "PR-3b must delegate ALL extraction to PR-3a via subprocess"
        )
    # The bridge MUST invoke pipeline via subprocess
    assert "subprocess" in text, "bridge must use subprocess to invoke PR-3a pipeline"
    assert "scripts.wiki_promotion" in text, (
        "bridge must invoke PR-3a as 'scripts.wiki_promotion.<module>'"
    )


def test_no_direct_wiki_canon_write() -> None:
    """
    Garde-fou architectural : le bridge ne touche JAMAIS wiki/<entity_type>/.
    Toute l'écriture passe par render_proposal qui a son propre garde-fou.
    """
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    # No direct write paths to wiki canon directories
    forbidden_paths = [
        'wiki_root / "wiki" /',
        '"wiki/gamme"',
        '"wiki/vehicle"',
        '"wiki/constructeur"',
        '"wiki/support"',
        '"wiki/diagnostic"',
    ]
    for needle in forbidden_paths:
        assert needle not in text, (
            f"bridge must NOT write into wiki canon path '{needle}'. "
            "Use render_proposal (subprocess) which writes to proposals/ only."
        )


def test_parse_rag_frontmatter(tmp_path: Path) -> None:
    sample = tmp_path / "x.md"
    sample.write_text(
        "---\n"
        "slug: test-slug\n"
        "title: Test Title\n"
        "category: gammes\n"
        "---\n"
        "body content here\n"
    )
    fm, body = _parse_rag_frontmatter(sample)
    assert fm["slug"] == "test-slug"
    assert fm["title"] == "Test Title"
    assert fm["category"] == "gammes"
    assert "body content here" in body


def test_category_from_frontmatter(tmp_path: Path) -> None:
    sample = tmp_path / "gammes" / "x.md"
    sample.parent.mkdir()
    sample.touch()
    assert _category_from_path_or_frontmatter(sample, {"category": "gammes"}) == "gammes"


def test_category_from_path_fallback(tmp_path: Path) -> None:
    """Si frontmatter category absent, fallback sur le nom du dossier."""
    sample = tmp_path / "vehicles" / "y.md"
    sample.parent.mkdir()
    sample.touch()
    assert _category_from_path_or_frontmatter(sample, {}) == "vehicles"


def test_unknown_category_raises(tmp_path: Path) -> None:
    sample = tmp_path / "unknown-cat" / "z.md"
    sample.parent.mkdir()
    sample.touch()
    import click

    with pytest.raises(click.ClickException, match="unable to determine rag category"):
        _category_from_path_or_frontmatter(sample, {})


def test_synthetic_html_preserves_body_literal() -> None:
    body = "## Section\n\nContent with <html> chars & special."
    html = _markdown_body_to_synthetic_html("Title", body, Path("/tmp/x.md"))
    # Body must appear escaped (verbatim) inside the synthetic wrap
    assert "## Section" in html
    assert "Content with &lt;html&gt; chars &amp; special." in html
    assert "<h1>Title</h1>" in html
    assert "<article><pre>" in html


def test_synthetic_html_minimal_no_markdown_lib_dependency() -> None:
    """
    Le bridge ne dépend PAS d'une lib markdown→HTML. Il wrappe le body en
    <pre> brut. C'est intentionnel : pas de logique d'extraction parallèle.
    """
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "import markdown" not in text
    assert "from markdown" not in text
    assert "import mistune" not in text
    assert "from mistune" not in text
