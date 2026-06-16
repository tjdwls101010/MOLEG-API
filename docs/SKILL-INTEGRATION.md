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
- law terms, related terms, related articles, related laws, query expansion, and comparable-mechanism discovery

Use WebSearch for facts outside MOLEG's legal corpus:
- latest social context
- statistics
- news
- policy announcements
- recent government reports
- non-legal background evidence

## Progressive Loading Rules

Use MOLEG-API in layers instead of asking one call to load everything:

1. Start with candidate/planning interfaces such as `search_laws()`, `expand_legal_query()`, `find_comparable_mechanisms()`, `search_administrative_rules()`, `search_annex_forms()`, `search_interpretations()`, and judicial searches.
2. Load full text only for sources that are likely to matter: `get_law()`, `get_article()`, `get_administrative_rule()`, `get_annex_form_body()`, `get_interpretation()`, `get_case()`, or `get_constitutional_decision()`.
3. Use `load_legal_context_bundle()` as a staged first pass when the question is broad or under-specified. Treat its candidates and deferred lookups as the next menu, not as proof that every relevant source body has been inspected.
4. Use `load_institutional_system()` after the skill has an explicit statute set for one 제도. It composes those statutes into one staged bundle; it does not discover the set or decide which statute is primary.

Do not optimize for the absolute smallest number of public methods. A single maximal API wastes context and hides source-choice decisions. Do not optimize for one method per source endpoint either. The right public method is one Claude can choose by legislative intent.

Do not treat unused law.go.kr endpoints as missing context. If a source is optional, demand-gated, customized, local-only, or outside the user's legislative question, leave it alone until it prevents answering a concrete question.

## Default Workflow From A Promulgated Bill

1. Query `congress-db` for the bill and its promulgation bridge fields.
2. Call `resolve_promulgated_law(prom_law_nm=..., prom_no=..., promulgation_dt=...)`.
3. If the result is ambiguous, surface the candidates instead of choosing silently.
4. Call `get_law(..., basis="effective")` or `get_article(..., basis="effective")` to inspect the text currently in force.
5. Call `trace_law_history()` or `compare_law_versions()` to explain what the bill changed. When `congress-db` already returned the enacting `bill_id`, pass a `promulgation_bridge` map so matching `HistoryEvent` rows carry that `bill_id`.
6. Call `find_delegated_rules()` to inspect article-level delegation to enforcement decrees, enforcement rules, notices, and administrative rules.
7. Call `get_law_structure()` when the task needs the broader `lsStmd` law hierarchy across statutes, enforcement instruments, and administrative rules; do not expect article-level `source_article` links from this structure.
8. Call `search_administrative_rules()` and `get_administrative_rule()` when delegated or practical execution criteria may live in notices, directives, established rules, or other administrative rules.
9. Call `search_annex_forms()` when the legal question may depend on attached tables, thresholds, amounts, criteria, application formats, or other 별표ㆍ서식 material. Call `get_annex_form_body()` for selected candidates before treating the attached content as inspected.
10. Call `search_interpretations()` and `search_cases()` when legal meaning, application constraints, or constitutional risk matter.
11. Use WebSearch only for current social facts or context outside law.go.kr.

## Query Planning Rules

- Prefer effective-date basis for "current law", "now in force", and "현재 시행" questions.
- Use promulgation-date basis when resolving a `congress-db` promulgation bridge or reconstructing historical promulgation context.
- Use `trace_law_history()` without article/date filters when law-level amendment chronology matters. It parses the HTML-only `lsHistory` list table into normalized metadata events. Use `trace_law_history(article=...)` when the wording evolution of one provision matters; article-scoped events may include `article_text` for the post-change snapshot, while full-law history keeps `article_text=None`.
- Treat `HistoryEvent.promulgation_law_name`, `HistoryEvent.promulgation_number`, and `HistoryEvent.promulgation_date` as the bridge keys for joining back to `congress-db.public.bill_final_outcomes(prom_law_nm, prom_no, promulgation_dt)`. `HistoryEvent.bill_id` is populated only when the caller supplies a bridge map; MOLEG-API does not query `congress-db` directly.
- Treat law-name search as candidate discovery. Multiple plausible results are an ambiguity, not permission to pick the first hit.
- Use `expand_legal_query()` for search planning, not as final legal authority; its follow-up searches can include annex/form discovery before WebSearch handoff.
- Treat annex/form search as candidate discovery. It exposes metadata and file/detail links; call `get_annex_form_body()` for a selected law/admin-rule candidate when the attached table, threshold, amount, criterion, or form may be operative. If `AnnexFormText.structured_data` is present, use `parsing_confidence` before relying on rows; the plain `text` remains the fallback source for irregular or low-confidence tables.
- Treat administrative-rule `source_law_id`, `source_law_name`, `source_article`, and `source_article_title` as source-provided back-references only. If they are `None`, the correct interpretation is "not exposed in this MOLEG payload"; do not infer that the rule has no authorizing statute.
- Use `find_comparable_mechanisms()` when the task is legislative design or comparative 제도 discovery, such as "find statutes with similar 과징금, 인허가, 신고제, authorization, or sanction structures." Treat the returned `LawIdentity` values as planning candidates with article/source provenance; load the selected law or article before citing or drawing a legal conclusion.
- Treat constitutional doctrines such as `과잉금지원칙` or `평등원칙` as free-text search terms, not structured filters. The law.go.kr `detc` source does not expose a doctrine/category field, so `search_constitutional_decisions(search_body=True)` can find candidate decisions by keyword but cannot prove doctrine-indexed coverage.
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

