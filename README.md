# MOLEG-API

MOLEG-API is a task-level Python interface for loading Korean legal sources from
[law.go.kr](https://www.law.go.kr/). It is designed for applications and agent
systems that need normalized legal context without memorizing individual MOLEG
OpenAPI `target` values, identifier rules, or response-shape quirks.

The Python package name is `moleg-api`; import it as `moleg_api`.

This is not a complete wrapper around every law.go.kr endpoint. The public
interface is intentionally small and deep: search or plan first, then load the
selected legal source text, authority detail, delegated rule context, or
annex/form body.

## Install

After the package is published:

```bash
pip install moleg-api
```

From a repository checkout:

```bash
python -m pip install .
```

Live law.go.kr calls require an OpenAPI credential in `MOLEG_OC`:

```bash
export MOLEG_OC="your-law-go-kr-oc"
```

## Quick Example

```python
from moleg_api import MolegApi

api = MolegApi()

hits = api.search_laws("자동차관리법", basis="effective", display=5)
selected = hits[0].identity

article = api.get_article(selected, "제26조", basis="effective")
print(article.text)
```

For broader questions, use a staged bundle and inspect deferred follow-ups:

```python
bundle = api.load_legal_context_bundle(
    query="자동차 방치 처리 기준",
    mode="question",
    budget="standard",
)

for lookup in bundle.deferred:
    if lookup.interface == "load_administrative_rule_context":
        rule_context = api.load_followup(lookup)
        break
```

Public dataclasses serialize recursively:

```python
payload = bundle.to_dict()                  # omits raw source payloads
debug_payload = bundle.to_dict(include_raw=True)
json_text = bundle.to_json_string()
```

## What It Covers

- Current and promulgated statutes
- Statute articles, including moved/deleted article status
- Supplementary provisions
- Law history and before/after text comparison
- Delegated rules and legal hierarchy
- Administrative rules, notices, directives, and established rules
- Law and administrative-rule annex/form body loading
- MOLEG official interpretations and ministry first-instance interpretations
- Ordinary court cases and Constitutional Court decisions
- Query expansion and comparable-mechanism discovery
- Staged context bundles with executable follow-up lookups

## Documentation

- [Quickstart](https://github.com/tjdwls101010/MOLEG-API/blob/main/docs/quickstart.md)
- [API guide](https://github.com/tjdwls101010/MOLEG-API/blob/main/docs/api-guide.md)
- [Follow-up lookups](https://github.com/tjdwls101010/MOLEG-API/blob/main/docs/followups.md)
- [Source coverage and limits](https://github.com/tjdwls101010/MOLEG-API/blob/main/docs/source-coverage.md)
- [Documentation map](https://github.com/tjdwls101010/MOLEG-API/blob/main/docs/README.md)

Consumer-specific notes for a future legislative-expert skill remain in
[docs/SKILL-INTEGRATION.md](https://github.com/tjdwls101010/MOLEG-API/blob/main/docs/SKILL-INTEGRATION.md)
and
[docs/SKILL-AUTHOR-COOKBOOK.md](https://github.com/tjdwls101010/MOLEG-API/blob/main/docs/SKILL-AUTHOR-COOKBOOK.md).
They are examples of one integration, not the package's general-purpose
contract.

## Status

The package is alpha (`0.1.x`). The interface is ready for package-level
experimentation, but law.go.kr live behavior can vary by source, credential, and
endpoint availability. Treat search results as candidates until selected detail
loaders have retrieved source text.

This package is a legal-source loader, not legal advice.
