# Decisions

Newest first. Each entry: `## YYYY-MM-DD — short title`, then 1-3 sentences with context, decision, and why.

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
