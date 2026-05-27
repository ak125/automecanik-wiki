# `_scripts/gates/` — 5 wrappers Pydantic-typed des gates existants

Référence : [ADR-059 SEO Runtime Projection](https://github.com/ak125/governance-vault/blob/main/ledger/decisions/adr/ADR-059-seo-runtime-projection.md) — Phase B PR-4.

## Principe non-négociable

**Aucun nouveau gate atomique.** Chaque wrapper compose par dimension les fonctions `gate_*` existantes de `_scripts/quality-gates.py` et les expose via un contrat Pydantic `GateResult` strict.

## Mapping inventaire → 5 wrappers

Step 0 audit `ast.parse` sur `_scripts/quality-gates.py` (618 lignes, 0 classes, 22 fonctions dont **13 gates atomiques**) :

| Wrapper              | Gates legacy composés                                                                                                    |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `source_gate`        | `gate_source_catalog_raw_refs` + `gate_sources_missing`                                                                  |
| `claim_gate`         | `gate_schema_invalid` + `gate_slug_collision` + `gate_path_anti_patterns`                                                |
| `contradiction_gate` | `gate_diagnostic_relations` + `gate_legacy_symptoms_block`                                                               |
| `risk_gate`          | `gate_pollution` + `gate_catalog_leak` + `gate_commercial_promise` + `gate_safety_unsourced` + `gate_maintenance_advice` |
| `confidence_gate`    | `gate_symptom_unstructured`                                                                                              |

## Contrat de retour (Pydantic v2 strict)

```python
class GateResult(BaseModel):
    gate_name: Literal["source", "claim", "contradiction", "risk", "confidence"]
    target_file: str
    status: Literal["pass", "fail", "warn"]
    violations: list[GateViolation]

    @property
    def exit_code(self) -> int:
        return {"pass": 0, "fail": 1, "warn": 2}[self.status]
```

## Garde-fous architecturaux (vérifiés par 18 tests Pytest)

- `test_no_new_atomic_gate_defined_in_wrappers` : refuse toute fonction `def gate_*` dans `gates/*.py` (forbids re-inventing what exists in legacy)
- `test_no_llm_inference_imports_in_wrappers` : refuse `anthropic / openai / groq / cohere / mistralai / google.generativeai`
- `test_no_db_imports_in_wrappers` : refuse `psycopg / asyncpg / supabase / sqlalchemy / django`
- `test_all_wrappers_expose_gate_result` : chaque `*_gate.py` exporte `run_<name>_gate` retournant `GateResult`
- `test_legacy_gates_module_loads` : importlib loader résout `_scripts/quality-gates.py` (filename avec tiret)

## Usage CLI

```bash
# Un wrapper individuel
python3 -m _scripts.gates.source_gate --target proposals/filtre-a-huile.md --format json

# Les 5 wrappers en cascade (exit 0 ssi tous PASS)
python3 -m _scripts.gates.run_all --target proposals/filtre-a-huile.md --format json
```

## Tests

```bash
cd _scripts
pytest gates/test_gates.py -v
```

Résultat : **18 passed**.

## Option future (hors PR-4)

Migration possible vers **OPA/Conftest avec Rego policies** pour policy-as-code uniforme (CI + pre-commit + runtime). Avantage : versionnage policies découplé du code, audit trail OPA decision logs. À évaluer après stabilité empirique des 5 wrappers (followup ADR séparé).

## Hors scope PR-4

- PR-5a/5b : exports SEO JSON builder + cron systemd timer
- PR-6 : DB projection 7 tables + 2 MVs + replay_projection.py
- PR-7 : RPC + adapter pages + depcruise/ast-grep guards

Ces composants attendent l'instruction explicite séparée.
