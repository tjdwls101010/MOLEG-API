# Fake Skill Tracer Bullet Gate

This is the deterministic pre-skill consumer gate for MOLEG-API. It plays the future legislative-expert skill just far enough to prove that the public `MolegApi` interface can be orchestrated across institutional-analysis workflows without raw law.go.kr target knowledge.

The executable harness is `scripts/fake_skill_tracer_bullet.py`.
The regression gate is `tests/test_fake_skill_tracer_bullet.py`.
The next-layer answer-readiness audit is `scripts/legislative_expert_e2e_audit.py`, documented in `docs/design/LEGISLATIVE-EXPERT-E2E-AUDIT.md`.

## Purpose

Live e2e tests prove that representative law.go.kr source families are reachable. This fake-skill tracer bullet proves a different property: a Claude-like consumer can move from a legislative task to loaded context, candidates, deferred lookups, authority labels, bridge keys, and WebSearch gaps through public MOLEG-API methods only.

The harness is not a legal reasoning engine. It does not decide which rule controls, whether a sanction design is valid, or whether a constitutional doctrine applies. It loads and records source context so the real skill can reason later.

## Covered Archetypes

| Archetype | Public interfaces exercised | Gate evidence |
|---|---|---|
| Sanction design | `load_legal_context_bundle()`, `get_annex_form_body()` | statute/delegation loaded, interpretation/case/Constitutional Court detail eagerly loaded only as bounded first-pass context, annex table structured, WebSearch gap preserved |
| Delegated-criteria tracing | `load_institutional_system()` | law text, `lsStmd` structure, delegation graph, administrative-rule and annex candidates |
| Statute evolution | `trace_law_history()` | article-scoped history has post-change `article_text`, normalized promulgation number, and caller-supplied `bill_id` |
| congress-bill to current law | `load_legal_context_bundle(mode="promulgated_bill")` | promulgation bridge resolves to effective current law, history/diff follow-ups remain deferred |
| Constitutional-risk scan | `load_legal_context_bundle()` | top Constitutional Court details eagerly load by query intent, remaining decisions stay deferred |
| Multi-law concept assembly | `load_institutional_system()` | explicit statute set loads as one staged bundle with law structures and delegations |
| Comparative design | `find_comparable_mechanisms()`, `get_article()` | comparable law candidates preserve discovery endpoint and article anchors, selected article loads before use |

## Contract

- The harness calls public `MolegApi` methods only.
- It uses deterministic source-shaped fake payloads; no live MOLEG or congress-db calls run here.
- It records loaded context separately from candidates and deferred lookups.
- It treats WebSearch as an explicit gap for non-MOLEG context.
- It verifies consumer-critical shape, not source reachability or final legal conclusions.

## Current Evidence

Last run on 2026-06-17:

```bash
python3 scripts/fake_skill_tracer_bullet.py
python3 scripts/legislative_expert_e2e_audit.py
python3 scripts/legislative_expert_prompt_dry_run.py
python3 scripts/legislative_expert_answer_discipline.py
python3 -m pytest tests/test_fake_skill_tracer_bullet.py -q
python3 -m pytest tests/test_legislative_expert_e2e_audit.py -q
python3 -m pytest tests/test_legislative_expert_prompt_dry_run.py -q
python3 -m pytest tests/test_legislative_expert_gate_crosswalk.py -q
python3 -m pytest tests/test_legislative_expert_artifact_safety.py -q
python3 -m pytest tests/test_legislative_expert_answer_discipline.py -q
python3 -m pytest -q -m 'not live'
```

Results:

```text
scripts/fake_skill_tracer_bullet.py -> emitted JSON summaries for 7 archetypes
scripts/legislative_expert_e2e_audit.py -> emitted JSON summaries for 59 scenarios
scripts/legislative_expert_prompt_dry_run.py -> emitted JSON summaries for 42 prompt plans
scripts/legislative_expert_answer_discipline.py -> emitted JSON summaries for 46 answer-discipline reports
tests/test_fake_skill_tracer_bullet.py -q -> 2 passed
tests/test_legislative_expert_e2e_audit.py -q -> 53 passed
tests/test_legislative_expert_prompt_dry_run.py -q -> 42 passed
tests/test_legislative_expert_gate_crosswalk.py -q -> 2 passed
tests/test_legislative_expert_artifact_safety.py -q -> 54 passed
tests/test_legislative_expert_answer_discipline.py -q -> 47 passed
python3 -m pytest -q -m 'not live' -> 400 passed, 54 deselected
```

## Non-Goals

- Building the actual legislative-expert skill.
- Generating legal conclusions, rankings, or policy recommendations.
- Replacing live smoke/e2e tests.
- Querying `congress-db`; bridge data is caller-supplied.
- Proving every future skill prompt is covered.
