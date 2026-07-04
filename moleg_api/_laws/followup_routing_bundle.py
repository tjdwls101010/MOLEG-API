from __future__ import annotations

from .followup_routing import NO_FOLLOWUP_RESULT
from .support import *


def route_bundle_followup(
    api: Any,
    lookup: DeferredLookup | FollowUpSearch,
    interface: str,
    filters: dict[str, Any],
    query: str,
) -> Any:
    if interface == "load_authority_context":
        return api.load_authority_context(
            followup_law_identity(lookup, filters, basis="effective"),
            articles=followup_required_articles(filters),
            query=followup_str(filters, "authority_query") or query or None,
            budget=followup_budget(filters),
            as_of=followup_str(filters, "as_of"),
        )
    if interface == "load_legal_context_bundle":
        return api.load_legal_context_bundle(
            query or None,
            promulgation_bridge=followup_promulgation_bridge(filters),
            law_identifier=followup_optional_law_identity(lookup, filters),
            articles=followup_articles(filters),
            mode=followup_bundle_mode(filters),
            budget=followup_budget(filters),
            as_of=followup_str(filters, "as_of"),
        )
    if interface == "load_institutional_system":
        return api.load_institutional_system(
            followup_statute_identifiers(lookup, filters),
            articles=followup_articles(filters),
            budget=followup_budget(filters),
            as_of=followup_str(filters, "as_of"),
        )
    if interface == "load_delegated_criteria":
        return api.load_delegated_criteria(
            followup_law_identity(lookup, filters, basis="effective"),
            articles=followup_articles(filters),
            query=followup_str(filters, "criteria_query") or query or None,
            budget=followup_budget(filters),
            as_of=followup_str(filters, "as_of"),
        )
    return NO_FOLLOWUP_RESULT


__all__ = [name for name in globals() if not name.startswith("__")]
