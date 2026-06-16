# MOLEG-API

MOLEG-API is a local Python facade over MOLEG OpenAPI surfaces for a future legislative-expert Claude skill.

The intended caller is not an end-user application. It is Claude, with the legislative-expert skill loaded, using MOLEG-API together with `congress-db` and WebSearch to load Korean legal context reliably.

Start with `AGENTS.md` for project rules and `docs/SKILL-INTEGRATION.md` for the skill-facing interface plan.

After package publication, skill runtimes can install `moleg-api` and import `MolegApi` directly. Public model dataclasses serialize with `to_dict(include_raw=False)` and `to_json_string(include_raw=False)` so Claude can receive normalized legal context without raw law.go.kr payloads by default. See `docs/SKILL-AUTHOR-COOKBOOK.md` for call sequences, serialization guidance, and vendored fallback instructions.

Current readiness evidence is tracked in `docs/design/GOAL-COMPLETION-AUDIT.md`; the live legislative scenario gate is documented in `docs/design/LIVE-E2E-SCENARIOS.md`; residual risks are tracked in `docs/design/COMPLETION-RISK-AUDIT.md`. The 2026-06-16 review of fitness as a tool for the consuming skill is in `docs/design/CONSUMER-READINESS-REVIEW.md`; its roadmap is implemented on integration PR #89 with deterministic GitHub Actions CI, pending review/merge.
