# CLI Reference

`moleg_api` ships a shell CLI so you can load [law.go.kr](https://www.law.go.kr/) legal sources without writing Python. Every task-level `MolegApi` method is exposed as a subcommand, and every call prints exactly **one JSON envelope** to stdout. The shell can branch on the outcome using the process **exit code** without parsing that JSON.

No configuration is required — the package ships a shared default OC credential, so calls work out of the box (see the [Installation](Installation.md) page for using your own OC).

## Invocation

Two entry points are equivalent:

```bash
python -m moleg_api <command> [flags]     # module form — always available after install
moleg <command> [flags]                   # console-script alias (declared in pyproject.toml)
```

Every command accepts a global `--raw` flag (placed before the subcommand) that includes the raw law.go.kr payloads inside `data`, for debugging:

```bash
moleg --raw get-article --law 001248 제3조
```

Per-command flags are documented on `moleg <command> --help`. The full command list, standing conventions, and routing rules live in `moleg catalog` (see [Start with `catalog`](#start-with-catalog)).

## The envelope

Every successful command prints a JSON object with this shape:

```json
{
  "ok": true,
  "command": "get-article",
  "kind": "article_text",
  "source": "법제처 / 법령 조문",
  "count": 3,
  "data": { "...": "serialized result dataclass (raw omitted unless --raw)" },
  "flags": { "basis": "effective", "effective_date": "20260102" },
  "discipline": ["정의·예외·요건은 text의 항·호·목 중첩에 있다 — ..."],
  "next": [{ "why": "...", "cmd": "moleg ..." }]
}
```

| field | meaning |
|-------|---------|
| `ok` | `true` for a completed call (**including a zero-hit search**), `false` for any error envelope. |
| `command` | the subcommand that ran (e.g. `"get-article"`); `null` on an argument-parsing failure. |
| `kind` | the typed result category. Its suffix carries the **candidate vs. loaded** distinction (see [The `kind` suffix convention](#the-kind-suffix-convention)). On errors this is an error kind like `needs_search_first` or `source_access_error`. |
| `source` | a human-readable Korean source label, e.g. `"법제처 / 법령검색"`, `"법제처 / 헌재결정 본문"`. Present on success envelopes. |
| `count` | present only on list-returning searches — the number of hits. `0` on a zero-hit search. |
| `data` | the serialized result. A search returns a JSON array; a loader returns a single object. Nested dataclasses serialize recursively; raw source payloads are omitted unless `--raw` is passed. |
| `flags` | structural signals pulled from the result's own fields — e.g. `is_deleted`, `moved_to`, `not_effective_as_of`, `has_supplementary`, `authority_gaps`, `parsing_confidence`, `ambiguous_versions`, `count`, `searched`. Present only when the result carries such a signal. |
| `discipline` | source-integrity notes that appear **only when the relevant trap is live in this result** (a deleted article, an authority/article mismatch, a future effective date). The frequent path stays quiet; the rare dangerous states speak up. |
| `next` | the highest-leverage follow-up commands, ready to run and capped at three. The full follow-up set stays in `data`; any overflow is counted in `flags.more_followups`. |

On error, the envelope carries `ok: false`, an error `kind`, and an `error` message string (plus `discipline` and, where useful, `next`). It does **not** carry `data`.

### The `kind` suffix convention

`kind` encodes structurally whether a result is a **search candidate** (not citable on its own) or **loaded source text** (citable). The suffix tells you which:

- `*_hit` / `*_candidate` / `*_planning` — **search candidates.** These are a menu of what to load next, not source text. A `law_hit`, an `admin_rule_hit`, an `annex_form_hit`, a `comparable_planning` item, or a `query_expansion_planning` result must not be cited for wording, thresholds, holdings, or legal equivalence.
- `*_text` / `*_context` / `*_identity` — **loaded source text.** A `law_text`, `article_text`, `article_context`, `constitutional_text`, `law_identity`, etc. is the actual retrieved source.

`kind` is derived from the **result dataclass type**, not from the subcommand name. So a list reached through [`load-followup`](#load-followup-and-the-pipe-idiom) is typed by the interface that actually executed, not by the command you typed. The closed list of all `kind` values is printed by `moleg catalog` under `kinds`.

The practical rule (also stated in `catalog`'s conventions): **cite only from loaded bodies.** `search-*`, `expand-legal-query`, and `find-comparable-mechanisms` results are always candidates — load the selected item before citing anything.

## Exit codes

The exit code lets a script branch on the outcome without reading the JSON:

| code | name | meaning |
|------|------|---------|
| `0` | success | the call completed — **including a zero-hit search** (`ok:true`, `count:0`). |
| `2` | ambiguous | multiple plausible identities matched; the envelope lists candidates. Surface them, do not silently pick the first. |
| `3` | source access | a transient source-access failure (rate limit, retry exhausted, parse failure, or other source error) — **not** proof of absence. |
| `4` | no result | a loader found no source text for an otherwise valid identifier. |
| `5` | usage | a bad argument, an unsupported format/path, **or** a loader handed a law *name* instead of a law ID (search first). |

Two outcomes are deliberately kept distinct: a **zero-hit search** is a scoped `ok:true` result with exit `0` and `count:0`, whereas a **source-access failure** is `ok:false` with `kind:"source_access_error"` and exit `3`. Neither is proof that a source does not exist.

Error kinds map to exit codes as follows:

| exit | `kind` values |
|------|---------------|
| `2` | `ambiguous` |
| `3` | `source_access_error`, `parse_error`, `error` |
| `4` | `no_result` |
| `5` | `needs_search_first`, `usage_error`, `unsupported` |

## Start with `catalog`

`moleg catalog` is the self-documenting entry point. It prints, in one envelope, every subcommand grouped by intent, the standing conventions, the routing rules for choosing between similar commands, and the closed list of `kind` values. There is no introspection ritual to run first — read the catalog, then read a command's `--help` for its flags.

```bash
moleg catalog
```

The `data` object has four sections:

- **`convention`** — the standing rules that apply to every call (the `kind` suffix meaning, "cite only from loaded bodies," source-authority ordering, the exit-code legend, the search→load contract, the deferred-pipe idiom, and how `--as-of` resolves historical versions).
- **`routing_rules`** — how to choose between adjacent commands, e.g. `get-article` vs. `load-article-context`, `compare-law-versions` vs. `trace-law-history`, `get-law-structure` vs. `find-delegated-rules`, and which bundle loader fits which situation.
- **`commands`** — every subcommand grouped into four buckets: `검색·계획(후보)` (search/planning candidates), `본문 로드` (body loaders), `연혁·체계·위임` (history/structure/delegation), and `권위·묶음` (authority/bundles).
- **`kinds`** — the closed list of every `kind` value the CLI can emit, success and error.

## The search → load contract

Loaders (`get-law`, `get-article`, `load-article-context`, `trace-law-history`, `compare-law-versions`, `find-delegated-rules`, `get-law-structure`, and the bundle loaders) take a numeric `law_id` string in `--law`, **not** a law name. Passing a name returns `kind:"needs_search_first"` at exit `5`, with the exact `search-laws` command to run:

```bash
$ moleg get-article --law "주택임대차보호법" 제3조
```
```json
{
  "ok": false,
  "command": "get-article",
  "kind": "needs_search_first",
  "error": "Identifier '주택임대차보호법' looks like a law name, not a law ID. ...",
  "discipline": ["로더에 법령명이 들어옴 — search-laws로 law_id를 먼저 얻어 --law에 넘겨라."],
  "next": [{ "why": "먼저 신원 검색", "cmd": "moleg search-laws \"주택임대차보호법\"" }]
}
```

So the flow is always search → select a `law_id` → load:

```bash
moleg search-laws "주택임대차보호법"          # → candidates carrying law_id + effective_date
moleg get-article --law 001248 제3조           # load the current version
moleg get-article --law 001248 --as-of 2021-01-01 제3조   # load the version in force on that date
```

A `search-laws` whose name resolves to several effective dates sets `flags.ambiguous_versions` and returns disambiguating `next` commands — the current text loads with a bare `--law`, and a past version loads with `--as-of <date>`:

```bash
$ moleg search-laws "주택임대차보호법" --display 3
```
```json
{
  "ok": true, "command": "search-laws", "kind": "law_hit_list",
  "source": "법제처 / 법령검색", "count": 3,
  "data": [ { "identity": { "law_id": "001248", "effective_date": "20260102", "...": "..." } }, "..." ],
  "flags": { "count": 3, "ambiguous_versions": true },
  "discipline": ["동명 후보가 시행일 다름 — 현행본은 그냥 get-law --law, 특정 시점 버전은 --as-of <시행일>로 로드."],
  "next": [
    { "why": "후보 로드: 주택임대차보호법 (시행 20260102)", "cmd": "moleg get-law --law 001248" },
    { "why": "후보 로드: 주택임대차보호법 (시행 20230719)", "cmd": "moleg get-law --law 001248 --as-of 20230719" }
  ]
}
```

The complementary error case — a zero-hit search — is `ok:true` at exit `0` with `count:0`, and records what was searched so you can distinguish "not found by this query" from "does not exist":

```bash
$ moleg search-cases "존재하지않는판례검색어" --display 3
```
```json
{
  "ok": true, "command": "search-cases", "kind": "case_hit_list",
  "source": "법제처 / 판례 검색", "count": 0, "data": [],
  "flags": { "count": 0, "searched": { "query": "존재하지않는판례검색어", "court": "all" } },
  "discipline": ["0건 — 이 검색어·범위로 못 찾음일 뿐, 부재의 증명 아님."]
}
```

## Historical versions with `--as-of`

`--as-of <date>` loads the statute or article text **in force on that date**, not today's. The loaders resolve the version whose 시행일 is the latest on or before the requested date. Always read the returned `flags.effective_date`; a `flags.version_request_unfulfilled` means no version was yet in force on the requested date and a later one was returned instead. For what a specific amendment *changed* (before/after wording), use `compare-law-versions` rather than diffing two separate loads.

## `load-followup` and the pipe idiom

`load-legal-context-bundle` and `expand-legal-query` return follow-up records (`data.deferred[...]` and `data.follow_up_searches[...]`) describing what to load next. Execute one by **piping it back** into `load-followup` — do not hand-type the JSON, because Korean text and nested quotes make that error-prone:

```bash
moleg load-legal-context-bundle --query "온라인 플랫폼 허위광고 규율" \
  | jq '.data.deferred[0]' \
  | moleg load-followup --json -
```

`load-followup` accepts either `--json '<object>'` inline or `--json -` to read one object from stdin. The `interface` field in the object is validated against the known method set, so a search candidate cannot be smuggled in as if it were loaded text. Follow-ups whose interface points outside law.go.kr — `websearch` or `congress-db` handoffs — are recognized but belong to those other sources, not to this CLI. (The `next` field of most envelopes also contains ready-to-run `moleg load-followup --json ...` commands with the object already embedded, so you can often copy one directly instead of piping.)

## Related pages

- [Getting Started](Quickstart.md) — install, credentials, first calls.
- [Envelope and Discipline](CLI-Reference.md) — the envelope fields, `flags`, and `discipline` in depth.
- [Python API](API-Reference.md) — the `MolegApi` methods behind each subcommand.
- [Follow-up Lookups](Core-Concepts.md) — `DeferredLookup`, `FollowUpSearch`, and `load_followup`.
