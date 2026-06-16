# Decisions

Newest first. Each entry: `## YYYY-MM-DD — short title`, then 1-3 sentences with context, decision, and why.

## 2026-06-17 — Comparable mechanisms use AI search as discovery, not synthesis

Catalog and live checks show `aiSearch` returns source law/article rows for mechanism terms such as 과징금, while `aiRltLs` and `lstrmRltJo` can supplement related-law and term-article anchors. MOLEG-API therefore exposes `find_comparable_mechanisms()` as bounded planning candidates with endpoint/article provenance in `raw_keys`, not as ranked 제도 classification or citable legal authority.

## 2026-06-17 — Administrative-rule back-references require explicit source metadata

The `admrul` catalog/live samples do not expose a stable standard back-reference field, while some administrative-rule prose can mention legal bases inside body/change-reason text. Decision: MOLEG-API exposes `source_law_id`, `source_law_name`, `source_article`, and `source_article_title` only from explicit delegation/authorization metadata fields, including explicitly named basis fields such as `위임근거`, and never by body parsing or reverse lookup; `None` means unknown in the source payload, not proof that no delegation exists.

## 2026-06-17 — Institutional-system loading composes explicit statutes, not inferred 제도 reasoning

The multi-statute 제도 helper could either infer which statutes form an institution or compose a statute set the skill already selected. MOLEG-API chooses the latter: `load_institutional_system()` loads explicit statute identities, law structures, delegations, and bounded candidates/deferred lookups, while relationship reasoning, primary-statute judgment, and full legal-authority detail loading remain in the skill or later eager-loading slices.

## 2026-06-17 — lsStmd is a hierarchy source, not article delegation

Live `lsStmd` JSON exposes a nested law hierarchy (`법률` → `시행령` / `시행규칙` / `행정규칙`) but no `조문` or article-level delegation keys. MOLEG-API therefore exposes `get_law_structure()` as a structural hierarchy loader and keeps article-level delegation on `find_delegated_rules()` / `lsDelegated`, rather than inventing `source_article` links the source does not provide.

## 2026-06-17 — Interpretation `all` fails closed without a ministry

`search_interpretations(source="all")` used to mean "MOLEG plus one specified ministry", but without `ministry` it silently returned only MOLEG results, which is dangerous under-coverage for legal analysis. Decision: keep `source="all"` as MOLEG plus exactly one ministry and require `ministry`; add `source="all_ministries"` for explicit MOLEG plus all ministry fan-out despite the higher call cost.

## 2026-06-16 — compare_law_versions rejects arbitrary date windows

The law.go.kr `oldAndNew` detail surface exposes a source-supplied before/after pair, not arbitrary caller-selected `before`/`after` dates. MOLEG-API keeps `compare_law_versions()` for that source-supplied pair and rejects date-window arguments with `UnsupportedFormatError`, rather than pretending to compare dates it cannot actually honor.

## 2026-06-16 — Detail loaders reject bare law-name strings

Detail loaders still accept numeric law ID strings for compatibility, but non-numeric bare strings are treated as unresolved law names and rejected with guidance to call `search_laws()` first. This was chosen over auto-resolving names inside detail loaders because implicit search would hide ambiguity, rate-limit, and progressive-loading behavior behind methods that are supposed to load already-resolved law identities.

## 2026-06-16 — Full pre-skill gate, de-risked by a tracer-bullet fake skill

