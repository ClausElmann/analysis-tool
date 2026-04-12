# temp.md — CLEARED

No active wave.
All state moved to `/analysis/`.
See `analysis/system-status.md` for complete state snapshot.

---

## VALIDATED ANALYSIS FILES (permanent SSOT)

| File | Contents |
|---|---|
| [analysis/sms-domain.md](analysis/sms-domain.md) | SMS tables, StatusCode state machine, dispatch SQL, Profile/Customer coupling, isolation A/B/C |
| [analysis/lookup-pipeline.md](analysis/lookup-pipeline.md) | Command-event engine, 13-step chain, LookupState fields, retry/recovery |
| [analysis/address-domain.md](analysis/address-domain.md) | Addresses/PhoneNumbers/AddressOwners tables, Kvhx role, address expansion flow, external deps |
| [analysis/service-boundaries.md](analysis/service-boundaries.md) | Wave 3 — 6 service candidates, data ownership, A/B/C build structure, Hard Truths Q1–Q3 |
| [analysis/ai-fitness-scores.md](analysis/ai-fitness-scores.md) | Wave 3.5 — AI fitness scores (6 services), critical findings, P0–P3 decoupling list |
| [analysis/ai-safe-rules.md](analysis/ai-safe-rules.md) | **BINDING GOVERNANCE** — 10 principles, 10 constraints, 6 AI failure patterns, 7 properties, 10 red lines |
| [analysis/architectural-decisions.md](analysis/architectural-decisions.md) | Wave 5 — D1–D5 + ForwardingNumber correction, all code-verified (APPROVED) |
| [analysis/service-contracts.md](analysis/service-contracts.md) | Wave 6 — 5 shared types + 7 service contracts + Lock 1 + Lock 2 (APPROVED) |
| [analysis/implementation-slices.md](analysis/implementation-slices.md) | Wave 8 code-level spec — Slices 1–3: domain models, commands, handlers, interfaces, tests |
| [analysis/dlr-domain.md](analysis/dlr-domain.md) | Wave 10 — DLR Domain SSOT: state machine, status mapping, correlation, write model, batch contract, terminal states, failure modes, critical risks |
| [analysis/dlr-invariants.md](analysis/dlr-invariants.md) | Wave 10 — DLR hard invariants (non-negotiable rules, no design, no interpretation) |
| [analysis/dlr-design-boundary.md](analysis/dlr-design-boundary.md) | Wave 10 — Design scope: allowed / must-not-change / 4 unknowns (U-1 through U-4) |
| [analysis/dlr-control-model.md](analysis/dlr-control-model.md) | Wave 10 Phase 1 — 6 control points, state authority, linear flow, recovery model, compatibility constraints |
| [analysis/dlr-state-vocabulary.md](analysis/dlr-state-vocabulary.md) | Wave 10 Phase 2 — 3 lifecycle states, 5+1 evidence classes, transition matrix, terminality model |
| [analysis/dlr-write-model.md](analysis/dlr-write-model.md) | Wave 10 Phase 3 — 3+1 actors, 6 write targets, terminal guard, idempotency, recovery writes, 7 failure modes |
| [analysis/dlr-contracts.md](analysis/dlr-contracts.md) | Wave 10 Phase 4 — 3 touchpoints, correlation model, trust model, error handling, internal exposure |
| [analysis/dlr-slice-1.md](analysis/dlr-slice-1.md) | Wave 10 Phase 5 — Send→Correlation→Callback→Closure: 5 components, 12-step flow, 9 test scenarios |
| [analysis/dlr-slice-2.md](analysis/dlr-slice-2.md) | Wave 10 Phase 6 — Recovery + Missing DLR: 2 new components, 6-step flow, 4 race types, 8 test scenarios |
| [analysis/dlr-slice-3.md](analysis/dlr-slice-3.md) | Wave 10 Phase 7 — Orphan + Corruption: 4 new components, 5 flows, 2 discrepancy types, 10 test scenarios |
| [analysis/dlr-build-masterplan.md](analysis/dlr-build-masterplan.md) | Wave 11 — DLR Build Masterplan: 41 atomic tasks / 8 layers / 65 tests / 8 stop-verify points |
| [analysis/system-status.md](analysis/system-status.md) | Wave 11.5 — Complete state snapshot: analysis completeness, design completeness, build readiness, known unknowns |
| [analysis/system_pre_refactor_audit.md](analysis/system_pre_refactor_audit.md) | 2026-04-02 — analysis-tool Python engine audit (entry points, pipeline, conflicts, technical debt) |
| [analysis/system_fix_plan.md](analysis/system_fix_plan.md) | 2026-04-02 — analysis-tool Python engine fix plan (8 slices, CRITICAL/HIGH/MEDIUM issues) |

## ARCHIVE

| Archive | Contents |
|---|---|
| [temp_history/temp_2026-04-12_wave1-wave2.md](temp_history/temp_2026-04-12_wave1-wave2.md) | Full Wave 1 + Wave 2 logs (5414 lines) |
| [temp_history/temp_2026-04-12_wave3-wave4.md](temp_history/temp_2026-04-12_wave3-wave4.md) | Full Wave 3 + Wave 3.5 + Wave 4 logs |
| [temp_history/temp_2026-04-12_wave6-wave7.md](temp_history/temp_2026-04-12_wave6-wave7.md) | Full Wave 6 (contracts + locks) + Wave 7 (vertical slices) |
| [temp_history/wave9-10b_2026-04-12.md](temp_history/wave9-10b_2026-04-12.md) | Full Wave 9 + DLR_ANALYSIS V1 + V2 + DLR_GAP_VALIDATION Wave 10-B (111 KB) |
