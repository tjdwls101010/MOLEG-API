# Legal Context Bundle Design

This is the implemented contract for #6. The goal is to let the future legislative-expert skill load enough legal context to reason well without turning every user question into an unbounded scrape of law.go.kr.

## Recommendation

Use a staged bundle, not a monolithic answer object.

`MolegApi.load_legal_context_bundle()` returns loaded official context, deferred follow-up handles, ambiguity records, and WebSearch gaps. It does not produce the legal conclusion. Claude remains responsible for reasoning from the returned sources.

The bundle should optimize for progressive loading, not maximum payload size. It loads high-leverage anchors first, exposes bounded candidates next, and leaves expensive/noisy detail as explicit follow-up work. If adding a source would make most ordinary bundle calls carry irrelevant text, keep it as a candidate or `DeferredLookup` instead.

## Public Interface

```python
MolegApi.load_legal_context_bundle(
    query: str | None = None,
    *,
    promulgation_bridge: dict | None = None,
    law_identifier=None,
    articles: list[str | int] | None = None,
    mode: str = "question",  # "question" | "promulgated_bill" | "statute_review"
    budget: str = "standard",  # "minimal" | "standard" | "broad"
) -> LegalContextBundle

MolegApi.load_institutional_system(
    statute_identifiers: list[str | LawIdentity | LawHit],
    *,
    articles: list[str | int] | None = None,
    budget: str = "standard",
) -> LegalContextBundle
```

The interface accepts either a user question, a `congress-db` promulgation bridge, or a known law identity. Passing raw MOLEG `target` values remains unsupported.
`load_institutional_system()` accepts an explicit statute set and returns the same bundle shape with `request.mode="institutional_system"` and `request.statute_ids` preserving the input statutes.

## Response Shape

```python
LegalContextBundle(
    request=BundleRequest(...),
    loaded=LoadedContext(...),
    candidates=CandidateContext(...),
    deferred=list[DeferredLookup],
    ambiguities=list[Ambiguity],
    gaps=list[ContextGap],
    source_notes=list[str],
)
```

`loaded` is source material already retrieved and safe for Claude to inspect. It contains statute texts, requested article texts, delegated-rule graphs, institutional-system `law_structures` when requested, and conditionally eager-loaded interpretation/case/Constitutional Court detail when the question warrants deeper legal-meaning, application, or constitutional analysis. Administrative-rule, annex/form, history, and diff details remain candidate/deferred context until explicitly loaded through their detail interfaces.

`candidates` are possible next sources, not authority. This includes administrative-rule, annex/form, interpretation, case, and Constitutional Court hits whose bodies should be loaded separately when they may be operative.

`deferred` contains handles for expensive or noisy follow-up calls, such as loading full cases after case search results are ranked.

`gaps` explicitly tells the skill when MOLEG is not the right source, especially for latest social facts, statistics, government announcements, news, or domain context that belongs in WebSearch.

## Implemented Behavior

- `mode="question"` calls `expand_legal_query()`, loads the first law candidate when available, finds delegated rules, searches administrative rules, law/admin-rule annex forms, interpretations, Supreme Court cases, and Constitutional Court decisions. Narrow lookup questions keep detail loading deferred; legal-meaning/application/constitutional questions eagerly load top-ranked interpretation, case, and/or Constitutional Court detail within budget.
- `mode="promulgated_bill"` starts from `congress-db` bridge fields and calls `resolve_promulgated_law()`. Ambiguity or no-result becomes structured `Ambiguity` plus a gap instead of a silent best guess. If exact `prom_no` / `promulgation_dt` matching fails but law-name candidates exist, the bundle preserves those candidates and emits `source_lag_or_manual_review_required` so Claude does not confuse MOLEG source lag with "not enacted."
- `mode="statute_review"` starts from a supplied law identity and loads the current law text or requested articles.
- `mode="institutional_system"` is produced by `load_institutional_system()`. It starts from an explicit statute set, loads statute text or requested articles for each statute, loads `get_law_structure(depth=1)`, loads article-level delegations where available, and keeps administrative-rule, annex/form, interpretation, case, and constitutional detail as bounded candidates/deferred lookups.
- Every bundle with a search query includes a `websearch_required` gap because latest social facts, statistics, policy announcements, and news are outside law.go.kr.
- `budget="standard"` is the default. `minimal` keeps interpretation and judicial full text deferred; `standard` and `broad` allow bounded eager detail loading only when query intent warrants it.

## Default Budgets

### `minimal`

Use when the user asks a narrow citation or lookup question.

- law candidates: 1
- loaded laws/articles: 1 law or up to 3 requested articles
- delegated rules: 3
- administrative rules: 3 search hits, no full text by default
- annex/forms: 3 search hits, selected body loading deferred
- interpretations: 3 search hits, no eager full text
- cases: 3 search hits, no eager full text
- constitutional decisions: 2 search hits, no eager full text

