# API Reference

`MolegApi` is the single public class of `moleg_api`. It exposes **27 task-level methods** for loading Korean legal sources from [law.go.kr](https://www.law.go.kr/). You choose a method by the *legal work* you need — search for a statute, load an article, trace amendment history, find delegated rules — and the method keeps law.go.kr source targets, identifier quirks, and article-number formatting inside the package.

```python
from moleg_api import MolegApi

api = MolegApi()                 # bundled default credential; no registration required
hits = api.search_laws("주택임대차보호법", display=5)
article = api.get_article(hits[0].identity, "제7조")
print(article.text)
```

Every method also has a CLI subcommand (the same name in `kebab-case`). See the [CLI Reference](CLI-Reference.md) for the JSON envelope contract.

- **Constructor:** `MolegApi(source=None)` — pass a custom `MolegSource` only for testing or advanced credential control; the default constructs a live `LawGoKrClient`.

## How to read this reference

The methods split into four intent groups:

1. **[Search & planning](#search--planning)** — find candidate identities or plan a query. Results are *candidates*, not legal substance.
2. **[Body loading](#body-loading)** — load the actual source text for a selected identity.
3. **[History, structure & delegation](#history-structure--delegation)** — amendment chronology, statute hierarchy, and delegated lower rules.
4. **[Authority & bundles](#authority--bundles)** — interpretations, cases, constitutional decisions, and staged multi-source bundles.

Across all groups, three conventions recur:

- **Identifiers.** Loader methods accept a `LawIdentity`, the matching `*Hit` from a search, **or** a bare source-ID string. Passing the object you got back from a search is the safest form; a bare string is treated as a source identifier.
- **`basis` and `as_of`.** `basis="effective"` (default) targets current-force text; `basis="promulgated"` targets the promulgated version. `as_of="YYYYMMDD"` asks for the text in force on a specific reference date.
- **Article notation.** Pass the human label such as `"제10조의2"` (or an `int` for a plain article number). You never format law.go.kr's six-digit `JO` value yourself.

### Return types serialize to JSON

Every method returns either a **dataclass** or a **list of dataclasses**. All of these dataclasses expose the same two serialization helpers:

```python
result.to_dict()                    # nested dict; omits raw source payloads
result.to_dict(include_raw=True)    # includes preserved raw law.go.kr metadata
result.to_json_string()             # JSON text; also accepts include_raw=True
```

For methods returning a `list[...]`, serialize each element: `[hit.to_dict() for hit in hits]`.

---

## Search & planning

Use these first, when the target identity is not yet fixed. **Search results are candidate metadata — do not cite them as legal substance until a body-loading method has retrieved the text.** Most searches return a `follow_up` field that points to the correct detail loader.

| Method | Signature (kwargs abbreviated) | Returns | Use when |
|---|---|---|---|
| `search_laws` | `search_laws(query, *, as_of=None, basis="effective", law_type=None, ministry=None, display=20)` | `list[LawHit]` | You have a law name or keyword and need candidate current/promulgated statute identities. |
| `search_administrative_rules` | `search_administrative_rules(query, *, ministry=None, rule_type=None, issued_on=None, include_history=False, display=20)` | `list[AdministrativeRuleHit]` | Execution criteria may live in ministry notices, directives, or established rules outside statute text. |
| `search_annex_forms` | `search_annex_forms(query, *, source="law", search_scope="source", annex_type=None, ministry=None, display=20)` | `list[AnnexFormHit]` | Operative content may be in 별표ㆍ서식 — tables, thresholds, amounts, or required forms. |
| `search_interpretations` | `search_interpretations(query, *, source="moleg", ministry=None, search_body=False, interpreted_on=None, display=20)` | `list[InterpretationHit]` | You need official MOLEG/ministry interpretation of how a statute is applied. Use `source="all"` for MOLEG plus one ministry; `source="all_ministries"` only for deep, registry-wide analysis. |
| `search_cases` | `search_cases(query, *, court="all", court_name=None, search_body=False, decided_on=None, case_number=None, display=20)` | `list[JudicialDecisionHit]` | You need Supreme Court or lower-court precedent, holdings, or judicial limits. |
| `search_constitutional_decisions` | `search_constitutional_decisions(query, *, search_body=False, decided_on=None, case_number=None, display=20)` | `list[JudicialDecisionHit]` | You need constitutional-risk context, reviewed statutes, or Constitutional Court reasoning. |
| `expand_legal_query` | `expand_legal_query(query, *, display=5, include_websearch_hint=True)` | `LegalQueryExpansion` | A broad or lay-worded query needs legal terms, related laws/articles, and search-planning hints before you load anything. Returns planning context, **not** legal authority. |
| `find_comparable_mechanisms` | `find_comparable_mechanisms(concept, *, display=5)` | `list[LawIdentity]` | You are doing legislative design and want laws using a similar mechanism (e.g. 과징금, 인허가, 신고제). Article anchors are preserved in each candidate's `raw_keys`. |

Notes:

- `search_*` methods return an **empty list** for no results (not an error). `expand_legal_query` and `find_comparable_mechanisms` raise `NoResultError` on a blank query/concept.
- Interpretations, ordinary cases, and constitutional decisions are **separate authority types**, not flags on one search. Keep them distinct downstream.

---

## Body loading

Load the actual source text for a selected identity. Pass the `*Hit` or `LawIdentity` you got from a search where possible.

| Method | Signature (kwargs abbreviated) | Returns | Use when |
|---|---|---|---|
| `get_law` | `get_law(identifier, *, as_of=None, basis="effective", articles=None, include_metadata=True)` | `LawText` | You have a statute identity and need its effective or promulgated text (optionally limited to selected `articles`). |
| `get_article` | `get_article(law_identifier, article, *, as_of=None, basis="effective")` | `ArticleText` | You need one precise provision by human label such as `제10조의2`. |
| `resolve_promulgated_law` | `resolve_promulgated_law(*, prom_law_nm=None, prom_no=None, promulgation_dt=None)` | `LawIdentity` | A National Assembly bill row has reached promulgation and supplies bridge fields (law name, promulgation number, or date). Stricter than `search_laws`; raises `AmbiguousLawError` if several identities remain. |
| `get_administrative_rule` | `get_administrative_rule(identifier, *, articles=None, include_metadata=True)` | `AdministrativeRuleText` | You selected a notice/directive/established rule and need its inspectable text (raw source rows). |
| `get_annex_form_body` | `get_annex_form_body(identifier, *, source="law", title=None, include_metadata=True, attempt_structuring=True)` | `AnnexFormText` | An annex/form candidate may carry operative criteria and you need its `text/plain` body (with optional structured table rows). |
| `get_interpretation` | `get_interpretation(identifier, *, source=None, ministry=None, include_metadata=True)` | `InterpretationText` | A selected interpretation needs its question, answer, reason, and related-law text. |
| `get_case` | `get_case(identifier, *, include_metadata=True)` | `JudicialDecisionText` (labeled `case`) | A selected ordinary court case needs holdings, summary, full text, or referenced statutes/cases. |
| `get_constitutional_decision` | `get_constitutional_decision(identifier, *, include_metadata=True)` | `JudicialDecisionText` (labeled `constitutional`) | A selected Constitutional Court decision needs holdings, reviewed statutes, or reasoning. |

Notes:

- `get_case` raises `UnsupportedFormatError` if passed a constitutional identity, and `get_constitutional_decision` raises it for an ordinary case identity — use the matching loader for each.
- `include_metadata=False` (and, on the judicial loaders, dropping raw metadata) trims the payload when you are budgeting context.
- For articles that may have been **moved or deleted**, prefer `load_article_context` / `load_administrative_rule_context` (below) so you do not mistake a move marker for operative text.

---

## History, structure & delegation

Chronology, hierarchy, and the lower rules a statute delegates to.

| Method | Signature (kwargs abbreviated) | Returns | Use when |
|---|---|---|---|
| `trace_law_history` | `trace_law_history(law_identifier, *, date_range=None, article=None, promulgation_bridge=None)` | `LawHistory` | You need amendment chronology, amendment reasons, promulgation numbers, or effective dates — not the current text. Pass `article=` for article-level events. |
| `compare_law_versions` | `compare_law_versions(law_identifier, *, before=None, after=None, article=None)` | `LawDiff` | You need MOLEG's `oldAndNew` before/after text surface for a statute or article. Arbitrary two-date windows are **not** supported (raises `UnsupportedFormatError`). |
| `find_delegated_rules` | `find_delegated_rules(law_identifier, *, article=None)` | `DelegationGraph` | Statute text may delegate details to enforcement decrees/rules, notices, or administrative rules. Optionally filter by source `article`. |
| `get_law_structure` | `get_law_structure(law_identifier, *, depth=0)` | `LawStructure` | You need the broader 법률 → 시행령 / 시행규칙 / 행정규칙 hierarchy (`lsStmd`), not article-level delegation. Does **not** provide source-article links. |
| `load_article_context` | `load_article_context(law_identifier, article, *, as_of=None, basis="effective", follow_moved=True)` | `ArticleContext` | You need current/as-of article substance and must resolve moved/deleted article state before making a substance claim. |
| `load_administrative_rule_context` | `load_administrative_rule_context(identifier, *, articles=None, include_metadata=True, follow_moved=True)` | `AdministrativeRuleContext` | You need current operational criteria from an administrative rule and must resolve moved/deleted articles first. |
| `load_delegated_criteria` | `load_delegated_criteria(law_identifier, *, articles=None, query=None, budget="standard", as_of=None)` | `LegalContextBundle` | From a known statute/article, you need the *bodies* of subordinate administrative rules and annexes/forms for concrete operational criteria. |

Notes:

- `compare_law_versions` raises `NoResultError` when the source exposes no comparable changes.
- `get_law_structure` is hierarchy context only. Use `find_delegated_rules` when you need actual article-level delegation rows.
- The `load_*_context` methods surface **gaps** and **deferred lookups** for moved-destination loads that failed, rather than raising — inspect those before treating loaded text as final.

---

## Authority & bundles

Article-scoped authority (interpretations/cases/decisions) and staged multi-source bundles for broad questions.

| Method | Signature (kwargs abbreviated) | Returns | Use when |
|---|---|---|---|
| `load_authority_context` | `load_authority_context(law_identifier, *, articles, query=None, budget="standard", as_of=None)` | `AuthorityContext` | You need interpretations, cases, and constitutional decisions scoped to **specific statute articles**, filtered to dated matches so mismatched/pre-amendment authority is not treated as current support. |
| `load_legal_context_bundle` | `load_legal_context_bundle(query=None, *, promulgation_bridge=None, law_identifier=None, articles=None, mode="question", budget="standard", as_of=None)` | `LegalContextBundle` | The question is broad, under-specified, or starts from a statute/bill anchor and you want one bounded first pass over likely sources. |
| `load_institutional_system` | `load_institutional_system(statute_identifiers, *, articles=None, budget="standard", as_of=None)` | `LegalContextBundle` (`mode="institutional_system"`) | You have **already selected** the statute set for a 제도 and want them composed into one staged bundle. |
| `load_followup` | `load_followup(lookup)` | *(varies)* | You received a `DeferredLookup` or `FollowUpSearch` from a bundle or query expansion and want it executed via the right public loader. Returns whatever the routed method returns; raises `UnsupportedFormatError` for WebSearch handoffs. |

A `LegalContextBundle` is a **source-loading packet, not a conclusion**. Inspect its fields before deciding what to load next:

- `loaded` — successfully loaded law/article/delegation (and, for `load_delegated_criteria`, rule/annex) bodies.
- `candidates` — bounded discovery results not yet loaded in full.
- `deferred` — staged follow-up lookups you can run with `load_followup`.
- `ambiguities`, `gaps`, `source_notes` — unresolved choices, missing pieces, and non-fatal source failures.

Executing a follow-up:

```python
bundle = api.load_legal_context_bundle(query="자동차 방치 처리 기준", mode="question")

for lookup in bundle.deferred:
    if lookup.interface == "load_administrative_rule_context":
        rule_context = api.load_followup(lookup)
        break
```

See [Follow-up Lookups](Core-Concepts.md) for the deferred-lookup workflow.

---

## Errors

All methods raise subclasses of `MolegApiError`:

| Exception | Meaning |
|---|---|
| `NoResultError` | The source returned no usable result for the requested legal task. |
| `AmbiguousLawError` | The request matched multiple plausible law identities (carries `.candidates`). |
| `UnsupportedFormatError` | The requested format, handoff, or source path is outside this interface. |
| `SourceApiError` | The law.go.kr source API failed or returned an invalid response. |
| `RateLimitError` | Subclass of `SourceApiError` — the source rate-limited the request. |
| `RetryExhaustedError` | Subclass of `SourceApiError` — retryable failures continued through all attempts. |
| `ParseFailureError` | A source response could not be normalized into the public model. |

**A source-access failure is not a legal no-result.** When you catch a `SourceApiError` (or its subclasses), retry or surface the source gap — do not conclude that the law, authority, or rule does not exist.

---

## See also

- [API Guide](API-Reference.md) — narrative walkthrough of choosing a method by legal task.
- [CLI Reference](CLI-Reference.md) — the `moleg` subcommands and JSON envelope contract.
- [Quickstart](Quickstart.md) — end-to-end first-use example.
- [Follow-up Lookups](Core-Concepts.md) — running deferred lookups from bundles and expansions.
- [Source Coverage & Limits](Sources-and-Coverage.md) — which law.go.kr sources are covered and their known limits.
