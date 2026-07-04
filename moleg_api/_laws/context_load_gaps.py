from __future__ import annotations

from .foundation import *
from .config import *

def append_empty_delegation_lookup_gap(
    identity: LawIdentity,
    gaps: list[ContextGap],
    deferred: list[DeferredLookup],
    *,
    recommended_interface: str = "get_law_structure",
    deferred_interface: str | None = "get_law_structure",
    deferred_source_type: str | None = "law_structure",
    deferred_reason: str | None = None,
) -> None:
    gaps.append(
        ContextGap(
            kind="empty_delegation_graph",
            reason=(
                "find_delegated_rules returned no delegated rows for this scoped lookup. "
                "Do not treat one empty delegation graph as proof that no lower-rule, "
                "subordinate source, notice, annex, or delegated criteria exists."
            ),
            query=identity.name,
            recommended_interface=recommended_interface,
        )
    )
    if deferred_interface is None:
        return
    filters: dict[str, Any] = {}
    if identity.law_id:
        filters["law_id"] = identity.law_id
    elif identity.mst:
        filters["mst"] = identity.mst
    else:
        filters["law_name"] = identity.name
    deferred.append(
        DeferredLookup(
            interface=deferred_interface,
            query=identity.name,
            reason=deferred_reason or (
                "Load law hierarchy or alternate lower-rule paths before making "
                "any no-delegated-rule or no-delegated-criteria claim."
            ),
            source_type=deferred_source_type,
            filters=filters,
        )
    )


def append_law_structure_load_gap(
    exc: MolegApiError,
    identity: LawIdentity,
    gaps: list[ContextGap],
    deferred: list[DeferredLookup],
) -> None:
    gap_kind = "source_access_failure" if isinstance(exc, SourceApiError) else "law_structure_not_loaded"
    if not law_identity_has_source_identifier(identity):
        gaps.append(
            ContextGap(
                kind=gap_kind,
                reason=(
                    f"Law-structure lookup failed with {type(exc).__name__}: {exc}. "
                    "Resolve one MOLEG law identity before retrying hierarchy loading."
                ),
                query=identity.name,
                recommended_interface="search_laws",
            )
        )
        append_law_identity_resolution_deferred(
            identity,
            deferred,
            reason="Resolve one LawIdentity before retrying hierarchy loading.",
        )
        return
    gaps.append(
        ContextGap(
            kind=gap_kind,
            reason=f"Law-structure lookup failed with {type(exc).__name__}: {exc}",
            query=identity.name,
            recommended_interface="get_law_structure",
        )
    )
    filters: dict[str, Any] = {"depth": 1}
    if identity.law_id:
        filters["law_id"] = identity.law_id
    elif identity.mst:
        filters["mst"] = identity.mst
    else:
        filters["law_name"] = identity.name
    deferred.append(
        DeferredLookup(
            interface="get_law_structure",
            query=identity.name,
            reason="Load hierarchy context before claiming lower instruments are unavailable.",
            source_type="law_structure",
            filters=filters,
        )
    )


def law_identity_has_source_identifier(identity: LawIdentity) -> bool:
    return bool(identity.law_id or identity.mst)


def append_law_identity_resolution_deferred(
    identity: LawIdentity,
    deferred: list[DeferredLookup],
    *,
    reason: str,
) -> None:
    if any(
        item.interface == "search_laws"
        and item.source_type == "law"
        and item.query == identity.name
        and item.filters == {"basis": identity.basis}
        for item in deferred
    ):
        return
    deferred.append(
        DeferredLookup(
            interface="search_laws",
            query=identity.name,
            reason=reason,
            source_type="law",
            filters={"basis": identity.basis},
        )
    )


def limit_delegation_graph(graph: DelegationGraph, limit: int) -> DelegationGraph:
    return DelegationGraph(identity=graph.identity, rules=graph.rules[:limit], raw=graph.raw)

from .validation import *
from .annex_tables import *
from .identity_params import *
from .admin_scope import *
from .temporal_gaps import *
from .delegated_scope import *
from .source_matching import *
from .article_gaps import *
from .history_identity import *
from .authority_sources import *
from .candidates import *
from .followup_searches import *
from .followup_hits import *
from .limits_intents import *
from .authority_article_gaps import *
from .authority_temporal_gaps import *
from .authority_temporal_filters import *
from .followup_basic import *
from .followup_identities import *
from .bridge import *
from .requested_load_gaps import *
from .ranking import *

__all__ = [name for name in globals() if not name.startswith("__")]
