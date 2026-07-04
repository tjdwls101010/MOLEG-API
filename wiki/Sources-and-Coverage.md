# Sources and Coverage

MOLEG-API loads Korean legal sources from [law.go.kr](https://www.law.go.kr/). It covers the source families most useful for recurring legal source-loading tasks, and it deliberately does **not** expose every law.go.kr OpenAPI endpoint as a one-to-one SDK method. This page describes what is covered, what is out of scope, and the coverage limits you should keep in mind when citing what you load.

Every method listed here has a matching `moleg` CLI subcommand. Run `python -m moleg_api catalog` for the full command list and routing rules.

## What is covered

| Source family | Python interfaces | CLI subcommands |
|---|---|---|
| Current and promulgated statutes | `search_laws`, `resolve_promulgated_law`, `get_law`, `get_article`, `load_article_context` | `search-laws`, `resolve-promulgated-law`, `get-law`, `get-article`, `load-article-context` |
| Supplementary provisions (부칙) | returned inside `get_law` | inside `get-law` |
| Law history and before/after text | `trace_law_history`, `compare_law_versions` | `trace-law-history`, `compare-law-versions` |
| Delegated rules and legal hierarchy | `find_delegated_rules`, `get_law_structure` | `find-delegated-rules`, `get-law-structure` |
| Administrative rules (고시·훈령·예규 등) | `search_administrative_rules`, `get_administrative_rule`, `load_administrative_rule_context` | `search-administrative-rules`, `get-administrative-rule`, `load-administrative-rule-context` |
| Annexes and forms (별표·서식) | `search_annex_forms`, `get_annex_form_body` | `search-annex-forms`, `get-annex-form-body` |
| MOLEG and ministry interpretations | `search_interpretations`, `get_interpretation` | `search-interpretations`, `get-interpretation` |
| Ordinary court cases | `search_cases`, `get_case` | `search-cases`, `get-case` |
| Constitutional Court decisions | `search_constitutional_decisions`, `get_constitutional_decision` | `search-constitutional-decisions`, `get-constitutional-decision` |
| Query planning and staged bundles | `expand_legal_query`, `find_comparable_mechanisms`, `load_legal_context_bundle`, `load_institutional_system`, `load_delegated_criteria` | `expand-legal-query`, `find-comparable-mechanisms`, `load-legal-context-bundle`, `load-institutional-system`, `load-delegated-criteria` |

### Current and promulgated statutes

`search_laws` finds statute identity candidates by name or keyword; `get_law` and `get_article` load the text behind a chosen identity. Both accept a `basis` argument (`"effective"` or `"promulgated"`) — see [Effective date versus promulgation date](#effective-date-versus-promulgation-date).

```python
from moleg_api import MolegApi

api = MolegApi()

hits = api.search_laws("주택임대차보호법", basis="effective", display=2)
law = api.get_law(hits[0].identity, basis="effective")
article = api.get_article(hits[0].identity, "제7조", basis="effective")
print(article.text)
```

```bash
python -m moleg_api search-laws "주택임대차보호법" --display 2
python -m moleg_api get-article --law 001248 제7조
```

`resolve_promulgated_law` is a stricter bridge resolver: given the promulgation metadata of an enacted bill (law name, promulgation number, promulgation date) it resolves to one promulgated `LawIdentity`, rather than doing free-text discovery.

### Statute articles, including moved and deleted status

`get_article` loads one provision by human notation such as `제10조의2`, without you formatting MOLEG's six-digit `JO` value. `ArticleText` carries a `moved_from` / `moved_to` pair and an `is_deleted` flag, so a moved or deleted article marker is not mistaken for operative text.

`load_article_context` builds on this: it loads the requested article and, when the article has moved, resolves the current destination article. It returns the requested article, the current destination (when one is safely loaded), all loaded rows, and any context gaps or deferred lookups you should resolve before making a substance claim.

### Supplementary provisions (부칙)

`get_law` extracts supplementary provisions alongside the main articles and returns them in `LawText.supplementary_provisions` when the source law exposes them. There is no separate loader — 부칙 come back with the statute body.

### Law history and before/after text comparison

`trace_law_history` loads amendment-history events for a whole statute, a date range, or a single article (`article="제7조"`). Events carry chronology, amendment reasons, promulgation numbers, and effective dates.

`compare_law_versions` loads MOLEG's `oldAndNew` before/after comparison surface for a statute or article. Note: the source does not support arbitrary two-date windows. Calling `compare_law_versions` with `before=`/`after=` raises `UnsupportedFormatError`; call it without those arguments to load the source-supplied before/after pair, and use `trace_law_history` to pick dates or amendment events.

### Delegated rules and legal hierarchy

`find_delegated_rules` returns the delegated lower-rule context for a statute (enforcement decrees, enforcement rules, notices, administrative rules), optionally filtered by source article. `get_law_structure` loads the broader 법률 → 시행령 / 시행규칙 / 행정규칙 hierarchy from MOLEG's `lsStmd` structural view. The two differ: `find_delegated_rules` preserves article-level delegation links; `lsStmd` gives the hierarchy but does not provide source-article links.

### Administrative rules (행정규칙)

`search_administrative_rules` searches notices, directives, established rules, and other ministry-level administrative rules (고시·훈령·예규 등) — the practical execution criteria that often live outside statute text. `get_administrative_rule` loads a selected rule body, and `load_administrative_rule_context` stages the surrounding context for one rule.

### Annexes and forms (별표·서식) — text extraction only

Operative content often lives in annex material: tables, thresholds, criteria, amounts, and required forms. `search_annex_forms` finds annex/form candidates attached to a statute (`source="law"`) or an administrative rule (`source="administrative_rule"`), filterable by `annex_type` (별표, 서식, 별지, 별도, 부록 and their English aliases). `get_annex_form_body` loads the body of a selected candidate as **plain text**.

Extraction preserves the `text/plain` body and, for table-like annexes, attempts best-effort structuring into `structured_data`. **This interface does not parse HWP or PDF files directly** — it uses law.go.kr's text export endpoints. When table structuring is low confidence, empty structured rows do not necessarily mean no criteria exist; the plain text is still preserved and authoritative.

### MOLEG and ministry interpretations

`search_interpretations` searches official legal interpretations, distinct from court decisions. The `source` argument selects the authority scope: `"moleg"` (MOLEG official interpretations, the default), `"ministry"` (a named ministry's first-instance interpretations), `"all"` (MOLEG plus one specified ministry), or `"all_ministries"` (registry-wide fan-out, for deep institutional analysis only). `get_interpretation` loads the question, answer, reason, and related-law text for a selected interpretation. MOLEG interpretation and ministry interpretation are separate authority types and are not interchangeable — see [Authority types stay separate](#authority-types-stay-separate).

### Court cases and Constitutional Court decisions

`search_cases` / `get_case` cover ordinary court decisions (Supreme Court and lower courts). `search_constitutional_decisions` / `get_constitutional_decision` cover Constitutional Court decisions — reviewed statutes, holdings, and constitutional reasoning. These are distinct sources: ordinary court precedent and Constitutional Court decisions are not interchangeable, and neither is interchangeable with an interpretation.

Constitutional-doctrine discovery is keyword-based free-text search unless the loaded decision detail itself provides stronger structure.

### Query planning and staged bundles

These interfaces plan a search or assemble a staged bundle of the source families above. They are **planning aids, not legal authority** — use their outputs to drive the primary loaders before citing anything.

- `expand_legal_query` — turns broad wording into candidate laws, legal and everyday terms, related articles/laws, and follow-up recommendations.
- `find_comparable_mechanisms` — finds source-backed law candidates that use a similar legal mechanism (예: 과징금, 인허가, 신고제), for comparative 제도 design.
- `load_legal_context_bundle` — a staged bundle for a broad question, with executable deferred follow-up lookups (see [Follow-up lookups](Core-Concepts.md)).
- `load_institutional_system` — one staged bundle across an explicitly selected set of statutes.
- `load_delegated_criteria` — subordinate administrative-rule and annex/form bodies from a known statute anchor.

## What is not covered

- **National Assembly bill data.** MOLEG-API does not query bill databases. Bill status, sponsors, votes, committee minutes, and the promulgation bridge fields are a separate source's job. (`resolve_promulgated_law` *consumes* bridge metadata that a bill source provides, but does not itself retrieve it.) Use a National Assembly / 의안정보 source for anything on the legislative-process side.
- **Foreign or comparative law.** Only Korean law.go.kr sources are covered. Foreign statutes, treaties, and comparative-law material are out of scope — use WebSearch or another external source.
- **Latest statistics, news, policy announcements, and social context.** These are not legal sources; use WebSearch or another current source.
- **Legal advice.** MOLEG-API is a legal-source *loader*. It retrieves and normalizes source text; it does not interpret or advise.

## Coverage limits

Keep these in mind when you cite what you load.

### Empty results are scoped, not proof of absence

An empty search result is scoped to the exact query, source family, and filters you used. It means "no source rows for this query," **not** "no relevant law, rule, case, interpretation, or annex exists." Broaden the query or try a related source family before concluding that something does not exist.

### Search hits are candidates, not citable text

Search hit metadata (titles, IDs, dates) is not citable source text. Treat search results as *candidates*: load the selected detail with the matching loader (`get_law`, `get_article`, `get_interpretation`, `get_case`, `get_annex_form_body`, and so on) before quoting or reasoning from source content.

### Authority types stay separate

MOLEG official interpretation, ministry first-instance interpretation, ordinary court case, and Constitutional Court decision are distinct authorities with different weight. The models preserve their authority labels; do not flatten them into one another.

### Effective date versus promulgation date

A promulgated law can be loadable while **not yet effective** on your reference date. Use effective-date lookups (`basis="effective"`) for current-force questions, and promulgated-basis lookups (`basis="promulgated"`) to resolve enacted-law bridge metadata or historical promulgation context.

When the reference date matters, pass `as_of="YYYY-MM-DD"` and inspect the returned `ContextGap` values such as `not_effective_as_of`.

```python
api.get_law("001248", basis="effective", as_of="2026-01-01")
```

```bash
python -m moleg_api get-law --law 001248 --basis effective --as-of 2026-01-01
```

### Source failures are not legal absence

`RateLimitError`, `RetryExhaustedError`, and other `SourceApiError` states mean source access failed. Treat them as temporary source-access problems or explicit gaps — never as evidence that a law or decision does not exist. See [Errors and Reliability](Error-Handling.md) for handling.

### Annex extraction preserves plain text

Annex/form body extraction keeps the plain text even when table structuring is low confidence. Empty `structured_data` rows do not mean the annex has no criteria — read the plain text.

## Raw payloads

Public return models put normalized fields first and omit raw law.go.kr payloads by default. When you need to debug a parser or inspect the underlying source shape, pass `include_raw=True`:

```python
bundle.to_dict(include_raw=True)
```

Normal application context should use the default `include_raw=False`.

## See also

- [Effective vs Promulgated](Core-Concepts.md) — choosing the right `basis`
- [Follow-up lookups](Core-Concepts.md) — executing deferred bundle lookups
- [Errors and Reliability](Error-Handling.md) — source-failure handling
- [CLI Reference](CLI-Reference.md) — the JSON envelope contract and subcommands
