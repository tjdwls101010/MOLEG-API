# Maintainer Notes

This page explains the package layout and the refactor guardrails used to keep `moleg-api` maintainable without changing the public API.

## Public compatibility surface

Keep these imports stable:

```python
from moleg_api import MolegApi
from moleg_api import LawGoKrClient
import moleg_api.models
import moleg_api.laws
import moleg_api.normalization
import moleg_api.cli
```

The public facade modules (`models.py`, `laws.py`, `normalization.py`, `cli.py`) are intentionally small compatibility layers. They re-export the implementation packages below so existing users do not need to change imports.

The CLI has 27 task subcommands plus `catalog`. `moleg catalog` is the source of truth for the command list, routing rules, and emitted `kind` values. When adding or removing a task method, update the parser, catalog, API reference, and CLI reference together.

## Internal layout

The implementation is grouped by responsibility:

| Package/module area | Responsibility |
|---|---|
| `_models/` | Public dataclasses, serialization helpers, and model re-exports. |
| `_normalization/` | law.go.kr payload parsing and source-specific normalization. |
| `_laws/api_*.py` | Public `MolegApi` mixin methods. These files should read as orchestration shells. |
| `_laws/*_pipeline.py`, `_laws/*_details.py`, `_laws/*_candidates.py` | Private helpers for staged loaders, candidate discovery, eager detail loading, and gap/deferred construction. |
| `_cli/` | CLI parser, dispatcher, signal generation, catalog, and JSON envelope entry point. |

Prefer adding a helper next to the domain that owns it (`bundle_*`, `authority_context_*`, `delegated_criteria_*`, `institutional_*`) instead of creating generic utility modules. A maintainer should be able to find the helper by starting from the public method name.

## File-size tradeoff

The goal is small, meaningful files, not the maximum number of files. Use these guardrails:

- Public facade files should stay thin and compatibility-focused.
- Public `api_*.py` mixin files should show validation, high-level orchestration, and final return shape.
- Private helpers should stay below roughly 250 lines of executable code. A file can be slightly longer in total lines when whitespace, imports, and public API docstrings make the code easier to scan.
- Split a file when it mixes different responsibilities, such as candidate discovery and detail loading.
- Do not split a cohesive algorithm just to satisfy a line-count target; prefer a clear domain name over a generic `utils.py`.

Current large-loader split:

- `load_legal_context_bundle` uses `bundle_modes`, `bundle_primary`, `bundle_candidates`, `bundle_eager`, and `bundle_finalize`.
- `load_authority_context` uses `authority_context_pipeline` and `authority_context_details`.
- `load_institutional_system` uses `institutional_resolution`, `institutional_pipeline`, and `institutional_candidates`.
- `load_delegated_criteria` uses `delegated_criteria_pipeline` and `delegated_criteria_details`.
- `load_followup` uses `followup_routing`, `followup_routing_authority`, and `followup_routing_bundle`.

## Regression checks

Before release, run:

```bash
python -m compileall moleg_api tests -q
python -m pytest -q -m "not live"
MOLEG_OC=chunghun1 python -m pytest -q -m live
python -m moleg_api catalog
```

For packaging:

```bash
python -m build
python -m twine check dist/*
```

The bundled default OC is `chunghun1`. It is a free law.go.kr account id, not a secret. Users can still override it with `LawGoKrClient(oc=...)` or `MOLEG_OC`.
