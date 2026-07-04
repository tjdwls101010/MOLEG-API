from __future__ import annotations

from .followup_routing import (
    NO_FOLLOWUP_RESULT,
    route_administrative_followup,
    route_annex_followup,
    route_law_followup,
    route_planning_followup,
)
from .followup_routing_authority import route_authority_followup
from .followup_routing_bundle import route_bundle_followup
from .support import *


class FollowupMixin:
    def __init__(self, source: MolegSource | None = None) -> None:
        self.source = source or LawGoKrClient()

    def load_followup(self, lookup: DeferredLookup | FollowUpSearch) -> Any:
        """Execute one staged follow-up lookup through the public interface.

        Use when: the skill receives a `DeferredLookup` or `FollowUpSearch`
        from query expansion or a context bundle and wants MOLEG-API to turn it
        into the right task-level loader without exposing source target names,
        `ID`/`MST` rules, or article formatting.
        Returns: the same value returned by the routed public method, such as a
        law text, article text, search-hit list, or context bundle.
        Raises: `UnsupportedFormatError` for WebSearch handoffs or unknown
        interfaces; routed method errors propagate unchanged.
        Related: `expand_legal_query`, `load_legal_context_bundle`, and
        `load_institutional_system` produce follow-up records this method can
        execute.
        """
        interface = followup_interface(lookup)
        filters = followup_filters(lookup)
        query = followup_query(lookup)

        if interface == "websearch" or interface.startswith("websearch."):
            raise UnsupportedFormatError(
                "websearch follow-up is outside MOLEG-API; use WebSearch for latest or non-MOLEG facts."
            )
        if interface == "congress-db" or interface.startswith("congress-db."):
            raise UnsupportedFormatError(
                "congress-db follow-up is outside MOLEG-API; use congress-db for National Assembly bill facts and promulgation bridge fields."
            )

        planning_result = route_planning_followup(self, interface, filters, query)
        if planning_result is not NO_FOLLOWUP_RESULT:
            return planning_result

        for route in (
            route_law_followup,
            route_administrative_followup,
            route_annex_followup,
            route_authority_followup,
            route_bundle_followup,
        ):
            result = route(self, lookup, interface, filters, query)
            if result is not NO_FOLLOWUP_RESULT:
                return result

        raise UnsupportedFormatError(f"Unsupported follow-up interface: {interface}")


__all__ = [name for name in globals() if not name.startswith("__")]
