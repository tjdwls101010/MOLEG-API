# MOLEG-API PRD

## Problem Statement

The future legislative-expert skill needs reliable access to law.go.kr legal sources, but the source OpenAPI catalog contains 195 guides with duplicated surfaces, mobile views, demand-gated domains, source-specific key names, and date-basis traps.

A shallow SDK with one function per endpoint would push source complexity onto the skill caller. That would make the caller remember raw `target` values, choose between promulgation-date and effective-date endpoints, format article numbers as `JO`, and distinguish MOLEG interpretations, ministry interpretations, cases, and Constitutional Court decisions on every request.

## Solution

Build MOLEG-API as a small set of deep task-level interfaces for legislative work. The implementation may call many source endpoints internally, but the public surface should speak in legal tasks: search laws, resolve promulgated law identity, get effective text, get an article, trace history, compare versions, find delegated rules, search administrative rules, search annex/forms, load selected annex/form bodies, search interpretations, search cases, expand legal queries, and discover comparable legal mechanisms.

The live MOLEG API and the local catalog DB remain authoritative for endpoint behavior. Design docs record scope, traps, and decisions, but implementation should verify source behavior through the current catalog and live samples when credentials are available.

The primary caller is Claude running the future legislative-expert skill. Interfaces should return enough normalized context for that caller to combine MOLEG legal sources with `congress-db` bill facts and WebSearch social context without loading raw endpoint trivia into the skill prompt.

The public surface must balance two failure modes: too many methods make Claude choose among confusing source-specific tools, while too few methods force oversized responses that waste context. MOLEG-API should expose progressive loading: cheap candidate/search calls first, explicit detail loaders second, and budgeted bundles that stage likely context without pretending to load everything.

Completeness means covering the legal-source paths a legislative expert repeatedly needs, not using every law.go.kr OpenAPI. Catalog entries that are local, customized, narrow, duplicated, user-specific, or outside national legislative analysis should remain optional or rejected until a concrete skill scenario proves their value.

## User Stories

