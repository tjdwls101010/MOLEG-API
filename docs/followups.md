# Follow-Up Lookups

MOLEG-API uses follow-up records to keep the public interface small while still
letting callers continue source loading without knowing law.go.kr internals.

Two public model types can be routed through `MolegApi.load_followup()`:

- `DeferredLookup` - a selected or recommended detail/source lookup.
- `FollowUpSearch` - a planned search from query expansion.

## Basic Pattern

```python
from moleg_api import MolegApi

api = MolegApi()

hits = api.search_laws("자동차관리법", display=5)
lookup = hits[0].follow_up

if lookup is not None:
    law_text = api.load_followup(lookup)
```

The caller does not need to know whether the selected law uses `ID`, `MST`,
`LID`, `JO`, or another raw source parameter. The follow-up carries the public
interface name plus normalized filters.

## Bundle Pattern

```python
bundle = api.load_legal_context_bundle("자동차 방치 처리 기준")

for lookup in bundle.deferred:
    if lookup.interface in {"load_administrative_rule_context", "get_annex_form_body"}:
        detail = api.load_followup(lookup)
```

Common `lookup.interface` values include:

- `get_law`
- `get_article`
- `load_article_context`
- `find_delegated_rules`
- `get_law_structure`
- `load_administrative_rule_context`
- `get_annex_form_body`
- `get_interpretation`
- `get_case`
- `get_constitutional_decision`
- `load_authority_context`
- `load_legal_context_bundle`
- `load_institutional_system`
- `load_delegated_criteria`

## External Handoffs

Some follow-ups intentionally point outside MOLEG-API:

- `websearch` or `websearch.*`
- `congress-db` or `congress-db.*`

`load_followup()` rejects those with `UnsupportedFormatError`. Handle them with
the appropriate external system. This prevents MOLEG legal text from being
mistaken for latest statistics, news, bill facts, or other non-MOLEG evidence.

## Candidate Versus Loaded Source

Follow-ups make the loading path explicit, but they do not make candidate data
citable by themselves:

- A `LawHit` is not statute text.
- An `AdministrativeRuleHit` is not operational criteria.
- An `AnnexFormHit` is not the attached table or form body.
- An interpretation/case/constitutional search hit is not authority detail.
- A comparable-mechanism candidate is not legal equivalence.

Load the selected detail before citing wording, holdings, criteria, thresholds,
or legal structure.

## Serialization

Follow-up records serialize like other public dataclasses:

```python
payload = lookup.to_dict()
```

Filters are normalized into JSON-safe values. For example, sets are sorted, and
identifier filters preserve the public names needed by `load_followup()`.
