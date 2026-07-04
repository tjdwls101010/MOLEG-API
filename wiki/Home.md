# moleg-api

**moleg-api** is a task-level Python interface for loading Korean legal sources from [law.go.kr](https://www.law.go.kr/). It normalizes law.go.kr's MOLEG OpenAPI responses so that applications and agent systems can retrieve legal context without memorizing individual `target` values, identifier rules (`ID`, `MST`, `LID`, `JO`, …), or per-endpoint response-shape quirks. You pick an interface by the legal work you need to do — search a statute, load an article, trace an amendment, find a delegated rule, read a Constitutional Court decision — not by a raw endpoint name.

The PyPI package name is `moleg-api`; import it as `moleg_api`. Live calls use a law.go.kr OpenAPI credential (the "OC"), but the package ships with a shared default, so calls work out of the box with **no registration required**. This is not a complete wrapper around every law.go.kr endpoint: the public interface is intentionally small and deep. The recurring pattern is **search or plan first, then load** the selected source text, authority detail, delegated-rule context, or annex/form body — search hits are candidates, not citable source text.

## What it covers

- Current (`effective`) and promulgated (`promulgated`) statutes
- Statute articles, including moved/deleted article status
- Supplementary provisions (부칙)
- Law history and before/after text comparison
- Delegated rules and legal hierarchy (statute → enforcement instrument → administrative rule)
- Administrative rules — 고시 (notices), 훈령 (directives), 예규 (established rules)
- Law and administrative-rule annex/form bodies (별표·서식), with optional structured table rows
- MOLEG official interpretations and ministry first-instance interpretations
- Ordinary court cases and Constitutional Court (헌재) decisions
- Query expansion, comparable-mechanism discovery, and staged context bundles with executable follow-up lookups

## What it does not cover

- **Legal advice.** moleg-api loads legal sources; it does not interpret them for a decision.
- **National Assembly bill data.** Bill status, sponsors, votes, and minutes are out of scope — use a separate bill source.
- **Latest statistics, news, or policy announcements.** Use WebSearch or another current external source.
- Empty search results are scoped to the exact query, source family, and filters used — never proof that no relevant source exists.
- MOLEG interpretation, ministry interpretation, ordinary court case, and Constitutional Court decision have different source authority and stay separate — they are not interchangeable.

## Quick start

Search returns candidates; load the selected detail before citing legal substance.

**Python**

```python
from moleg_api import MolegApi

api = MolegApi()

hits = api.search_laws("자동차관리법", basis="effective", display=5)
identity = hits[0].identity

article = api.get_article(identity, "제26조", basis="effective")
print(article.text)
```

**CLI** — every method is also a `moleg` subcommand that prints one JSON envelope:

```bash
python -m moleg_api catalog                        # self-documenting entry point
python -m moleg_api search-laws "자동차관리법"       # → candidates with law_id
python -m moleg_api get-article --law 001760 제26조  # load a chosen candidate
```

## Navigation

- [Installation & Setup](Installation.md) — install the package and configure your own OC credential.
- [Quickstart](Quickstart.md) — the search-then-load flow and staged bundles, end to end.
- [API Reference](API-Reference.md) — every public `MolegApi` method and when to use it.
- [Command-Line Interface](CLI-Reference.md) — the `moleg` subcommands, the JSON envelope, and exit codes.
- [Follow-up Lookups](Core-Concepts.md) — how candidate results carry the next executable call.
- [Source Coverage & Limits](Sources-and-Coverage.md) — supported source families and what stays out of scope.
- [Data Models](API-Reference.md) — the public dataclasses and their serialization.
- [Error Handling](Error-Handling.md) — the exception hierarchy and source-access versus legal-absence.
- [Maintainer Notes](Maintainer-Notes.md) — package layout, compatibility facades, and refactor guardrails.

## Status

The package is alpha (`0.2.x`). The interface is ready for package-level experimentation, but law.go.kr live behavior can vary by source, credential, and endpoint availability. Treat search results as candidates until a selected detail loader has retrieved source text. moleg-api is a legal-source loader, not legal advice.
