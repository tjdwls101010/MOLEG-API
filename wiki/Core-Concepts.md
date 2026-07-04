# Core Concepts

`moleg-api` is a task-level loader for Korean legal sources from [law.go.kr](https://www.law.go.kr/). Its public interface is small and deep: you search or plan first, then load the selected legal text, authority detail, or delegated-rule context. A handful of concepts make the difference between a citation you can trust and a citation that quietly misleads. This page covers the six that matter most.

If you are looking for method signatures, see the [API Guide](API-Reference.md). If you are calling from a shell, see the [CLI](CLI-Reference.md).

## 1. The search → select → load discipline

Every source family in this SDK separates *discovery* from *loading*, and the two are not interchangeable.

- **Search / plan** methods (`search_laws`, `search_administrative_rules`, `search_interpretations`, `search_cases`, `search_constitutional_decisions`, `expand_legal_query`, `find_comparable_mechanisms`) return **candidate identity metadata** — enough to identify a source and decide whether to load it, but *not the source text*.
- **Load** methods (`get_law`, `get_article`, `get_administrative_rule`, `get_interpretation`, `get_case`, `get_constitutional_decision`, `get_annex_form_body`, and the `load_*_context` loaders) retrieve the actual normalized text of a source you selected.

**A search hit is a candidate, not a citation.** After only `search_laws()`, you have a law's identity, name, and dates — you do not have its article wording, duties, sanctions, or procedures. You must load the selected law or article before citing any of that. The same rule holds for every family: an interpretation, case, or Constitutional Court *search hit* carries title and date metadata only; the holding, reasoning, and reviewed statutes come from the corresponding `get_*` loader.

Search results carry a `follow_up` field that spells out the next load step and pre-fills the identifiers, so you do not re-type keys by hand:

```python
from moleg_api import MolegApi

api = MolegApi()

hits = api.search_laws("주택임대차보호법", basis="effective", display=5)
selected = hits[0].identity          # a LawIdentity candidate — not citable text

law = api.get_law(selected, basis="effective")   # now you have article text
print(law.articles[0].text)
```

```bash
python -m moleg_api search-laws "주택임대차보호법"          # → candidates
python -m moleg_api get-law --law 001248                    # load a chosen candidate
```

`expand_legal_query()` and `find_comparable_mechanisms()` sit even earlier in the chain: they are *planning* tools. Their term, related-law, related-article, and comparable-mechanism suggestions are a menu of what to search or load next — never final authority. Load selected source text before citing anything from them.

**Empty results are scoped, not absolute.** A zero-hit search means "this exact query, on this basis/scope, returned no rows" — it does not prove that no such law, rule, precedent, or attached material exists. Widen the terms, try an alternate source family, or load a detail path before making any absence claim.

## 2. Candidate identity vs. loaded text

The distinction above is reflected directly in the data model, so you can tell at a glance whether you are holding a candidate or real text.

| You have… | Type | What it contains | Citable as source text? |
|---|---|---|---|
| A search hit | `LawHit`, `AdministrativeRuleHit`, `InterpretationHit`, `JudicialDecisionHit`, `AnnexFormHit` | A normalized `*Identity` plus the raw source row and a `follow_up` | No |
| A loaded body | `LawText`, `ArticleText`, `AdministrativeRuleText`, `InterpretationText`, `JudicialDecisionText`, `AnnexFormText` | The normalized text, articles, and structured fields | Yes |

A `LawHit` wraps a `LawIdentity` (the identity) plus the raw row; a `LawText` wraps that identity *and* the extracted articles and supplementary provisions. Reach for identity fields (name, dates, ministry, `law_id`, `mst`) from a hit; reach for wording, duties, and requirements only from a loaded body.

One caveat on loaded article text: definitions, exceptions, application targets, and requirements often live in nested 항 / 호 / 목 inside `ArticleText.text`, not in the article title (`조문제목`) or the top-level `조문내용`. Summarize from the full `text`, not from the title alone.

## 3. Effective (시행) vs. promulgated (공포) basis

Most load and search methods take a `basis` argument, typed as `Literal["effective", "promulgated"]`, defaulting to `"effective"`. It selects which legal reality you are asking about, and confusing the two produces correct-sounding but wrong answers.

- **`basis="effective"` (시행일 기준)** — the text that is or was *in force*. This is the right basis for "what does current law say?", "is this in force now?", and "현재 시행" questions. It is the default.
- **`basis="promulgated"` (공포일 기준)** — lookup keyed by promulgation date and number. Use it for two situations: resolving a promulgation bridge from enacted-bill facts, and reconstructing historical promulgation context.

**A promulgated law is not necessarily in force.** A statute can be promulgated (공포) with an effective date (시행일) still in the future. Resolving a promulgation bridge or loading promulgated text proves *identity and wording*, not *current force*. For current-force questions, pass an explicit reference date via `as_of=` and check whether the loaded effective date is later than your reference date before calling the law current.

State the basis in your answer whenever the distinction matters — say whether a text was retrieved by effective-date or promulgation-date basis.

```python
# Current-force text (default basis)
current = api.get_law(selected, basis="effective")

# The version in force on a specific date
as_filed = api.get_article(selected, "제3조", basis="effective", as_of="2023-08-01")
```

For history and repealed-law (구법 / 폐지법) questions, treat the task as loading a *historical* source: carry an as-of date and preserve the history/repeal status in your answer. A current-basis search returning nothing is not proof that the historical source never existed.

## 4. Versions and MST (same law, different effective dates)

A single statute exists as a series of **versions**, one per effective date. All versions share the same `law_id` (법령ID), but each version has its own **`mst`** (법령일련번호, the master sequence number) that pins that specific version.

This is the key that makes historical and as-of loading work. law.go.kr's `ID + efYd` detail lookups do **not** select a past version — they silently return the current text even when you pass an old effective date. The `mst` is the only key that pins a version. The SDK handles this for you: when you pass an `as_of` that resolves to a non-current version, it lists the statute's version rows, finds the version in force at that date (latest 시행일 ≤ `as_of`), and reloads the correct version by `mst`. You do not manage `mst` by hand — but knowing it exists explains why `as_of` reliably returns historical text.

You can see the version fan-out directly in a search. `주택임대차보호법` returns several rows sharing `law_id` `001248`, each with a distinct `mst` and effective date:

```
law_id  mst      promulgation_date  effective_date   promulgation_number
001248  276291   20251001           20260102         21065
001248  249999   20230418           20230719         19356
```

Both `LawIdentity.law_id` and `LawIdentity.mst` are exposed on every identity. When you hand a `LawHit` or `LawIdentity` straight into a loader, its `mst` carries the exact version through — so a candidate you picked is the version you load.

Do not treat `law_id`, `mst`, `lid`, and other raw keys as interchangeable. `law_id` names the *law*; `mst` names a *version of that law*. The raw source keys are preserved under `identity.raw_keys` for audit, but the normalized `law_id` / `mst` fields are what you build on.

## 5. Authority types are distinct (do not flatten them)

MOLEG exposes four different kinds of legal authority, and they do not carry the same weight. Keep the source label attached to every citation.

| Authority | Model source label | law.go.kr family | Notes |
|---|---|---|---|
| MOLEG official interpretation (법령해석례) | `source_type` on the interpretation | `expc` | The 법제처 official interpretation. |
| Ministry first-instance interpretation | `source_type` / `source_target` | `*CgmExpc` | A central ministry's own reading — a different authority level from a MOLEG interpretation. |
| Supreme Court case (판례) | `JudicialDecisionIdentity.source_type` | `prec` | Ordinary court precedent. |
| Constitutional Court decision (헌재결정) | `JudicialDecisionIdentity.source_type` | `detc` | Constitutional review — not ordinary precedent. |

These map to distinct search and load methods (`search_interpretations` / `get_interpretation`, `search_cases` / `get_case`, `search_constitutional_decisions` / `get_constitutional_decision`), and each loaded result preserves its `source_type` / `source_target` so the authority level survives into your answer. A MOLEG interpretation, a ministry interpretation, a Supreme Court case, and a Constitutional Court decision are four different things — never merge them under a generic "the law says."

Two practical notes:

- On `search_interpretations()`, `source="all"` means MOLEG **plus one specified ministry**; `source="all_ministries"` is the intentional, higher-cost fan-out across the ministry registry. They are not the same scope.
- Constitutional doctrines such as 과잉금지원칙 or 평등원칙 are **free-text search terms**, not indexed categories. The `detc` source has no doctrine field, so a keyword search can surface candidate decisions but cannot prove exhaustive doctrine coverage or "no constitutional risk." Load selected detail with `get_constitutional_decision()` before citing 판시사항, 결정요지, or reviewed statutes.

When you need authority scoped to specific statute articles, use `load_authority_context()` and cite from its `current_authorities`, using the `referenced_articles` / `reviewed_articles` on each loaded result to confirm the authority actually addresses your target article.

## 6. Staged context bundles and deferred follow-ups

For a broad or under-specified question — or one that begins from a statute or bill anchor — loading each source by hand is tedious. `load_legal_context_bundle()` runs one bounded first pass over the likely sources and returns a `LegalContextBundle` that separates what was actually loaded from what is only a lead.

A bundle has three tiers:

- **`loaded`** (`LoadedContext`) — source text already retrieved and citable: laws, articles, delegations, and any eagerly loaded interpretation/case/ Constitutional Court detail.
- **`candidates`** (`CandidateContext`) — sources discovered but *not* loaded. These are still just candidates (see concept 2): identity metadata only.
- **`deferred`** (a list of `DeferredLookup`) — bounded next lookups the bundle chose not to run, plus `ambiguities`, `gaps`, and `source_notes`.

**A bundle is source loading, not a conclusion.** Treat its candidates and deferred lookups as the next menu, never as proof that every relevant source body has been inspected. Do not claim exhaustive interpretation, case, Constitutional Court, administrative-rule, or annex/form coverage from a bundle alone.

A **deferred follow-up** is a bounded, executable next step. Each `DeferredLookup` names an `interface`, a `query`, filters, and a `reason`. You run it through `load_followup()`, which routes it to the right task-level loader without you touching source target names, `ID`/`mst` rules, or article formatting:

```python
bundle = api.load_legal_context_bundle(
    query="자동차 방치 처리 기준",
    mode="question",
    budget="standard",
)

for lookup in bundle.deferred:
    if lookup.interface == "load_administrative_rule_context":
        rule_context = api.load_followup(lookup)   # executes the routed loader
        break
```

`load_followup()` executes MOLEG-API follow-ups only. A follow-up whose `interface` is `websearch` or `congress-db` raises `UnsupportedFormatError` — a deliberate handoff signal: latest social facts belong to WebSearch, and National Assembly bill and vote facts belong to congress-db, not to this SDK.

Two related staged loaders share the bundle shape:

- `load_institutional_system()` — composes an explicit set of statutes you already selected (via repeated `statute_ids`) into one bundle. It composes the set; it does **not** discover it or decide which statute is primary.
- `load_delegated_criteria()` — anchors on one statute and additionally loads bounded administrative-rule and annex/form operational criteria.

Every public dataclass — including the whole bundle — serializes recursively, so you can inspect or persist it:

```python
payload = bundle.to_dict()                    # omits raw source payloads
debug = bundle.to_dict(include_raw=True)      # keeps raw law.go.kr rows
text = bundle.to_json_string()
```

## Where to go next

- [API Guide](API-Reference.md) — every task-level method and its arguments.
- [CLI](CLI-Reference.md) — the same methods as shell subcommands and the JSON envelope.
- [Follow-up Lookups](Core-Concepts.md) — running deferred lookups end to end.
- [Source Coverage and Limits](Sources-and-Coverage.md) — what each source family does and does not expose.
