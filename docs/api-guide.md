# API Guide

`MolegApi` exposes task-level methods. Callers choose an interface by the legal
work they need to perform, not by raw law.go.kr endpoint names.

## Candidate Search

Use search methods when the source identity is not fixed yet. Search results are
candidate metadata and usually include a `follow_up` lookup for the selected
detail loader.

| Interface | Use when | Next step |
|---|---|---|
| `search_laws()` | Find current or promulgated statute identities. | `get_law()` or `get_article()` |
| `search_administrative_rules()` | Find notices, directives, established rules, and other administrative rules. | `load_administrative_rule_context()` |
| `search_annex_forms()` | Find statute or administrative-rule annexes/forms. | `get_annex_form_body()` |
| `search_interpretations()` | Find MOLEG or ministry interpretation candidates. | `get_interpretation()` |
| `search_cases()` | Find ordinary court case candidates. | `get_case()` |
| `search_constitutional_decisions()` | Find Constitutional Court decision candidates. | `get_constitutional_decision()` |
| `find_comparable_mechanisms()` | Find laws/articles with similar legal mechanisms for design comparison. | Load selected law or article first. |

Do not cite search hits as legal substance. They are candidates until a selected
detail method has loaded text.

## Statute Text And Articles

| Interface | Use when |
|---|---|
| `resolve_promulgated_law()` | Resolve enacted-bill bridge fields such as law name, promulgation number, and promulgation date. |
| `get_law()` | Load one statute text, optionally limited to selected articles. |
| `get_article()` | Load one precise article by human article label such as `제10조의2`. |
| `load_article_context()` | Load an article and follow moved/deleted article state before citing current substance. |
| `trace_law_history()` | Inspect law or article amendment chronology. |
| `compare_law_versions()` | Load before/after wording deltas from MOLEG's old-and-new surface. |

Use `basis="effective"` for current-force questions. Use
`basis="promulgated"` for promulgation bridge and historical promulgation
contexts. Pass `as_of` when the answer depends on a reference date.

## Delegation, Hierarchy, And Operational Criteria

| Interface | Use when |
|---|---|
| `find_delegated_rules()` | Inspect article-level delegation rows from a known statute. |
| `get_law_structure()` | Load broader statute -> enforcement instrument -> administrative-rule hierarchy. |
| `get_administrative_rule()` | Load selected administrative-rule text. |
| `load_administrative_rule_context()` | Load selected administrative-rule text while handling moved/deleted articles. |
| `get_annex_form_body()` | Load selected annex/form body text and optional structured table rows. |
| `load_delegated_criteria()` | From a known statute/article, load bounded administrative-rule and annex/form bodies for operational criteria. |

`get_law_structure()` is hierarchy context. It does not prove article-level
delegation or inspect lower-rule body text.

## Interpretations, Cases, And Constitutional Decisions

| Interface | Use when |
|---|---|
| `get_interpretation()` | Load selected interpretation detail. |
| `get_case()` | Load selected ordinary court decision detail. |
| `get_constitutional_decision()` | Load selected Constitutional Court decision detail. |
| `load_authority_context()` | Load authority candidates/details around specific statute articles. |

MOLEG official interpretations, ministry first-instance interpretations,
ordinary court cases, and Constitutional Court decisions have different source
authority. Keep them separate in downstream reasoning and citation.

## Planning And Bundles

| Interface | Use when |
|---|---|
| `expand_legal_query()` | Expand a query into law, term, related-law/article, authority, annex, and WebSearch planning candidates. |
| `load_legal_context_bundle()` | Load a staged first pass for a broad question or statute/bill anchor. |
| `load_institutional_system()` | Compose a caller-selected statute set into one staged bundle. |
| `load_followup()` | Execute a `DeferredLookup` or `FollowUpSearch` returned by another interface. |

Bundles are source-loading packets, not final legal conclusions. Inspect
`loaded`, `candidates`, `deferred`, `ambiguities`, `gaps`, and `source_notes`
before deciding what to load next.

## Errors To Expect

- `NoResultError`: the requested source or selected text was not found.
- `AmbiguousLawError`: several identities matched and the caller must choose.
- `SourceApiError`, `RateLimitError`, `RetryExhaustedError`: law.go.kr access failed.
- `UnsupportedFormatError`: the requested format, handoff, or source path is outside this interface.
- `ParseFailureError`: law.go.kr returned data that could not be normalized.

Source-access failures are not legal no-results. Retry or surface the source
gap rather than claiming the law or authority does not exist.
