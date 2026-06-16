# MOLEG-API Skill Author Cookbook

This guide is for the future legislative-expert skill that imports MOLEG-API as a Python package. MOLEG-API loads legal sources from law.go.kr; it does not reason to the final legal conclusion and does not replace `congress-db` or WebSearch.

## Installation And Setup

Install the package in the skill runtime:

```bash
pip install moleg-api
```

Instantiate the public facade:

```python
from moleg_api import MolegApi

api = MolegApi()  # reads MOLEG_OC from the environment
```

`MOLEG_OC` must be supplied at runtime. Do not store it in skill files, prompts, logs, committed fixtures, or packaged artifacts.

## Serialization

All public model dataclasses support:

```python
data = result.to_dict()
json_text = result.to_json_string()
debug_data = result.to_dict(include_raw=True)
```

Use `include_raw=False` by default. It omits `raw` source payloads recursively, which keeps Claude context smaller and avoids carrying endpoint-shaped data unless debugging a source mismatch. Normalized identity metadata such as `raw_keys` remains present because it is small and often useful for follow-up calls.

Use `include_raw=True` only when diagnosing a live law.go.kr shape, parser gap, or source bug. Do not place raw payloads into ordinary legislative reasoning context.

Approximate context budgeting:

| Return type | Typical use | Budget guidance |
|---|---|---|
| `LawIdentity`, `ArticleText`, search hits | Candidate selection and citations | Cheap; safe to include several. |
| `LawText` | Full statute context | Potentially large when many articles are loaded; prefer `get_article()` or `get_law(..., articles=[...])` for narrow questions. |
| `DelegationGraph` | Delegated rules from a statute/article | Moderate; include when implementation criteria may live in enforcement decrees, enforcement rules, notices, or administrative rules. |
| `LawStructure` | Broader 법률 -> 시행령 / 시행규칙 / 행정규칙 hierarchy | Moderate; use when the institutional hierarchy matters, not as a substitute for article-level delegation. |
| `AnnexFormText` | Selected 별표ㆍ서식 body text | Can be long; inspect `structured_data.parsing_confidence` before relying on structured rows. |
| `JudicialDecisionText`, `InterpretationText` | Authority detail | Load selectively after candidate ranking; full text can be long. |
| `LawIdentity` values from `find_comparable_mechanisms()` | Comparable 제도 planning | Cheap candidates only; load selected articles/laws before citing or concluding similarity. |
| `LegalContextBundle` | First staged context pass | Include the serialized bundle as a plan plus loaded anchors; inspect `deferred` before loading every candidate. |

## Scenario 1: From congress-db Promulgation Bridge To Current Law

Use `congress-db` for National Assembly bill facts and bridge fields. Use MOLEG-API only after the bill has a promulgation bridge.

```python
from moleg_api import AmbiguousLawError, MolegApi

api = MolegApi()

try:
    identity = api.resolve_promulgated_law(
        prom_law_nm=prom_law_nm,
        prom_no=prom_no,
        promulgation_dt=promulgation_dt,
    )
except AmbiguousLawError as exc:
    # Surface exc.candidates; do not pick silently.
    candidates = [candidate.to_dict() for candidate in exc.candidates]
    raise

current_article = api.get_article(identity, "제5조", basis="effective")

history = api.trace_law_history(
    identity,
    article="제5조",
    promulgation_bridge={
        (prom_law_nm, str(prom_no), promulgation_dt): bill_id,
    },
)

context = {
    "current_article": current_article.to_dict(),
    "article_history": history.to_dict(),
}
```

Use effective-date basis for current-force questions. Use promulgation-date basis only when reconstructing the source bridge or historical promulgation context.

`trace_law_history(article=...)` may carry `HistoryEvent.article_text` for the post-change article snapshot. Full-law history is chronology metadata only. MOLEG-API does not query `congress-db`; pass the `promulgation_bridge` map when the skill already has `bill_id` values from `congress-db`.

