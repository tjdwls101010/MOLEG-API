# MOLEG-API

MOLEG-API is a local Python facade over MOLEG OpenAPI surfaces for a future legislative-expert Claude skill.

The intended caller is not an end-user application. It is Claude, with the legislative-expert skill loaded, using MOLEG-API together with `congress-db` and WebSearch to load Korean legal context reliably.

Start with `AGENTS.md` for project rules and `docs/SKILL-INTEGRATION.md` for the skill-facing interface plan.

Current readiness evidence is tracked in `docs/design/GOAL-COMPLETION-AUDIT.md`; the live legislative scenario gate is documented in `docs/design/LIVE-E2E-SCENARIOS.md`.
