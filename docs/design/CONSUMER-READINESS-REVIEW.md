# MOLEG-API Consumer-Readiness Review

Reviewed on 2026-06-16, from the perspective of the **future legislative-expert skill (Claude)** that will consume MOLEG-API together with `congress-db` and WebSearch. This review evaluates fitness *as a tool for an LLM consumer*, not code cleanliness.

It is the durable record behind the 2026-06-16 improvement issues. The completion audits (`GOAL-COMPLETION-AUDIT.md`, `COMPLETION-RISK-AUDIT.md`) established that the *initial loader core* is implemented and live-proven; this review opens the next layer: **is the loaded context discoverable, callable, and analysis-ready for institutional (제도) analysis and legislative design?**

## Method

Two adversarial multi-agent review rounds against the actual code (`moleg_api/*.py`) and docs:

1. **Ergonomics round** — 8 diverse lenses (invocation seam, interface depth/deletion-test, scenario coverage, error/ambiguity model, return-shape/context-budget, naming/selection, docs-drift, skill-author readiness) → each finding adversarially verified against the code → completeness critic. 48 findings survived verification (1 P0, 11 P1, 27 P2, 9 P3); 6 were refuted.
2. **Analytical-sufficiency round** — 7 real 제도-analysis scenarios (sanction design, delegated-criteria tracing, statute evolution, congress-bill→current-law, constitutional-risk scan, multi-law concept assembly, comparative design for new legislation) walked through the real API → every claimed capability gap adversarially verified (3 refuted) → cross-scenario synthesis. 51 verified gaps (17 P1, 28 P2, 6 P3). Per-scenario insight-readiness: **2/5, 2/5, 2/5, 2/5, 3/5, 3/5, 2/5**.

## Verdict

**As a loader of single-statute legal materials: strong, production-grade.** Law-identity normalization, article-notation handling (`제10조의2` → six-digit `JO`, [normalization.py:887](../../moleg_api/normalization.py:887)), date-basis multiplicity, delegated-rule `source_article` linking, HTML-only `lsHistory` fallback, and authority-label separation (MOLEG interpretation / ministry interpretation / case / constitutional decision) are genuinely deep. 15 of 19 methods pass the deletion test as real abstractions.

**As an analysis-ready, multi-source, institution-level context provider: not yet (2/5).** Loaded text is *not structured for analysis* — the linking that turns loaded sources into an analyzable institutional picture (which interpretation/case concerns which article; how a 제도 spans multiple statutes; how a delegation chain recurses to a 고시 별표) is left entirely to Claude as manual orchestration. **This weak axis is exactly where the project's stated purpose — 제도 분석 and 법안 설계 — lives.**

The single most consequential finding recurred in **all 7** analytical scenarios: interpretation/case/constitutional results used to carry statute references only as free-text strings, forcing Claude to read 15–20 full texts to find the 3–4 that bear on the article in question. Resolved by #59: detail models now preserve those free-text fields and add structured `referenced_articles` / `reviewed_articles` when article references are unambiguous.

## Strategic decision — hybrid analysis-readiness placement

Cheap, high-leverage **structuring and normalization** (article references, the 법령 체계도 structural view, administrative-rule→statute back-references, an honest bundle, a multi-statute *loading* helper) belongs **in MOLEG-API** — it is "load and normalize sources well," which is already MOLEG-API's job. Heavy **synthesis and insight generation** (judging which statute is primary in a 제도, designing a new sanction tier, deriving legal conclusions) stays **in the skill's reasoning**, consistent with the standing decision that bundles "load sources, not conclusions." See `DECISIONS.md` (2026-06-16).

## Findings by theme

Severities are post-verification. `file:line` is the verified evidence location.

### Tier 0 — Foundation (does the skill even have a callable seam?)

- **T0.1 Invocation & serialization seam (P1).** #50 adds package metadata, recursive `to_dict(include_raw=False)` / `to_json_string()` on public model dataclasses, and `docs/SKILL-AUTHOR-COOKBOOK.md`. The consumer can now import MOLEG-API as a package and serialize normalized results without carrying large `raw` payloads by default; PyPI publishing itself remains a human release step.

### Tier 1 — Correctness / contract (wrong answers, silent failure)

- **T1.1 `get_law(articles=[...])` silently uses only `articles[0]` (P1).** [laws.py](../../moleg_api/laws.py) sets `params["JO"]` from the first article only; the returned `LawText` then contains *all* articles. Highest cross-lens consensus (flagged 7×). Claude requesting a subset gets the whole law and wastes context.
- **T1.2 `AmbiguousLawError` flattens candidates into a message string (P1).** [laws.py](../../moleg_api/laws.py) joins names into text; no machine-readable `candidates`. The bundle, by contrast, returns structured `Ambiguity` objects — two incompatible paradigms the skill must both handle. Decision: enrich exceptions with structured `candidates`/`kind`.
- **T1.3 `identity_from_identifier(str)` aliases one string as both `law_id` and `name` (P1).** [laws.py](../../moleg_api/laws.py). An LLM naturally passes a law *name*; it becomes `law_id="개인정보 보호법"` and silently misqueries.
- **T1.4 `compare_law_versions(before, after)` ignores its date arguments (P1).** [laws.py](../../moleg_api/laws.py) calls a single `oldAndNew` payload and only echoes `before`/`after` into `raw`. Arbitrary two-date diffs are impossible despite the signature implying them.

