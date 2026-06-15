# Completion Risk Audit

Audited on 2026-06-15 after the legislative live e2e gate was added.

## Verdict

MOLEG-API is ready for the initial legislative-expert skill prototype, but it is not reasonable to call it "perfect" for every legislative-expert use case.

The current implementation has strong evidence for the core progressive-loading path: statute/article lookup, delegation, administrative rules, annex/form candidates, official interpretations, cases, query expansion, context bundles, and read-only congress-db bridge integration. The remaining risks are not hidden defects in that core. They are known limits where the current interface either intentionally stops at candidate metadata, relies on sample-dependent live availability, or needs a more specialized parser/fallback before Claude can safely treat the context as complete.

## Proven Core

- Public `MolegApi` methods hide raw law.go.kr `target` values.
- Live law.go.kr smoke passed across representative source families.
- The legislative live e2e gate passed 40 scenario tests.
- Full pytest with local credentials passed: `94 passed, 1 skipped`.
- congress-db was introspected with `congress_ro`, with `transaction_read_only: on`.
- Promulgated-bill bundles preserve law-name candidates and a `source_lag_or_manual_review_required` gap when exact congress-db bridge matching fails.
- Credentials remain in ignored local env files, not committed.

## Residual Risks

| Risk | Why it matters for a legislative-expert Claude | Tracking |
|---|---|---|
| Annex/form bodies are not loaded or parsed. | Attached tables, amounts, standards, and required forms can carry the operative rule. Candidate metadata is not enough to answer all questions. | [#38](https://github.com/tjdwls101010/MOLEG-API/issues/38) |
| Full law history remains unsupported beyond JSON-reachable article/date changes. | Some amendment-history questions need law-level history, not only article/date-range JSON surfaces. | [#39](https://github.com/tjdwls101010/MOLEG-API/issues/39) |
| Ministry first-instance interpretation live coverage is not yet stable. | The registry design exists, but live proof should cover at least one ministry source path. | [#42](https://github.com/tjdwls101010/MOLEG-API/issues/42) |

## Not A Completion Blocker For The Initial Core

The following remain demand-gated by design:

- One wrapper per all 195 MOLEG catalog guides.
- Local ordinance, treaty, administrative appeal, special administrative appeal, and committee-decision modules.
- Bulk mirror/cache of law.go.kr.
- WebSearch/news/statistics retrieval inside MOLEG-API.

They are not required for the current initial core because `docs/design/MOLEG-API-AUDIT.md` classifies them as optional or rejected for the first legislative-expert path. They should be revisited only when repeated skill scenarios prove the need.

## Mitigated Risks

| Risk | Mitigation |
|---|---|
| Recent congress-db promulgation rows may not resolve exactly in MOLEG yet. | `load_legal_context_bundle(mode="promulgated_bill")` now preserves law-name candidates and emits `source_lag_or_manual_review_required` when exact bridge matching fails, so Claude can explain source lag/manual review instead of overclaiming. |
| Constitutional Court live e2e previously sample-skipped. | `tests/test_live_e2e_scenarios.py` now loads a stable live `detc` detail ID and verifies constitutional source labels plus non-empty text. Search remains query-sensitive, but detail loading is live-proven. |

## How To Read The Current Status

"No known blocker" means no blocker for the current initial MOLEG-API core and its documented progressive-loading contract. It does not mean every possible legislative-expert source path is implemented or live-proven.

The stronger claim that can be defended today is:

> MOLEG-API is implemented and live-tested enough to support the first legislative-expert skill prototype, with known residual risks tracked as follow-up slices.
