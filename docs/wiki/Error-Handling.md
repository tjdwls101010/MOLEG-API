# Error Handling

moleg-api raises a small hierarchy of typed exceptions, all rooted at `MolegApiError`. Every exception distinguishes one thing above all: **a failure to reach the source is not the same as a legal source being absent.** A rate limit, a timeout, or a parse failure means "we could not get an answer right now" — never "no such law exists." Treat the two differently, and the errors below tell you which one you are looking at.

All exception classes are importable from the package root:

```python
from moleg_api import (
    MolegApiError,
    NoResultError,
    AmbiguousLawError,
    UnsupportedFormatError,
    SourceApiError,
    RateLimitError,
    RetryExhaustedError,
    ParseFailureError,
)
```

## Exception hierarchy

```
Exception
└── MolegApiError                 base for all public-interface failures
    ├── NoResultError             no usable source text for the request
    ├── AmbiguousLawError         request matched multiple law identities
    ├── UnsupportedFormatError    source cannot provide a supported format
    ├── ParseFailureError         a response could not be normalized
    └── SourceApiError            the law.go.kr call itself failed
        ├── RateLimitError        law.go.kr rate limited the request (HTTP 429)
        └── RetryExhaustedError   retryable failures continued through all attempts
```

Catch `MolegApiError` to handle any package-raised failure at once; catch a subclass to react to a specific condition. Because `RateLimitError` and `RetryExhaustedError` are subclasses of `SourceApiError`, catching `SourceApiError` also catches both.

## The exceptions

### `MolegApiError`

Base class for every failure the public interface raises. It carries no extra fields of its own. Use it as the broadest catch:

```python
from moleg_api import MolegApi, MolegApiError

api = MolegApi()
try:
    article = api.get_article(identity, "제26조")
except MolegApiError as exc:
    log.warning("moleg lookup failed: %s", exc)
```

### `NoResultError`

The source API returned no usable result for a valid, well-formed request — for example, a load that found no article text for an identifier, or a history lookup that returned no events. This is a *scoped* absence: it means nothing was found for **this identifier, article, or query**, not that the material does not exist anywhere. Widen the search terms or scope before concluding a source is absent.

Three callers of `NoResultError` deserve special note:

- **A loader handed a law name instead of a law ID.** `get_law`, `get_article`, and the other loaders expect a `LawIdentity`, a `LawHit`, or a numeric source identifier — not a free-text statute name. Passing a name raises `NoResultError` whose message tells you to search first. The CLI surfaces this distinctly as `needs_search_first` (exit code **5**); see below.
- **A nonexistent identifier is a `no_result`, not a source failure.** law.go.kr answers a detail lookup for an identifier it does not have with an *empty body* (`{}`), not with the `일치하는 …` sentence it returns for a law-name miss. Before 0.3.0 that empty body raised `ParseFailureError` and exited **3**, whose discipline told the caller to retry — advice for a lookup that can never succeed. It is now a `NoResultError` (exit **4**) that steers back to `search-*`.
- **A zero-hit search is not an error.** The search methods themselves may raise internally when nothing matches, but at the CLI a search that finds nothing is reported as a normal, scoped success (`ok:true`, `count:0`, exit **0**). Only *loads* raise a surfaced `no_result`.

```python
from moleg_api import MolegApi, NoResultError

api = MolegApi()
try:
    article = api.get_article(identity, "제999조")
except NoResultError:
    # Nothing at this article for this identity — not proof the law lacks it.
    ...
```

### `AmbiguousLawError`

The request matched **more than one** plausible law identity, and the package refuses to silently pick one for you. This is raised, for example, when a promulgation bridge (`resolve_promulgated_law`) matches several distinct statutes. The exception exposes the choices so you can present them:

- `.candidates` — a list of the matched `LawIdentity` objects (name, `law_id`, `mst`, promulgation/effective dates, ministry, and so on).
- `.kind` — a short label for the ambiguity source (e.g. `"promulgation_bridge"`).
- `.message` — the human-readable summary.

