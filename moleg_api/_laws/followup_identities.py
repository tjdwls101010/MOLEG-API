from __future__ import annotations

from .foundation import *
from .config import *

def followup_administrative_rule_identity(
    lookup: DeferredLookup | FollowUpSearch,
    filters: dict[str, Any],
) -> AdministrativeRuleIdentity:
    serial_id = followup_str(filters, "serial_id", "id")
    rule_id = followup_str(filters, "rule_id", "lid")
    name = (
        followup_str(filters, "rule_name", "name")
        or followup_query(lookup)
        or serial_id
        or rule_id
    )
    if not name:
        raise NoResultError("follow-up administrative-rule identity requires an ID, LID, name, or query")
    return AdministrativeRuleIdentity(serial_id=serial_id, name=name, rule_id=rule_id)


def followup_annex_source(filters: dict[str, Any]) -> AnnexFormSource:
    source = followup_str(filters, "source") or "law"
    validate_choice("source", source, ANNEX_SOURCE_VALUES)
    return source  # type: ignore[return-value]


def followup_annex_sources(filters: dict[str, Any]) -> list[AnnexFormSource]:
    raw_sources = filters.get("sources")
    if isinstance(raw_sources, (list, tuple, set)):
        sources = [str(source) for source in raw_sources if string_value(source)]
    elif raw_sources not in (None, ""):
        sources = [str(raw_sources)]
    else:
        sources = [followup_annex_source(filters)]
    for source in sources:
        validate_choice("source", source, ANNEX_SOURCE_VALUES)
    return sources  # type: ignore[return-value]


def followup_annex_search_scope(filters: dict[str, Any]) -> AnnexSearchScope:
    search_scope = followup_str(filters, "search_scope") or "source"
    validate_choice("search_scope", search_scope, ANNEX_SEARCH_SCOPE_VALUES)
    return search_scope  # type: ignore[return-value]


def followup_annex_form_identity(
    lookup: DeferredLookup | FollowUpSearch,
    filters: dict[str, Any],
    *,
    source: AnnexFormSource,
) -> AnnexFormIdentity | str:
    annex_id = followup_str(filters, "annex_id", "id")
    title = followup_str(filters, "title") or followup_query(lookup) or annex_id
    if annex_id:
        source_type = annex_source_type(source)
        return AnnexFormIdentity(
            annex_id=annex_id,
            title=title or annex_id,
            source_type=source_type,
            source_target=annex_target_for(source_type),
            related_name=followup_str(filters, "related_name"),
        )
    return title or followup_query(lookup)


def followup_interpretation_source(filters: dict[str, Any]) -> InterpretationSearchSource:
    source = followup_str(filters, "source") or "moleg"
    validate_choice("source", source, INTERPRETATION_SOURCE_VALUES)
    return source  # type: ignore[return-value]


def followup_case_court(filters: dict[str, Any]) -> CaseCourt:
    court = followup_str(filters, "court") or "all"
    validate_choice("court", court, COURT_VALUES)
    return court  # type: ignore[return-value]


def followup_detail_id(
    lookup: DeferredLookup | FollowUpSearch,
    filters: dict[str, Any],
    *keys: str,
) -> str:
    identifier = followup_str(filters, *keys) or followup_query(lookup)
    if not identifier:
        raise NoResultError("follow-up detail lookup requires a source ID")
    return identifier


def followup_statute_identifiers(
    lookup: DeferredLookup | FollowUpSearch,
    filters: dict[str, Any],
) -> list[str | LawIdentity | LawHit]:
    identifiers = filters.get("statute_identifiers") or filters.get("statute_ids")
    if isinstance(identifiers, (list, tuple, set)):
        return list(identifiers)
    if identifiers not in (None, ""):
        return [identifiers]
    identity = followup_optional_law_identity(lookup, filters)
    if identity:
        return [identity]
    query = followup_query(lookup)
    if query:
        return [query]
    raise NoResultError("follow-up institutional-system lookup requires statute identifiers")


def statute_identifier_label(identifier: str | LawIdentity | LawHit) -> str:
    if isinstance(identifier, LawHit):
        return identifier.identity.name
    if isinstance(identifier, LawIdentity):
        return identifier.name
    return str(identifier)

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
from .bridge import *
from .requested_load_gaps import *
from .context_load_gaps import *
from .ranking import *

__all__ = [name for name in globals() if not name.startswith("__")]
