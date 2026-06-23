# Quickstart

## Install

From PyPI, after publication:

```bash
pip install moleg-api
```

From a repository checkout:

```bash
python -m pip install .
```

For development and tests:

```bash
python -m pip install -e ".[dev]"
```

## Configure Credentials

Live law.go.kr calls use an OpenAPI credential (the "OC"). The package ships with
a shared default OC, so calls work without registration. To use your own — best
if you call the API heavily, since the shared default can hit law.go.kr rate
limits — set it:

```bash
export MOLEG_OC="your-law-go-kr-oc"
```

`MolegApi()` uses `LawGoKrClient()`, which resolves the OC in this order: the
`oc=` argument, then `MOLEG_OC` (environment or a local `.env`/`.env.local`),
then the bundled default. Do not commit your own credentials to `.env`,
fixtures, docs, or packaged files.

## Search Then Load

Search calls return candidates. Load selected text before citing legal substance.

```python
from moleg_api import MolegApi

api = MolegApi()

hits = api.search_laws("자동차관리법", basis="effective", display=5)
if not hits:
    raise RuntimeError("No law candidates")

identity = hits[0].identity
article = api.get_article(identity, "제26조", basis="effective")

print(article.article)
print(article.text)
```

## Use A Staged Bundle

Use `load_legal_context_bundle()` for broad or under-specified questions. The
bundle loads a bounded first pass and returns candidates plus follow-up lookups.

```python
bundle = api.load_legal_context_bundle(
    query="자동차 방치 처리 기준",
    mode="question",
    budget="standard",
)

print([law.name for law in bundle.candidates.laws])
print([gap.kind for gap in bundle.gaps])

for lookup in bundle.deferred:
    if lookup.interface == "load_administrative_rule_context":
        rule_context = api.load_followup(lookup)
        print(rule_context.rule.identity.name)
        break
```

## Serialize Results

All public model dataclasses support `to_dict()` and `to_json_string()`.

```python
data = bundle.to_dict()
json_text = bundle.to_json_string()
debug_data = bundle.to_dict(include_raw=True)
```

Use `include_raw=False` by default. Raw law.go.kr payloads are useful for parser
debugging, but they are noisy for ordinary application context.

## Handle Ambiguity And Source Gaps

MOLEG-API deliberately separates source loading from final legal reasoning:

- Multiple plausible laws are ambiguity, not permission to pick the first hit.
- Empty search results are scoped no-results, not proof that no legal source exists.
- `ContextGap` values explain what source remains unverified.
- `DeferredLookup` and `FollowUpSearch` values can be passed to `load_followup()`.
- `websearch.*` and `congress-db.*` handoffs are outside MOLEG-API and should be handled by those systems.

## Run Tests

Deterministic tests:

```bash
python -m pytest -m "not live" -q
```

Live smoke tests require `MOLEG_OC`:

```bash
python -m pytest -m live -q
```
