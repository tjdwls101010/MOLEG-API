# Goal Completion Audit

Audited on 2026-06-15 against `.Seongjin/goal.md`.

## Verdict

The MOLEG-API layer is substantially implemented and has passed representative live law.go.kr smoke verification. The overall goal is **not complete** only because fresh read-only `congress-db` verification still needs a local `CONGRESS_DB_READONLY_URL`.

Remaining blocker: [#15 — Provide live credentials for final smoke verification](https://github.com/tjdwls101010/MOLEG-API/issues/15).

Current environment evidence:

- law.go.kr live smoke passed with a local `MOLEG_OC`: `MOLEG_OC=... .venv/bin/python -m pytest tests/test_live_smoke.py -q` -> `8 passed, 1 skipped`.
- `CONGRESS_DB_READONLY_URL` is missing, so a fresh read-only Neon re-introspection cannot be rerun from this shell.
- Last deterministic command without `MOLEG_OC`: `.venv/bin/python -m pytest -q` -> `42 passed, 9 skipped`.
- Last full command with `MOLEG_OC`: `MOLEG_OC=... .venv/bin/python -m pytest -q` -> `50 passed, 1 skipped`.

## Requirement Audit

| Requirement from goal | Current evidence | Status |
|---|---|---|
| Inspect the current codebase before implementation. | Project structure and implementation now live in `moleg_api/`, `tests/`, `scripts/`, and `docs/`; all merged slices were implemented through branch/PR flow. | Proven by repository state. |
| Find and inspect the MOLEG catalog SQLite DB. | `.Seongjin/DataBases/법제처 api.db` exists locally; `scripts/audit_moleg_catalog.py` reads it. A direct count returns 195 guides. | Proven locally. |
| Audit all 195 MOLEG OpenAPI catalog guides. | `docs/design/MOLEG-API-AUDIT.md` says "Audited guides: 195" and records the generated classification. | Proven by audit artifact. |
| Classify core / optional / rejected APIs with reasons. | `docs/design/MOLEG-API-AUDIT.md` records counts: core 116, optional 53, rejected 26, with per-endpoint reasons. | Proven by audit artifact. |
| Prefer deep task-level interfaces over 195 shallow endpoint wrappers. | Public surface in `moleg_api/laws.py` exposes task methods such as `search_laws()`, `get_article()`, `find_delegated_rules()`, `search_administrative_rules()`, `search_annex_forms()`, `search_interpretations()`, `search_cases()`, `expand_legal_query()`, and `load_legal_context_bundle()`; raw MOLEG targets stay inside implementation. | Proven by code and PRD. |
| Implement first vertical slice: law search / congress bridge candidate -> normalized identity -> effective law text or article. | `MolegApi.search_laws()`, `resolve_promulgated_law()`, `get_law()`, and `get_article()` exist; tests cover effective default, bridge resolution, ambiguity, no-result, law text, live MST detail lookup, and article `JO` formatting. | Proven by deterministic and live smoke tests. |
| Implement history/comparison next. | `trace_law_history()` and `compare_law_versions()` exist; tests cover JSON-reachable article history, unsupported full HTML history scope, and `oldAndNew` normalization. | Proven for JSON-reachable history/comparison; full `lsHistory` HTML parsing remains intentionally unsupported and documented. |
| Implement delegation/hierarchy. | `find_delegated_rules()` normalizes `lsDelegated`; deterministic tests cover lower-rule relationships. | Proven by deterministic tests. |
| Implement administrative-rule context. | `search_administrative_rules()` and `get_administrative_rule()` exist; tests cover hit normalization, structured article loading/filtering, exact-name identity, flat text preservation, and live `AdmRulService` wrapper shape. | Proven by deterministic and live smoke tests. |
| Implement annex/form candidate context. | `search_annex_forms()` exists for law and administrative-rule annex/form candidates through `licbyl` and `admbyl`; tests cover normalized metadata, hidden numeric search/type codes, unsupported local ordinance refusal, bundle inclusion, and live smoke. HWP/PDF body parsing remains intentionally out of scope. | Proven by deterministic and live smoke tests. |
| Implement official and ministry interpretations with registry, not one public function per ministry. | `search_interpretations()` and `get_interpretation()` use an internal ministry registry; tests cover official MOLEG source, ministry source, detail loading, and unsupported ministry detail refusal. | Proven by deterministic tests. |
| Implement judicial and constitutional authorities with distinct labels. | `search_cases()`, `get_case()`, `search_constitutional_decisions()`, and `get_constitutional_decision()` exist; tests cover `prec` vs `detc` normalization and refusal to load a constitutional identity through `get_case()`. | Proven by deterministic tests. |
| Implement legal terms and query expansion as planning context, not final authority. | `expand_legal_query()` exists; tests cover legal/everyday terms, related terms/articles/laws, AI surfaces, and WebSearch follow-ups. Decision log says query expansion is planning context. | Proven by deterministic tests and `docs/design/DECISIONS.md`. |
| Implement a Claude-friendly legal context bundle. | `load_legal_context_bundle()` exists; tests cover `question`, `promulgated_bill`, `statute_review`, ambiguity preservation, annex/form candidates, deferred lookups, and WebSearch gaps. | Proven by deterministic tests. |
| Keep `congress-db` read-only and use only `congress_ro`. | `scripts/introspect_congress_db.py` refuses owner/admin-looking roles; `docs/design/congress-db-introspection/README.md` records `current_user: congress_ro` and transaction read-only `on`. | Proven by stored introspection evidence; fresh rerun is blocked by missing `CONGRESS_DB_READONLY_URL`. |
| Connect congress-db promulgation bridge fields to MOLEG identity resolution. | `resolve_promulgated_law()` accepts `prom_law_nm`, `prom_no`, `promulgation_dt`; `docs/design/congress-db-introspection/README.md` identifies those fields in `public.bill_final_outcomes`. | Proven by code, tests, and introspection artifact. |
| Reflect JSON/XML/HTML support differences and ID/MST/LID key traps in docs/code. | `docs/design/MOLEG-API-AUDIT.md` records source formats and required params; code normalizes `ID`, `MST`, law names, promulgation/effective dates; `trace_law_history()` refuses full HTML-only `lsHistory` without parser support. | Proven for implemented surfaces; XML parsing is documented by catalog but not separately implemented because JSON is the chosen source format. |
| Keep MOLEG credentials in env vars only. | `LawGoKrClient` reads `MOLEG_OC`; `.env.example` documents `MOLEG_OC` and `CONGRESS_DB_READONLY_URL`; `.gitignore` excludes `.env*` except `.env.example`; secret grep has passed in PRs. | Proven by code and git hygiene. |
| Clarify error model. | `errors.py` defines no-result, ambiguity, unsupported format, source API, parse failure, rate-limit, and retry-exhausted errors; tests cover source retry/rate-limit behavior. | Proven by code and tests. |
| Avoid large mirror DB/cache at the start. | No committed mirror/cache implementation exists; `.gitignore` excludes local DB files. `docs/design/PRD.md` records "Caching starts small." | Proven by repository state. |
| Write skill integration docs explaining MOLEG-API, congress-db, and WebSearch responsibilities. | `docs/SKILL-INTEGRATION.md` documents source responsibilities, promulgated-bill workflow, query planning, fallback rules, public interfaces, and answering discipline. | Proven by document. |
| Record decisions and API traps in decision log. | `docs/design/DECISIONS.md` contains decisions for deep interface, effective-date default, congress-db read-only use, admin `issued_on`, interpretation registry, judicial/constitutional separation, query expansion, context bundles, and retry semantics. | Proven by document. |
| Use GitHub issues/branches/PRs to maintain progress visibility. | Merged PRs include #2, #7, #8, #9, #11, #12, #14, #17, and #19; open blocker is #15. | Proven by GitHub state at audit time. |
| Run full tests and necessary live smoke tests. | Deterministic tests pass without credentials: `.venv/bin/python -m pytest -q` -> `42 passed, 9 skipped`. Full suite with local `MOLEG_OC` passes: `50 passed, 1 skipped`. | Proven for law.go.kr; congress-db remains gated by `CONGRESS_DB_READONLY_URL`. |
| Verify live law.go.kr source behavior through sample calls when credentials are available. | `tests/test_live_smoke.py` covers statute detail/article, delegation, context bundle, administrative rules, annex/forms, interpretations, cases, Constitutional Court decisions, history/comparison, and query expansion. Latest run: `8 passed, 1 skipped`. | Proven for representative samples; one history/comparison sample-level skip remains acceptable when the chosen live sample has no data. |
| Verify read-only congress-db access when needed. | Stored introspection evidence exists under `docs/design/congress-db-introspection/`; script can rerun with `CONGRESS_DB_READONLY_URL`. | Missing fresh evidence: `CONGRESS_DB_READONLY_URL` is absent in this environment. |

## Commands For Final Verification

Run these after local credentials are provided. Do not commit credentials.

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest tests/test_live_smoke.py -q
.venv/bin/python scripts/introspect_congress_db.py
```

Expected behavior:

- Normal deterministic tests should pass.
- Before running the live commands, set `MOLEG_OC` and `CONGRESS_DB_READONLY_URL` locally in the shell or `.env.local`; never commit them.
- Live smoke should pass or produce explicit sample-level skips only where a chosen live sample has no data.
- congress-db introspection must show `current_user` / `session_user` as `congress_ro`, not owner/admin, and must not write to the database.

## Remaining Work

1. Provide local `CONGRESS_DB_READONLY_URL` for the `congress_ro` role and rerun read-only introspection if fresh congress-db evidence is required.
2. Update this audit and close #15 only after the fresh congress-db evidence exists or the PM explicitly decides stored introspection evidence is sufficient.

Until those are done, the active goal must remain incomplete.
