# MOLEG-API Documentation

Use these documents first when integrating MOLEG-API as a general-purpose Python
package:

- [Quickstart](quickstart.md) - install, configure `MOLEG_OC`, and make the first calls.
- [API guide](api-guide.md) - when to use each public `MolegApi` interface.
- [Follow-up lookups](followups.md) - how candidate results point to the next executable call.
- [Source coverage and limits](source-coverage.md) - what law.go.kr source families are supported and what remains out of scope.
- [Release checklist](release-checklist.md) - local checks before TestPyPI or PyPI publication.

Consumer-specific integration documents:

- [Skill integration](SKILL-INTEGRATION.md) - guidance for a legislative-expert skill that combines MOLEG-API with `congress-db` and WebSearch.
- [Skill author cookbook](SKILL-AUTHOR-COOKBOOK.md) - call sequences and serialization guidance for that skill runtime.

Maintainer and design documents:

- [Design docs](design/README.md) - audits, decisions, source investigations, and completion evidence.

The general-purpose docs above are the public user entry point. The design docs
explain why the interface has its current shape; they are not required reading
for normal package use.
