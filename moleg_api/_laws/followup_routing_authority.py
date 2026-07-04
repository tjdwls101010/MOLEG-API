from __future__ import annotations

from .followup_routing import NO_FOLLOWUP_RESULT
from .support import *


def route_authority_followup(
    api: Any,
    lookup: DeferredLookup | FollowUpSearch,
    interface: str,
    filters: dict[str, Any],
    query: str,
) -> Any:
    if interface == "search_interpretations":
        return api.search_interpretations(
            query,
            source=followup_interpretation_source(filters),
            ministry=followup_str(filters, "ministry"),
            search_body=followup_bool(filters, "search_body", False),
            interpreted_on=followup_str(filters, "interpreted_on"),
            display=followup_int(filters, "display", 20),
        )
    if interface == "get_interpretation":
        return api.get_interpretation(
            followup_detail_id(lookup, filters, "interpretation_id", "id"),
            source=followup_str(filters, "source"),
            ministry=followup_str(filters, "ministry"),
            include_metadata=followup_bool(filters, "include_metadata", True),
        )
    if interface == "search_cases":
        return api.search_cases(
            query,
            court=followup_case_court(filters),
            court_name=followup_str(filters, "court_name"),
            search_body=followup_bool(filters, "search_body", False),
            decided_on=followup_str(filters, "decided_on"),
            case_number=followup_str(filters, "case_number"),
            display=followup_int(filters, "display", 20),
        )
    if interface == "get_case":
        return api.get_case(
            followup_detail_id(lookup, filters, "decision_id", "case_id", "id"),
            include_metadata=followup_bool(filters, "include_metadata", True),
        )
    if interface == "search_constitutional_decisions":
        return api.search_constitutional_decisions(
            query,
            search_body=followup_bool(filters, "search_body", False),
            decided_on=followup_str(filters, "decided_on"),
            case_number=followup_str(filters, "case_number"),
            display=followup_int(filters, "display", 20),
        )
    if interface == "get_constitutional_decision":
        return api.get_constitutional_decision(
            followup_detail_id(lookup, filters, "decision_id", "case_id", "id"),
            include_metadata=followup_bool(filters, "include_metadata", True),
        )
    return NO_FOLLOWUP_RESULT


__all__ = [name for name in globals() if not name.startswith("__")]