The bundle contract for Claude is in `docs/design/LEGAL-CONTEXT-BUNDLE.md`. `MolegApi.load_legal_context_bundle()` implements staged loading: statutes/articles first, delegated context next, administrative-rule and annex/form candidates when lower-rule or attached material may matter, interpretation and judicial context as bounded candidates with selective full-text loading, and explicit WebSearch gaps for latest social context.
`MolegApi.load_institutional_system()` uses the same bundle shape for multi-statute 제도 review when Claude already selected the statutes. It loads statute text/articles, law structures, and delegations for each statute, then leaves administrative-rule, annex/form, interpretation, case, and constitutional detail as candidates or deferred follow-ups.

## Expected Public Interfaces

These interfaces are implemented as the skill-facing contract. The future skill should expect task-level functions rather than raw MOLEG targets:

- `MolegApi.search_laws()`
- `MolegApi.resolve_promulgated_law()`
- `MolegApi.get_law()`
- `MolegApi.get_article()`
- `MolegApi.trace_law_history()`
- `MolegApi.compare_law_versions()`
- `MolegApi.find_delegated_rules()`
- `MolegApi.get_law_structure()`
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
- `MolegApi.find_comparable_mechanisms()`
- `MolegApi.load_legal_context_bundle()`
- `MolegApi.load_institutional_system()`

These interfaces are implemented across the initial core slices. Administrative-rule search uses source `admrul` but exposes `issued_on` rather than `as_of` because the catalog filter is 발령일자, not a true effective-date basis. Annex/form search uses `licbyl` and `admbyl` internally while exposing task terms such as `source`, `search_scope`, and `annex_type`; selected bodies load through `get_annex_form_body()` text-export calls rather than direct HWP/PDF parsing, with optional conservative `structured_data` for clear table-like text exports. Interpretation search uses official `expc` and registry-backed ministry `*CgmExpc` targets while preserving source authority labels; `source="all"` means MOLEG plus one specified ministry, while `source="all_ministries"` performs an explicit high-cost fan-out across the ministry registry. The implementation normalizes live `Expc.expc` and `CgmExpc.cgmExpc` list wrappers so Claude does not need to know those source shapes. Case search uses `prec`; Constitutional Court decision search uses `detc`. Query expansion uses legal terms, everyday terms, related terms/articles/laws, AI search surfaces, and annex/form follow-up recommendations as planning hints only. Comparable-mechanism discovery uses `aiSearch`, `aiRltLs`, and `lstrmRltJo` to return bounded law candidates with endpoint/article provenance, not a ranked 제도 taxonomy. The context bundle composes those interfaces into one staged loading surface for Claude, while preserving deferred lookups, ambiguities, WebSearch gaps, and conditionally loaded interpretation/judicial detail when the first bundle needs it. Institutional-system loading reuses that bundle shape for an explicit statute set and records the input statutes in `request.statute_ids`.

Administrative-rule back-references are deliberately conservative. MOLEG-API can surface the delegating statute/article from explicit `admrul` metadata such as 위임/근거/수권/상위 법령ㆍ조문 fields or an explicitly named `위임근거` field, but it does not parse ordinary body text, change reasons, or run reverse delegation lookups to fabricate missing links.

## Answering Discipline For The Skill

- Never describe a proposed bill as current law unless MOLEG-API or another authoritative enacted-law source proves it.
- State whether a law text was retrieved by effective-date or promulgation-date basis when the distinction matters.
- Cite source type and identity metadata with legal text.
- Use `referenced_articles` and `reviewed_articles` on interpretation, case, and Constitutional Court detail results to filter by article before spending reasoning budget on full free-text review.
- Surface ambiguity and no-result states clearly.
- Move to WebSearch for latest non-legal facts instead of forcing MOLEG-API to answer them.
- When annex/form candidates appear, mention them as possible operative attached material unless the answer has actually inspected the selected body through `get_annex_form_body()` or another authoritative source.
- Treat `expand_legal_query()` output as candidate planning context. It can suggest terms, laws, articles, and WebSearch follow-ups, but it is not a source to cite as final authority.
- Treat `load_legal_context_bundle()` as source loading, not legal reasoning. Claude still decides what each loaded source means and which deferred lookups to run; eager-loaded interpretation/case/Constitutional Court detail is a bounded first pass, not an exhaustive authority survey.
- Treat `load_institutional_system()` as composition over a statute set Claude already chose. If the statute set is uncertain, run `search_laws()` / `expand_legal_query()` first and surface ambiguity instead of asking MOLEG-API to infer the 제도.
- Treat `find_comparable_mechanisms()` output as candidate planning context. It can suggest statutes and article anchors for comparison, but the skill must inspect selected sources before saying the mechanisms are legally equivalent or appropriate for a new bill.