Returning to MOLEG-API after the legislative-expert skill integrates it is expensive (repo freeze/handoff plus skill↔API coupling — an API change then forces a skill change), so the API must clear a full gate before stage 2 begins. Decision: do not start skill creation until MOLEG-API passes a full gate (Tier 0–2 plus all justified Tier 3); and because the real skill is too costly to use as the feedback loop, pull consumer feedback forward with a throwaway "fake skill" tracer-bullet E2E across the seven review scenarios to reveal the correct shape of the design-led interfaces (#62/#64/#65…) before building them. Sequence: low-regret first (Tier 0–2, #59/#60/#61) → tracer-bullet → design-led Tier 3 → final gate.

## 2026-06-16 — Analysis-readiness is hybrid: structuring in MOLEG-API, synthesis in the skill

The consumer-readiness review (`CONSUMER-READINESS-REVIEW.md`) scored institutional-analysis insight-readiness at 2/5: the API loads sources well but leaves all cross-source linking to Claude. Decision: add cheap, high-leverage *structuring/normalization* (structured article references on interpretations/cases, the `lsStmd` 체계도 view, administrative-rule→statute back-references, a multi-statute loading helper) inside MOLEG-API, but keep heavy *synthesis and insight generation* in the skill's reasoning — because normalization is MOLEG-API's job while legal conclusions are not, consistent with the bundle/query-expansion decisions.

## 2026-06-16 — Bundle LoadedContext made honest now; eager conditional loading deferred

`load_legal_context_bundle` never populates `loaded.{interpretations,cases,constitutional_decisions,administrative_rules,histories,diffs}`, yet `LEGAL-CONTEXT-BUNDLE.md` described conditional top-1 full-text loading. Decision: first make the shape and docs honest (these are candidate/deferred, not loaded), and treat eager conditional full-text loading as a separate, demand-gated enhancement rather than blocking on it now.

## 2026-06-16 — Ambiguity surfaces as enriched exceptions carrying structured candidates

Direct methods raised `AmbiguousLawError` with candidate names flattened into a message string, while the bundle returned structured `Ambiguity` objects — forcing the skill to parse text in one path and read objects in the other. Decision: keep direct methods raising (backward-compatible, low-churn) but enrich the exception with structured `candidates`/`kind` fields so callers never parse a message string; chosen over a full Result-return refactor to avoid touching 19 methods and 43 tests.

## 2026-06-16 — Skill consumes MOLEG-API as a PyPI package with a serialization layer

The intended consumer is Claude+skill, but the repo had no invocation seam: no MCP server/CLI, no package metadata, and frozen dataclasses with no serialization. Decision: distribute MOLEG-API as a **PyPI package the skill imports**, add a **serialization layer** (`to_dict(include_raw=False)`/JSON — the real seam, needed regardless of transport), and ship a **skill-author cookbook**, with a documented vendored fallback for sandboxes lacking network `pip`. PyPI is the distribution mechanism; serialization is the substantive contract. The free, leak-tolerant `MOLEG_OC` key stays a runtime env var and is never packaged.

## 2026-06-15 — Annex/form bodies use text export before file parsers

law.go.kr exposes selected law and administrative-rule annex/form bodies through text-export endpoints, while the visible detail pages often route through iframe/PDF-viewer surfaces. MOLEG-API therefore adds explicit `get_annex_form_body()` loading through `lsBylTextDownLoad.do` / `admRulBylTextDownLoad.do` and keeps direct HWP/PDF parsing out of the first body-loading interface.

## 2026-06-15 — Full law history uses the lsHistory list table

`lsHistory` is HTML-only, and its detail endpoint returns a large UI iframe rather than a stable machine-readable history body. MOLEG-API parses the law-history list table into normalized `LawHistory` events and raises parse failure on unexpected table shape, preserving a deep `trace_law_history()` interface without making Claude handle raw HTML.

## 2026-06-15 — Endpoint availability is not feature justification

The MOLEG catalog is an input to design, not a backlog that must be exhausted. A source becomes part of MOLEG-API only when a recurring legislative-expert workflow, authority distinction, or demonstrated reasoning failure justifies it; unused optional/rejected endpoints are acceptable.

## 2026-06-15 — Progressive loading over maximal bundles

Claude needs broad legal-source reach, but not every source detail in the first response. MOLEG-API therefore favors cheap candidate/search interfaces, explicit detail loaders, deferred follow-ups, and budgeted context bundles, balancing a small public surface against context waste from oversized all-in-one calls.

## 2026-06-15 — Annex/form search starts as candidate context

Annexes and forms often contain operative tables, thresholds, amounts, and required formats that statute text alone can hide. MOLEG-API exposes law and administrative-rule annex/form search as bounded candidates with file/detail links, then loads selected bodies through an explicit text-body interface instead of automatically spending context on every attachment.

## 2026-06-15 — Source adapter owns transient retry semantics

Rate limits and temporary law.go.kr failures are source-access states, not legal no-result states. `LawGoKrClient` performs bounded retries and raises `RateLimitError` or `RetryExhaustedError`, so legal-task interfaces can keep their no-result/ambiguity semantics clean.

## 2026-06-15 — Legal context bundles load sources, not conclusions

The future legislative-expert skill needs a reliable first bundle of legal context, but MOLEG-API should not become a legal-answer generator. `load_legal_context_bundle()` therefore stages statutes/articles, delegations, administrative-rule candidates, interpretation and judicial candidates, ambiguity records, deferred lookups, and WebSearch gaps while leaving legal reasoning to Claude.

## 2026-06-15 — Query expansion is planning context, not legal authority

Legal-term, everyday-term, related-article, AI search, and related-law surfaces help Claude choose better follow-up calls, but they do not prove the legal answer. MOLEG-API therefore returns `expand_legal_query()` output as candidates and recommended searches, including WebSearch handoff, rather than as citable legal authority.

## 2026-06-15 — Keep cases and Constitutional Court decisions separate

The source catalog exposes ordinary cases through `prec` and Constitutional Court decisions through `detc`, with different date fields and authority meaning. MOLEG-API exposes both as judicial context but keeps separate public methods and source labels so the legislative-expert skill does not treat constitutional review as ordinary precedent.

## 2026-06-15 — Ministry interpretations use a registry, not public functions per ministry

The `cgmExpc...` family is regular but large, and a few ministries expose list-only surfaces without a cataloged detail endpoint. MOLEG-API keeps those source targets in an internal registry with source labels and detail-support flags, so the skill calls one interpretation interface and gets an explicit refusal when a ministry lacks detail support.

## 2026-06-15 — Administrative-rule search exposes issuing-date filter honestly

The `admrul` list catalog supports `date` as 행정규칙 발령일자, while detail payloads separately expose 시행일자. MOLEG-API therefore exposes this filter as `issued_on` instead of `as_of`, so the legislative-expert skill does not mistake a promulgation/issuing-date lookup for effective-date reasoning.

## 2026-06-15 — Optimize interfaces for Claude skill context loading

The primary caller is not a human browsing law.go.kr and not a generic SDK consumer; it is Claude running a legislative-expert skill alongside `congress-db` and WebSearch. Public functions should return normalized legal context and source authority labels that the skill can reason with directly, while source endpoint trivia stays inside implementation and docs.

## 2026-06-15 — Source adapter behind first MOLEG public interface

The first vertical slice uses `MolegApi` with an injectable source adapter, so deterministic tests can exercise public behavior without live law.go.kr calls. The live `LawGoKrClient` stays behind that seam and reads `MOLEG_OC` from the environment.

## 2026-06-15 — congress-db is read-only reference input

MOLEG-API needs `congress-db` only to understand how enacted bill facts connect to law.go.kr identities. We introspect the Neon DB with the `congress_ro` role and treat `public.bill_final_outcomes(prom_law_nm, prom_no, promulgation_dt)` as the reference promulgation bridge, but this repository must not require owner/admin access or write to that DB.

## 2026-06-15 — Keep AGENTS.md as core memory only

`AGENTS.md` is loaded on every session, so it should hold only the project principles that Codex must always remember. Detailed scope, endpoint classification, and implementation plans belong in `CONTEXT.md`, `docs/design/PRD.md`, `docs/design/MOLEG-API-AUDIT.md`, and other project docs.

## 2026-06-15 — Deep interface instead of 195 endpoint SDK

The source catalog has 195 MOLEG OpenAPI guides, but most are duplicated, view-specific, demand-gated, or too narrow for direct skill use. MOLEG-API will expose task-level legal interfaces and keep raw targets, key quirks, and fallback behavior inside implementation and docs.

## 2026-06-15 — Effective-date reasoning is the current-law default

MOLEG separates promulgation-date and effective-date statute surfaces. For questions about law currently in force, MOLEG-API defaults to effective-date reasoning while keeping promulgation-date lookup available for congress-db promulgation bridge resolution.
