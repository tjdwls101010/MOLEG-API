# MOLEG-API Skill Integration

This document describes how the future legislative-expert skill should use MOLEG-API alongside `congress-db` and WebSearch. It is a living integration guide; update it when public interfaces or source traps change.

The intended user is Claude with a legislative-expert skill loaded. MOLEG-API should therefore return normalized legal context that can be inserted into reasoning, citations, and follow-up calls, not raw endpoint payloads that force the skill prompt to memorize law.go.kr trivia.

For package installation, serialization examples, vendored fallback, and skill-runtime error handling, use `docs/SKILL-AUTHOR-COOKBOOK.md`.

## Source Responsibilities

Use `congress-db` for National Assembly facts:
- bills and bill versions
- sponsors and committees
- votes
- minutes and meeting-bill links
- promulgation bridge fields: `prom_law_nm`, `prom_no`, `promulgation_dt`

The live `congress-db` schema was introspected through the read-only `congress_ro` Neon role. The current evidence is stored in `docs/design/congress-db-introspection/`. The bridge fields live in `public.bill_final_outcomes`, joined to `public.bills` by stable `bill_no`.

Use MOLEG-API for legal sources from law.go.kr:
- current statutes and articles
- promulgation-date and effective-date law identity resolution
- law history and before/after comparison
- delegated enforcement decrees, enforcement rules, notices, and administrative rules
- annex/form candidates and selected text bodies for statutes and administrative rules
- MOLEG official interpretations and ministry first-instance interpretations
- Supreme Court cases and Constitutional Court decisions
- law terms, related terms, related articles, related laws, and query expansion

Use WebSearch for facts outside MOLEG's legal corpus:
- latest social context
- statistics
- news
- policy announcements
- recent government reports
- non-legal background evidence

## Progressive Loading Rules

Use MOLEG-API in layers instead of asking one call to load everything:

1. Start with candidate/planning interfaces such as `search_laws()`, `expand_legal_query()`, `search_administrative_rules()`, `search_annex_forms()`, `search_interpretations()`, and judicial searches.
2. Load full text only for sources that are likely to matter: `get_law()`, `get_article()`, `get_administrative_rule()`, `get_annex_form_body()`, `get_interpretation()`, `get_case()`, or `get_constitutional_decision()`.
3. Use `load_legal_context_bundle()` as a staged first pass when the question is broad or under-specified. Treat its candidates and deferred lookups as the next menu, not as proof that every relevant source body has been inspected.

Do not optimize for the absolute smallest number of public methods. A single maximal API wastes context and hides source-choice decisions. Do not optimize for one method per source endpoint either. The right public method is one Claude can choose by legislative intent.

Do not treat unused law.go.kr endpoints as missing context. If a source is optional, demand-gated, customized, local-only, or outside the user's legislative question, leave it alone until it prevents answering a concrete question.

## Default Workflow From A Promulgated Bill

1. Query `congress-db` for the bill and its promulgation bridge fields.
2. Call `resolve_promulgated_law(prom_law_nm=..., prom_no=..., promulgation_dt=...)`.
3. If the result is ambiguous, surface the candidates instead of choosing silently.
4. Call `get_law(..., basis="effective")` or `get_article(..., basis="effective")` to inspect the text currently in force.
5. Call `trace_law_history()` or `compare_law_versions()` to explain what the bill changed.
6. Call `find_delegated_rules()` to inspect enforcement decrees, enforcement rules, notices, and administrative rules.
7. Call `search_administrative_rules()` and `get_administrative_rule()` when delegated or practical execution criteria may live in notices, directives, established rules, or other administrative rules.
8. Call `search_annex_forms()` when the legal question may depend on attached tables, thresholds, amounts, criteria, application formats, or other 별표ㆍ서식 material. Call `get_annex_form_body()` for selected candidates before treating the attached content as inspected.
9. Call `search_interpretations()` and `search_cases()` when legal meaning, application constraints, or constitutional risk matter.
10. Use WebSearch only for current social facts or context outside law.go.kr.

## Query Planning Rules

- Prefer effective-date basis for "current law", "now in force", and "현재 시행" questions.
- Use promulgation-date basis when resolving a `congress-db` promulgation bridge or reconstructing historical promulgation context.
- Use `trace_law_history()` without article/date filters when law-level amendment chronology matters. It parses the HTML-only `lsHistory` list table into normalized events; article/date filters still use JSON-reachable history surfaces.
- Treat law-name search as candidate discovery. Multiple plausible results are an ambiguity, not permission to pick the first hit.
- Use `expand_legal_query()` for search planning, not as final legal authority; its follow-up searches can include annex/form discovery before WebSearch handoff.
- Treat annex/form search as candidate discovery. It exposes metadata and file/detail links; call `get_annex_form_body()` for a selected law/admin-rule candidate when the attached table, threshold, amount, criterion, or form may be operative.
- Preserve source authority labels in answers: MOLEG interpretation, ministry interpretation, Supreme Court case, and Constitutional Court decision are different source types.

