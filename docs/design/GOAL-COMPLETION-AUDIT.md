# Goal Completion Audit

Initial core audited on 2026-06-15 against `.Seongjin/goal.md`.
Consumer-readiness gate status updated on 2026-06-17 against umbrella issue #49.

## Verdict

The MOLEG-API layer is implemented for the initial core goal in `.Seongjin/goal.md` and has passed representative live law.go.kr smoke verification, a 44-scenario legislative live e2e gate, and fresh read-only `congress-db` introspection.

No known blocker remains for the initial core progressive-loading contract. This is not a claim that every possible legislative-expert use case is perfect; residual risks are tracked in `docs/design/COMPLETION-RISK-AUDIT.md`.

The 2026-06-16 consumer-readiness roadmap is implemented on the integration gate branch `codex/49-consumer-readiness-integration-gate` and opened as PR #89. That gate proves the #50-#68 slice stack integrates and passes deterministic plus live MOLEG checks, but it is not yet a merged release or final stage-2 skill handoff. The open review work is the PR/issue review gate, not an unimplemented code blocker discovered by this audit.

Current environment evidence:

- law.go.kr live smoke passed with a local `MOLEG_OC`: `python3 -m pytest tests/test_live_smoke.py -q` -> `8 passed, 1 skipped`.
- Legislative live e2e passed with local credentials: `python3 -m pytest tests/test_live_e2e_scenarios.py -q` -> `44 passed, 1 skipped`.
- Package invocation seam passed on the integration branch: `python3 -m pip wheel . --no-deps -w <tmpdir>` -> built `moleg_api-0.1.0-py3-none-any.whl` with `moleg_api/py.typed`; `python3 -m pip install . --no-deps --target <tmpdir>` followed by repo-external import/serialization check, including package-root `Basis` import -> passed.
- Fresh congress-db read-only introspection passed with local `.env.local` `CONGRESS_DB_READONLY_URL`: `.venv/bin/python scripts/introspect_congress_db.py`.
- Fresh congress-db evidence shows `current_user: congress_ro`, `session_user: congress_ro`, `transaction_read_only: on`, and `included_schemas: public`.
- Fake-skill tracer-bullet gate passed: `python3 scripts/fake_skill_tracer_bullet.py` -> emitted JSON summaries for 7 archetypes; `python3 -m pytest tests/test_fake_skill_tracer_bullet.py -q` -> `2 passed`.
- Last deterministic command excluding live tests: `python3 -m pytest -q -m 'not live'` -> `116 passed, 54 deselected`.
- PR #89 deterministic GitHub Actions CI runs on the pushed head after #91: non-live tests on Python 3.10, 3.11, and 3.12 plus a package wheel/install gate with Node 24 opt-in. The PR status checks are the authoritative current-head CI evidence because each pushed evidence-only update creates a new run.
- Integration hygiene: `rg -n "<<<<<<<|=======|>>>>>>>" .` -> no conflict markers; `python3 -m compileall moleg_api` -> passed; `git diff --check` -> passed.

## Requirement Audit

