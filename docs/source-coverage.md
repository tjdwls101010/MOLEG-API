# Source Coverage And Limits

MOLEG-API covers law.go.kr source families that are useful for recurring legal
source-loading tasks. It deliberately does not expose every MOLEG OpenAPI
endpoint as a one-to-one SDK method.

## Covered Source Families

| Source family | Public interfaces |
|---|---|
| Current and promulgated statutes | `search_laws`, `resolve_promulgated_law`, `get_law`, `get_article`, `load_article_context` |
| Law history and before/after text | `trace_law_history`, `compare_law_versions` |
| Delegated rules and hierarchy | `find_delegated_rules`, `get_law_structure` |
| Administrative rules | `search_administrative_rules`, `get_administrative_rule`, `load_administrative_rule_context` |
| Annexes and forms | `search_annex_forms`, `get_annex_form_body` |
| MOLEG and ministry interpretations | `search_interpretations`, `get_interpretation` |
| Ordinary court cases | `search_cases`, `get_case` |
| Constitutional Court decisions | `search_constitutional_decisions`, `get_constitutional_decision` |
| Query planning and bundles | `expand_legal_query`, `find_comparable_mechanisms`, `load_legal_context_bundle`, `load_institutional_system`, `load_delegated_criteria` |

## Important Limits

- MOLEG-API loads legal sources. It does not provide legal advice.
- It does not query National Assembly bill databases. Use a separate bill source
  for bill status, sponsors, votes, minutes, and promulgation bridge fields.
- It does not provide latest statistics, news, policy announcements, or social
  context. Use WebSearch or another current external source.
- Empty search results are scoped to the exact query, source family, and filters
  used. They are not proof that no relevant law, rule, case, interpretation, or
  annex exists.
- Search hit metadata is not citable source text. Load selected detail first.
- Authority types remain separate: MOLEG interpretation, ministry
  interpretation, ordinary court case, and Constitutional Court decision are not
  interchangeable.
- Some source families expose free-text search rather than structured doctrine
  filters. For example, Constitutional Court doctrine discovery is keyword-based
  unless the loaded detail itself provides stronger structure.
- Annex/form body extraction preserves plain text even when table structuring is
  low confidence. Empty structured rows do not necessarily mean no criteria
  exist.

## Effective Date Versus Promulgation Date

Use effective-date lookups for current-force questions. Use promulgation-date
lookups to resolve enacted-law bridge metadata or historical promulgation
context. A promulgated law can be source-loadable while not yet effective on the
answer's reference date.

When the reference date matters, pass `as_of` and inspect `ContextGap` values
such as `not_effective_as_of`.

## Source Failures

`RateLimitError`, `RetryExhaustedError`, and other `SourceApiError` states mean
source access failed. Treat them as temporary source-access problems or explicit
gaps, not as legal absence.

## Raw Payloads

Public return models keep normalized fields first. Raw law.go.kr payloads are
available through `to_dict(include_raw=True)` for debugging parser or source
shape issues, but normal application context should use the default
`include_raw=False`.
