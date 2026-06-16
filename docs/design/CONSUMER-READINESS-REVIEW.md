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

The single most consequential finding recurred in **all 7** analytical scenarios: interpretation/case/constitutional results carry their statute references only as free-text strings (`InterpretationText.related_laws` [models.py:258](../../moleg_api/models.py:258); `JudicialDecisionText.referenced_statutes`/`reviewed_statutes` [models.py:297](../../moleg_api/models.py:297)), with no structured `article` field — so Claude must read 15–20 full texts to find the 3–4 that bear on the article in question.

## Strategic decision — hybrid analysis-readiness placement

Cheap, high-leverage **structuring and normalization** (article references, the 법령 체계도 structural view, administrative-rule→statute back-references, an honest bundle, a multi-statute *loading* helper) belongs **in MOLEG-API** — it is "load and normalize sources well," which is already MOLEG-API's job. Heavy **synthesis and insight generation** (judging which statute is primary in a 제도, designing a new sanction tier, deriving legal conclusions) stays **in the skill's reasoning**, consistent with the standing decision that bundles "load sources, not conclusions." See `DECISIONS.md` (2026-06-16).

## Findings by theme

Severities are post-verification. `file:line` is the verified evidence location.

### Tier 0 — Foundation (does the skill even have a callable seam?)

- **T0.1 Invocation & serialization seam is undefined (P1).** No MCP server, no CLI, no package metadata ([pyproject.toml](../../pyproject.toml) holds only pytest config), and no serialization (`to_dict`/`__str__`/JSON) on the ~40 frozen dataclasses ([models.py](../../moleg_api/models.py)). The consumer is an LLM, but the return type is a Python object graph with embedded `raw` dicts. Decision: distribute as a **PyPI package** the skill imports, add a **serialization layer** (the real seam), and ship a **skill-author cookbook**; document a vendored fallback for sandboxes without network `pip`.

### Tier 1 — Correctness / contract (wrong answers, silent failure)

- **T1.1 `get_law(articles=[...])` silently uses only `articles[0]` (P1).** [laws.py:280](../../moleg_api/laws.py:280) sets `params["JO"]` from the first article only; the returned `LawText` then contains *all* articles. Highest cross-lens consensus (flagged 7×). Claude requesting a subset gets the whole law and wastes context.
- **T1.2 `AmbiguousLawError` flattens candidates into a message string (P1).** [laws.py:262](../../moleg_api/laws.py:262) joins names into text; no machine-readable `candidates`. The bundle, by contrast, returns structured `Ambiguity` objects — two incompatible paradigms the skill must both handle. Decision: enrich exceptions with structured `candidates`/`kind`.
- **T1.3 `identity_from_identifier(str)` aliases one string as both `law_id` and `name` (P1).** [laws.py:1222](../../moleg_api/laws.py:1222). An LLM naturally passes a law *name*; it becomes `law_id="개인정보 보호법"` and silently misqueries.
- **T1.4 `compare_law_versions(before, after)` ignores its date arguments (P1).** [laws.py:385](../../moleg_api/laws.py:385) calls a single `oldAndNew` payload and only echoes `before`/`after` into `raw`. Arbitrary two-date diffs are impossible despite the signature implying them.

### Tier 2 — Discoverability / guardrails (LLM mis-selection)

- **T2.1 No docstrings on any of the 19 public methods (P1).** A skill author must read 1,692 lines to learn return shapes, params, failure modes, and when to pick which method.
- **T2.2 Free-form string params lack `Literal` types or validation (P1).** `source`/`court`/`basis`/`mode`/`search_scope`/`annex_type` accept any string; a misspelled `basis` silently defaults to effective, a bad `source` raises an opaque error.
- **T2.3 Bundle `LoadedContext` had six always-empty fields vs. docs that promised conditional full-text loading (P1).** Resolved by #57: `loaded` now exposes only statute/article/delegation material actually retrieved by `load_legal_context_bundle()`, while administrative-rule, interpretation, case, Constitutional Court, history, and diff details remain candidate/deferred context. Eager conditional full-text loading remains a deferred enhancement (T3.5).
- **T2.4 `search_interpretations(source="all")` returns only MOLEG + one specified ministry, not all ministries (P2).** [laws.py:568](../../moleg_api/laws.py:568) + the ministry registry ([laws.py:169](../../moleg_api/laws.py:169)). "all" is misleading; a 제도 enforced by several ministries is under-covered. (Note: the "≈38 live calls fan-out" hazard was *refuted* — `source="all"` does not loop all ministries.)

### Tier 3 — Analysis-readiness layer (the project's purpose-critical axis; hybrid placement)

