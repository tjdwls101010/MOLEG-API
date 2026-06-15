# Live Legislative E2E Scenarios

This document records the live scenario gate for MOLEG-API as used by a future legislative-expert Claude skill. The goal is not endpoint coverage. The goal is to prove that realistic legislative context-loading tasks work through the public `MolegApi` interface without making Claude memorize raw law.go.kr targets.

The executable gate is `tests/test_live_e2e_scenarios.py`.

## Scope

The gate exercises:

- Current statute identity and article loading for 13 stable statutes.
- Full law-level history loading through the HTML-only `lsHistory` list table.
- Delegated-rule loading for statute-to-lower-rule context.
- Administrative-rule search and detail loading.
- Law annex/form candidate discovery and selected body loading.
- MOLEG official interpretation search and detail loading.
- Ministry first-instance interpretation search, detail loading, and source-label separation.
- Court case search and detail loading.
- Constitutional Court detail loading through a stable live decision ID.
- Legal query expansion as planning context, including WebSearch handoff gaps.
- Legal context bundles for broad questions and specific statute review.
- Real `congress-db` promulgation bridge rows resolved through MOLEG identity lookup.

The assertions deliberately avoid exact legal text. Live legal text changes over time, and brittle text snapshots would turn useful source drift into false failures. The gate asserts stable contracts instead: normalized identity, basis/source labels, non-empty loaded text, article-label preservation, deferred lookup structure, WebSearch gaps, and read-only congress bridge compatibility.

## Scenario Groups

| Group | Scenario count | Public interface |
|---|---:|---|
| Statute articles | 13 | `search_laws()` -> `get_article()` |
| Law history | 1 | `trace_law_history()` |
| Delegation | 3 | `find_delegated_rules()` |
| Administrative rules | 3 | `search_administrative_rules()` -> `get_administrative_rule()` |
| Annex/forms | 2 | `search_annex_forms()` |
| Annex/form body | 1 | `search_annex_forms()` -> `get_annex_form_body()` |
| Official interpretations | 2 | `search_interpretations()` -> `get_interpretation()` |
| Ministry interpretations | 1 | `search_interpretations(source="ministry")`, `get_interpretation()`, `search_interpretations(source="all")` |
| Cases | 3 | `search_cases()` -> `get_case()` |
| Constitutional decisions | 1 | `get_constitutional_decision()` |
| Query planning | 5 | `expand_legal_query()` |
| Question bundles | 4 | `load_legal_context_bundle(mode="question")` |
| Statute-review bundles | 2 | `load_legal_context_bundle(mode="statute_review")` |
| congress-db bridge | 1 credential-dependent | `bill_final_outcomes` -> `resolve_promulgated_law()` |

## Current Evidence

Last run on 2026-06-15:

```bash
.venv/bin/python -m pytest tests/test_live_e2e_scenarios.py -q
```

Result:

```text
43 passed in 195.25s (0:03:15)
```

The Constitutional Court scenario uses a stable detail ID because current live `detc` search queries can return no rows even while detail loading remains available.
The ministry interpretation scenario uses a stable 방위사업청 search/detail path and verifies that official MOLEG `expc` results remain distinct from ministry `dapaCgmExpc` results when `source="all"`.
The full law-history scenario uses `lsHistory` HTML list parsing for 건축법 and verifies normalized law-level history events.
The annex/form body scenario searches 식품위생법 law annexes, selects the 과태료 별표 candidate, and verifies non-empty text from `lsBylTextDownLoad.do`.

## Operating Notes

- Requires local `MOLEG_OC`; otherwise the whole file skips.
- The congress bridge scenario also requires local `CONGRESS_DB_READONLY_URL`; it reads with `congress_ro` and sets `default_transaction_read_only = on`.
- Connection strings and keys stay in ignored `.env` / `.env.local` files.
- A live source no-result is not the same as a temporary source-access failure. `NoResultError`, `RateLimitError`, and retry errors remain distinct.
