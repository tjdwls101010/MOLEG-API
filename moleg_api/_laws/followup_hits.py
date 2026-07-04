from __future__ import annotations

from .foundation import *
from .config import *

def law_load_followup_key(law_id: str | None, mst: str | None) -> tuple[str, str] | None:
    if law_id:
        return ("law_id", law_id)
    if mst:
        return ("mst", mst)
    return None


def law_identity_followup_filters(
    identity: LawIdentity,
    *,
    include_basis: bool = False,
) -> dict[str, str]:
    filters = {"basis": identity.basis} if include_basis else {}
    if identity.law_id:
        filters["law_id"] = identity.law_id
    if identity.mst:
        filters["mst"] = identity.mst
    if not identity.law_id and not identity.mst:
        filters["law_name"] = identity.name
    return filters


def law_hit_follow_up(identity: LawIdentity) -> DeferredLookup | None:
    if not law_identity_has_source_identifier(identity):
        return None
    return DeferredLookup(
        interface="get_law",
        query=identity.name,
        reason="Load selected law text before citing current legal substance.",
        source_type="law",
        filters=law_identity_followup_filters(identity, include_basis=True),
    )


def administrative_rule_hit_follow_up(identity: AdministrativeRuleIdentity) -> DeferredLookup | None:
    if not identity.serial_id and not identity.rule_id:
        return None
    filters: dict[str, Any] = {}
    if identity.serial_id:
        filters["id"] = identity.serial_id
    if identity.rule_id:
        filters["rule_id"] = identity.rule_id
    return DeferredLookup(
        interface="load_administrative_rule_context",
        query=identity.name,
        reason="Load selected administrative-rule text before citing operational criteria.",
        source_type="administrative_rule",
        filters=filters,
    )


def annex_form_hit_follow_up(identity: AnnexFormIdentity) -> DeferredLookup | None:
    source_id = identity.annex_id
    if not source_id:
        return None
    return DeferredLookup(
        interface="get_annex_form_body",
        query=identity.title,
        reason="Load selected annex/form body before citing attached criteria or forms.",
        source_type="annex_form",
        filters=deferred_lookup_filters(identity, source_id),
    )


def interpretation_hit_follow_up(identity: InterpretationIdentity) -> DeferredLookup | None:
    if not identity.interpretation_id or not interpretation_detail_supported(identity):
        return None
    return DeferredLookup(
        interface="get_interpretation",
        query=identity.title,
        reason="Load selected interpretation detail before citing question, answer, or reason.",
        source_type=identity.source_type,
        filters=deferred_lookup_filters(identity, identity.interpretation_id),
    )


def interpretation_detail_supported(identity: InterpretationIdentity) -> bool:
    if identity.source_target == OFFICIAL_INTERPRETATION_SOURCE.target:
        return OFFICIAL_INTERPRETATION_SOURCE.can_get
    for spec in MINISTRY_INTERPRETATION_SOURCES.values():
        if spec.target == identity.source_target:
            return spec.can_get
    return True


def judicial_decision_hit_follow_up(identity: JudicialDecisionIdentity) -> DeferredLookup | None:
    if not identity.decision_id:
        return None
    if identity.source_type == "constitutional":
        interface = "get_constitutional_decision"
        reason = (
            "Load selected Constitutional Court decision detail before citing holdings or reviewed statutes."
        )
    else:
        interface = "get_case"
        reason = "Load selected case detail before citing holdings, summary, or full text."
    return DeferredLookup(
        interface=interface,
        query=identity.title,
        reason=reason,
        source_type=identity.source_type,
        filters=deferred_lookup_filters(identity, identity.decision_id),
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
from .limits_intents import *
from .authority_article_gaps import *
from .authority_temporal_gaps import *
from .authority_temporal_filters import *
from .followup_basic import *
from .followup_identities import *
from .bridge import *
from .requested_load_gaps import *
from .context_load_gaps import *
from .ranking import *

__all__ = [name for name in globals() if not name.startswith("__")]
