# Completion Risk Audit

Initial core risk audited on 2026-06-15 after the legislative live e2e gate and annex/form body loading were added. Current integration-branch evidence was refreshed on 2026-06-17 after the consumer-readiness gate work.

## Verdict

MOLEG-API is ready for the initial legislative-expert skill prototype, but it is not reasonable to call it "perfect" for every legislative-expert use case.

The current implementation has strong evidence for the core progressive-loading path: statute/article lookup, law history, delegation, administrative rules, annex/form candidates and selected text bodies, official and ministry interpretations, cases, query expansion, context bundles, and read-only congress-db bridge integration.

## Proven Core

- Public `MolegApi` methods hide raw law.go.kr `target` values.
- Live law.go.kr smoke passed across representative source families.
- The legislative live e2e gate passed 44 scenario tests, including selected annex/form body loading, comparable-mechanism discovery, institutional-system loading, and congress bridge resolution.
- Deterministic non-live tests passed on the integration branch: `120 passed, 54 deselected`.
- PR #89 now runs deterministic GitHub Actions CI on the pushed head: non-live tests on Python 3.10/3.11/3.12 plus a package wheel/install gate. The PR status checks are the authoritative current-head CI evidence because each pushed evidence-only update creates a new run.
- Live smoke and live e2e gates passed separately with local credentials: `8 passed, 1 skipped` and `44 passed, 1 skipped`.
- congress-db was introspected with `congress_ro`, with `transaction_read_only: on`, and with the default scope limited to the `public` schema.
- Promulgated-bill bundles preserve law-name candidates and a `source_lag_or_manual_review_required` gap when exact congress-db bridge matching fails.
- Credentials remain in ignored local env files, not committed.

## Residual Risks

No known blocker remains for the initial core progressive-loading contract. Direct HWP/PDF attachment parsing is still intentionally out of scope; selected law/admin-rule annex/form bodies load through text-export endpoints instead.

## Not A Completion Blocker For The Initial Core

The following remain demand-gated by design:

- One wrapper per all 195 MOLEG catalog guides.
- Local ordinance, treaty, administrative appeal, special administrative appeal, and committee-decision modules.
- Direct HWP/PDF parsing for every annex/form attachment.
- Bulk mirror/cache of law.go.kr.
- WebSearch/news/statistics retrieval inside MOLEG-API.

They are not required for the current initial core because `docs/design/MOLEG-API-AUDIT.md` classifies them as optional or rejected for the first legislative-expert path. They should be revisited only when repeated skill scenarios prove the need.

## Mitigated Risks

| Risk | Mitigation |
|---|---|
| Recent congress-db promulgation rows may not resolve exactly in MOLEG yet. | `load_legal_context_bundle(mode="promulgated_bill")` now preserves law-name candidates and emits `source_lag_or_manual_review_required` when exact bridge matching fails, so Claude can explain source lag/manual review instead of overclaiming. |
| Constitutional Court live e2e previously sample-skipped. | `tests/test_live_e2e_scenarios.py` now loads a stable live `detc` detail ID and verifies constitutional source labels plus non-empty text. Search remains query-sensitive, but detail loading is live-proven. |
| Ministry first-instance interpretation live coverage was not yet stable. | `tests/test_live_e2e_scenarios.py` now live-proves 방위사업청 ministry search, a stable ministry detail ID, and `source="all"` official-plus-one-ministry label separation. The parser normalizes live `Expc.expc` and `CgmExpc.cgmExpc` wrappers without exposing ministry-specific public functions. |
| Full law history was unsupported beyond JSON-reachable article/date changes. | `trace_law_history()` now parses the HTML-only `lsHistory` list table into normalized law-level events, preserves source MST/effective-date row metadata, keeps article/date-range JSON behavior intact, and raises `ParseFailureError` if the live table shape changes. |
| Annex/form bodies previously stopped at candidate metadata. | `get_annex_form_body()` now loads selected law/admin-rule bodies through law.go.kr text-export endpoints, with deterministic tests for law/admin-rule endpoint selection and a live e2e 식품위생법 시행령 과태료 별표 body scenario. |

## How To Read The Current Status

"No known blocker" means no blocker for the current initial MOLEG-API core and its documented progressive-loading contract. It does not mean every possible legislative-expert source path is implemented or live-proven.

The stronger claim that can be defended today is:

> MOLEG-API is implemented and live-tested enough to support the first legislative-expert skill prototype, with demand-gated extensions documented instead of hidden.
