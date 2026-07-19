# Gotchas

`moleg-api` normalizes law.go.kr sources, but it does not decide what a source *means*. Several distinctions are easy to collapse and will quietly produce a wrong legal claim if you do. This page lists the traps that matter most to a first-time integrator, the model fields that expose each one, and the discipline each field enforces.

Two ideas run through every gotcha:

- **Search hits are identity candidates, not source text.** A `*_hit` / `*_candidate` / `*_planning` result tells you *what to load next*, never *what the law says*. Only `*_text` / `*_context` bodies loaded through a detail method are citable.
- **Absence of a result is not proof of absence.** A zero-hit search, a `NoResultError`, or a source-access failure means "this query, this scope, this moment" — not "no such law, article, precedent, or criterion exists."

When a trap is *live* in a given result, the CLI surfaces a `discipline` line and often a `flags` entry for it (these fire only when the condition is actually present, so the common path stays quiet). The Python API exposes the same conditions as model fields. Both are shown below.

## Search hits are candidates, not loadable text

`search_laws()`, `search_administrative_rules()`, `search_annex_forms()`, `search_interpretations()`, `search_cases()`, and `search_constitutional_decisions()` return `*Hit` objects wrapping an `identity`. They resolve *which* source you mean; they do not carry citable article wording, duties, sanctions, procedures, holdings, or criteria.

Do not quote from a hit. Load the selected identity first, then cite the loaded body:

```python
hits = api.search_laws("주택임대차보호법", basis="effective", display=5)
selected = hits[0].identity          # identity candidate — not citable
law = api.get_law(selected, basis="effective")
article = api.get_article(selected, "제3조", basis="effective")
print(article.text)                  # loaded source text — citable
```

```bash
python -m moleg_api search-laws "주택임대차보호법"      # kind: law_hit_list  (candidates)
python -m moleg_api get-article --law 001248 제3조      # kind: article_text  (loadable body)
```

The CLI enforces the ordering structurally: pass a **law name** to a loader (`get-law`, `get-article`, …) and it refuses with `kind: needs_search_first` (exit 5), because loaders take a `law_id`, not a name.

```bash
$ python -m moleg_api get-article --law "주택임대차보호법" 제3조
{ "ok": false, "kind": "needs_search_first",
  "discipline": ["로더에 법령명이 들어옴 — search-laws로 law_id를 먼저 얻어 --law에 넘겨라."],
  "next": [{"cmd": "moleg search-laws \"주택임대차보호법\""}] }
```

The same rule applies to `expand_legal_query()` and `find_comparable_mechanisms()`: their `term_candidates`, `related_laws`, `related_articles`, and returned `LawIdentity` anchors are *planning* context. They are never legal authority until you load the selected law/article text. See [Follow-up lookups](Core-Concepts.md) for how a candidate's `follow_up` / `deferred` points to the exact next call.

## Effective date is not promulgation date

A law can be promulgated (published) and still not be in force. `LawIdentity` carries both dates as separate fields:

- `promulgation_date` — when it was published
- `effective_date` — when it takes (or took) effect
- `basis` — `"effective"` or `"promulgated"`, the basis the row was retrieved on

For "is this currently in force?" questions, use `basis="effective"` and compare `effective_date` to your reference date. A live example from `search_laws("주택임대차보호법")` returns a candidate with `promulgation_date="20251001"` but `effective_date="20260102"` — promulgated in 2025, not effective until 2026.

When you load through a bundle with a reference date, pass `as_of` and inspect the `not_effective_as_of` gap before calling a law current:

```python
bundle = api.load_legal_context_bundle(
    law_identifier="001248", articles=["제3조"], as_of="2025-11-01",
)
gap_kinds = {g.kind for g in bundle.gaps}
if "not_effective_as_of" in gap_kinds:
    ...  # promulgated / source-loadable, but NOT in force on 2025-11-01
```

The CLI raises `flags.not_effective_as_of` with the discipline line *"공포됐으나 기준일 미시행 — '현재 시행 중'으로 단정 금지"* when this gap is present. A resolved promulgation bridge (`resolve_promulgated_law()` → `LawIdentity`) proves *identity*, not *current force*: the `law_identity` result carries the discipline *"공포 bridge 신원 확정일 뿐 … not_effective 여부 확인"*.

## `as_of` loads the version in force *at that date* — verify what came back

