# moleg-api

`moleg-api` is a task-level Python interface for loading Korean legal sources from [law.go.kr](https://www.law.go.kr/). It normalizes the Ministry of Government Legislation (법제처) OpenAPI so applications and agents can retrieve legal context without memorizing individual `target` values, identifier rules (`ID`, `MST`, `LID`, `JO`), or per-endpoint response quirks.

You pick an interface by the legal task you need — search a statute, load an article, trace an amendment, find a delegated rule, read a Constitutional Court decision — not by a raw endpoint name. It is not a complete wrapper around every law.go.kr endpoint; the public interface is intentionally small and deep. The recurring pattern is **search or plan first, then load** the selected source: search hits are candidates, not citable text.

The PyPI package is `moleg-api`; import it as `moleg_api`.

## Install

```bash
pip install moleg-api
```

Live calls use a law.go.kr OpenAPI credential (the "OC" — a free, non-secret account id). The package ships a shared default, so calls work out of the box with **no registration required**. To use your own OC (recommended for heavy use), register at law.go.kr and set `MOLEG_OC`, or pass `oc=` to `LawGoKrClient`. See [Installation](wiki/Installation.md).

## Quickstart

Python — search, then load the chosen candidate:

```python
from moleg_api import MolegApi

api = MolegApi()
hits = api.search_laws("주택임대차보호법")        # candidate identities
article = api.get_article(hits[0].identity, "제3조")  # loaded source text
print(article.text)
```

Shell — every method is also a `moleg` subcommand printing one JSON envelope:

```bash
python -m moleg_api catalog                          # self-documenting command list
python -m moleg_api search-laws "주택임대차보호법"    # → candidates with law_id
python -m moleg_api get-article --law 001248 제3조    # load the current article
python -m moleg_api get-article --law 001248 --as-of 2021-01-01 제3조  # the version in force then
```

Public dataclasses serialize recursively with `to_dict()` / `to_json_string()` (raw payloads omitted unless `include_raw=True`).

## What it covers

- Current (`effective`) and promulgated (`promulgated`) statutes and articles, including moved/deleted status
- Supplementary provisions (부칙), law history, and before/after text comparison
- Historical versions — load the text in force on a past date with `as_of`
- Delegated rules, legal hierarchy, and administrative rules (고시·훈령·예규)
- Law and administrative-rule annex/form bodies (별표·서식)
- MOLEG and ministry legal interpretations, Supreme Court cases, and Constitutional Court (헌재) decisions
- Query expansion, comparable-mechanism discovery, and staged context bundles with executable follow-up lookups

Out of scope: legal advice, National Assembly bill data (status, votes, minutes), and latest statistics/news.

## Documentation

Full documentation is in the [`wiki/`](wiki/Home.md) folder:

- [Installation](wiki/Installation.md) · [Quickstart](wiki/Quickstart.md) · [Core Concepts](wiki/Core-Concepts.md)
- [CLI Reference](wiki/CLI-Reference.md) · [API Reference](wiki/API-Reference.md)
- [Historical Versions](wiki/Historical-Versions.md) · [Sources & Coverage](wiki/Sources-and-Coverage.md)
- [Gotchas](wiki/Gotchas.md) · [Error Handling](wiki/Error-Handling.md)

## Status

Alpha (`0.2.x`). The interface is ready for use, but law.go.kr live behavior can vary by source, credential, and endpoint availability. Treat search results as candidates until a detail loader has retrieved source text. This package is a legal-source loader, not legal advice.

## License

MIT — see [LICENSE](LICENSE).
