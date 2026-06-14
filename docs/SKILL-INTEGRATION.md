# MOLEG-API Skill Integration

This document describes how the future legislative-expert skill should use MOLEG-API alongside `congress-db` and WebSearch. It is a living integration guide; update it when public interfaces or source traps change.

The intended user is Claude with a legislative-expert skill loaded. MOLEG-API should therefore return normalized legal context that can be inserted into reasoning, citations, and follow-up calls, not raw endpoint payloads that force the skill prompt to memorize law.go.kr trivia.

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

## Default Workflow From A Promulgated Bill

1. Query `congress-db` for the bill and its promulgation bridge fields.
2. Call `resolve_promulgated_law(prom_law_nm=..., prom_no=..., promulgation_dt=...)`.
3. If the result is ambiguous, surface the candidates instead of choosing silently.
4. Call `get_law(..., basis="effective")` or `get_article(..., basis="effective")` to inspect the text currently in force.
5. Call `trace_law_history()` or `compare_law_versions()` to explain what the bill changed.
6. Call `find_delegated_rules()` to inspect enforcement decrees, enforcement rules, notices, and administrative rules.
7. Call `search_interpretations()` and `search_cases()` when legal meaning, application constraints, or constitutional risk matter.
8. Use WebSearch only for current social facts or context outside law.go.kr.

## Query Planning Rules

- Prefer effective-date basis for "current law", "now in force", and "현재 시행" questions.
- Use promulgation-date basis when resolving a `congress-db` promulgation bridge or reconstructing historical promulgation context.
- Treat law-name search as candidate discovery. Multiple plausible results are an ambiguity, not permission to pick the first hit.
- Use `expand_legal_query()` for search planning, not as final legal authority.
- Preserve source authority labels in answers: MOLEG interpretation, ministry interpretation, Supreme Court case, and Constitutional Court decision are different source types.

## Fallback Rules

- If MOLEG-API cannot answer because the needed source is outside law.go.kr, use WebSearch.
- If MOLEG-API finds no law for a bill that has no promulgation bridge, return to `congress-db` and treat the bill as not proven enacted/current.
- If a source endpoint is HTML-only, use the documented parser/fallback for that interface; do not assume JSON exists.
- If a law delegates details to lower rules, do not stop at statute text unless the user explicitly asks for statute-only review.

## Expected Public Interfaces

These names may change as implementation settles, but the future skill should expect task-level functions rather than raw MOLEG targets:

- `MolegApi.search_laws()`
- `MolegApi.resolve_promulgated_law()`
- `MolegApi.get_law()`
- `MolegApi.get_article()`
- `MolegApi.trace_law_history()`
- `MolegApi.compare_law_versions()`
- `MolegApi.find_delegated_rules()`
- `search_administrative_rules()`
- `get_administrative_rule()`
- `search_interpretations()`
- `get_interpretation()`
- `search_cases()`
- `get_case()`
- `expand_legal_query()`

The first seven are implemented across the initial core slices. Administrative rules, interpretations, cases, and query expansion are planned expansion surfaces.

## Answering Discipline For The Skill

- Never describe a proposed bill as current law unless MOLEG-API or another authoritative enacted-law source proves it.
- State whether a law text was retrieved by effective-date or promulgation-date basis when the distinction matters.
- Cite source type and identity metadata with legal text.
- Surface ambiguity and no-result states clearly.
- Move to WebSearch for latest non-legal facts instead of forcing MOLEG-API to answer them.
