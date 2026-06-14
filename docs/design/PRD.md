# MOLEG-API PRD

## Problem Statement

The future legislative-expert skill needs reliable access to law.go.kr legal sources, but the source OpenAPI catalog contains 195 guides with duplicated surfaces, mobile views, demand-gated domains, source-specific key names, and date-basis traps.

A shallow SDK with one function per endpoint would push source complexity onto the skill caller. That would make the caller remember raw `target` values, choose between promulgation-date and effective-date endpoints, format article numbers as `JO`, and distinguish MOLEG interpretations, ministry interpretations, cases, and Constitutional Court decisions on every request.

## Solution

Build MOLEG-API as a small set of deep task-level interfaces for legislative work. The implementation may call many source endpoints internally, but the public surface should speak in legal tasks: search laws, resolve promulgated law identity, get effective text, get an article, trace history, compare versions, find delegated rules, search administrative rules, search interpretations, search cases, and expand legal queries.

The live MOLEG API and the local catalog DB remain authoritative for endpoint behavior. Design docs record scope, traps, and decisions, but implementation should verify source behavior through the current catalog and live samples when credentials are available.

The primary caller is Claude running the future legislative-expert skill. Interfaces should return enough normalized context for that caller to combine MOLEG legal sources with `congress-db` bill facts and WebSearch social context without loading raw endpoint trivia into the skill prompt.

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
14. As a legislative-expert skill, I want to search MOLEG official interpretations, so that I can identify official interpretation constraints.
15. As a legislative-expert skill, I want to search ministry first-instance interpretations by ministry/source registry, so that the public interface does not expose dozens of ministry-specific functions.
16. As a legislative-expert skill, I want to search Supreme Court cases, so that I can identify judicial interpretations and limits.
17. As a legislative-expert skill, I want to search Constitutional Court decisions separately, so that constitutional-risk analysis keeps authority labels intact.
18. As a legislative-expert skill, I want legal-term and related-law expansion, so that I can plan better searches without treating expansion results as final authority.
19. As a legislative-expert skill, I want clear error types for no result, ambiguity, unsupported format, source API error, parse failure, and retry exhaustion, so that I can decide whether to ask the user, retry, or fall back.
20. As a legislative-expert skill, I want guidance on when to use WebSearch instead, so that latest social context is not incorrectly searched in MOLEG.

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
- Caching starts small. Do not build a mirror DB until repeated calls prove a speed or cost problem.

## Public Interface Candidates

- `search_laws(query, *, as_of=None, basis="effective", law_type=None, ministry=None)`
- `get_law(identifier, *, as_of=None, basis="effective", articles=None, include_metadata=True)`
- `get_article(law_identifier, article, *, as_of=None, basis="effective")`
- `trace_law_history(law_identifier, *, date_range=None, article=None)`
- `compare_law_versions(law_identifier, *, before, after, article=None)`
- `find_delegated_rules(law_identifier, *, article=None)`
- `search_administrative_rules(query, *, ministry=None, rule_type=None, issued_on=None)`
- `get_administrative_rule(identifier, *, articles=None)`
- `search_interpretations(query, *, source="moleg", ministry=None)`
- `get_interpretation(identifier, *, source=None)`
- `search_cases(query, *, court="all", court_name=None, decided_on=None, case_number=None)`
- `get_case(identifier)`
- `search_constitutional_decisions(query, *, decided_on=None, case_number=None)`
- `get_constitutional_decision(identifier)`
- `expand_legal_query(query)`
- `resolve_promulgated_law(*, prom_law_nm=None, prom_no=None, promulgation_dt=None)`

Names may change to match code style, but the interface principle should not: one deep module per recurring legal task is better than one shallow function per MOLEG endpoint.

## Testing Decisions

- Tests should exercise public interfaces, not internal source-target helper functions.
- The first deterministic tests prove law search, identity normalization, promulgation bridge resolution, law text retrieval, article retrieval, ambiguity handling, and no-result handling through `MolegApi`.
- Live smoke tests should verify at least one real source response for the first vertical slice when `MOLEG_OC` is available.
- Parser tests should use recorded source-shaped payloads for JSON and, where needed, XML/HTML.

## Implemented Core Slices

- `MolegApi.search_laws()` searches law names without exposing raw `law` / `eflaw` targets to callers.
- `MolegApi.resolve_promulgated_law()` accepts `congress-db` bridge fields (`prom_law_nm`, `prom_no`, `promulgation_dt`) and returns one normalized `LawIdentity` or raises no-result/ambiguity errors.
- `MolegApi.get_law()` retrieves effective/promulgation-basis law text and normalizes articles.
- `MolegApi.get_article()` accepts human article notation such as `제10조의2` and formats the source `JO` value internally.
- `MolegApi.trace_law_history()` currently supports JSON-reachable article/date-range change history and explicitly refuses full `lsHistory` usage until an HTML parser/fallback is designed.
- `MolegApi.compare_law_versions()` normalizes `oldAndNew` before/after article text behind a public comparison interface.
- `MolegApi.find_delegated_rules()` normalizes `lsDelegated` relationships so the caller sees delegated-rule context rather than raw lower-law fields.
- `MolegApi.search_administrative_rules()` searches current or historical administrative rules through source `admrul`, preserving serial ID, rule ID, rule type, issuing date, effective date, ministry, and current/history status.
- `MolegApi.get_administrative_rule()` loads administrative-rule text by source serial ID, rule ID, or exact name and returns normalized structured articles when available, while preserving flat source text when the source does not expose article structure.
- `MolegApi.search_interpretations()` searches official MOLEG interpretations through `expc` and ministry first-instance interpretations through a registry-backed `*CgmExpc` source family.
- `MolegApi.get_interpretation()` loads one interpretation by source ID and preserves source type, source target, ministry, case number, interpretation date, inquiry agency, reply/interpretation agency, question, answer, reason, and related-law text.
- `MolegApi.search_cases()` and `MolegApi.get_case()` load Supreme Court/lower-court case context through `prec`, including case number, decision date, court, case type, holdings, summary, referenced statutes, referenced cases, and full text.
- `MolegApi.search_constitutional_decisions()` and `MolegApi.get_constitutional_decision()` load Constitutional Court decision context through `detc`, preserving constitutional source labels, final date, case number, holdings, summary, reviewed statutes, referenced statutes, referenced cases, and full text.
- `LawGoKrClient` is the live JSON source adapter and reads `MOLEG_OC` from the environment.
- Normal tests use fake adapters; `tests/test_live_smoke.py` is marked `live` and skips unless `MOLEG_OC` exists.

## Out of Scope

- A generic wrapper for all 195 MOLEG guides.
- Direct SQL access to `congress-db`.
- Web search, news, statistics, or social-context retrieval.
- Local ordinance, treaty, administrative appeal, special administrative appeal, and committee-decision modules until repeated skill scenarios justify them.
- A large local mirror database.