## Scenario 2: Search Law, Load Targeted Articles

```python
api = MolegApi()

hits = api.search_laws("탄소중립", basis="effective", display=5)
if len(hits) != 1:
    # Treat multiple plausible laws as an ambiguity for Claude to resolve.
    candidate_context = [hit.to_dict() for hit in hits]
else:
    law = api.get_law(hits[0].identity, basis="effective", articles=["제1조", "제8조"])
    serialized = law.to_dict()
```

Prefer targeted article loading when the user asks about specific provisions. Full-law loading is appropriate when the question is broad or when neighboring provisions must be inspected together.

## Scenario 3: Delegated Rules And Administrative Rules

Statute text alone can miss operative detail delegated to lower rules.

```python
api = MolegApi()

# Select this identity only after search ambiguity has been resolved.
identity = building_act_identity
article = api.get_article(identity, "제5조")
delegation = api.find_delegated_rules(identity, article="제5조")
structure = api.get_law_structure(identity, depth=1)

payload = {
    "article": article.to_dict(),
    "delegation": delegation.to_dict(),
    "law_structure": structure.to_dict(),
}
```

When `DelegationGraph.rules` points to notices, directives, established rules, or other administrative rules, continue with `search_administrative_rules()` and `get_administrative_rule()` before claiming the execution criteria have been inspected.

Use `find_delegated_rules()` for article-level delegation links. Use `get_law_structure()` for the broader `lsStmd` hierarchy across statutes, enforcement instruments, and administrative rules. Do not invent a source-article link from `get_law_structure()`; that source does not provide one.

## Scenario 4: Staged Legal Context Bundle

Use the bundle when the question is broad or under-specified.

```python
api = MolegApi()

bundle = api.load_legal_context_bundle(
    query="건축 인허가 기준과 위임 규정",
    mode="question",
    budget="standard",
)

data = bundle.to_dict()
```

Interpret the bundle in layers:

- `loaded` contains official source context already retrieved and safe to inspect.
- `candidates` contains possible next sources, not final authority.
- `deferred` contains bounded follow-up calls the skill may run after ranking relevance.
- `ambiguities` must be surfaced or resolved with more source context.
- `gaps` tells the skill when WebSearch or human review is needed.

Do not treat `LegalContextBundle` as a legal conclusion. It is a context-loading result and planning guide.

## Scenario 5: Multi-Statute Institutional System

Use this only after Claude has an explicit statute set for one 제도. It composes selected statutes; it does not discover the set or decide which statute is primary.

```python
api = MolegApi()

# These identities should come from prior search/ambiguity resolution.
selected_statutes = [
    privacy_law_identity,
    credit_information_law_identity,
]

bundle = api.load_institutional_system(
    selected_statutes,
    articles=["제15조"],
    budget="standard",
)

data = bundle.to_dict()
```

Read it like a staged bundle: loaded laws, `law_structures`, and delegations are available first; administrative rules, annex/forms, interpretations, cases, and Constitutional Court decisions may remain candidates or deferred lookups. If the statute set is uncertain, run `search_laws()` or `expand_legal_query()` first and surface ambiguity instead of using this helper as a discovery engine.

## Scenario 6: Comparable Mechanism Discovery

Use this for legislative design questions such as "similar 과징금 structures" or "statutes with comparable authorization/reporting mechanisms."

```python
api = MolegApi()

candidates = api.find_comparable_mechanisms("과징금", display=5)
candidate_context = [candidate.to_dict() for candidate in candidates]

# Choose this after Claude ranks candidate_context for the user's drafting task.
selected = ranked_candidate
source_articles = selected.raw_keys.get("source_articles", [])
article_anchor = source_articles[0]["article"] if source_articles else None
detail = (
    api.get_article(selected, article_anchor)
    if article_anchor
    else api.get_law(selected)
)
```