- **T3.1 Sources lack structured article-level linking (P0/P1; recurs in all 7 scenarios).** Add `referenced_articles` / `reviewed_articles: list[ArticleReference{law_id, article}]` parsed onto interpretation/judicial models. Eliminates the largest source of manual text-parsing across every scenario.
- **T3.2 法令 체계도 (`lsStmd`) structural view + recursive delegation (P1).** `lsStmd` is classified **core** in [MOLEG-API-AUDIT.md:87](MOLEG-API-AUDIT.md) but **unimplemented** — only `lsDelegated` (1-level) exists. The 체계도 gives the 법→시행령→시행규칙→고시 tree, the backbone for assembling a 제도 and tracing multi-level delegation.
- **T3.3 Administrative-rule → delegating-statute back-reference (P1).** `DelegatedRule.source_article` links statute→rule, but the reverse (rule→authorizing article) is missing, so delegation chains cannot be rebuilt from the rule side.
- **T3.4 Multi-statute 제도 *loading* helper (P1; design-led/HITL).** All methods are single-law- or query-rooted; nothing assembles a concept spanning multiple statutes. A loading helper (not a reasoning engine) that gathers the laws/delegations/structured-links for a named 제도.
- **T3.5 Bundle eager conditional full-text loading (P2).** Implement the deferred half of T2.3: selectively load top-N high-confidence interpretation/case/constitutional/history detail when the question warrants it.
- **T3.6 Annex/form structured table parsing (P2; HITL — tension with the no-HWP/PDF-parsing decision).** Penalty/criteria tables (별표) lose row/column structure as plain text-export. Optional structured extraction for table-type annexes.
- **T3.7 Similar-제도 / mechanism catalog for comparative design (P2; HITL).** "Find statutes with similar sanction/permit/authorization structures" — directly serves 법안 설계.
- **T3.8 Per-article text version history (P2).** `trace_law_history` returns events, not the article *text* at each point; reconstructing textual evolution is manual.
- **T3.9 `HistoryEvent` → congress-db `bill_id` link (P2).** `HistoryEvent.reason` is free text; link each amendment to the enacting bill for legislative-intent analysis.
- **T3.10 Doctrine-indexed constitutional search (P3; conditional on source fields).** No filter for 과잉금지원칙/평등원칙; free-text keyword only.

## What was refuted (do not act on these)

- `source="all"` does **not** make ≈38 live ministry calls (3 ergonomics + 1 analytical finding refuted) — it queries MOLEG + one ministry.
- Statistics / social context / crawled enforcement data are **by-design WebSearch boundaries**, not MOLEG-API gaps.
- `find_delegated_rules`↔`search_administrative_rules` identity mapping is present enough to refute the "no mapping" claim.
- `search_laws` returning an empty list (not raising) on no match is intended.

## Issue roadmap

All themes are published as 2026-06-16 GitHub issues, tracked under umbrella **#49**.

| Theme | Issue | Type |
|---|---|---|
| T0.1 serialization + PyPI + cookbook | #50 | HITL |
| T1.1 `get_law(articles)` first-article bug | #51 | bug, AFK |
| T1.2 structured candidates on `AmbiguousLawError` | #52 | AFK |
| T1.3 identity string aliasing | #53 | bug, AFK |
| T1.4 `compare_law_versions` before/after | #54 | bug, AFK |
| T2.1 docstrings + selection guidance | #55 | AFK |
| T2.2 `Literal` params + validation | #56 | AFK |
| T2.3 honest bundle `LoadedContext` | #57 | AFK |
| T2.4 true all-ministries + `source='all'` semantics | #58 | AFK |
| T3.1 structured article references *(keystone)* | #59 | AFK |
| T3.2 `lsStmd` structural view + recursive delegation | #60 | HITL |
| T3.3 admin-rule → statute back-reference | #61 | AFK |
| T3.4 multi-statute 제도 loader | #62 | HITL (blocked by #59, #60) |
| T3.5 bundle eager conditional loading | #63 | AFK (blocked by #57) |
| T3.6 annex/form structured table parsing | #64 | HITL |
| T3.7 similar-제도 / mechanism discovery | #65 | HITL |
| T3.8 per-article text version history | #66 | AFK |
| T3.9 `HistoryEvent` → congress-db `bill_id` | #67 | AFK |
| T3.10 doctrine-indexed constitutional search | #68 | HITL |

Near-term implementation set: Tier 0–2 (#50–#58) plus #59/#60/#61. The rest (#62–#68) are queued.

## Gate strategy & implementation sequence

Moving to stage 2 (the legislative-expert skill) is a costly one-way step: once the skill integrates MOLEG-API, the repo is effectively frozen/handed off, and any later API change forces a corresponding skill change (skill↔API coupling). MOLEG-API therefore clears a **full gate** before stage 2 — and because the real skill is too expensive to use as the feedback loop, consumer feedback is pulled forward with a cheap **tracer-bullet "fake skill"**.

1. **Low-regret first.** Implement Tier 0–2 (#50–#58) and the cheap structuring/normalization (#59 keystone, #60, #61). Land #50 (serialization + PyPI) early so later validation consumes the package the way the skill will.
2. **Tracer-bullet E2E.** A throwaway script that plays Claude+skill across the seven review scenario archetypes against the improved API — surfacing the exact shape the design-led interfaces need, plus any residual blocker, while fixes are still cheap.
3. **Design-led Tier 3, informed by the tracer bullet.** Build #62 (multi-statute loader), #63 (eager bundle loading), #64 (annex tables), #65 (similar-제도), #66, #67, #68 in the shape the tracer bullet revealed — not blind.
4. **Final gate → stage 2.** Only after the gate does skill creation begin in a fresh session.

This sequence resolves the tension between "return is expensive" (argues for full coverage now) and "building design-led interfaces blind risks rework" (argues for waiting on the consumer): the tracer bullet is the cheap consumer-proxy that lets full coverage be built right the first time.

## Out of scope (unchanged)

Generic 195-endpoint SDK; direct SQL to `congress-db`; WebSearch/news/statistics inside MOLEG-API; local ordinances / treaties / administrative-appeal modules until a scenario justifies them; a large local mirror DB. MOLEG-API stays a source loader/normalizer, never a legal-reasoning or insight-generation engine.
