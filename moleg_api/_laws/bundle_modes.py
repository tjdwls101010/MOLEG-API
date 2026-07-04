from __future__ import annotations

from .bundle_state import BundleSeed, BundleState
from .support import *


def resolve_bundle_seed(
    api: Any,
    request: BundleRequest,
    limits: dict[str, int],
    state: BundleState,
) -> BundleSeed:
    if request.mode == "question":
        return resolve_question_bundle_seed(api, request, limits, state)
    if request.mode == "promulgated_bill":
        return resolve_promulgated_bundle_seed(api, request, limits, state)
    if request.mode == "statute_review":
        if request.law_identifier is None:
            raise NoResultError("law_identifier is required for statute_review bundles")
        primary_identity = identity_from_identifier(request.law_identifier, basis="effective")
        state.law_candidates = [primary_identity]
        return BundleSeed(primary_identity, request.query or primary_identity.name)
    raise UnsupportedFormatError(f"Unsupported legal context bundle mode: {request.mode}")


def resolve_question_bundle_seed(
    api: Any,
    request: BundleRequest,
    limits: dict[str, int],
    state: BundleState,
) -> BundleSeed:
    query = require_query(request.query)
    try:
        state.query_expansion = api.expand_legal_query(query, display=limits["law_candidates"])
        state.gaps.extend(state.query_expansion.source_failures)
        if state.query_expansion.source_failures:
            state.deferred.append(
                DeferredLookup(
                    interface="expand_legal_query",
                    query=query,
                    reason="Retry query expansion after source-access recovery before treating missing planning candidates as legal absence.",
                    source_type="query_expansion",
                )
            )
        state.law_candidates = state.query_expansion.law_candidates[: limits["law_candidates"]]
        if len(state.law_candidates) == 1:
            return BundleSeed(state.law_candidates[0], query)
        if len(state.law_candidates) > 1:
            state.ambiguities.append(
                Ambiguity(
                    kind="statute_identity",
                    message=(
                        "Question query matched multiple MOLEG law identities; "
                        "select one LawIdentity or use statute_review before loading statute text."
                    ),
                    candidates=state.law_candidates,
                )
            )
            state.gaps.append(
                ContextGap(
                    kind="manual_review_required",
                    reason="The question matched multiple MOLEG law identities, so no statute text was auto-loaded.",
                    query=query,
                    recommended_interface="search_laws",
                )
            )
            state.deferred.append(
                DeferredLookup(
                    interface="search_laws",
                    query=query,
                    reason="Resolve one LawIdentity before loading current statute text.",
                    source_type="law",
                    filters={"basis": "effective"},
                )
            )
    except MolegApiError as exc:
        state.source_notes.append(f"Query expansion skipped: {exc}")
        append_query_expansion_failure_gap(exc, query, state.gaps, state.deferred)
    return BundleSeed(None, query)


def resolve_promulgated_bundle_seed(
    api: Any,
    request: BundleRequest,
    limits: dict[str, int],
    state: BundleState,
) -> BundleSeed:
    if not request.promulgation_bridge:
        raise NoResultError("promulgation_bridge is required for promulgated_bill bundles")

    prom_law_nm = string_value(request.promulgation_bridge.get("prom_law_nm"))
    prom_no = string_value(request.promulgation_bridge.get("prom_no"))
    promulgation_dt = string_value(request.promulgation_bridge.get("promulgation_dt"))
    try:
        primary_identity = api.resolve_promulgated_law(
            prom_law_nm=prom_law_nm,
            prom_no=prom_no,
            promulgation_dt=promulgation_dt,
        )
        state.law_candidates = [primary_identity]
        return BundleSeed(primary_identity, primary_identity.name)
    except AmbiguousLawError as exc:
        append_promulgated_ambiguity(exc, prom_law_nm, prom_no, promulgation_dt, state)
        return BundleSeed(None, None)
    except NoResultError as exc:
        handle_promulgated_no_result(
            api,
            exc,
            prom_law_nm,
            prom_no,
            promulgation_dt,
            limits,
            state,
        )
    except MolegApiError as exc:
        state.source_notes.append(f"Promulgation bridge resolution skipped: {exc}")
        append_promulgation_bridge_resolution_failure_gap(
            exc,
            prom_law_nm=prom_law_nm,
            prom_no=prom_no,
            promulgation_dt=promulgation_dt,
            gaps=state.gaps,
            deferred=state.deferred,
        )
    return BundleSeed(None, prom_law_nm)


