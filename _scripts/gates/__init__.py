"""
gates/ — 5 wrappers Pydantic-typés des gates existants de _scripts/quality-gates.py.

Référence : ADR-059 SEO Runtime Projection (accepted 2026-05-13), Phase B PR-4.

**Principe non-négociable** : aucun nouveau gate. Chaque wrapper regroupe par
dimension les fonctions `gate_*` existantes de `_scripts/quality-gates.py` et
les expose via un contrat Pydantic `GateResult` strict.

Mapping inventaire (audit ast.parse Step 0) → 5 wrappers :

| Wrapper             | Gates existants composés                                       |
|---------------------|----------------------------------------------------------------|
| source_gate         | gate_source_catalog_raw_refs, gate_sources_missing             |
| claim_gate          | gate_schema_invalid, gate_slug_collision, gate_path_anti_patterns |
| contradiction_gate  | gate_diagnostic_relations, gate_legacy_symptoms_block          |
| risk_gate           | gate_pollution, gate_catalog_leak, gate_commercial_promise,    |
|                     | gate_safety_unsourced, gate_maintenance_advice                 |
| confidence_gate     | gate_symptom_unstructured                                       |
"""