`find_comparable_mechanisms()` returns bounded planning candidates with discovery endpoint and article-anchor provenance in `raw_keys`. It does not prove that mechanisms are legally equivalent. Load the selected article or law before citing it or using it as a drafting model.

## Scenario 7: Annex/Form Body Inspection

Search results for 별표ㆍ서식 are candidates. Load the selected body before treating attached criteria, thresholds, forms, or tables as inspected.

```python
api = MolegApi()

hits = api.search_annex_forms(
    "과태료 부과기준",
    source="law",
    annex_type="별표",
    display=5,
)

candidate_context = [hit.to_dict() for hit in hits]

# Choose this after Claude ranks candidate_context for the attached material question.
selected_hit = ranked_annex_hit
body = api.get_annex_form_body(selected_hit.identity)

if body.structured_data and body.structured_data.parsing_confidence == "high":
    table_rows = body.structured_data.rows
else:
    fallback_text = body.text
```

`get_annex_form_body()` uses law.go.kr text-export surfaces for law and administrative-rule annex/forms. Structured rows are conservative convenience data; the plain `text` remains the source fallback for irregular or low-confidence tables. Direct HWP/PDF parsing is intentionally outside this interface.

## Scenario 8: Interpretation Coverage Across Authorities

Keep MOLEG official interpretations and ministry first-instance interpretations distinguishable.

```python
api = MolegApi()

official_hits = api.search_interpretations(
    "영업정지",
    source="moleg",
    search_body=True,
    display=5,
)

labor_scope_hits = api.search_interpretations(
    "영업정지",
    source="all",
    ministry="고용노동부",
    display=3,
)

registry_wide_hits = api.search_interpretations(
    "영업정지",
    source="all_ministries",
    display=1,
)
```

Use `source="all"` for MOLEG plus one specified ministry; it requires `ministry`. Use `source="all_ministries"` only when the task justifies the higher-cost fan-out across the ministry registry. Preserve `identity.source_type`, `identity.source_target`, and `identity.ministry` in Claude context so the final answer does not collapse different authority levels.

## Scenario 9: Constitutional Risk Search

```python
api = MolegApi()

hits = api.search_constitutional_decisions(
    "과잉금지원칙",
    search_body=True,
    display=5,
)

details = [api.get_constitutional_decision(hit.identity).to_dict() for hit in hits[:1]]
```

The `detc` source does not expose structured doctrine/category fields. Doctrine terms such as `과잉금지원칙` or `평등원칙` are free-text search terms, not source-backed filters.

## Vendored Fallback

If the skill sandbox cannot install from PyPI, vendor the source tree into the skill package, for example:

```text
<skill_sandbox>/
  vendored/
    moleg_api/
      __init__.py
      errors.py
      laws.py
      models.py
      normalization.py
      source.py
```

Then import from the vendored path:

```python
from vendored.moleg_api import MolegApi
```

The runtime contract stays the same: `MOLEG_OC` must be supplied by the environment, and source credentials must not be committed into the vendored copy.

## Error Handling

- `AmbiguousLawError`: surface `exc.candidates` or ask for a more precise identifier. Do not select the first result silently.
- `NoResultError`: treat as no source match for that exact task, not as proof that the legal claim is false.
- `RateLimitError` / `RetryExhaustedError`: treat as temporary source-access problems.
- `UnsupportedFormatError`: the requested source shape or parameter is outside the supported public interface.
- `ParseFailureError`: the live source shape changed or a parser encountered an unexpected structure; do not return partial legal context as if complete.
- `SourceApiError`: law.go.kr access failed before a legal-source result could be established.

## Source Boundaries

- Use `congress-db` for bills, votes, meeting facts, sponsors, and promulgation bridge fields.
- Use MOLEG-API for current/enacted law.go.kr legal sources and their normalized relationships.
- Use WebSearch for latest social facts, statistics, announcements, news, and non-law.go.kr context.