1. As a legislative-expert skill, I want to search current laws by name, so that I can find candidate law identities without choosing raw MOLEG targets.
2. As a legislative-expert skill, I want effective-date lookup to be the default for current-force questions, so that I do not confuse promulgated text with text in force.
3. As a legislative-expert skill, I want promulgation-date lookup to remain available, so that I can connect `congress-db` promulgation bridge fields to law.go.kr identities.
4. As a legislative-expert skill, I want ambiguous law-name matches surfaced explicitly, so that I do not silently cite the wrong law.
5. As a legislative-expert skill, I want a normalized law identity, so that I can reason across `ID`, `MST`, `LID`, law name, promulgation number, promulgation date, and effective date.
6. As a legislative-expert skill, I want full law text through a public interface, so that I can inspect the current effective statute without knowing the source endpoint.
7. As a legislative-expert skill, I want specific article retrieval by human article notation, so that I do not format MOLEG's six-digit `JO` values myself.
8. As a legislative-expert skill, I want article retrieval to preserve source metadata, so that citations remain auditable.
9. As a legislative-expert skill, I want to trace law history, so that I can explain what changed and when.
10. As a legislative-expert skill, I want to compare versions before and after a date or amendment, so that I can connect legislative action to current legal text.
11. As a legislative-expert skill, I want to find delegated rules from a statute or article, so that I do not miss enforcement decrees, enforcement rules, notices, or administrative rules.
12. As a legislative-expert skill, I want to search administrative rules, so that I can find practical execution criteria not visible in statute text alone.
13. As a legislative-expert skill, I want to retrieve administrative-rule text, so that I can cite notices, directives, and established rules.
14. As a legislative-expert skill, I want to search law and administrative-rule annex/form candidates, so that I do not miss attached tables, thresholds, amounts, criteria, or required forms.
15. As a legislative-expert skill, I want to load the text body for a selected annex/form candidate, so that I can inspect operative tables and forms without parsing raw HWP/PDF files myself.
16. As a legislative-expert skill, I want to search MOLEG official interpretations, so that I can identify official interpretation constraints.
17. As a legislative-expert skill, I want to search ministry first-instance interpretations by ministry/source registry, so that the public interface does not expose dozens of ministry-specific functions.
18. As a legislative-expert skill, I want to search Supreme Court cases, so that I can identify judicial interpretations and limits.
19. As a legislative-expert skill, I want to search Constitutional Court decisions separately, so that constitutional-risk analysis keeps authority labels intact.
20. As a legislative-expert skill, I want legal-term and related-law expansion, so that I can plan better searches without treating expansion results as final authority.
21. As a legislative-expert skill, I want to find statutes containing similar legal mechanisms for a concept such as 과징금, 인허가, or 신고제, so that I can compare legislative design patterns before drafting or reviewing a bill.
22. As a legislative-expert skill, I want a staged legal context bundle, so that I can load statutes, delegations, administrative rules, annex/form candidates, interpretations, cases, Constitutional Court decisions, ambiguity records, and WebSearch gaps without memorizing source call order.
23. As a legislative-expert skill, I want clear error types for no result, ambiguity, unsupported format, source API error, parse failure, and retry exhaustion, so that I can decide whether to ask the user, retry, or fall back.
24. As a legislative-expert skill, I want guidance on when to use WebSearch instead, so that latest social context is not incorrectly searched in MOLEG.
25. As a legislative-expert skill, I want normalized result objects to serialize without raw source payloads by default, so that I can place legal context into Claude prompts without wasting budget on endpoint-shaped data.
26. As a legislative-expert skill, I want law and administrative-rule supplementary provisions exposed as structured text, so that 시행일, 적용례, and 경과조치 questions do not depend on raw source payload parsing.
27. As a legislative-expert skill, I want article text to preserve nested 항, 호, and 목 units, so that definitions, application targets, exceptions, and requirements are not lost when MOLEG splits them outside top-level `조문내용`.
28. As a legislative-expert skill, I want article status fields exposed, so that a returned deleted or moved article is not cited as current operative text.

## Implementation Decisions

- Public interfaces hide raw MOLEG `target` values from callers.
- The first vertical slice is law search or promulgation-bridge candidate resolution -> normalized law identity -> effective-date law text or article retrieval.
- `basis` is explicit where date basis matters, and current-force workflows default to effective-date reasoning.
- MOLEG authentication comes from environment variables such as `MOLEG_OC`; secrets are never committed.
- The local catalog DB `.Seongjin/DataBases/법제처 api.db` is inspected before endpoint choices are made.
- `docs/design/MOLEG-API-AUDIT.md` records the 195-guide catalog classification and source format/key notes.
- `congress-db` is introspected read-only from the Neon `congress_ro` role and documented under `docs/design/congress-db-introspection/`; it is a reference fact DB, not this repository's implementation database.
- The promulgation bridge currently lives in `public.bill_final_outcomes` with `prom_law_nm`, `prom_no`, and `promulgation_dt`.
- Live tests are separate from deterministic tests. Normal tests should use fakes, recorded fixtures, or local adapters; live smoke tests should require explicit credentials/marker.
- The live source adapter distinguishes rate limits and retry exhaustion from legal no-result states.
- Caching starts small. Do not build a mirror DB until repeated calls prove a speed or cost problem.
- Add a public method only when it represents a recurring legislative task Claude can choose by intent. Do not expose a method merely because a source endpoint exists.
- Before promoting an optional source, document the legislative-expert scenario it serves and the reasoning failure it prevents. Otherwise, leave it out of the public surface.
- Keep noisy or expensive detail behind explicit loaders or `DeferredLookup` records. Candidate lists and context bundles should reveal what may matter without automatically spending context on every source body.
- A context bundle is an entry point, not a maximal answer object. It should load high-leverage anchors and bounded candidates, then leave selective follow-up calls visible to Claude. It cannot prove exhaustive authority coverage or absence of contrary interpretation, case, Constitutional Court, administrative-rule, or annex/form sources by itself.
- Annex/form body loading uses law.go.kr text-export endpoints for selected law and administrative-rule candidates. Direct HWP/PDF parsing remains outside the first body-loading interface.
- MOLEG-API is packaged as the `moleg-api` Python package; PyPI publication remains a human release step. Public model dataclasses serialize through `to_dict(include_raw=False)` and `to_json_string(include_raw=False)`, omitting `raw` payloads recursively by default.

