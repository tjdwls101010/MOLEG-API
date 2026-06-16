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
| `JudicialDecisionText`, `InterpretationText` | Authority detail | Load selectively after candidate ranking; full text can be long. |
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
context = current_article.to_dict()
```

Use effective-date basis for current-force questions. Use promulgation-date basis only when reconstructing the source bridge or historical promulgation context.

## Scenario 2: Search Law, Load Targeted Articles

```python
api = MolegApi()

hits = api.search_laws("탄소중립", basis="effective", display=5)
if len(hits) != 1:
    # Treat multiple plausible laws as an ambiguity for Claude to resolve.
    candidate_context = [hit.to_dict() for hit in hits]

law = api.get_law(hits[0].identity, basis="effective", articles=["제1조", "제8조"])
serialized = law.to_dict()
```

Prefer targeted article loading when the user asks about specific provisions. Full-law loading is appropriate when the question is broad or when neighboring provisions must be inspected together.

## Scenario 3: Delegated Rules And Administrative Rules

Statute text alone can miss operative detail delegated to lower rules.

```python
api = MolegApi()

identity = api.search_laws("건축법", display=1)[0].identity
article = api.get_article(identity, "제5조")
delegation = api.find_delegated_rules(identity, article="제5조")

payload = {
    "article": article.to_dict(),
    "delegation": delegation.to_dict(),
}
```

When `DelegationGraph.rules` points to notices, directives, established rules, or other administrative rules, continue with `search_administrative_rules()` and `get_administrative_rule()` before claiming the execution criteria have been inspected.

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

## Scenario 5: Constitutional Risk Search

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
