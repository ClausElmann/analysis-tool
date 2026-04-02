# Domain Engine Reference

## Canonical Engine

**`core/domain/domain_engine_v3.py`** (`DomainEngineV3`)

This is the only engine that should be used for all domain analysis work.

- Entry point: `run_domain_engine.py`
- Uses: `AIReasoner`, `DomainAIEnricher`, `DomainCompletionProtocol`
- Supports: `--once`, `--max-assets`, `--seeds`, `--dry-run`, `--reset-all`

## Legacy Engine (Deprecated)

**`core/domain/domain_engine.py`** (`DomainEngine` v1)

Deprecated. Retained for reference only. Do not run.

- Importing this module emits a `DeprecationWarning`
- Uses an incompatible AI chain (`core/domain/ai/` — domain_mapper, refiner, semantic_analyzer)
- Entry point: `run_domain_pipeline.py` (also deprecated, also emits warning)
- Will be removed in SLICE-07 cleanup

## Which script to run

| Task | Command |
|---|---|
| Run domain analysis | `python run_domain_engine.py` |
| Single iteration | `python run_domain_engine.py --once` |
| Limit assets | `python run_domain_engine.py --max-assets 50` |
| Dry run | `python run_domain_engine.py --dry-run` |

Do **not** run `run_domain_pipeline.py`.