## Public Interface

These are implemented public `MolegApi` methods. Type-level details live in code and docstrings; this list keeps the PM/spec view aligned with the callable skill surface.

- `search_laws(query, *, as_of=None, basis="effective", law_type=None, ministry=None, display=20)`
- `get_law(identifier, *, as_of=None, basis="effective", articles=None, include_metadata=True)`
- `get_article(law_identifier, article, *, as_of=None, basis="effective")`
- `load_article_context(law_identifier, article, *, as_of=None, basis="effective", follow_moved=True)`
- `trace_law_history(law_identifier, *, date_range=None, article=None, promulgation_bridge=None)`
- `compare_law_versions(law_identifier, *, before=None, after=None, article=None)`
- `find_delegated_rules(law_identifier, *, article=None)`
- `get_law_structure(law_identifier, *, depth=0)`
- `search_administrative_rules(query, *, ministry=None, rule_type=None, issued_on=None, include_history=False, display=20)`
- `get_administrative_rule(identifier, *, articles=None, include_metadata=True)`
- `load_administrative_rule_context(identifier, *, articles=None, include_metadata=True, follow_moved=True)`
- `search_annex_forms(query, *, source="law", search_scope="source", annex_type=None, ministry=None, display=20)`
- `get_annex_form_body(identifier, *, source="law", title=None, include_metadata=True, attempt_structuring=True)`
- `search_interpretations(query, *, source="moleg", ministry=None, search_body=False, interpreted_on=None, display=20)`
- `get_interpretation(identifier, *, source=None, ministry=None, include_metadata=True)`
- `search_cases(query, *, court="all", court_name=None, search_body=False, decided_on=None, case_number=None, display=20)`
- `get_case(identifier, *, include_metadata=True)`
- `search_constitutional_decisions(query, *, search_body=False, decided_on=None, case_number=None, display=20)`
- `get_constitutional_decision(identifier, *, include_metadata=True)`
- `load_authority_context(law_identifier, *, articles, query=None, budget="standard", as_of=None)`
- `expand_legal_query(query, *, display=5, include_websearch_hint=True)`
- `find_comparable_mechanisms(concept, *, display=5)`
- `load_legal_context_bundle(query=None, *, promulgation_bridge=None, law_identifier=None, articles=None, mode="question", budget="standard", as_of=None)`
- `load_institutional_system(statute_identifiers, *, articles=None, budget="standard", as_of=None)`
- `load_delegated_criteria(law_identifier, *, articles=None, query=None, budget="standard", as_of=None)`
- `resolve_promulgated_law(*, prom_law_nm=None, prom_no=None, promulgation_dt=None)`

`compare_law_versions(before=..., after=...)` is present as a guardrail-compatible signature, but arbitrary caller-selected date windows are not source-backed; passing those arguments is rejected rather than silently pretending to compare them.

The interface principle should not change: one deep module per recurring legal task is better than one shallow function per MOLEG endpoint.

## Testing Decisions

- Tests should exercise public interfaces, not internal source-target helper functions.
- The first deterministic tests prove law search, identity normalization, promulgation bridge resolution, law text retrieval, article retrieval, ambiguity handling, and no-result handling through `MolegApi`.
- Live smoke tests should verify representative real source responses across implemented public interfaces when `MOLEG_OC` is available, while remaining skipped in normal deterministic runs without credentials.
- Parser tests should use recorded source-shaped payloads for JSON and, where needed, XML/HTML.

## Implemented Core Slices