| Requirement from goal | Current evidence | Status |
|---|---|---|
| Inspect the current codebase before implementation. | Project structure and implementation now live in `moleg_api/`, `tests/`, `scripts/`, and `docs/`; all merged slices were implemented through branch/PR flow. | Proven by repository state. |
| Find and inspect the MOLEG catalog SQLite DB. | `.Seongjin/DataBases/법제처 api.db` exists locally; `scripts/audit_moleg_catalog.py` reads it. A direct count returns 195 guides. | Proven locally. |
| Audit all 195 MOLEG OpenAPI catalog guides. | `docs/design/MOLEG-API-AUDIT.md` says "Audited guides: 195" and records the generated classification. | Proven by audit artifact. |
| Classify core / optional / rejected APIs with reasons. | `docs/design/MOLEG-API-AUDIT.md` records counts: core 116, optional 53, rejected 26, with per-endpoint reasons. | Proven by audit artifact. |
| Prefer deep task-level interfaces over 195 shallow endpoint wrappers. | Public surface in `moleg_api/laws.py` exposes task methods such as `search_laws()`, `get_article()`, `find_delegated_rules()`, `search_administrative_rules()`, `search_annex_forms()`, `search_interpretations()`, `search_cases()`, `expand_legal_query()`, and `load_legal_context_bundle()`; raw MOLEG targets stay inside implementation. | Proven by code and PRD. |
| Implement first vertical slice: law search / congress bridge candidate -> normalized identity -> effective law text or article. | `MolegApi.search_laws()`, `resolve_promulgated_law()`, `get_law()`, and `get_article()` exist; tests cover effective default, bridge resolution, ambiguity, no-result, law text, live MST detail lookup, and article `JO` formatting. | Proven by deterministic and live smoke tests. |
| Implement history/comparison next. | `trace_law_history()` and `compare_law_versions()` exist; tests cover JSON-reachable article history, article-scoped post-change `article_text` snapshots, missing-snapshot fallback behavior, history-event promulgation bridge keys and optional `bill_id`, full law-level `lsHistory` HTML list parsing, parse failure on changed HTML shape, live full-history loading, and `oldAndNew` normalization. | Proven by deterministic and live tests. |
| Implement delegation/hierarchy. | `find_delegated_rules()` normalizes article-level `lsDelegated` relationships; `get_law_structure()` normalizes the `lsStmd` law hierarchy across statutes, enforcement instruments, and administrative rules with explicit depth. | Proven by deterministic and live smoke tests. |
| Implement administrative-rule context. | `search_administrative_rules()` and `get_administrative_rule()` exist; tests cover hit normalization, structured article loading/filtering, exact-name identity, flat text preservation, explicit source-law/source-article back-references, missing-back-reference `None` behavior, and live `AdmRulService` wrapper shape. | Proven by deterministic and live smoke tests. |
| Implement annex/form candidate and selected body context. | `search_annex_forms()` exists for law and administrative-rule annex/form candidates through `licbyl` and `admbyl`; `get_annex_form_body()` loads selected law/admin-rule bodies through text-export endpoints. Tests cover normalized metadata, hidden numeric search/type codes, unsupported local ordinance refusal, bundle inclusion, endpoint selection for law/admin-rule body loading, empty-body no-result behavior, and a live 식품위생법 시행령 과태료 별표 body scenario. Direct HWP/PDF parsing remains intentionally out of scope. | Proven by deterministic and live tests. |
| Implement official and ministry interpretations with registry, not one public function per ministry. | `search_interpretations()` and `get_interpretation()` use an internal ministry registry; tests cover official MOLEG source, ministry source, live wrapper shapes, detail loading, structured `referenced_articles`, `source="all"` official-plus-one-ministry source-label separation, true `source="all_ministries"` fan-out, and unsupported ministry detail refusal. | Proven by deterministic and live tests. |
| Implement judicial and constitutional authorities with distinct labels. | `search_cases()`, `get_case()`, `search_constitutional_decisions()`, and `get_constitutional_decision()` exist; tests cover `prec` vs `detc` normalization, structured `referenced_articles` / `reviewed_articles`, and refusal to load a constitutional identity through `get_case()`. | Proven by deterministic tests. |
| Implement legal terms and query expansion as planning context, not final authority. | `expand_legal_query()` exists; tests cover legal/everyday terms, related terms/articles/laws, AI surfaces, and WebSearch follow-ups. Decision log says query expansion is planning context. | Proven by deterministic tests and `docs/design/DECISIONS.md`. |
| Implement a Claude-friendly legal context bundle. | `load_legal_context_bundle()` exists; tests cover `question`, `promulgated_bill`, `statute_review`, ambiguity preservation, annex/form candidates, conditional eager loading for interpretation/case/Constitutional Court detail, failed eager-load fallback to deferred lookups, and WebSearch gaps. | Proven by deterministic tests. |
| Keep `congress-db` read-only and use only `congress_ro`. | `scripts/introspect_congress_db.py` refuses owner/admin-looking roles; fresh `docs/design/congress-db-introspection/README.md` records `current_user: congress_ro` and transaction read-only `on`. | Proven by fresh introspection evidence. |
| Connect congress-db promulgation bridge fields to MOLEG identity resolution. | `resolve_promulgated_law()` accepts `prom_law_nm`, `prom_no`, `promulgation_dt`; `trace_law_history()` emits the same bridge keys on `HistoryEvent` and can populate `bill_id` from a caller-supplied map. `docs/design/congress-db-introspection/README.md` identifies those fields in `public.bill_final_outcomes`. | Proven by code, tests, and introspection artifact. |
| Reflect JSON/XML/HTML support differences and ID/MST/LID key traps in docs/code. | `docs/design/MOLEG-API-AUDIT.md` records source formats and required params; code normalizes `ID`, `MST`, law names, promulgation/effective dates; `trace_law_history()` uses the documented HTML-only `lsHistory` list parser for full law-level history. | Proven for implemented surfaces; XML parsing is documented by catalog but not separately implemented because JSON/HTML are the chosen source formats. |
| Keep MOLEG credentials in env vars only. | `LawGoKrClient` reads `MOLEG_OC`; `.env.example` documents `MOLEG_OC` and `CONGRESS_DB_READONLY_URL`; `.gitignore` excludes `.env*` except `.env.example`; secret grep has passed in PRs. | Proven by code and git hygiene. |
| Clarify error model. | `errors.py` defines no-result, ambiguity, unsupported format, source API, parse failure, rate-limit, and retry-exhausted errors; tests cover source retry/rate-limit behavior. | Proven by code and tests. |
| Avoid large mirror DB/cache at the start. | No committed mirror/cache implementation exists; `.gitignore` excludes local DB files. `docs/design/PRD.md` records "Caching starts small." | Proven by repository state. |
| Write skill integration docs explaining MOLEG-API, congress-db, and WebSearch responsibilities. | `docs/SKILL-INTEGRATION.md` documents source responsibilities, promulgated-bill workflow, query planning, fallback rules, public interfaces, and answering discipline. `docs/SKILL-AUTHOR-COOKBOOK.md` documents package installation, serialization, canonical call sequences, vendored fallback, and error handling. | Proven by document. |
| Prove the skill invocation seam can be installed and imported outside the repository checkout. | `pyproject.toml` defines the `moleg-api` package; current integration-branch verification built a wheel, confirmed package metadata and `py.typed`, installed into an isolated target directory, imported `moleg_api` from `/tmp`, verified package-root public exports including `Basis`, and verified recursive serialization with and without raw payloads. | Proven by package build/install check. |
| Run dozens of realistic e2e scenarios from a legislative-expert Claude perspective. | `tests/test_live_e2e_scenarios.py` covers 44 scenarios across statute/article, full law history, delegation, administrative-rule, annex/form search, selected annex/form body loading, official/ministry interpretation, case, constitutional, query-planning, comparable-mechanism discovery, bundle, institutional-system, and congress bridge workflows through public `MolegApi` methods. | Proven by live e2e gate. |
| Run a pre-skill fake-skill tracer bullet across the seven consumer-readiness archetypes. | `scripts/fake_skill_tracer_bullet.py` and `tests/test_fake_skill_tracer_bullet.py` cover sanction design, delegated-criteria tracing, statute evolution, congress-bill to current-law bridge, constitutional-risk scan, multi-law concept assembly, and comparative design using public `MolegApi` methods only. | Proven by deterministic fake-skill gate. |
| Avoid overclaiming perfection. | `docs/design/COMPLETION-RISK-AUDIT.md` records no known initial-core blocker and keeps demand-gated extensions such as direct HWP/PDF parsing outside the completion claim; recent bridge lag, Constitutional Court detail coverage, ministry interpretation live coverage, full law history, and annex/form body loading are recorded as mitigated. | Proven by risk audit and GitHub issues. |
| Record decisions and API traps in decision log. | `docs/design/DECISIONS.md` contains decisions for deep interface, effective-date default, congress-db read-only use, admin `issued_on`, interpretation registry, judicial/constitutional separation, query expansion, context bundles, and retry semantics. | Proven by document. |
| Use GitHub issues/branches/PRs to maintain progress visibility. | Initial-core work was tracked through earlier issue/PR slices. The current consumer-readiness work is tracked by umbrella #49, child issues #50-#68 plus #90/#91, and integration PR #89 on `codex/49-consumer-readiness-integration-gate`. | Proven by GitHub state and PR #89. |
| Run deterministic and necessary live gates. | Deterministic tests pass with live tests excluded: `python3 -m pytest -q -m 'not live'` -> `116 passed, 54 deselected`. PR #89 now also has current-head GitHub Actions CI for non-live tests across Python 3.10/3.11/3.12 and a package install gate. Live source gates pass separately: `tests/test_live_smoke.py` -> `8 passed, 1 skipped`; `tests/test_live_e2e_scenarios.py` -> `44 passed, 1 skipped`. Fresh congress-db introspection also passes with local `.env.local`. | Proven. |
| Verify live law.go.kr source behavior through sample calls when credentials are available. | `tests/test_live_smoke.py` covers statute detail/article, delegation, context bundle, administrative rules, annex/forms, interpretations, cases, Constitutional Court decisions, history/comparison, and query expansion. Latest run: `8 passed, 1 skipped`. | Proven for representative samples; one history/comparison sample-level skip remains acceptable when the chosen live sample has no data. |
| Verify read-only congress-db access when needed. | Fresh introspection evidence exists under `docs/design/congress-db-introspection/`; script reran with local `.env.local` `CONGRESS_DB_READONLY_URL` and is scoped to the `public` schema by default. | Proven. |

## Commands For Final Verification

Run these after local credentials are provided. Do not commit credentials.

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest tests/test_live_smoke.py -q
.venv/bin/python -m pytest tests/test_live_e2e_scenarios.py -q
.venv/bin/python scripts/introspect_congress_db.py
```

Expected behavior:

- Normal deterministic tests should pass.
- Before running the live commands, set `MOLEG_OC` and `CONGRESS_DB_READONLY_URL` locally in the shell or `.env.local`; never commit them.
- Live smoke should pass or produce explicit sample-level skips only where a chosen live sample has no data.
- congress-db introspection must show `current_user` / `session_user` as `congress_ro`, not owner/admin, and must not write to the database.

## Remaining Work

None for the initial core completion criteria.

For the consumer-readiness roadmap, PR #89 is the current integration gate for #50-#68, #90, and #91. The remaining work is review/merge sequencing and any issues discovered by that review. Demand-gated extensions such as direct HWP/PDF annex/form parsing remain documented out of scope until repeated skill scenarios justify them.