## Fallback Rules

- If MOLEG-API cannot answer because the needed source is outside law.go.kr, use WebSearch.
- If MOLEG-API finds no law for a bill that has no promulgation bridge, return to `congress-db` and treat the bill as not proven enacted/current.
- If a `congress-db` promulgation bridge does not exactly resolve but the bundle returns law-name candidates with `source_lag_or_manual_review_required`, explain the source-lag/manual-review state instead of saying the bill was not enacted.
- If MOLEG-API raises `RateLimitError` or `RetryExhaustedError`, treat it as a temporary source-access problem, not proof that the legal source does not exist.
- If a source endpoint is HTML-only, use the documented parser/fallback for that interface; do not assume JSON exists. `lsHistory` is supported only through its list table parser, not by treating the law.go.kr UI iframe as stable structured data.
- If a law delegates details to lower rules, do not stop at statute text unless the user explicitly asks for statute-only review.
- If a result points to annex/form files that likely carry the operative criteria, run `get_annex_form_body()` for the selected candidate or surface the remaining direct HWP/PDF limitation instead of pretending statute text is complete.

## Context Bundle

The bundle contract for Claude is in `docs/design/LEGAL-CONTEXT-BUNDLE.md`. `MolegApi.load_legal_context_bundle()` implements staged loading: statutes/articles first, delegated context next, administrative-rule and annex/form candidates when attached material may matter, conditional top-ranked interpretation/case/Constitutional Court detail when the question asks for legal meaning, application, precedent, or constitutional-risk analysis, deferred follow-up handles for the remaining candidates, and WebSearch gaps for latest social context.

## Expected Public Interfaces

These names may change as implementation settles, but the future skill should expect task-level functions rather than raw MOLEG targets:

- `MolegApi.search_laws()`
- `MolegApi.resolve_promulgated_law()`
- `MolegApi.get_law()`
- `MolegApi.get_article()`
- `MolegApi.trace_law_history()`
- `MolegApi.compare_law_versions()`
- `MolegApi.find_delegated_rules()`
- `MolegApi.search_administrative_rules()`
- `MolegApi.get_administrative_rule()`
- `MolegApi.search_annex_forms()`
- `MolegApi.get_annex_form_body()`
- `MolegApi.search_interpretations()`
- `MolegApi.get_interpretation()`
- `MolegApi.search_cases()`
- `MolegApi.get_case()`
- `MolegApi.search_constitutional_decisions()`
- `MolegApi.get_constitutional_decision()`
- `MolegApi.expand_legal_query()`
- `MolegApi.load_legal_context_bundle()`

These interfaces are implemented across the initial core slices. Administrative-rule search uses source `admrul` but exposes `issued_on` rather than `as_of` because the catalog filter is 발령일자, not a true effective-date basis. Annex/form search uses `licbyl` and `admbyl` internally while exposing task terms such as `source`, `search_scope`, and `annex_type`; selected bodies load through `get_annex_form_body()` text-export calls rather than direct HWP/PDF parsing. Interpretation search uses official `expc` and registry-backed ministry `*CgmExpc` targets while preserving source authority labels; `source="all"` means MOLEG plus one specified ministry, while `source="all_ministries"` performs an explicit high-cost fan-out across the ministry registry. The implementation normalizes live `Expc.expc` and `CgmExpc.cgmExpc` list wrappers so Claude does not need to know those source shapes. Case search uses `prec`; Constitutional Court decision search uses `detc`. Query expansion uses legal terms, everyday terms, related terms/articles/laws, AI search surfaces, and annex/form follow-up recommendations as planning hints only. The context bundle composes those interfaces into one staged loading surface for Claude, while preserving deferred lookups, ambiguities, WebSearch gaps, and conditionally loaded interpretation/judicial detail when the first bundle needs it.

## Answering Discipline For The Skill

- Never describe a proposed bill as current law unless MOLEG-API or another authoritative enacted-law source proves it.
- State whether a law text was retrieved by effective-date or promulgation-date basis when the distinction matters.
- Cite source type and identity metadata with legal text.
- Surface ambiguity and no-result states clearly.
- Move to WebSearch for latest non-legal facts instead of forcing MOLEG-API to answer them.
- When annex/form candidates appear, mention them as possible operative attached material unless the answer has actually inspected the selected body through `get_annex_form_body()` or another authoritative source.
- Treat `expand_legal_query()` output as candidate planning context. It can suggest terms, laws, articles, and WebSearch follow-ups, but it is not a source to cite as final authority.
- Treat `load_legal_context_bundle()` as source loading, not legal reasoning. Claude still decides what each loaded source means and which deferred lookups to run; eager-loaded interpretation/case/Constitutional Court detail is a bounded first pass, not an exhaustive authority survey.