- `MolegApi.search_laws()` searches law names without exposing raw `law` / `eflaw` targets to callers. Search hits are identity candidates; law text, article wording, duties, sanctions, and procedures require selected `get_law()` or `get_article()` loading before citation.
- `MolegApi.resolve_promulgated_law()` accepts `congress-db` bridge fields (`prom_law_nm`, `prom_no`, `promulgation_dt`) and returns one normalized `LawIdentity` or raises no-result/ambiguity errors.
- `MolegApi.get_law()` retrieves effective/promulgation-basis law text and normalizes articles.
- `MolegApi.get_article()` accepts human article notation such as `제10조의2` and formats the source `JO` value internally.
- `MolegApi.load_article_context()` loads the requested article and, by default, follows `moved_to` to load the destination article before exposing `current_article` for substantive current/as-of claims. Deleted articles and failed destination loads produce gaps/deferred lookups instead of promoting movement or deletion markers as operative text.
- `MolegApi.get_law()` and `MolegApi.get_article()` preserve nested source 항, 호, and 목 text inside `ArticleText.text`, so callers can review definitions, application targets, exceptions, and requirements without parsing raw article payloads or relying on top-level `조문내용` alone.
- `ArticleText` and `AdministrativeRuleArticleText` expose source-backed article status fields (`article_kind`, `revision_type`, `moved_from`, `moved_to`, `has_changes`, `is_deleted`) so a deleted or moved article can be cited as source state without being treated as current operative text.
- `MolegApi.get_law()` returns normalized articles plus `supplementary_provisions` parsed from source 부칙 fields, preserving 부칙 공포일자, 부칙 공포번호, and text. Callers must cite supplementary provisions separately when discussing 시행일, 적용례, or 경과조치 rather than inferring those answers from main-article text or law-level `effective_date` metadata alone.
- `MolegApi.trace_law_history()` supports JSON-reachable article/date-range change history and full law-level history through the HTML-only `lsHistory` list table. Article-scoped history events carry `article_text` for the post-change article snapshot when law.go.kr provides it or when the snapshot can be loaded by effective/change date; full-law history remains metadata-only. Every history event exposes `promulgation_law_name`, normalized `promulgation_number`, and `promulgation_date` bridge keys for `congress-db` joins, and can carry `bill_id` when the caller supplies a bridge map. If the live HTML shape changes, parsing fails explicitly instead of returning partial or misleading history.
- `MolegApi.compare_law_versions()` normalizes the source-supplied `oldAndNew` before/after article text behind a public comparison interface and rejects unsupported arbitrary date-window arguments.
- `MolegApi.find_delegated_rules()` normalizes `lsDelegated` relationships so the caller sees delegated-rule context rather than raw lower-law fields.
- `MolegApi.get_law_structure()` loads the `lsStmd` law-structure hierarchy as normalized law and administrative-rule nodes, preserving nested 법률→시행령→시행규칙→행정규칙 relationships while leaving article-level delegation to `find_delegated_rules()`.
- `MolegApi.search_administrative_rules()` searches current or historical administrative rules through source `admrul`, preserving serial ID, rule ID, rule type, issuing date, effective date, ministry, current/history status, and explicit source-law/source-article back-references when the payload provides delegation/authorization metadata. Search hits are candidate metadata; article text, criteria, supplementary provisions, and current operational criteria require selected `get_administrative_rule()` detail loading before citation.
- `MolegApi.get_administrative_rule()` loads administrative-rule text by source serial ID, rule ID, or exact name and returns normalized structured articles when available, while preserving flat source text when the source does not expose article structure. Administrative-rule identity and article text expose `source_law_id`, `source_law_name`, `source_article`, and `source_article_title` only from explicit source metadata; absent values are not reverse-looked-up or guessed. Selected administrative-rule detail preserves `effective_date`, and callers must compare it to their reference date before treating the text as current operational criteria because administrative-rule search `issued_on` is an issuing-date filter. Administrative-rule 부칙 is exposed as `supplementary_provisions` rather than raw metadata.
- `MolegApi.load_administrative_rule_context()` loads selected administrative-rule articles, keeps deleted articles as source-state gaps, and follows moved articles to loaded destination articles before exposing `current_articles` for operational-criteria claims. Destination-load failures are preserved as gaps/deferred lookups rather than thrown after the initial selected rule is loaded.
- `MolegApi.search_annex_forms()` searches law and administrative-rule annex/form candidates through `licbyl` and `admbyl`, preserving related source identity, annex name/number/type, ministry/date metadata, and file/detail links while hiding source target and numeric code choices. Search hits are candidate metadata; attached thresholds, amounts, criteria, form content, body text, and extracted rows require selected `get_annex_form_body()` detail loading before citation.
- `MolegApi.get_annex_form_body()` loads a selected law or administrative-rule annex/form body through law.go.kr text-export endpoints, preserving source identity, extraction method, file type, confidence, and metadata. For table-like annexes, it attempts conservative text-table structuring into `StructuredTableData` while always preserving the original plain text; irregular tables return low-confidence structured data or text-only fallback rather than invented precision.
- `MolegApi.search_interpretations()` searches official MOLEG interpretations through `expc` and ministry first-instance interpretations through a registry-backed `*CgmExpc` source family, normalizing live `Expc.expc` and `CgmExpc.cgmExpc` list wrappers behind the public interface. `source="all"` means MOLEG plus one specified ministry and requires `ministry`; `source="all_ministries"` explicitly fans out across all ministry registry entries plus MOLEG for deeper institutional analysis. Search hits are candidate metadata; question, answer, reason, related-law analysis, and interpretation text require selected `get_interpretation()` detail loading before citation.
- `MolegApi.get_interpretation()` loads one interpretation by source ID and preserves source type, source target, ministry, case number, interpretation date, inquiry agency, reply/interpretation agency, question, answer, reason, related-law text, and structured `referenced_articles` parsed from that text when unambiguous.
- `MolegApi.search_cases()` and `MolegApi.get_case()` load Supreme Court/lower-court case context through `prec`, including case number, decision date, court, case type, holdings, summary, referenced statutes, structured `referenced_articles`, referenced cases, and full text. Search hits are candidate metadata; judicial holdings, summaries, referenced-statute reasoning, and full text require selected `get_case()` detail loading before citation.
- `MolegApi.search_constitutional_decisions()` and `MolegApi.get_constitutional_decision()` load Constitutional Court decision context through `detc`, preserving constitutional source labels, final date, case number, holdings, summary, reviewed statutes, referenced statutes, structured `reviewed_articles` / `referenced_articles`, referenced cases, and full text. Search hits are candidate metadata; holdings, summaries, reviewed-statute reasoning, referenced-statute reasoning, and full text require selected `get_constitutional_decision()` detail loading before citation.
- Loaded interpretation, case, and Constitutional Court details are not target-article authority unless their structured `referenced_articles` or `reviewed_articles` match the requested law/article; mismatched loaded authority details are follow-up search context, not citations.
- `MolegApi.load_authority_context()` starts from a statute/article anchor, loads bounded interpretation/case/Constitutional Court details, and separates all loaded details from `current_authorities`, which only includes structured article matches with parseable authority dates that do not predate the loaded current article wording. Mismatched, unverified, undated, or pre-amendment authority details stay in loaded context with gaps/deferred follow-ups instead of being promoted as current target-article authority.
- `MolegApi.expand_legal_query()` combines law-name search, legal terms, everyday terms, related terms, related articles, AI search, and related-law surfaces into query-planning candidates and follow-up search recommendations, including annex/form discovery before WebSearch handoff. Its output is not final legal authority; legal-term, related-law, related-article, and AI-search candidates require selected law/article detail loading before any legal-basis claim.
- `MolegApi.find_comparable_mechanisms()` uses AI search, related-law, and legal-term article surfaces to return bounded `LawIdentity` planning candidates for similar 제도/mechanism questions, with source endpoints and article anchors preserved in `raw_keys`. Its output is a discovery aid, not a ranked catalog or legal conclusion; selected article text must be loaded before legal-equivalence, source-structure, or design-suitability claims.
- `MolegApi.load_legal_context_bundle()` composes the task-level interfaces into a staged bundle for Claude, with loaded statute/article/delegation context, bounded administrative-rule and annex/form candidates, conditional eager loading for top-ranked interpretation/case/Constitutional Court detail when query intent warrants it, explicit follow-up detail loading for the rest, ambiguity records, and structured WebSearch gaps. Eager-loaded authority detail is bounded first-pass context, not an exhaustive authority survey or proof that no contrary authority exists. When requested articles are loaded, the bundle emits `authority_article_mismatch` gaps if eager-loaded interpretation/case/Constitutional Court detail references or reviews different articles, `authority_article_unverified` gaps if those structured article references are missing, `authority_article_partial_match` gaps if those structured references match only some requested articles, and `authority_temporal_mismatch` gaps if matching authority detail predates the loaded article's effective date or lacks a parseable authority date, so the skill runs scoped follow-up authority searches or history/as-of checks before citing those details for current target-article authority. When `as_of` is supplied, effective-basis law/article loaders use that reference date, version-sensitive structure/delegation follow-ups use the loaded article's `MST` when available, and the bundle emits `not_effective_as_of` if the loaded law's effective date is later than the reference date.
- `MolegApi` class and public-method docstrings provide method-selection guidance, return-shape summaries, error modes, and neighboring-interface distinctions for skill authors.
- `MolegApi.load_institutional_system()` composes an explicit set of statute identities into one staged institutional-system bundle, loading statute text/articles, law-structure hierarchy, and delegations while keeping administrative-rule, annex/form, interpretation, case, and constitutional detail as bounded candidates and deferred lookups. It accepts `as_of` for current-force review of the explicit statute set and emits `not_effective_as_of` for any loaded statute whose effective date is later than the reference date. It does not infer which statutes belong to a 제도, decide which statute is primary, or prove exhaustive discovery of every statute in the broader institution.
- `MolegApi.load_delegated_criteria()` starts from a known statute anchor and reuses the institutional-system bundle shape, but additionally loads bounded selected administrative-rule bodies and annex/form bodies into `LoadedContext`. It is for operational-criteria questions where candidate metadata is not enough; detail-load failures remain gaps plus deferred lookups, loaded administrative-rule source law/article references are checked against the target statute/article with `delegated_criteria_source_mismatch` or `delegated_criteria_source_unverified` gaps, and `as_of` still emits `not_effective_as_of` for future-effective loaded administrative rules.
- `LawGoKrClient` is the live JSON source adapter and reads `MOLEG_OC` from the environment.
- `LawGoKrClient` performs bounded retries for transient law.go.kr failures, including HTTP retryable statuses, URL errors, and read timeouts, and raises `RateLimitError` or `RetryExhaustedError` instead of collapsing temporary source-access failures into legal no-result states.
- Public model dataclasses expose recursive `to_dict()` and `to_json_string()` serialization. `raw` source payloads are omitted by default and included only when `include_raw=True`.
- `pyproject.toml` defines the distributable `moleg-api` package metadata; `docs/SKILL-AUTHOR-COOKBOOK.md` documents installation, canonical call sequences, serialization guidance, vendored fallback, and error handling for the future skill author.
- Normal tests use fake adapters; `tests/test_live_smoke.py` and `tests/test_live_e2e_scenarios.py` are marked `live` and skip unless `MOLEG_OC` exists. Smoke tests prove representative source families are callable; e2e scenarios prove legislative-expert workflows through public `MolegApi` methods.

## Out of Scope

- A generic wrapper for all 195 MOLEG guides.
- Direct SQL access to `congress-db`.
- Web search, news, statistics, or social-context retrieval.
- Local ordinance, treaty, administrative appeal, special administrative appeal, and committee-decision modules until repeated skill scenarios justify them.
- Direct HWP/PDF annex/form parsing and bulk attachment extraction. Selected law/admin-rule bodies are loaded through text-export endpoints instead.
- A large local mirror database.