def append_promulgated_ambiguity(
    exc: AmbiguousLawError,
    prom_law_nm: str,
    prom_no: str,
    promulgation_dt: str,
    state: BundleState,
) -> None:
    state.ambiguities.append(
        Ambiguity(
            kind=exc.kind or "promulgation_bridge",
            message=str(exc),
            candidates=exc.candidates,
        )
    )
    state.gaps.append(
        ContextGap(
            kind="manual_review_required",
            reason="The congress-db promulgation bridge matched multiple MOLEG law identities.",
            query=prom_law_nm,
            recommended_interface="resolve_promulgated_law",
        )
    )
    state.deferred.append(
        DeferredLookup(
            interface="resolve_promulgated_law",
            query=prom_law_nm or "",
            reason=(
                "Resolve the ambiguous congress-db promulgation bridge before "
                "loading current-law context for this bill."
            ),
            source_type="law",
            filters=promulgation_bridge_filters(
                prom_law_nm=prom_law_nm,
                prom_no=prom_no,
                promulgation_dt=promulgation_dt,
            ),
        )
    )


def handle_promulgated_no_result(
    api: Any,
    exc: NoResultError,
    prom_law_nm: str,
    prom_no: str,
    promulgation_dt: str,
    limits: dict[str, int],
    state: BundleState,
) -> None:
    candidate_hits: list[LawHit] = []
    if prom_law_nm:
        candidate_hits = safe_list(
            lambda: api.search_laws(
                prom_law_nm,
                basis="promulgated",
                display=max(2, limits["law_candidates"]),
            ),
            state.source_notes,
            "Promulgation bridge candidate search",
            gaps=state.gaps,
            deferred=state.deferred,
            query=prom_law_nm,
            recommended_interface="search_laws",
            source_type="law",
        )
    state.law_candidates = dedupe_identities([hit.identity for hit in candidate_hits])
    if state.law_candidates:
        append_promulgated_source_lag_gap(exc, prom_law_nm, prom_no, promulgation_dt, state)
    else:
        state.ambiguities.append(Ambiguity(kind="promulgation_bridge", message=str(exc)))
        state.gaps.append(
            ContextGap(
                kind="manual_review_required",
                reason="The congress-db promulgation bridge did not resolve to a MOLEG law identity.",
                query=prom_law_nm,
                recommended_interface="congress-db",
            )
        )


def append_promulgated_source_lag_gap(
    exc: NoResultError,
    prom_law_nm: str,
    prom_no: str,
    promulgation_dt: str,
    state: BundleState,
) -> None:
    state.ambiguities.append(
        Ambiguity(
            kind="promulgation_bridge_lag",
            message=(
                f"{exc}. Law-name candidates exist, but none matched "
                "`prom_no` and `promulgation_dt` exactly."
            ),
            candidates=state.law_candidates,
        )
    )
    state.gaps.append(
        ContextGap(
            kind="source_lag_or_manual_review_required",
            reason=(
                "The congress-db bridge did not exactly resolve in MOLEG. "
                "This may be source lag or a bridge-field mismatch; do not treat it as proof "
                "that the bill was not enacted."
            ),
            query=prom_law_nm,
            recommended_interface="resolve_promulgated_law",
        )
    )
    state.deferred.append(
        DeferredLookup(
            interface="resolve_promulgated_law",
            query=prom_law_nm or "",
            reason=(
                "Recheck the strict congress-db promulgation bridge after "
                "confirming source lag or bridge-field correction; do not "
                "treat this exact miss as proof the bill was not enacted."
            ),
            source_type="law",
            filters=promulgation_bridge_filters(
                prom_law_nm=prom_law_nm,
                prom_no=prom_no,
                promulgation_dt=promulgation_dt,
            ),
        )
    )


__all__ = [name for name in globals() if not name.startswith("__")]
