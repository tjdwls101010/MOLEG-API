from __future__ import annotations

from .foundation import *
from .config import *

def interpretation_sources_for(source: str, ministry: str | None) -> list[InterpretationSourceSpec]:
    validate_choice("source", source, INTERPRETATION_SOURCE_VALUES)
    if source == "moleg":
        return [OFFICIAL_INTERPRETATION_SOURCE]
    if source == "ministry":
        return [ministry_interpretation_source(ministry)]
    if source == "all":
        if not ministry:
            raise UnsupportedFormatError(
                "source='all'에는 --ministry가 필요하다 — 법제처 해석만이면 source='moleg', "
                "부처 해석까지 한 번에 보려면 source='all_ministries'."
            )
        specs = [OFFICIAL_INTERPRETATION_SOURCE]
        specs.append(ministry_interpretation_source(ministry))
        return specs
    if source == "all_ministries":
        return [OFFICIAL_INTERPRETATION_SOURCE, *MINISTRY_INTERPRETATION_SOURCES.values()]
    raise UnsupportedFormatError(f"Unsupported interpretation source: {source}")


def ministry_interpretation_source(ministry: str | None) -> InterpretationSourceSpec:
    if not ministry:
        raise UnsupportedFormatError(
            "부처 해석 검색·로드에는 --source ministry와 함께 --ministry <기관명>이 필요하다 "
            "(부처 해석을 법제처 해석과 한 번에 보려면 --source all_ministries)."
        )
    if ministry in MINISTRY_INTERPRETATION_SOURCES:
        return MINISTRY_INTERPRETATION_SOURCES[ministry]
    for spec in MINISTRY_INTERPRETATION_SOURCES.values():
        if ministry == spec.target:
            return spec
    raise UnsupportedFormatError(f"Unsupported ministry interpretation source: {ministry}")


def attach_interpretation_source_failures(
    hits: list[InterpretationHit],
    source_failures: list[ContextGap],
) -> list[InterpretationHit]:
    failures = source_failure_payloads(source_failures)
    return [
        InterpretationHit(
            identity=replace(
                hit.identity,
                raw_keys={**hit.identity.raw_keys, "source_failures": failures},
            ),
            raw=hit.raw,
            follow_up=hit.follow_up,
        )
        for hit in hits
    ]


def interpretation_source_for_identifier(
    identifier: InterpretationIdentity | InterpretationHit | str,
    *,
    source: str | None,
    ministry: str | None,
) -> InterpretationSourceSpec:
    if isinstance(identifier, InterpretationHit):
        return interpretation_source_for_identifier(identifier.identity, source=source, ministry=ministry)
    if isinstance(identifier, InterpretationIdentity):
        if identifier.source_target == OFFICIAL_INTERPRETATION_SOURCE.target:
            return OFFICIAL_INTERPRETATION_SOURCE
        for spec in MINISTRY_INTERPRETATION_SOURCES.values():
            if spec.target == identifier.source_target:
                return spec
        return InterpretationSourceSpec(
            source_type=identifier.source_type,
            target=identifier.source_target,
            ministry=identifier.ministry,
        )
    return interpretation_sources_for(source or "moleg", ministry)[0]


def interpretation_identity_from_identifier(
    identifier: InterpretationIdentity | InterpretationHit | str,
    spec: InterpretationSourceSpec,
) -> InterpretationIdentity:
    if isinstance(identifier, InterpretationHit):
        return identifier.identity
    if isinstance(identifier, InterpretationIdentity):
        return identifier
    text = str(identifier).strip()
    if not text.isdigit():
        raise NoResultError("Interpretation detail lookup requires a source interpretation ID")
    return InterpretationIdentity(
        interpretation_id=text,
        title=text,
        source_type=spec.source_type,
        source_target=spec.target,
        ministry=spec.ministry,
    )


def interpretation_identity_params(identity: InterpretationIdentity) -> dict[str, Any]:
    if identity.interpretation_id:
        return {"ID": identity.interpretation_id}
    raise NoResultError("Interpretation identity has no source interpretation ID")


def court_filter_code(court: str) -> str | None:
    validate_choice("court", court, COURT_VALUES)
    if court == "all":
        return None
    if court == "supreme":
        return "400201"
    if court == "lower":
        return "400202"
    raise AssertionError("validated court filter should be reachable")


def judicial_decision_identity_from_identifier(
    identifier: JudicialDecisionIdentity | JudicialDecisionHit | str,
    *,
    source_type: str,
    source_target: str,
) -> JudicialDecisionIdentity:
    if isinstance(identifier, JudicialDecisionHit):
        return identifier.identity
    if isinstance(identifier, JudicialDecisionIdentity):
        if identifier.source_target != source_target:
            raise UnsupportedFormatError(
                f"{identifier.source_target} identity cannot be loaded through {source_target}"
            )
        return identifier
    text = str(identifier).strip()
    if not text.isdigit():
        raise NoResultError("Judicial decision detail lookup requires a source decision ID")
    return JudicialDecisionIdentity(
        decision_id=text,
        title=text,
        source_type=source_type,
        source_target=source_target,
    )


def judicial_decision_identity_params(identity: JudicialDecisionIdentity) -> dict[str, Any]:
    if identity.decision_id:
        return {"ID": identity.decision_id}
    raise NoResultError("Judicial decision identity has no source decision ID")

from .validation import *
from .annex_tables import *
from .identity_params import *
from .admin_scope import *
from .temporal_gaps import *
from .delegated_scope import *
from .source_matching import *
from .article_gaps import *
from .history_identity import *
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
from .context_load_gaps import *
from .ranking import *

__all__ = [name for name in globals() if not name.startswith("__")]
