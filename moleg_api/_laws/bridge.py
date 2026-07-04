from __future__ import annotations

from .foundation import *
from .config import *

def normalize_history_bill_id_map(
    promulgation_bridge: dict[tuple[Any, Any, Any], Any] | None,
) -> dict[tuple[str, str, str], str] | None:
    if not promulgation_bridge:
        return None
    bill_id_map: dict[tuple[str, str, str], str] = {}
    for key, bill_id in promulgation_bridge.items():
        if not isinstance(key, tuple) or len(key) != 3:
            raise UnsupportedFormatError(
                "promulgation_bridge keys must be (prom_law_nm, prom_no, promulgation_dt)"
            )
        law_name, prom_no, promulgation_dt = key
        normalized_law_name = string_value(law_name)
        normalized_prom_no = compact_promulgation_number(prom_no)
        normalized_dt = compact_date(promulgation_dt)
        normalized_bill_id = string_value(bill_id)
        if (
            not normalized_law_name
            or not normalized_prom_no
            or not normalized_dt
            or not normalized_bill_id
        ):
            continue
        bill_id_map[(normalized_law_name, normalized_prom_no, normalized_dt)] = normalized_bill_id
    return bill_id_map or None


def safe_list(
    fn: Any,
    source_notes: list[str],
    label: str,
    *,
    gaps: list[ContextGap] | None = None,
    deferred: list[DeferredLookup] | None = None,
    query: str | None = None,
    recommended_interface: str | None = None,
    source_type: str | None = None,
    filters: dict[str, Any] | None = None,
    reason: str | None = None,
) -> list[Any]:
    try:
        return fn()
    except MolegApiError as exc:
        source_notes.append(f"{label} skipped: {exc}")
        if gaps is not None and recommended_interface is not None:
            append_source_failure_gap(
                exc,
                gaps,
                query=query,
                recommended_interface=recommended_interface,
                source_label=label,
            )
        if deferred is not None and recommended_interface is not None:
            deferred.append(
                DeferredLookup(
                    interface=recommended_interface,
                    query=str(query or ""),
                    reason=reason
                    or f"Retry {label} after source-access recovery before treating missing candidates as absence.",
                    source_type=source_type,
                    filters=dict(filters or {}),
                )
            )
        return []


def append_source_failure_gap(
    exc: MolegApiError,
    gaps: list[ContextGap],
    *,
    query: str | None,
    recommended_interface: str,
    source_label: str,
) -> None:
    gap_kind = "source_access_failure" if isinstance(exc, SourceApiError) else "source_loading_failed"
    gaps.append(
        ContextGap(
            kind=gap_kind,
            reason=f"{source_label} failed with {type(exc).__name__}: {exc}",
            query=query,
            recommended_interface=recommended_interface,
        )
    )


def source_failure_payloads(source_failures: list[ContextGap]) -> list[dict[str, str | None]]:
    return [
        {
            "kind": gap.kind,
            "reason": gap.reason,
            "query": gap.query,
            "recommended_interface": gap.recommended_interface,
        }
        for gap in source_failures
    ]


def append_eager_detail_failure_gap(
    exc: MolegApiError,
    gaps: list[ContextGap],
    *,
    candidate: Any,
    recommended_interface: str,
    source_label: str,
) -> None:
    identity = getattr(candidate, "identity", None)
    query_value = (
        getattr(identity, "title", None)
        or getattr(identity, "name", None)
        or getattr(identity, "interpretation_id", None)
        or getattr(identity, "decision_id", None)
        or getattr(identity, "serial_id", None)
    )
    append_source_failure_gap(
        exc,
        gaps,
        query=str(query_value) if query_value else None,
        recommended_interface=recommended_interface,
        source_label=source_label,
    )


def append_query_expansion_failure_gap(
    exc: MolegApiError,
    query: str,
    gaps: list[ContextGap],
    deferred: list[DeferredLookup],
) -> None:
    append_source_failure_gap(
        exc,
        gaps,
        query=query,
        recommended_interface="expand_legal_query",
        source_label="Query expansion",
    )
    deferred.append(
        DeferredLookup(
            interface="expand_legal_query",
            query=query,
            reason="Retry query expansion before treating missing planning candidates as a legal absence.",
            source_type="query_expansion",
        )
    )


def append_institutional_statute_resolution_failure_gap(
    exc: MolegApiError,
    query: str,
    gaps: list[ContextGap],
    deferred: list[DeferredLookup],
) -> None:
    append_source_failure_gap(
        exc,
        gaps,
        query=query,
        recommended_interface="search_laws",
        source_label=f"Institutional statute resolution for {query}",
    )
    deferred.append(
        DeferredLookup(
            interface="search_laws",
            query=query,
            reason="Retry statute identity resolution before treating this institutional-system member as unavailable.",
            source_type="law",
            filters={"basis": "effective"},
        )
    )


def append_promulgation_bridge_resolution_failure_gap(
    exc: MolegApiError,
    *,
    prom_law_nm: str | None,
    prom_no: str | None,
    promulgation_dt: str | None,
    gaps: list[ContextGap],
    deferred: list[DeferredLookup],
) -> None:
    query = prom_law_nm or prom_no
    append_source_failure_gap(
        exc,
        gaps,
        query=query,
        recommended_interface="resolve_promulgated_law",
        source_label="Promulgation bridge resolution",
    )
    deferred.append(
        DeferredLookup(
            interface="resolve_promulgated_law",
            query=str(query or ""),
            reason="Retry the strict congress-db promulgation bridge before treating the bill as not enacted or unavailable in MOLEG.",
            source_type="law",
            filters=promulgation_bridge_filters(
                prom_law_nm=prom_law_nm,
                prom_no=prom_no,
                promulgation_dt=promulgation_dt,
            ),
        )
    )


def promulgation_bridge_filters(
    *,
    prom_law_nm: str | None,
    prom_no: str | None,
    promulgation_dt: str | None,
) -> dict[str, str]:
    return {
        key: value
        for key, value in {
            "prom_law_nm": prom_law_nm,
            "prom_no": prom_no,
            "promulgation_dt": promulgation_dt,
        }.items()
        if value
    }

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
from .requested_load_gaps import *
from .context_load_gaps import *
from .ranking import *

__all__ = [name for name in globals() if not name.startswith("__")]