Passing `--as-of YYYY-MM-DD` to a loader does not filter; it resolves the historical version that was in force on that date. If no version was in force yet, the loader returns a *later* version instead. Check the returned `effective_date` against your requested date. The CLI computes this for you and sets `flags.version_request_unfulfilled` with a discipline line when the returned effective date is after the requested one — meaning there was no version in force on your date, and you may be looking at a future amendment rather than the historical text you asked for.

## A current-law bridge is not an amendment delta

Resolving a `congress-db` promulgation bridge and loading current text proves *identity and current wording*. It does **not** prove *what an enacted bill changed*. Before describing a change, load the delta explicitly:

- `compare_law_versions()` → `LawDiff` gives before/after wording for the **selected rows only**. It does not carry amendment reason, legislative intent, full bill purpose, or exhaustive changed-provision coverage — the `law_diff` result says exactly this.
- `trace_law_history()` → `LawHistory` gives the amendment chronology. Full-law history keeps `HistoryEvent.article_text=None`; article-scoped history (`article=...`) may populate `article_text` with the post-change snapshot.

`HistoryEvent.bill_id` is populated **only** when you supply a `promulgation_bridge` map; the package does not query `congress-db` itself. The bridge keys for joining back are `promulgation_law_name`, `promulgation_number`, and `promulgation_date`.

## Deleted and moved articles are source *status*, not current text

A loaded `ArticleText` (and `AdministrativeRuleArticleText`) exposes status fields that must be checked before you treat the text as an operative rule:

- `is_deleted: bool` and `revision_type == "삭제"` — the article is deleted. `제N조 삭제` is deleted source state, not a current duty, permission, sanction, or procedure.
- `moved_to` and `revision_type == "이동"` — the substance now lives at a different article. The marker is source state; the current text is at the destination.

```python
art = api.get_article(selected, "제5조")
if art.is_deleted or art.revision_type == "삭제":
    ...  # cite as deleted source state only
if art.moved_to:
    ctx = api.load_article_context(selected, "제5조")   # follows the move
    current = ctx.current_article                       # destination text
```

`load_article_context()` follows a move to its destination by default and returns the destination in `current_article`; if `current_article is None` for a moved/deleted request, the substance was not loaded — do not cite current obligations. `load_administrative_rule_context()` does the same for administrative rules, exposing only loaded destination rows in `current_articles`.

The CLI raises `flags.is_deleted` / `flags.moved_to` with matching discipline lines when either condition is present on a loaded article. (Note: law.go.kr emits `제0조` and blank strings as a non-move sentinel; the CLI treats those as parse noise, not a real destination.)

## Article substance lives in the nested text, not the title

`ArticleText.text` (and `AdministrativeRuleArticleText.text`) preserves the nested 항 / 호 / 목 structure. Definitions, exceptions, application targets, and requirements frequently live in those nested units. Do **not** summarize from the article title (`조문제목`) or a top-level `조문내용` alone — you will miss the operative clause. The `article_text` result carries the discipline *"정의·예외·적용대상·요건은 text의 항·호·목 중첩에 있다 — 조문제목·상위 조문내용만으로 요약 금지."*

## Supplementary provisions (부칙) are separate source text

시행일, 적용례, and 경과조치 live in 부칙, exposed as `supplementary_provisions` — a separate list of `SupplementaryProvision`, distinct from the main `articles`. Do not answer a transition-scope question from a main article, or from the law-level `LawIdentity.effective_date` metadata, alone:

```python
law = api.get_law(selected, basis="effective")
for prov in law.supplementary_provisions:      # 부칙 — 시행일/적용례/경과조치
    print(prov.text)
```

`AdministrativeRuleText` carries its own `supplementary_provisions`. Cite them separately for rule 시행일 / 적용례 / 경과조치; the rule-level `identity.effective_date` is not the full transition analysis. When present, the CLI sets `flags.has_supplementary` with the corresponding discipline line.

## Administrative-rule `issued_on` is 발령일자, not 시행일자

`search_administrative_rules(issued_on=...)` filters on **발령일자 (issue date)**, not 시행일자 (effective date). The search parameter is named `issued_on` (not `as_of`) precisely to prevent this confusion. A rule can be issued but not yet effective, or superseded.

Before calling a loaded rule the *current* operational criteria, compare the loaded `AdministrativeRuleText.identity.effective_date` to your reference date. If it is later, it is future-effective source text, not current criteria. The CLI attaches `flags.issued_on_note` on loaded administrative-rule results as a standing reminder, and `flags.issued_on_is` on the search result.