### Tier 2 — Discoverability / guardrails (LLM mis-selection)

- **T2.1 No docstrings on any of the 19 public methods (P1; implemented in #55).** A skill author previously had to read 1,692 lines to learn return shapes, params, failure modes, and when to pick which method. The implemented fix adds class-level method-selection guidance and narrative docstrings on each public `MolegApi` method, with a regression test that catches future public methods without caller guidance.
- **T2.2 Free-form string params lack `Literal` types or validation (P1).** `source`/`court`/`basis`/`mode`/`search_scope`/`annex_type` accept any string; a misspelled `basis` silently defaults to effective, a bad `source` raises an opaque error.
- **T2.3 Bundle `LoadedContext` had six always-empty fields vs. docs that promised conditional full-text loading (P1).** Resolved by #57/#63: `loaded` exposes only material actually retrieved by `load_legal_context_bundle()`. It always supports statute/article/delegation context and now conditionally includes interpretation/case/Constitutional Court detail only when query intent and budget warrant it; administrative-rule, history, and diff details remain candidate/deferred context.
- **T2.4 `search_interpretations(source="all")` returned only MOLEG + one specified ministry, not all ministries (P2).** Resolved by #58: `source="all"` now requires a ministry and means MOLEG plus that one ministry; `source="all_ministries"` explicitly performs the higher-cost MOLEG plus all-ministry fan-out for deep institutional analysis.

### Tier 3 — Analysis-readiness layer (the project's purpose-critical axis; hybrid placement)

- **T3.1 Sources lacked structured article-level linking (P0/P1; recurred in all 7 scenarios).** Resolved by #59: interpretation/judicial detail models now add `referenced_articles` / `reviewed_articles: list[ArticleReference{law_name, law_id, article}]` while preserving the original free-text fields for fallback.
- **T3.2 法令 체계도 (`lsStmd`) structural view + recursive hierarchy (P1).** Resolved by #60: `get_law_structure()` now loads the live `lsStmd` hierarchy as law/admin-rule nodes with explicit depth, while article-level `source_article` links remain the role of `find_delegated_rules()` / `lsDelegated`.
- **T3.3 Administrative-rule → delegating-statute back-reference (P1).** `DelegatedRule.source_article` links statute→rule, and #61 adds conservative reverse fields on administrative-rule identity/article text. These fields are populated only from explicit delegation/authorization metadata; absent fields remain unknown rather than guessed.
- **T3.4 Multi-statute 제도 *loading* helper (P1; implemented in #62 as explicit-statute composition).** `load_institutional_system()` assembles a statute set Claude already selected, loading statute text/articles, `lsStmd` structures, and delegations while preserving secondary sources as candidates/deferred lookups. It deliberately does not infer which statutes belong to a 제도 or synthesize the legal relationship.
- **T3.5 Bundle eager conditional full-text loading (P2).** #63 implements the deferred half of T2.3 for interpretation/case/Constitutional Court detail: selectively load top-N high-confidence detail when the question warrants it, while leaving unselected candidates deferred. History detail remains separate because `trace_law_history()` has different date/article semantics.
- **T3.6 Annex/form structured table parsing (P2).** #64 adds optional, confidence-flagged `StructuredTableData` for clear table-like text-export annexes while preserving plain text and avoiding direct HWP/PDF parsing.
- **T3.7 Similar-제도 / mechanism discovery for comparative design (P2; implemented as source discovery in #65).** "Find statutes with similar sanction/permit/authorization structures" directly serves 법안 설계. The implemented interface returns bounded source-labeled law/article candidates for Claude to inspect; ranked 제도 taxonomy and legal-design synthesis remain in the skill's reasoning, not MOLEG-API.
- **T3.8 Per-article text version history (P2).** #66 adds `HistoryEvent.article_text` for article-scoped `trace_law_history(article=...)` calls, populated from source text when present or by bounded post-change article snapshot lookups. Full-law history remains metadata-only.
- **T3.9 `HistoryEvent` → congress-db `bill_id` link (P2).** #67 adds `HistoryEvent` bridge keys (`promulgation_law_name`, normalized `promulgation_number`, `promulgation_date`) and optional caller-supplied `bill_id` population, without making MOLEG-API query `congress-db`.
- **T3.10 Doctrine-indexed constitutional search (P3; refuted by source discovery).** #68 found that law.go.kr `detc` exposes doctrines only in prose fields, not as structured source labels. Keep constitutional doctrine discovery as free-text search plus detail loading; do not add a fake doctrine filter.

## What was refuted (do not act on these)

- `source="all"` does **not** make registry-wide live ministry calls; use `source="all_ministries"` when the analysis really needs MOLEG plus every ministry interpretation source.
- Statistics / social context / crawled enforcement data are **by-design WebSearch boundaries**, not MOLEG-API gaps.
- `find_delegated_rules`↔`search_administrative_rules` identity mapping is present enough to refute the "no mapping" claim.
- `search_laws` returning an empty list (not raising) on no match is intended.
- Doctrine-indexed Constitutional Court search is **not source-backed** in `detc`; the catalog exposes only free-text/detail prose fields for doctrine terms.

## Issue roadmap

All themes are published as 2026-06-16 GitHub issues, tracked under umbrella **#49**.

| Theme | Issue | Type |
|---|---|---|
| T0.1 serialization + PyPI + cookbook | #50 | HITL release step after implementation |
| T1.1 `get_law(articles)` first-article bug | #51 | bug, AFK |
| T1.2 structured candidates on `AmbiguousLawError` | #52 | AFK |
| T1.3 identity string aliasing | #53 | bug, AFK |
| T1.4 `compare_law_versions` before/after | #54 | bug, AFK |
| T2.1 docstrings + selection guidance | #55 | AFK — implemented |
| T2.2 `Literal` params + validation | #56 | AFK |
| T2.3 honest bundle `LoadedContext` | #57 | AFK |
| T2.4 true all-ministries + `source='all'` semantics | #58 | AFK |
| T3.1 structured article references *(keystone)* | #59 | AFK |
| T3.2 `lsStmd` structural view + recursive delegation | #60 | HITL |
| T3.3 admin-rule → statute back-reference | #61 | AFK |
| T3.4 multi-statute 제도 loader | #62 | HITL-shaped explicit-statute composition |
| T3.5 bundle eager conditional loading | #63 | AFK (blocked by #57) |
| T3.6 annex/form structured table parsing | #64 | HITL implementation + review |
| T3.7 similar-제도 / mechanism discovery | #65 | HITL-shaped source discovery |
| T3.8 per-article text version history | #66 | AFK |
| T3.9 `HistoryEvent` → congress-db `bill_id` | #67 | AFK |
| T3.10 doctrine-indexed constitutional search | #68 | HITL discovery; not feasible unless law.go.kr adds a source field |
| Fake-skill tracer-bullet gate | #90 | consumer-readiness gate |
| Deterministic GitHub Actions CI | #91 | PR integration gate |

Near-term implementation set: Tier 0–2 (#50–#58) plus #59/#60/#61. Later Tier 3 items remain queued or in-flight; #62 is implemented as explicit-statute composition on top of #60's structure loader, and #65 is implemented as bounded source discovery rather than a ranked mechanism taxonomy. #90 and #91 are gate slices: the first proves public-interface orchestration through a fake skill, and the second makes deterministic PR verification visible in GitHub.

## Gate strategy & implementation sequence

Moving to stage 2 (the legislative-expert skill) is a costly one-way step: once the skill integrates MOLEG-API, the repo is effectively frozen/handed off, and any later API change forces a corresponding skill change (skill↔API coupling). MOLEG-API therefore clears a **full gate** before stage 2 — and because the real skill is too expensive to use as the feedback loop, consumer feedback is pulled forward with a cheap **tracer-bullet "fake skill"**.

1. **Low-regret first.** Implement Tier 0–2 (#50–#58) and the cheap structuring/normalization (#59 keystone, #60, #61). Land #50 (serialization + PyPI) early so later validation consumes the package the way the skill will.
2. **Tracer-bullet E2E.** A throwaway script that plays Claude+skill across the seven review scenario archetypes against the improved API — surfacing the exact shape the design-led interfaces need, plus any residual blocker, while fixes are still cheap. Implemented by #90 as `scripts/fake_skill_tracer_bullet.py`, with the contract recorded in `docs/design/FAKE-SKILL-TRACER-BULLET.md`.
3. **Design-led Tier 3, informed by the tracer bullet.** Build #63 (eager bundle loading), #64 (annex tables), #66, #67, and #68 in the shape the tracer bullet revealed — not blind. #62 is already narrowed to explicit-statute staged composition, and #65 is narrowed to source-labeled comparable-mechanism discovery, with relationship inference, taxonomy, and synthesis left to the skill.
4. **CI-backed final gate → stage 2.** #91 adds deterministic GitHub Actions checks for non-live tests across supported Python versions plus package installation, while live law.go.kr and congress-db checks remain credentialed local evidence. Only after the gate does skill creation begin in a fresh session.

This sequence resolves the tension between "return is expensive" (argues for full coverage now) and "building design-led interfaces blind risks rework" (argues for waiting on the consumer): the tracer bullet is the cheap consumer-proxy that lets full coverage be built right the first time.

## Out of scope (unchanged)

Generic 195-endpoint SDK; direct SQL to `congress-db`; WebSearch/news/statistics inside MOLEG-API; local ordinances / treaties / administrative-appeal modules until a scenario justifies them; a large local mirror DB. MOLEG-API stays a source loader/normalizer, never a legal-reasoning or insight-generation engine.
