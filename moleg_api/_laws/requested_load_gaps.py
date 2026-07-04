from __future__ import annotations

from .foundation import *
from .config import *

def append_requested_article_load_gap(
    exc: MolegApiError,
    identity: LawIdentity,
    article: str | int,
    gaps: list[ContextGap],
    deferred: list[DeferredLookup],
    *,
    as_of: str | None,
) -> None:
    article_label = article_label_for_filter(article)
    query = f"{identity.name} {article_label}"
    gap_kind = "source_access_failure" if isinstance(exc, SourceApiError) else "requested_article_not_loaded"
    if not law_identity_has_source_identifier(identity):
        gaps.append(
            ContextGap(
                kind=gap_kind,
                reason=(
                    f"Requested article load failed with {type(exc).__name__}: {exc}. "
                    "Resolve one MOLEG law identity before retrying article-detail loading."
                ),
                query=query,
                recommended_interface="search_laws",
            )
        )
        append_law_identity_resolution_deferred(
            identity,
            deferred,
            reason="Resolve one LawIdentity before retrying requested-article text loading.",
        )
        return
    gaps.append(
        ContextGap(
            kind=gap_kind,
            reason=f"Requested article load failed with {type(exc).__name__}: {exc}",
            query=query,
            recommended_interface="get_article",
        )
    )
    filters = {"article": article_label}
    if identity.law_id:
        filters["law_id"] = identity.law_id
    elif identity.mst:
        filters["mst"] = identity.mst
    else:
        filters["law_name"] = identity.name
    if as_of:
        filters["as_of"] = as_of
    deferred.append(
        DeferredLookup(
            interface="get_article",
            query=query,
            reason="Load the requested article before relying on current target-article text.",
            source_type="law_article",
            filters=filters,
        )
    )


def append_requested_law_load_gap(
    exc: MolegApiError,
    identity: LawIdentity,
    gaps: list[ContextGap],
    deferred: list[DeferredLookup],
    *,
    as_of: str | None,
) -> None:
    gap_kind = "source_access_failure" if isinstance(exc, SourceApiError) else "requested_law_not_loaded"
    if not law_identity_has_source_identifier(identity):
        gaps.append(
            ContextGap(
                kind=gap_kind,
                reason=(
                    f"Requested law load failed with {type(exc).__name__}: {exc}. "
                    "Resolve one MOLEG law identity before retrying law-detail loading."
                ),
                query=identity.name,
                recommended_interface="search_laws",
            )
        )
        append_law_identity_resolution_deferred(
            identity,
            deferred,
            reason="Resolve one LawIdentity before retrying whole-statute text loading.",
        )
        return
    gaps.append(
        ContextGap(
            kind=gap_kind,
            reason=f"Requested law load failed with {type(exc).__name__}: {exc}",
            query=identity.name,
            recommended_interface="get_law",
        )
    )
    filters: dict[str, Any] = {"basis": identity.basis}
    if identity.law_id:
        filters["law_id"] = identity.law_id
    elif identity.mst:
        filters["mst"] = identity.mst
    else:
        filters["law_name"] = identity.name
    if as_of:
        filters["as_of"] = as_of
    deferred.append(
        DeferredLookup(
            interface="get_law",
            query=identity.name,
            reason="Load the law text before relying on whole-statute current-law context.",
            source_type="law",
            filters=filters,
        )
    )


def append_delegation_lookup_failure_gap(
    exc: MolegApiError,
    identity: LawIdentity,
    gaps: list[ContextGap],
    deferred: list[DeferredLookup],
) -> None:
    if not law_identity_has_source_identifier(identity):
        append_source_failure_gap(
            exc,
            gaps,
            query=identity.name,
            recommended_interface="search_laws",
            source_label=f"Delegation lookup for {identity.name}",
        )
        append_law_identity_resolution_deferred(
            identity,
            deferred,
            reason="Resolve one LawIdentity before retrying delegation lookup.",
        )
        return
    append_source_failure_gap(
        exc,
        gaps,
        query=identity.name,
        recommended_interface="find_delegated_rules",
        source_label=f"Delegation lookup for {identity.name}",
    )
    filters: dict[str, Any] = {}
    if identity.law_id:
        filters["law_id"] = identity.law_id
    elif identity.mst:
        filters["mst"] = identity.mst
    else:
        filters["law_name"] = identity.name
    deferred.append(
        DeferredLookup(
            interface="find_delegated_rules",
            query=identity.name,
            reason="Retry delegation lookup before assuming lower-rule context is unavailable.",
            source_type="delegation",
            filters=filters,
        )
    )

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
from .context_load_gaps import *
from .ranking import *

__all__ = [name for name in globals() if not name.startswith("__")]
