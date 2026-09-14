"""Shared gamme authoring titles and explicit structural scoring aliases.

An alias counts a section's structure, never the truth or coverage of its facts.
Each heading belongs to at most one scoring criterion.
"""

# Preserve the authoring order and exact emitted titles (ADR-086 section keys).
SECTION_SPEC: dict[str, tuple[str, str]] = {
    "function": ("## Rôle technique", "function"),
    "failure_symptoms": ("## Symptômes & diagnostic", "failure_symptoms"),
    "maintenance_interval": ("## Entretien & bonnes pratiques", "maintenance_interval"),
    "variants": ("## Compatibilité & versions", "variants"),
    "selection_criteria": ("## Critères de choix selon le véhicule", "selection_criteria"),
    "quality_tiers": ("## Marques & qualité", "quality_tiers"),
    "standards_norms": ("## Normes & conformité", "standards_norms"),
    "replacement_guidance": ("## Montage & erreurs fréquentes", "replacement_guidance"),
    "faq": ("## FAQ", "faq"),
}

# The five legacy criteria and their weights remain unchanged. In particular,
# "function" is NOT also a definition, and optional roles create no extra points.
GAMME_SCORING_ALIASES = {
    "Fonctionnement": (SECTION_SPEC["function"][0][3:], "Fonction"),
    "Symptômes d'usure": (
        SECTION_SPEC["failure_symptoms"][0][3:],
        "Symptômes système auxquels cette pièce peut contribuer",
    ),
    "Choix selon véhicule": (SECTION_SPEC["selection_criteria"][0][3:],),
}
