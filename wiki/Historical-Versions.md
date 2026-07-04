# Historical Versions

By default, [`get_law`](API-Reference.md) and [`get_article`](API-Reference.md) load a statute's **current** consolidated text. To load the text of a statute or article **as it was in force on a past date**, pass `as_of=<date>` (Python) or `--as-of <date>` (CLI). The loader resolves the version whose 시행일 (effective date) is the latest on or before your date and returns that version's text.

```python
from moleg_api import MolegApi

api = MolegApi()

current = api.get_article("001248", "제3조")                    # current version
past    = api.get_article("001248", "제3조", as_of="2015-01-01") # version in force on 2015-01-01

print(current.effective_date)  # e.g. 20260102
print(past.effective_date)     # 20140101
```

```bash
python -m moleg_api get-article --law 001248 제3조                    # current version
python -m moleg_api get-article --law 001248 --as-of 2015-01-01 제3조  # historical version
```

Both `get_law` (whole statute) and `get_article` (one article) accept `as_of`.

## Always read the returned `effective_date`

`as_of` is a *request*, not a guarantee. Confirm which version you actually got by reading the `effective_date` on the returned identity or article — it is the 시행일 of the version that was loaded, not the date you asked for. In the example above, asking for `2015-01-01` returns the version whose 시행일 is `20140101`, because that was the version in force on your date.

`effective_date` is exposed on:

- [`ArticleText.effective_date`](API-Reference.md) — the loaded article's version date.
- [`LawText`](API-Reference.md)`.identity.effective_date` — the loaded statute version's date.

In CLI output it also surfaces in the envelope's `flags.effective_date`, alongside the echoed `flags.as_of`.

## When no version was in force yet

If you request a date **before the statute was first enacted** (or before any tracked version's 시행일), no historical version can be resolved, and the loader falls back to the current text. This is detectable:

- **Python** — the returned `effective_date` will be *later* than your `as_of` date. Compare them.
- **CLI** — the envelope sets `flags.version_request_unfulfilled: true` and adds a `discipline` note. When this flag is present, the text you received is **not** the version in force on your requested date.

```bash
python -m moleg_api get-article --law 001248 --as-of 1950-01-01 제1조
```

```json
{
  "flags": {
    "basis": "effective",
    "effective_date": "20260102",
    "as_of": "1950-01-01",
    "version_request_unfulfilled": true
  }
}
```

Here the returned `effective_date` (`20260102`) is far later than the requested `1950-01-01`, so the loaded text is the current version, not a 1950 one — the statute simply had no version in force on that date. Always name the reference date you actually loaded when you cite historical text.

## Why `as_of` exists — the silent-current trap

law.go.kr's plain detail lookups (`ID` + `efYd`) do **not** select a past version. Handed a numeric law id and a non-current effective date, the source silently returns *current* text without any error. A version is pinned only by its master sequence number (MST, 법령일련번호), which is version-specific.

So `as_of` does more than pass a date through. The loader:

1. Lists the statute's effective-date version rows (each carrying an MST, 시행일, and 공포번호).
2. Resolves the version whose 시행일 is the latest on or before `as_of`.
3. Reloads that version by its MST — the only key that actually pins a version.

This correction path is only taken when needed, so ordinary current-text loads keep their single source call. The practical takeaway: **do not construct your own `efYd`-based date lookups against the raw endpoints expecting a past version** — use `as_of`, which performs the MST resolution for you, and then verify `effective_date`.

## Historical text vs. what an amendment changed

`as_of` gives you the *full text as it stood* on a date. It does not tell you what a specific amendment **changed** relative to the prior version. For a before/after delta of the amended articles, use [`compare_law_versions`](API-Reference.md):

```python
diff = api.compare_law_versions("001248")
for change in diff.changes:
    print(change.article)
    print("before:", change.before_text)
    print("after:", change.after_text)
```

```bash
python -m moleg_api compare-law-versions --law 001248
```

`compare_law_versions` loads the before/after comparison pair that law.go.kr itself exposes for the statute (the source's `oldAndNew` surface). It does not accept arbitrary two-date windows — passing `before`/`after` dates raises `UnsupportedFormatError`, because the source does not support that comparison. To reconstruct a delta across two arbitrary dates, load each version with `as_of` and compare the texts yourself; to enumerate which amendments exist and their dates, use [`trace_law_history`](API-Reference.md).

## Accepted date formats

`as_of` accepts `YYYY-MM-DD` (the CLI's documented form), `YYYY.M.D`, or a bare `YYYYMMDD` — all are normalized internally to the 8-digit form the source uses.

## Notes and caveats

- `as_of` applies to the `effective` basis (current-force text). It has no effect when loading `basis="promulgated"` text, which is keyed differently.
- Version resolution depends on the statute's effective-date version list being available from the source. If that list cannot be retrieved and the direct lookup also fails, the load raises rather than silently returning current text.
- An empty or failed version list is never proof that no past version exists — it is scoped to what the source returned for that lookup.

## See also

- [API Reference](API-Reference.md) — full signatures for `get_law`, `get_article`, `compare_law_versions`, and `trace_law_history`.
- [Command-Line Interface](CLI-Reference.md) — the JSON envelope, `flags`, and `discipline` notes.
- [Data Models](API-Reference.md) — `ArticleText`, `LawText`, `LawDiff`, and the `effective_date` field.
