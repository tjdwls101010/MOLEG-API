# Decisions

Newest first. Each entry: `## YYYY-MM-DD — short title`, then 1-3 sentences with context, decision, and why.

## 2026-06-15 — Full law history uses the lsHistory list table

`lsHistory` is HTML-only, and its detail endpoint returns a large UI iframe rather than a stable machine-readable history body. MOLEG-API parses the law-history list table into normalized `LawHistory` events and raises parse failure on unexpected table shape, preserving a deep `trace_law_history()` interface without making Claude handle raw HTML.

## 2026-06-15 — Endpoint availability is not feature justification

The MOLEG catalog is an input to design, not a backlog that must be exhausted. A source becomes part of MOLEG-API only when a recurring legislative-expert workflow, authority distinction, or demonstrated reasoning failure justifies it; unused optional/rejected endpoints are acceptable.

## 2026-06-15 — Progressive loading over maximal bundles

Claude needs broad legal-source reach, but not every source detail in the first response. MOLEG-API therefore favors cheap candidate/search interfaces, explicit detail loaders, deferred follow-ups, and budgeted context bundles, balancing a small public surface against context waste from oversized all-in-one calls.

## 2026-06-15 — Annex/forms are candidate context, not loaded text

Annexes and forms often contain operative tables, thresholds, amounts, and required formats that statute text alone can hide. MOLEG-API exposes law and administrative-rule annex/form search as bounded candidates with file/detail links, but does not download or parse HWP/PDF bodies until a separate parser interface is designed and live-verified.

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
