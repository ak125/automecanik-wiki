"""Tests for _scripts/check-coverage-map.py (validateur coverage-map, ADR-089).

Construit une mini-arbo wiki en tmp_path et exerce les 4 vérifications :
PASS (coverage valide), WARN (coverage absente mais H2 présents),
FAIL FK (source_slug hors source-catalog), FAIL anchor (section ∉ H2 de la fiche).
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
import yaml

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = SCRIPTS_DIR.parent

spec = importlib.util.spec_from_file_location("check_coverage_map", SCRIPTS_DIR / "check-coverage-map.py")
ccm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ccm)


def _make_wiki(tmp_path: Path, *, catalog_slugs, fiche_body, coverage=None) -> Path:
    (tmp_path / "_meta" / "schema").mkdir(parents=True)
    (tmp_path / "proposals" / "_coverage").mkdir(parents=True)
    # source-catalog
    cat = {"sources": [{"slug": s} for s in catalog_slugs]}
    (tmp_path / "_meta" / "source-catalog.yaml").write_text(yaml.safe_dump(cat), encoding="utf-8")
    # real schema (copied from repo so the test exercises the canonical contract)
    schema_src = REPO_ROOT / "_meta" / "schema" / "coverage-map.schema.json"
    (tmp_path / "_meta" / "schema" / "coverage-map.schema.json").write_text(
        schema_src.read_text(encoding="utf-8"), encoding="utf-8")
    # fiche
    (tmp_path / "proposals" / "demo.md").write_text(
        "---\nslug: demo\n---\n" + fiche_body, encoding="utf-8")
    if coverage is not None:
        (tmp_path / "proposals" / "_coverage" / "demo.coverage.yaml").write_text(
            yaml.safe_dump(coverage), encoding="utf-8")
    return tmp_path


def _check(root: Path):
    catalog = ccm._load_catalog_slugs(root)
    schema = ccm._load_schema(root)
    return ccm.check_fiche(root / "proposals" / "demo.md", root, catalog, schema)


def _valid_entry(section="## Fonctionnement", slug="oem_x"):
    return {
        "claim_id": "demo-claim-un", "section": section, "source_slug": slug,
        "evidence_type": "oem_workshop_excerpt", "confidence": "high",
        "source_policy": "1_high", "source_status": "captured",
    }


def test_pass_valid_coverage(tmp_path):
    root = _make_wiki(
        tmp_path, catalog_slugs=["oem_x"],
        fiche_body="## Fonctionnement\ntexte\n",
        coverage={"fiche": "demo", "schema_version": "1.0.0", "coverage_entries": [_valid_entry()]},
    )
    r = _check(root)
    assert r["status"] == "PASS", r["fails"] + r["warns"]


def test_warn_when_coverage_absent_but_h2_present(tmp_path):
    root = _make_wiki(tmp_path, catalog_slugs=["oem_x"], fiche_body="## Fonctionnement\ntexte\n", coverage=None)
    r = _check(root)
    assert r["status"] == "WARN"
    assert any("coverage_map_absente" in w for w in r["warns"])


def test_fail_fk_unknown_source_slug(tmp_path):
    root = _make_wiki(
        tmp_path, catalog_slugs=["oem_x"],
        fiche_body="## Fonctionnement\ntexte\n",
        coverage={"fiche": "demo", "schema_version": "1.0.0",
                  "coverage_entries": [_valid_entry(slug="slug_inconnu")]},
    )
    r = _check(root)
    assert r["status"] == "FAIL"
    assert any("source-catalog" in f for f in r["fails"])


def test_fail_section_anchor_not_in_fiche(tmp_path):
    root = _make_wiki(
        tmp_path, catalog_slugs=["oem_x"],
        fiche_body="## Fonctionnement\ntexte\n",
        coverage={"fiche": "demo", "schema_version": "1.0.0",
                  "coverage_entries": [_valid_entry(section="## Section Fantome")]},
    )
    r = _check(root)
    assert r["status"] == "FAIL"
    assert any("H2" in f for f in r["fails"])


def test_pass_h3_section_anchor(tmp_path):
    # Un claim peut s'ancrer sur une sous-section H3 réelle (ex. version sous entretien).
    root = _make_wiki(
        tmp_path, catalog_slugs=["oem_x"],
        fiche_body="## Particularités d'entretien\ntexte\n### Spécificités par version\ndétail\n",
        coverage={"fiche": "demo", "schema_version": "1.0.0",
                  "coverage_entries": [_valid_entry(section="### Spécificités par version")]},
    )
    r = _check(root)
    assert r["status"] == "PASS", r["fails"] + r["warns"]


def test_fail_h4_section_anchor_is_item_level(tmp_path):
    # H4 = niveau-item, volontairement hors ancrage : ancrer au H2/H3 parent.
    root = _make_wiki(
        tmp_path, catalog_slugs=["oem_x"],
        fiche_body="## Motorisations\ntexte\n#### Ford Focus RS Mk3\ndétail\n",
        coverage={"fiche": "demo", "schema_version": "1.0.0",
                  "coverage_entries": [_valid_entry(section="#### Ford Focus RS Mk3")]},
    )
    r = _check(root)
    assert r["status"] == "FAIL"
    assert any("H2/H3" in f for f in r["fails"])


def test_strict_exit_code_via_cli(tmp_path, monkeypatch, capsys):
    root = _make_wiki(
        tmp_path, catalog_slugs=["oem_x"],
        fiche_body="## Fonctionnement\ntexte\n",
        coverage={"fiche": "demo", "schema_version": "1.0.0",
                  "coverage_entries": [_valid_entry(slug="slug_inconnu")]},
    )
    monkeypatch.setattr("sys.argv", ["check-coverage-map.py", "--all", "--wiki-root", str(root), "--strict"])
    assert ccm.main() == 1  # FAIL → enforcement exit 1
    monkeypatch.setattr("sys.argv", ["check-coverage-map.py", "--all", "--wiki-root", str(root)])
    assert ccm.main() == 0  # report-only → exit 0 malgré le FAIL


@pytest.mark.parametrize("body,anchor,section,expected", [
    ("## Fonctionnement\nLe **filtre** retient les particules.\n", "Le filtre retient les particules.", "## Fonctionnement", "PASS"),
    ("## Fonctionnement\nLe filtre\nretient les particules.\n", "Le filtre retient les particules.", "## Fonctionnement", "PASS"),
    ("## Fonctionnement\nMédia prévu.\n", "Me\u0301dia prévu.", "## Fonctionnement", "PASS"),
    ("## Fonctionnement\nAutre texte.\n## FAQ\nAffirmation ailleurs.\n", "Affirmation ailleurs.", "## Fonctionnement", "FAIL"),
    ("## Fonctionnement\nAncienne phrase modifiée.\n", "Affirmation supprimée.", "## Fonctionnement", "FAIL"),
    ("## Fonctionnement\ntexte\n### Enfant\nAffirmation enfant.\n", "Affirmation enfant.", "## Fonctionnement", "PASS"),
    ("## Fonctionnement\n### Enfant\ntexte\n### Voisin\nAffirmation ailleurs.\n", "Affirmation ailleurs.", "### Enfant", "FAIL"),
    ("## Fonctionnement\nLe filtre retient\n\nles particules.\n", "Le filtre retient les particules.", "## Fonctionnement", "FAIL"),
    ("## Fonctionnement\n<!-- Affirmation cachee. -->\n", "Affirmation cachee.", "## Fonctionnement", "FAIL"),
    ("## Fonctionnement\n```\nAffirmation exemple.\n```\n", "Affirmation exemple.", "## Fonctionnement", "FAIL"),
    ("```\n## Fonctionnement\nAffirmation exemple.\n```\n", "Affirmation exemple.", "## Fonctionnement", "FAIL"),
    ("## Fonctionnement\n[Source](https://example.test/affirmation-inventee)\n", "affirmation-inventee", "## Fonctionnement", "FAIL"),
    ("## Fonctionnement\ntexte\n## Fonctionnement\nAffirmation ambigue.\n", "Affirmation ambigue.", "## Fonctionnement", "FAIL"),
    ("## Fonctionnement\nLe filtre ne convient pas.\n", "Le filtre convient.", "## Fonctionnement", "FAIL"),
    ("## Fonctionnement\nValeur 40 bar.\n", "Valeur 4 bar.", "## Fonctionnement", "FAIL"),
    ("## Fonctionnement\ntexte\n", "   ", "## Fonctionnement", "FAIL"),
])
def test_text_anchor_is_present_in_its_real_section(tmp_path, body, anchor, section, expected):
    entry = {**_valid_entry(section=section), "text_anchor": anchor}
    root = _make_wiki(tmp_path, catalog_slugs=["oem_x"], fiche_body=body,
                      coverage={"fiche": "demo", "schema_version": "1.0.0", "coverage_entries": [entry]})
    result = _check(root)
    assert result["status"] == expected, result
    if expected == "FAIL":
        assert any("text_anchor" in f or "section" in f for f in result["fails"]), result


def test_missing_optional_anchor_keeps_schema_contract(tmp_path):
    root = _make_wiki(tmp_path, catalog_slugs=["oem_x"], fiche_body="## Fonctionnement\ntexte\n",
                      coverage={"fiche": "demo", "schema_version": "1.0.0", "coverage_entries": [_valid_entry()]})
    assert _check(root)["status"] == "PASS"


def _anchorable_by_section(body: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for block in ccm.visible_text_blocks(body):
        if block["anchorable"]:
            for label in block["sections"]:
                out.setdefault(label, []).append(ccm._normalize_anchor(block["text"]))
    return out


_PARITY_BODIES = [p.read_text(encoding="utf-8") for d in ("proposals", "wiki")
                  for p in sorted((REPO_ROOT / d).rglob("*.md"))]


@pytest.mark.parametrize("body", [
    "## A\nLe **filtre** retient.\n### B\nEnfant.\n## A\nRépété.\n",
    "## A\n<!-- caché -->\n```\ncode\n```\n| x | y |\n|---|---|\n| 1 | 2 |\n",
    "intro\n## A\n- item <b>html</b>\n- item simple\n> cité\n",
    "## A\nTexte <b>70</b> Nm.\n\n<div>\n<b>40</b>&nbsp;Nm\n</div>\n\nSuite.\n",
    *[ccm._split_md(text)[1] for text in _PARITY_BODIES],
])
def test_visible_blocks_mark_exactly_the_anchorable_prose(body):
    # Le décideur localise une ancre via visible_text_blocks ; check_fiche la prouve via
    # _prose_sections. Les deux doivent voir la même prose, sinon la preuve et le scan divergent.
    expected = {label: [b for occurrence in occurrences for b in occurrence]
                for label, occurrences in ccm._prose_sections(body).items()}
    expected = {label: blocks for label, blocks in expected.items() if blocks}
    assert _anchorable_by_section(body) == expected


def test_visible_blocks_reach_text_that_is_not_anchorable_prose():
    body = ("## Couple 120 Nm\n<!-- 90 Nm -->\n```\n80 Nm\n```\n"
            "Texte <span>70 Nm</span>.\n\n![schéma 60 Nm](x.png)\n\n    50 Nm\n")
    texts = " | ".join(b["text"] for b in ccm.visible_text_blocks(body))
    for value in ("120 Nm", "90 Nm", "80 Nm", "70 Nm", "60 Nm", "50 Nm"):
        assert value in texts, texts
    assert not any(b["anchorable"] for b in ccm.visible_text_blocks(body)
                   if any(v in b["text"] for v in ("120 Nm", "90 Nm", "80 Nm", "70 Nm", "60 Nm", "50 Nm")))


@pytest.mark.parametrize("body, shown", [
    ("Texte <b>70</b> Nm.\n", "Texte 70 Nm."),
    ("<div>\n<b>40</b>&nbsp;Nm\n</div>\n", "40 Nm"),
    ("<p>2,5&#8239;bar</p>\n", "2,5 bar"),
])
def test_visible_blocks_read_html_as_a_renderer_shows_it(body, shown):
    # Un renderer HTML retire les balises et décode les entités : `<b>70</b> Nm` s'affiche
    # « 70 Nm », valeur qu'aucune lecture du texte tel qu'écrit ne voit entière.
    blocks = ccm.visible_text_blocks(body)
    assert ("rendue", shown) in [(b["form"], b["text"]) for b in blocks], blocks
    assert not any(b["anchorable"] for b in blocks)


@pytest.mark.parametrize("body, form, text", [
    # HTML brut, en bloc ou en ligne : tel qu'écrit, entités décodées ou non.
    ('<div title="25&#32;mm">x</div>\n', "écrite", '<div title="25&#32;mm">x</div>'),
    ('<div title="25&#32;mm">x</div>\n', "écrite", '<div title="25 mm">x</div>'),
    ('Jeu <b title="25&#32;mm">x</b>.\n', "écrite", 'Jeu <b title="25&#32;mm">x</b>.'),
    ('Jeu <b title="25&#32;mm">x</b>.\n', "écrite", 'Jeu <b title="25 mm">x</b>.'),
    # Code : affiché tel quel ; info du bloc, écrite.
    ("```\n25 \u339c\n```\n", "rendue", "25 mm"),
    ("```25mm\nx\n```\n", "écrite", "25mm"),
    # Liens et images : titre, destination aux échappements décodés, image du texte alternatif.
    ('Voir [x](https://e.x "25 mm").\n', "écrite", "25 mm"),
    ("Voir [x](https://e.x/25%20mm).\n", "écrite", "https://e.x/25 mm"),
    ("![x](img/25%20mm.png)\n", "écrite", "img/25 mm.png"),
    ("![![y](b/25%20mm.png)](a.png)\n", "écrite", "b/25 mm.png"),
    # … et telle qu'écrite, échappements d'URL gardés (lien, image, autolien, définition).
    ("Voir [x](<https://e.x/tarage :%45 bar>).\n", "écrite", "https://e.x/tarage :%45 bar"),
    ("![x](img/25%20mm.png)\n", "écrite", "img/25%20mm.png"),
    ("Voir <https://e.x/25%20mm>.\n", "écrite", "https://e.x/25%20mm"),
    ("[r]: <https://e.x/%45 bar>\n", "écrite", "https://e.x/%45 bar"),
    # Texte affiché : texte alternatif d'image (entités comprises), code, retour à la ligne.
    ("Jeu ![25&#32;mm](x.png).\n", "rendue", "Jeu 25 mm."),
    ("Jeu <b>x</b> `25` mm.\n", "rendue", "Jeu x 25 mm."),
    ("Jeu <b>x</b> 25\nmm.\n", "rendue", "Jeu x 25 mm."),
    # Définition de référence : ligne sans jeton, titre et destination, définition répétée comprise.
    ('[r]: https://e.x/25&#32;mm "t"\n', "écrite", '[r]: https://e.x/25&#32;mm "t"'),
    ('[r]: https://e.x/25&#32;mm "t"\n', "écrite", '[r]: https://e.x/25 mm "t"'),
    ('[r]: https://e.x/25&#32;mm "t"\n', "sans balisage", 'r: https://e.x/25 mm "t"'),
    ('[r]: https://e.x/25&#32;mm "t"\n', "écrite", "https://e.x/25 mm"),
    ('[r]: /a\n[r]: /25%20mm "25 Nm"\n', "écrite", "25 Nm"),
    ('[r]: /a\n[r]: /25%20mm "25 Nm"\n', "écrite", "/25 mm"),
    # Définition imbriquée dans une citation ou une liste : son conteneur n'a pas de jeton pour elle.
    ("> [jeu 25 mm]: https://e.x/n\n", "écrite", "> [jeu 25 mm]: https://e.x/n"),
    ("- [jeu 25 mm]: https://e.x/n\n", "sans balisage", "- jeu 25 mm: https://e.x/n"),
    # Sans balisage : entités, balises, commentaires, caractères de balisage, liens imbriqués.
    ("```\n25&#32;mm\n```\n", "sans balisage", "25 mm"),
    ("```\n25 <b>mm</b>\n```\n", "sans balisage", "25 mm"),
    ("```\n25<!-- x --> mm\n```\n", "sans balisage", "25 mm"),
    ("```\n25 *mm*\n```\n", "sans balisage", "25 mm"),
    ("Serrer à 25\\Nm.\n", "sans balisage", "Serrer à 25Nm."),
    ("Jeu de 25~mm.\n", "sans balisage", "Jeu de 25mm."),
    ("Jeu ![[25](a) mm](b).\n", "sans balisage", "Jeu 25 mm."),
    # Caractère de format (trait d'union conditionnel) retiré.
    ("```\n25\u00admm\n```\n", "rendue", "25mm"),
    # Hors prose ancrable : lu à la compatibilité près, invisibles retirés, exposant replié sauf
    # celui de l'unité `mm²`.
    ("Jeu de 2,5 \u339f et 3 \u33a5.\n", "rendue", "Jeu de 2,5 mm² et 3 m3."),
    ("Jeu de 2,5 \u339f et 3 \u33a5.\n", "sans balisage", "Jeu de 2,5 mm² et 3 m3."),
    ("Jeu de 25\u034fmm.\n", "rendue", "Jeu de 25mm."),
    # `$` et commande TeX : aucune lecture en formule, lus sans balisage tels qu'écrits.
    ("Serrer à $120\\Nm$.\n", "sans balisage", "Serrer à $120Nm$."),
    ("Kit à 30 $ ; serrage 120\\Nm ; main-d'œuvre 50 $.\n", "sans balisage",
     "Kit à 30 $ ; serrage 120Nm ; main-d'œuvre 50 $."),
    ("```math\n120\\Nm\n```\n", "sans balisage", "120Nm"),
])
def test_visible_blocks_read_each_construct_in_its_form(body, form, text):
    # Chaque construction est lue sous la forme que la docstring lui donne : le texte seul ne
    # suffit pas, une autre forme le retrouverait souvent.
    blocks = ccm.visible_text_blocks(body)
    assert (form, text) in [(b["form"], b["text"]) for b in blocks], blocks


@pytest.mark.parametrize("separator", ["\u2028", "\u0085", "\u000c", "\u2029", "\x1c"])
def test_visible_blocks_count_lines_as_the_parser_does(separator):
    # Un séparateur que l'analyseur ne compte pas comme une fin de ligne ne décale pas les lignes
    # lues telles qu'écrites : la définition de note reste lue, pas le paragraphe qui la suit.
    body = f"## Montage\n\nVoir{separator}la note[^1].\n\n[^1]: 25**Nm**\nTexte suivant.\n"
    blocks = ccm.visible_text_blocks(body)
    assert ("sans balisage", "^1: 25Nm") in [(b["form"], b["text"]) for b in blocks], blocks


def test_visible_blocks_read_plain_prose_once_per_form():
    # Une prose sans balisage : une fois rendue (ancrable), une fois sans balisage ; ses lignes
    # sont couvertes par leur jeton et ne sont pas relues telles qu'écrites.
    blocks = ccm.visible_text_blocks("Jeu de 25 mm.\n")
    assert [(b["form"], b["text"], b["anchorable"], b["origin"]) for b in blocks] == [
        ("rendue", "Jeu de 25 mm.", True, None), ("sans balisage", "Jeu de 25 mm.", False, 0)]


@pytest.mark.parametrize("text, read", [
    ("2,5 \u339f", "2,5 mm²"),           # ㎟ : décomposé, l'exposant de l'unité gardé
    ("2,5 mm\u00b2", "2,5 mm²"),
    ("x\u00b2 H\u2082O 25\u00b9", "x2 H2O 251"),  # tout autre exposant ou indice : replié, comme NFKC
    ("1,2\u00b710\u00b2 Nm", "1,2·102 Nm"),
    ("\u00b2\u2078 mm", "28 mm"),
    ("\u2081\u2082\u2080 Nm", "120 Nm"),
    ("120 \u1d3a\u1d50", "120 Nm"),
    ("mm\u00b2\u2075", "mm25"),         # ² suivi d'un exposant : un nombre, pas l'unité
    ("mm\N{SUPERSCRIPT TWO}\N{SUBSCRIPT FIVE}", "mm25"),   # … ou d'un indice
    ("3 \u33a5", "3 m3"),
    ("120 \u2103", "120 °C"),
    ("\uff12\uff15 \uff4d\uff4d", "25 mm"),
    ("25\u200b\u034f\u3164mm", "25mm"),  # invisibles retirés, dans et hors Cf
    ("e\u0301  25", "é 25"),              # composé (NFC), espaces réduits
])
def test_compat_reads_like_nfkc_but_keeps_the_square_of_mm(text, read):
    assert ccm._compat(text) == read


def test_compat_char_is_nfkc_except_through_superscripts_and_subscripts():
    # Exhaustif : la décomposition de `_compat_char` est celle de NFKC pour tout point de code,
    # sauf quand elle passe par un exposant ou un indice, gardé tel quel.
    import unicodedata

    def through_super_or_sub(ch):
        decomposition = unicodedata.decomposition(ch)
        return decomposition.startswith(("<super>", "<sub>")) or any(
            through_super_or_sub(chr(int(cp, 16))) for cp in decomposition.split() if not cp.startswith("<"))

    differ = [cp for cp in range(0x110000) if not 0xD800 <= cp <= 0xDFFF
              and unicodedata.normalize("NFC", ccm._compat_char(chr(cp))) != unicodedata.normalize("NFKC", chr(cp))]
    assert differ and all(through_super_or_sub(chr(cp)) for cp in differ)


def test_compat_of_each_character_is_nfkc_except_the_square_of_mm_and_blank_glyphs():
    # Exhaustif : `_compat` lit chaque point de code comme NFKC (invisibles retirés, espaces
    # réduits), sauf ㎟, seul dont la lecture produit l'unité `mm²`, et les glyphes vides, lus
    # comme un espace.
    import unicodedata

    def nfkc(text):
        return " ".join("".join(c for c in unicodedata.normalize("NFKC", text) if not ccm.invisible(c)).split())

    differ = [cp for cp in range(0x110000) if not 0xD800 <= cp <= 0xDFFF
              and ccm._compat(chr(cp)) != nfkc(chr(cp))]
    # Attendu écrit en dur : une constante sous test ne fait pas son propre oracle.
    assert differ == [0x2800, 0x339F, 0x13441, 0x13442, 0x16FE4, 0x1D159]


def test_invisible_is_format_or_default_ignorable():
    # Exhaustif, oracle indépendant du code : catégorie Cf, plus Default_Ignorable_Code_Point
    # recopié de DerivedCoreProperties.txt (Unicode).
    import unicodedata

    ignorable = ((0x00AD, 0x00AD), (0x034F, 0x034F), (0x061C, 0x061C), (0x115F, 0x1160),
                 (0x17B4, 0x17B5), (0x180B, 0x180D), (0x180E, 0x180E), (0x180F, 0x180F),
                 (0x200B, 0x200F), (0x202A, 0x202E), (0x2060, 0x2064), (0x2065, 0x2065),
                 (0x2066, 0x206F), (0x3164, 0x3164), (0xFE00, 0xFE0F), (0xFEFF, 0xFEFF),
                 (0xFFA0, 0xFFA0), (0xFFF0, 0xFFF8), (0x1BCA0, 0x1BCA3), (0x1D173, 0x1D17A),
                 (0xE0000, 0xE0000), (0xE0001, 0xE0001), (0xE0002, 0xE001F), (0xE0020, 0xE007F),
                 (0xE0080, 0xE00FF), (0xE0100, 0xE01EF), (0xE01F0, 0xE0FFF))
    points = [cp for cp in range(0x110000) if not 0xD800 <= cp <= 0xDFFF]
    expected = [cp for cp in points if unicodedata.category(chr(cp)) == "Cf"
                or any(lo <= cp <= hi for lo, hi in ignorable)]
    assert [cp for cp in points if ccm.invisible(chr(cp))] == expected
    # Cf hors de toute plage ignorable : retiré lui aussi
    assert ccm._compat("25\ufffbNm") == ccm._compat("25\U000110bdNm") == "25Nm"


@pytest.mark.parametrize("name", ["BRAILLE PATTERN BLANK", "EGYPTIAN HIEROGLYPH FULL BLANK",
                                  "EGYPTIAN HIEROGLYPH HALF BLANK", "KHITAN SMALL SCRIPT FILLER",
                                  "MUSICAL SYMBOL NULL NOTEHEAD"])
def test_compat_reads_a_blank_glyph_as_a_space(name):
    # Dessiné sans encre, il sépare le nombre de son unité comme un espace.
    import unicodedata

    ch = unicodedata.lookup(name)
    assert ccm._compat(f"25{ch}Nm") == "25 Nm"
    assert unicodedata.category(ch) != "Zs" and not ccm.invisible(ch)


def test_visible_blocks_read_a_table_by_its_cells():
    # Un tableau est un bloc feuille : chaque cellule est lue rendue (ancrable) et sans balisage,
    # ses lignes source ne sont pas relues telles qu'écrites (une valeur ancrée y resterait).
    blocks = ccm.visible_text_blocks("| Pièce | Jeu |\n| --- | --- |\n| Étrier | 25 mm |\n")
    assert [(b["form"], b["text"], b["anchorable"]) for b in blocks] == [
        (form, cell, form == "rendue") for cell in ("Pièce", "Jeu", "Étrier", "25 mm")
        for form in ("rendue", "sans balisage")]


def test_form_text_reads_an_excerpt_like_its_derived_block():
    # Un extrait ancré est masqué dans les blocs dérivés sous leur forme : sans balisage, le
    # caractère `_` d'une référence disparaît comme dans le bloc.
    assert ccm.form_text("Jeu de 25 mm (cote_A)", "sans balisage") == "Jeu de 25 mm (coteA)"
    assert ccm.form_text("Jeu de 25\u00a0mm (cote_A)", "rendue") == "Jeu de 25 mm (cote_A)"
