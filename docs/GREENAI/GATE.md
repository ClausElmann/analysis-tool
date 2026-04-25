# GATE.md — SUPERSEDED

> Indhold er konsolideret i:
> `/shared/GOVERNANCE.md` §3 GATE
>
> reference = /shared/GOVERNANCE.md

```
- Entities:       ≥ 0.90  (verified count / total)
- Behaviors:      ≥ 0.90  (verified count / total)
- Flows:          ≥ 0.90  (file + method + verified=true required; line NOT required)
- Business Rules: ≥ 0.90  (capability-level verification allowed)
```

Hvis én metric fejler → BUILD FORBUDT

---

## EVIDENSKRAV

| Metric | Minimum evidens |
|---|---|
| Entities | entity_id + name + source_file |
| Behaviors | behavior_id + component + classification=VERIFIED |
| Flows | flow_id + source_file + method + classification=VERIFIED_STRUCTURAL |
| Business Rules | rule_id + text + entity_ids + confidence_score ≥ 0.90 |

---

## COVERAGE SCOPE

- Vurdér KUN locked domains (ikke global domain_coverage_global)
- domain_coverage_global ignoreres ved per-slice gate

---

## GATE RESULT FORMAT

```
GATE CHECK:
- Entities:       X.XX ≥ 0.90  ✅/❌
- Behaviors:      X.XX ≥ 0.90  ✅/❌
- Flows:          X.XX ≥ 0.90  ✅/❌
- Business Rules: X.XX ≥ 0.90  ✅/❌

Gate: PASSED ✅ / FAILED ❌
```

Hvis PASSED → READY FOR N-B APPROVAL
Hvis FAILED → stop, rapportér hvilken metric fejler