```bash
python -m moleg_api search-administrative-rules "..." --issued-on 20240101   # 발령일자 filter
```

## Annex/form thresholds require loading the body

`search_annex_forms()` returns metadata and file/detail links only. Thresholds, amounts, criteria, and form content live in the attached table (별표·서식), which is loaded through `get_annex_form_body()`. **Do not cite a threshold, amount, criterion, or extracted row from a search hit** — the `annex_form_hit_list` result carries the discipline *"임계값·금액·기준은 get-annex-form-body로 본문 로드 후에만 인용."*

When a body loads, `AnnexFormText.structured_data` (a `StructuredTableData`) is best-effort. Check `parsing_confidence` before relying on `rows`. If `rows` is empty or `parsing_confidence` is `"low"`, that is **not** "no criteria" — fall back to the plain `text`. The CLI raises this as a discipline line when the structured rows are empty or low-confidence.

An **empty** `search_annex_forms()` result is scoped evidence for "this exact search found nothing," not proof that no attached criteria, annex, form, or threshold table exists. Check the source law text, administrative-rule annex/forms, and alternate terms before any absence claim.

## Preserve source authority — interpretations, cases, decisions are different levels

MOLEG official interpretations, ministry first-instance interpretations, ordinary court cases, Constitutional Court decisions, committee decisions, and administrative appeal rulings are distinct authority levels and must not be flattened. Their identity carries the distinguishing metadata:

- `InterpretationIdentity.source_type` / `source_target` — MOLEG interpretation vs. ministry interpretation. In search, `source="all"` means MOLEG **plus one specified ministry**; `source="all_ministries"` is a registry-wide fan-out — use it only when that breadth is intentional.
- `JudicialDecisionIdentity.source_type` / `court` — ordinary court case (`prec`) vs. Constitutional Court decision (`detc`).
- `AdjudicationIdentity.source_type` / `source_authority` — a committee decision (`committee_decision`) vs. an administrative appeal ruling (`administrative_appeal` / `special_administrative_appeal`).

**Neither kind of adjudication is precedent.** A 위원회 결정 is an administrative disposition by the regulator that administers the statute — it shows how that agency applies the law, not what the law means, and it can be overturned in 행정소송. An 행정심판 재결 reviews *another* agency's disposition from inside the executive branch, and a losing party can still take it to court. Citing either as 판례 overstates what it settles. They carry separate `kind` values (`committee_decision_text`, `administrative_appeal_text`) for exactly this reason.

The CLI preserves these via `flags.source_type` / `flags.source_authority` and a discipline line on loaded interpretation and decision bodies. Carry the label into any answer that cites the source.

Use `referenced_articles` (interpretations, cases) and `reviewed_articles` (decisions) to confirm a loaded authority actually concerns your target article before citing it for that article. In a bundle, `authority_article_mismatch` / `authority_article_unverified` / `authority_article_partial_match` gaps flag when eager-loaded authority points to different articles — cite only what `current_authorities` contains, not everything in `loaded`.

## An agency with no records is not an agency that did nothing

`search-committee-decisions` and `search-administrative-appeals` get used to ask whether a regulator acted — which makes a zero-hit result the most dangerous result in the package, because the wrong reading points in exactly the direction the question was aimed. Zero hits are returned by all of: the agency never receiving a complaint, receiving one and not opening a case, deciding it but not publishing the 의결서, and the matter belonging to a different body's docket. None of those is "nothing happened."

Two concrete traps:

- **Wrong docket reads as absence.** 소청, 조세, and 해양안전 rulings are *not* in the general `decc` list; they live in the special tribunals (`--tribunal acr|adap|tt|kmst`). A search that only asked `decc` has not covered them.
- **Wrong agency reads as absence.** The same conduct can sit with different regulators depending on which statute frames it. Try the other plausible `--committee` code before concluding anything.

When the public record runs out, that is the point to reach for an official document request rather than to record a negative finding.

## Constitutional doctrines are free-text search terms, not an index

`search_constitutional_decisions(search_body=True)` searches the `detc` source as **free text**. Doctrines like `과잉금지원칙` or `평등원칙` are query strings, not structured filters — law.go.kr exposes no doctrine/category field. A keyword search can surface candidate decisions, but it cannot prove doctrine-indexed coverage, and **it cannot support a "no constitutional risk" or "doctrine exhaustively covered" claim.**

This discipline fires even when the search returns zero hits — which is exactly when it matters most:

```bash
$ python -m moleg_api search-constitutional-decisions "과잉금지원칙"
{ "ok": true, "kind": "constitutional_hit_list", "count": 0,
  "discipline": [
    "doctrine(과잉금지원칙 등)는 색인 아닌 자유텍스트 검색어 — '위헌 소지 없음'·doctrine 망라 단정 금지. get-constitutional-decision으로 로드.",
    "0건 — 이 검색어·범위로 못 찾음일 뿐, 부재의 증명 아님."
  ] }
```

Load selected detail with `get_constitutional_decision()` before citing 판시사항, 결정요지, 심판대상조문, reviewed statutes, or full text.

## Zero results and source-access failures are not proof of absence

Two distinct outcomes both mean "not found here, now" — neither means "does not exist":

**Zero-hit searches.** An empty `search_*` result is scoped to the exact query, source, and filter. It supports "this search returned zero hits," never "no such law / precedent / interpretation / delegated rule / annex / constitutional decision exists." Before any absence claim, disclose the searched terms and try alternate terms, source families, or detail loaders. The CLI returns these as `ok: true, count: 0` (exit 0) with the discipline *"0건 — 이 검색어·범위로 못 찾음일 뿐, 부재의 증명 아님."* An empty `find_delegated_rules()` (or its `NoResultError`) is likewise scoped to the searched law/article, not proof of no delegation.

**Source-access failures.** `RateLimitError` and `RetryExhaustedError` are *temporary source problems*, not zero-hit results. The CLI reports them as `kind: source_access_error` (exit 3), kept structurally distinct from a zero-hit search (exit 0) and from `no_result` (exit 4). A rate limit must never collapse into "no current law" or "no source exists." (`ParseFailureError` — a response that could not be normalized — is also distinct: it is not source absence either.)

| Outcome | CLI `kind` | Exit | Means |
|---|---|---|---|
| Zero-hit search | `*_hit_list`, `count: 0` | 0 | Nothing matched this query/scope |
| Multiple identities | `ambiguous` | 2 | Surface candidates; do not pick |
| Rate limit / retry / parse | `source_access_error`, `parse_error` | 3 | Temporary — retry, not absence |
| Loader found no body | `no_result` | 4 | No source text for this identifier |
| Law name given to a loader | `needs_search_first` | 5 | Search for the `law_id` first |

See [CLI reference](CLI-Reference.md) for the full exit-code contract.

## A table of contents is not the statute, and a 요지 is not the ruling

`get-law --toc` and `--brief` exist to keep a load from costing more than the question is worth, and both re-open the candidate-vs-body gap *inside* a single document.

- `--toc` returns `kind: law_toc_map`, not `*_text`. An article's number and title tell you where to look, never what it requires — 「제15조(개인정보의 수집·이용)」 does not tell you which conditions apply or what the exceptions are. Load the article before saying what it does.
- `--brief` returns the court's or agency's own précis with the full body withheld. A 결정요지 paraphrases; a verbatim quotation attributed to a ruling must come from the full text. `flags.brief.withheld` lists exactly which sections were held back, and reports only those the document actually had — so it never implies a section exists that the source never carried.

## `AmbiguousLawError` is not permission to pick the first candidate

When a request matches multiple plausible law identities, the package raises `AmbiguousLawError`, which carries a `candidates` list. This is an **ambiguity to surface**, not a signal to silently take `candidates[0]`. Multiple plausible hits from a law-name search are the same: an ambiguity, not a default.

```python
from moleg_api.errors import AmbiguousLawError

try:
    ...
except AmbiguousLawError as exc:
    for cand in exc.candidates:      # surface these — do not auto-select
        ...
```

The CLI reports this as `kind: ambiguous` (exit 2) with the discipline *"모호성이지 첫 후보를 고를 허가가 아님 — 후보를 사용자에게 제시."* Same-name candidates that differ by effective date are the common case: load the current one with `get_law(law_id)` and a specific historical version with `as_of=<effective date>`, but only after you (or the user) have chosen which one.

## See also

- [Quickstart](Quickstart.md) — install and first calls
- [API guide](API-Reference.md) — when to use each interface
- [Follow-up lookups](Core-Concepts.md) — turning a candidate into the next executable call
- [CLI reference](CLI-Reference.md) — envelope, exit codes, and the search→load discipline
- [Source coverage and limits](Sources-and-Coverage.md) — supported source families and what is out of scope