Ambiguity is a signal to disambiguate, **not** a license to take the first candidate. Surface the candidates and let the caller (or user) choose, then re-issue the load with the selected identity.

```python
from moleg_api import MolegApi, AmbiguousLawError

api = MolegApi()
try:
    identity = api.resolve_promulgated_law(prom_law_nm="...", prom_no="...")
except AmbiguousLawError as exc:
    for cand in exc.candidates:
        print(cand.name, cand.law_id, cand.promulgation_date)
    # Pick one deliberately, then call get_law(chosen)…
```

### `UnsupportedFormatError`

The source endpoint could not provide a response in a format the package can consume — for example, law.go.kr returned HTML where JSON was requested, or a text-export endpoint returned a non-text content type. This is a source/path limitation, not a legal-absence result. The material may still be reachable by a different command or a different source (WebSearch, National Assembly bill data, and so on).

### `SourceApiError`

The law.go.kr call itself failed or returned an invalid response — a non-retryable HTTP error, or a body that was not valid JSON. This is the general "the source did not answer usefully" error and the parent of the two transient errors below. It signals a **source-access failure**, not that the requested law is absent.

### `RateLimitError`

law.go.kr rate limited the request (HTTP **429**) and the package exhausted its retries. Because the package ships with a shared default OC credential, heavy or concurrent use can hit this. **This is a temporary access failure, never evidence that a law does not exist.** Back off and retry later; if you hit it often, register your own OC (see [Installation](Installation.md)) to get your own rate budget.

### `RetryExhaustedError`

A retryable source failure — a timeout, a connection error, or a retryable HTTP status (408, 500, 502, 503, 504) — persisted through every allowed attempt. Like `RateLimitError`, this is a **transient access failure, not an absence.** Retry later. (When retries are disabled by configuring `max_retries=0`, a retryable timeout or connection error surfaces as a plain `SourceApiError` instead.)

### `ParseFailureError`

A source response was retrieved but could not be normalized into the public data model — for example, an identity payload missing its law name, or a law-structure payload with an unexpected shape. This is neither a source-access failure nor a legal absence: the data arrived but did not fit the expected structure.

**Retrying will not help.** It shares exit code 3 with the transient errors, but only because both mean "the source side went wrong"; a response shape the package does not recognize will be just as unrecognizable on the next call. Rule out an identifier mistake first (`search-*` to re-confirm the identity), then try a different command or path before drawing any conclusion.

## Transient failure versus absence

The single most important distinction when handling these errors:

| Meaning | Exceptions | How to react |
| --- | --- | --- |
| **Temporary access failure** — could not reach or read the source right now | `RateLimitError`, `RetryExhaustedError`, `SourceApiError` | Retry later. Do **not** treat as "no such law." Fill time-sensitive facts (e.g. effective dates) from a fallback only with an "unverified" label; leave constitutionality/case-law claims as "needs primary confirmation." |
| **Response could not be normalized** | `ParseFailureError` | Not an absence, and **not transient** — a retry returns the same shape. Rule out an identifier mistake, then try another command or path. |
| **Scoped absence** — a valid request found nothing for this exact scope, *including an identifier the source has no record of* | `NoResultError` (surfaced as `no_result`) | Widen the query/scope, or re-confirm the identifier with `search-*`. Never conclude the material does not exist without stating the exact query, source family, and filters used. |
| **Wrong input / ordering** — a name where an ID was needed, bad arguments | `NoResultError` (surfaced as `needs_search_first`), argument errors | Search first to get the identity, or fix the arguments. |
| **Multiple matches** | `AmbiguousLawError` | Present the `candidates`; choose one deliberately, then re-load. |

## Built-in retries

`LawGoKrClient` retries transient source failures automatically before raising. The retry policy is configurable on the client:

- **Retryable conditions** — HTTP status **408, 429, 500, 502, 503, 504**, plus timeouts and connection (`URLError`) failures.
- **`max_retries`** — additional attempts after the first (default **2**, so up to **3** total attempts).
- **`retry_delay_seconds`** — fixed delay between attempts (default **0.5**).
- **`timeout_seconds`** — per-request timeout (default **30**).