### `standard` recommended default

Use for ordinary legislative review questions.

- law candidates: up to 3
- loaded laws/articles: 1 primary law plus up to 5 article candidates
- history/comparison: only when a promulgation bridge, article, or date is present
- delegated rules: up to 5 relationships
- administrative rules: up to 5 search hits; load full text later with `get_administrative_rule()` when a selected hit is directly relevant
- annex/forms: up to 5 hits; call `get_annex_form_body()` only when the question turns on attached criteria, tables, amounts, or forms
- interpretations: up to 5 search hits; top-1 full text is eagerly loaded when legal meaning or application intent is detected
- cases: up to 5 search hits; top-1 full text is eagerly loaded when legal meaning or application intent is detected
- constitutional decisions: up to 3 search hits; top-1 full text is eagerly loaded when legal meaning or constitutional-risk intent is detected

### `broad`

Use only when the user asks for a survey, memo, or risk scan.

- law candidates: up to 5
- loaded laws/articles: one primary law or up to 10 requested articles
- delegated/admin/annex-form/interpretation/case searches: up to 10 hits each
- interpretation/case/Constitutional Court detail: top-2 per triggered source type; remaining candidates stay deferred

## Workflow By Mode

### `promulgated_bill`

1. Resolve `promulgation_bridge` through `resolve_promulgated_law()`.
2. Load current effective text through `get_law()` or requested `get_article()`.
3. Use `trace_law_history()` or `compare_law_versions()` when dates/articles make the change traceable.
4. Use `find_delegated_rules()` to identify enforcement decrees, enforcement rules, notices, and administrative rules.
5. Search annex/forms when operative standards may live in attached tables, thresholds, amounts, or forms. Load selected annex/form bodies only when needed. For table-like annexes, inspect `structured_data.parsing_confidence` before using extracted rows; keep the plain text as fallback authority.
6. Search administrative-rule, interpretation, and judicial context as candidates; load selected detail only after Claude ranks the bundle unless eager detail loading is triggered by the question.
7. Add a WebSearch gap for social context, statistics, or current policy background.

### `question`

1. Call `expand_legal_query()`.
2. Load a small number of law/article candidates.
3. Search delegated/admin/annex-form/interpretation/judicial context using expansion terms.
4. Keep unresolved candidates and ambiguities visible.
5. Add WebSearch gaps when the question asks for current facts outside law.go.kr.

### `statute_review`

1. Start from the supplied law identity.
2. Load the requested articles or the current law text.
3. Trace delegated rules and search administrative-rule candidates first.
4. Search annex/forms when the loaded text references 별표, 서식, 기준표, 금액, 요건, 신청서, or similar attached material. Use `get_annex_form_body()` for selected candidates before relying on the attached content.
5. Search interpretations and cases second.
6. Search constitutional decisions when the review asks about limits, rights, sanctions, equality, proportionality, or constitutional risk.

### `institutional_system`

1. Start from the statute identities Claude already selected. Do not use this mode to infer a 제도 from a concept alone.
2. Load current text or requested articles for each statute.
3. Load the `lsStmd` law hierarchy and article-level `lsDelegated` rows for each statute.
4. Search administrative rules, annex/forms, interpretations, cases, and Constitutional Court decisions by statute name.
5. Keep those secondary sources as candidates/deferred detail unless a later explicit loader is needed.
6. Preserve ambiguous or unresolved statute identifiers in `ambiguities`, `gaps`, and `deferred` instead of guessing.

## Default Answer To #6 Open Questions

### What should the default bundle size be for a single user question?

Use `budget="standard"`: up to 3 law candidates, one primary law or up to 5 requested articles, up to 5 delegated/admin/annex-form/interpretation/case candidates, and detail loading only after the bundle shows which candidates matter. This keeps the first context bundle useful without turning every question into a broad research memo.

### Should the bundle prefer statute/article context first and defer cases?

Yes. Load statute/article context first because it anchors the legal question. Search interpretations and cases in the same bundle, but defer full text until legal meaning, application constraints, or constitutional risk are central to the question.

### How should gaps be represented so Claude knows when to invoke WebSearch?

Use explicit `ContextGap` records:

```python
ContextGap(
    kind="websearch_required",
    reason="latest social statistics are outside law.go.kr",
    query="...",
    recommended_interface="websearch",
)
```

Do not bury gaps in prose. The skill should be able to inspect a structured gap and make a separate WebSearch call.

## Non-Goals

- Do not implement a legal conclusion generator inside MOLEG-API.
- Do not load every case or interpretation detail by default.
- Do not load every annex/form body by default.
- Do not treat query expansion candidates as authority.
- Do not use this bundle to replace `congress-db` SQL for bill facts.
- Do not make WebSearch optional for current social facts outside law.go.kr.
