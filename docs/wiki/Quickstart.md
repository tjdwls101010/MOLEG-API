# Quickstart

Load your first Korean legal source in five minutes. `moleg-api` is a task-level loader for [law.go.kr](https://www.law.go.kr/): you pick an interface by the legal work you need — search a statute, load an article — not by a raw endpoint name. The recurring pattern is **search first, then load** the selected source text.

This page shows the same workflow in the **Python API** and the **CLI** side by side. For installation details see [Installation](Installation.md); for the concepts behind the workflow see [Core Concepts](Core-Concepts.md).

## Install

```bash
pip install moleg-api
```

The PyPI package name is `moleg-api`; import it as `moleg_api`. Live calls use a law.go.kr OpenAPI credential (the "OC"), but the package ships with a shared default, so calls work out of the box with **no registration required**. If you call the API heavily, set your own OC to avoid the shared credential's rate limits:

```bash
export MOLEG_OC="your-law-go-kr-oc"
```

See [Installation](Installation.md) for OC resolution order and the editable install used for development.

## Search, then load

A search returns *candidates* — normalized identities you choose from. You load selected source text before citing any legal substance. Multiple candidates are ambiguity, not permission to pick the first hit, and an empty result is a scoped no-result, not proof that no legal source exists.

### Python API

```python
from moleg_api import MolegApi

api = MolegApi()

# 1. Search for law identity candidates.
hits = api.search_laws("주택임대차보호법", basis="effective", display=5)
if not hits:
    raise RuntimeError("No law candidates")

# 2. Choose one candidate's identity and load a precise article.
identity = hits[0].identity
article = api.get_article(identity, "제7조", basis="effective")

print(article.article)   # 제7조
print(article.title)     # 차임 등의 증감청구권
print(article.text)      # full article body with 항·호·목
```

`search_laws` returns a list of `LawHit` values, each carrying a normalized `LawIdentity` (with `law_id`, `name`, `basis`, `effective_date`, and more). Pass the `LawIdentity` — or the `LawHit` itself — straight into `get_article`, so you never format law.go.kr's identifier or six-digit `JO` article code yourself. An empty list means no source rows; it does not raise.

`get_article` returns an `ArticleText` with the article label, title, body, effective date, and normalized source identity. See [API Reference](API-Reference.md) for the full method and field list.

### CLI

Every `MolegApi` method is also a `moleg` subcommand, so you can load sources from a shell without writing Python. Each call prints exactly one JSON envelope to stdout.

```bash
# 1. Search — returns candidates with law_id.
python -m moleg_api search-laws "주택임대차보호법" --display 5

# 2. Load a chosen candidate by its law_id (from step 1).
python -m moleg_api get-article --law 001248 "제7조"
```

The search envelope carries the candidates under `data`, each with an `identity.law_id` you pass to a loader. It also suggests the next command:

```json
{
  "ok": true,
  "command": "search-laws",
  "kind": "law_hit_list",
  "source": "법제처 / 법령검색",
  "count": 1,
  "data": [
    {
      "identity": {
        "law_id": "001248",
        "name": "주택임대차보호법",
        "basis": "effective",
        "effective_date": "20260102",
        "law_type": "법률"
      }
    }
  ],
  "next": [
    { "why": "후보 로드: 주택임대차보호법 (시행 20260102)",
      "cmd": "moleg get-law --law 001248" }
  ]
}
```

Passing a **law name** to a loader is rejected (`needs_search_first`, exit code 5) — always resolve a `law_id` with `search-laws` first. The envelope contract, exit codes, and `kind` suffix conventions are documented in [CLI Reference](CLI-Reference.md). To see the commands and routing rules at any time, run `python -m moleg_api catalog`.

## Broad or under-specified questions: use a staged bundle

When you do not yet have a specific law name — the question is broad or under-specified — start with `load_legal_context_bundle()` instead of a single search. The bundle runs one bounded first pass over likely law.go.kr sources and returns candidates, any source text it could safely auto-load, plus a list of **deferred** follow-up lookups you can choose to run next. The bundle loads sources, not conclusions.

### Python API

```python
bundle = api.load_legal_context_bundle(
    query="자동차 방치 처리 기준",
    mode="question",
    budget="standard",
)

# Candidate law identities discovered in the first pass.
print([law.name for law in bundle.candidates.laws])

# What remains unverified, and which source should fill it.
print([gap.kind for gap in bundle.gaps])

# Executable follow-ups. Run one with load_followup().
for lookup in bundle.deferred:
    if lookup.interface == "load_administrative_rule_context":
        rule_context = api.load_followup(lookup)
        print(rule_context.rule.identity.name)
        break
```

`bundle.candidates` is a `CandidateContext` (its `laws` list holds `LawIdentity` values), `bundle.loaded` holds any source text already retrieved, `bundle.gaps` holds `ContextGap` values naming what is still unverified, and `bundle.deferred` holds `DeferredLookup` values. Pass any `DeferredLookup` (or `FollowUpSearch`) to `load_followup()` and it routes to the right task-level loader for you.

`mode` accepts `"question"`, `"promulgated_bill"`, or `"statute_review"`; `budget` accepts `"minimal"`, `"standard"`, or `"broad"` and bounds how much the first pass loads.

Handoffs whose interface is `websearch.*` or `congress-db.*` are **outside** `moleg-api` — passing one to `load_followup()` raises `UnsupportedFormatError`, because those facts belong to WebSearch and National Assembly bill systems, not law.go.kr. See [Core Concepts](Core-Concepts.md) for how the bundle and deferred lookups fit together, and [Gotchas](Gotchas.md) for the distinctions the gaps guard against.

### CLI

```bash
python -m moleg_api load-legal-context-bundle "자동차 방치 처리 기준" \
    --mode question --budget standard

# Run a deferred follow-up the bundle returned, by piping its JSON object:
echo '<deferred object from the bundle>' | python -m moleg_api load-followup --json -
```

## Serialize results

Every public model dataclass supports `to_dict()` and `to_json_string()`, and they serialize recursively — a bundle serializes its nested laws, articles, candidates, and deferred lookups in one call.

```python
data = article.to_dict()               # plain dict, ready for json.dumps
json_text = bundle.to_json_string()    # JSON string

# Raw law.go.kr payloads are omitted by default; opt in for parser debugging.
debug_data = bundle.to_dict(include_raw=True)
```

By default the `raw` source payload is dropped, which keeps ordinary application context clean. Use `include_raw=True` only when you need the original law.go.kr response for debugging. The CLI applies the same rule: it omits `raw` unless you pass the global `--raw` flag.

## Where to go next

- [Core Concepts](Core-Concepts.md) — search-then-load discipline, bases, candidates vs. loaded text, bundles and deferred lookups.
- [API Reference](API-Reference.md) — every `MolegApi` method and model field.
- [CLI Reference](CLI-Reference.md) — the JSON envelope, exit codes, and subcommand list.
- [Gotchas](Gotchas.md) — distinctions (bill vs. current law, promulgation vs. effective date, empty result vs. absence) that quietly produce wrong claims.
- [Sources and Coverage](Sources-and-Coverage.md) — which law.go.kr source families are covered and their limits.

This package is a legal-source loader, not legal advice.
