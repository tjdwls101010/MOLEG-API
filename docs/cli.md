# MOLEG-API CLI

`moleg_api` ships a shell CLI so an agent can load law.go.kr sources without
writing Python. It wraps every task-level `MolegApi` method as a subcommand and
prints one JSON envelope per call.

```bash
python -m moleg_api <subcommand> [flags]     # always available from an install
moleg <subcommand> [flags]                   # console-script alias
```

No configuration is required — the package ships a shared default OC credential.

## Start with `catalog`

`moleg catalog` prints every subcommand grouped by intent, the standing
conventions, and the closed list of `kind` values. It is the self-documenting
entry point; per-command flags are on `moleg <cmd> --help`. There is no
introspection ritual to run first.

## The envelope

Every command prints exactly one JSON object to stdout:

```json
{
  "ok": true,
  "command": "get-article",
  "kind": "article_text",
  "source": "법제처 / 법령 조문",
  "data": { "...": "serialized result dataclass (raw omitted unless --raw)" },
  "flags": { "basis": "effective", "effective_date": "20260102" },
  "discipline": ["정의·예외·요건은 text의 항·호·목 중첩에 있다 — 조문제목만으로 요약 금지."],
  "next": [{ "why": "...", "cmd": "moleg ..." }]
}
```

* **`kind`** carries the candidate/loaded distinction structurally. `*_hit`,
  `*_candidate`, `*_planning` are search candidates — **not citable**. `*_text`,
  `*_context`, `*_identity` are loaded source text. `kind` is derived from the
  result type, so a list reached through `load-followup` is typed by what it
  executed, not by the subcommand.
* **`flags`** are structural signals pulled from the result's own fields:
  `is_deleted`, `moved_to`, `not_effective_as_of`, `has_supplementary`,
  `authority_gaps`, `parsing_confidence`, `source_backref_present`, `count`, …
* **`discipline`** appears **only when the trap is live** in this result. A
  clean article carries the one standing note about nested 항·호·목; a deleted
  or moved article adds the note that fires for that state; a bundle whose
  eager-loaded authority mismatches the target article adds the gate note. The
  frequent path stays quiet; the rare dangerous states speak up.
* **`next`** mirrors the highest-leverage follow-up as a ready-to-run command,
  capped at three. The full follow-up set stays in `data`; overflow is counted
  in `flags.more_followups`.

Pass `--raw` to include the raw law.go.kr payloads in `data` for debugging.

## Exit codes

The shell can branch on the outcome without parsing:

| code | meaning |
|------|---------|
| 0 | success, **including a zero-hit search** (`ok:true`, `count:0`) |
| 2 | ambiguous — multiple plausible identities; surface, don't pick |
| 3 | transient source-access failure (rate limit / retry / source) — not absence |
| 4 | a load found no source text for a valid identifier |
| 5 | usage error, or a loader was handed a law name (search first) |

A zero-hit search and a source-access failure are deliberately different: the
first is a scoped `ok:true` result, the second is `kind:"source_access_error"`.
Neither is proof that a source does not exist.

## The search → select → load contract

Loaders (`get-law`, `get-article`, …) accept a numeric `law_id` string, not a
law name. Passing a name returns `kind:"needs_search_first"` (exit 5) with the
`search-laws` command to run. So the flow is always:

```bash
moleg search-laws "주택임대차보호법"          # → candidates with law_id + effective_date
moleg get-article --law 001248 제3조           # load the current version
moleg get-article --law 001248 --as-of 2021-01-01 제3조   # load the version in force on that date
```

`search-laws` sets `flags.ambiguous_versions` and disambiguating `next`
commands when the same name resolves to several effective dates — the current
text loads with a bare `--law`, and a past version loads with `--as-of <date>`.

## Historical versions

`--as-of <date>` loads the statute/article text **in force on that date**, not
today's. The loaders resolve the version whose 시행일 is the latest on or before
the date and reload it by its master sequence, because law.go.kr's plain
`ID`+`efYd` lookup silently returns current text. Always read the returned
`effective_date`; `flags.version_request_unfulfilled` means no version was in
force yet on the requested date. For what a specific amendment *changed*, use
`compare-law-versions` (before/after text) rather than diffing two loads.

## Follow-ups without hand-typed JSON

`load-legal-context-bundle` and `expand-legal-query` return `deferred` /
`follow_up_searches`. Execute one by piping it back — do **not** hand-type the
JSON (Korean text and nested quotes make that error-prone):

```bash
moleg load-legal-context-bundle --query "온라인 플랫폼 허위광고 규율" \
  | jq '.data.deferred[0]' \
  | moleg load-followup --json -
```

`load-followup` accepts `--json '<object>'` or `--json -` (stdin). The
`interface` is validated against the known method set, so a candidate cannot be
smuggled in as loaded text.

## Testing against a fake source

`main(argv, api=...)` accepts an injected `MolegApi`, so the CLI can be tested
deterministically without live calls. Signal derivation (`signals_for`) is
keyed on the result dataclass type and is unit-tested independently in
`tests/test_cli.py`.