When retries are exhausted, an HTTP 429 raises `RateLimitError`; any other retryable condition raises `RetryExhaustedError`. Non-retryable HTTP errors and invalid-JSON bodies raise `SourceApiError` immediately, without retrying.

To tune the policy, construct the client explicitly:

```python
from moleg_api import MolegApi, LawGoKrClient

api = MolegApi(source=LawGoKrClient(max_retries=4, retry_delay_seconds=1.0))
```

## CLI exit codes

The `moleg` command prints one JSON envelope per invocation and maps each error class to a distinct exit code, so a shell or agent can branch on the outcome without parsing the message. The envelope's `kind` field names the condition; the exit code encodes it.

| Exit | `kind` | Meaning | Underlying exception |
| --- | --- | --- | --- |
| **0** | (varies) | Success — **including a zero-hit search** (`ok:true`, `count:0`) | — |
| **2** | `ambiguous` | Multiple plausible identities; candidates in `flags.candidates` | `AmbiguousLawError` |
| **3** | `source_access_error` | Transient source access failure — **retry later** | `RateLimitError`, `RetryExhaustedError` |
| **3** | `parse_error` | Unrecognized response shape — **a retry will not help** | `ParseFailureError` |
| **3** | `error` | Other source-side failure | `SourceApiError` and other `MolegApiError` |
| **4** | `no_result` | A load found no source text — including an identifier the source has no record of | `NoResultError` |
| **5** | `needs_search_first` | A loader was handed a law name — search for the ID first | `NoResultError` (name-not-ID) |
| **5** | `unsupported` | The source cannot provide this format/path | `UnsupportedFormatError` |
| **5** | `usage_error` | Bad arguments, missing subcommand, or unknown command | argument parsing |

There is no exit code 1: the errors that scripts must branch on each get a dedicated code (2–5), and everything else that succeeds is 0.

**Exit 3 carries two kinds, and only one of them is worth retrying.** `source_access_error` means the source could not be reached — back off and try again. `parse_error` means it answered with something the package cannot read, which the next identical call will do too. Branch on `kind`, not on the exit code alone, or a retry loop will spin on a permanent condition.

`no_result` (exit 4) is deliberately kept apart from `needs_search_first` (exit 5): the former is a genuine scoped absence, the latter a fixable input-ordering mistake.

### CLI error envelope

A failed CLI call still prints a structured envelope. For example, handing a loader a law name instead of an ID:

```bash
python3 -m moleg_api get-article --law "주택임대차보호법" 제1조
```

```json
{
  "ok": false,
  "command": "get-article",
  "kind": "needs_search_first",
  "error": "Identifier '주택임대차보호법' looks like a law name, not a law ID. Call `search_laws('주택임대차보호법')` to find the law ID, then pass the result or its `law_id` to this method.",
  "discipline": [ "로더에 법령명이 들어옴 — search-laws로 law_id를 먼저 얻어라." ],
  "next": [ { "why": "먼저 신원 검색", "cmd": "moleg search-laws \"주택임대차보호법\"" } ]
}
```

The exit code for this envelope is **5**. The correct fix is to search first, then load with the resulting `law_id`:

```bash
python3 -m moleg_api search-laws "주택임대차보호법"      # → law_id
python3 -m moleg_api get-article --law <law_id> 제1조    # load the chosen identity
```

When the failure is ambiguity, the envelope carries the candidates under `flags.candidates` and exits **2**, leaving the choice to you rather than picking one. A transient `source_access_error` (exit **3**) means retry later — it is not proof the law is absent.

## See also

- [Command-Line Interface](CLI-Reference.md) — the full JSON envelope contract and the search→load discipline.
- [Installation & Setup](Installation.md) — configuring your own OC credential to avoid the shared rate budget.
- [Data Models](API-Reference.md) — the `LawIdentity` fields returned in `AmbiguousLawError.candidates`.
