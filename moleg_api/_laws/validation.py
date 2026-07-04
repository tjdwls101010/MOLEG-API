from __future__ import annotations

from .foundation import *
from .config import *

def validate_choice(
    param: str,
    value: str,
    valid_values: tuple[str, ...],
    *,
    context: str | None = None,
) -> None:
    if value in valid_values:
        return
    label = f"{param} for {context}" if context else param
    valid = ", ".join(repr(item) for item in valid_values)
    raise UnsupportedFormatError(f"Invalid {label}: {value!r}. Valid values: {valid}.")


def require_query(query: Any) -> str:
    normalized = string_value(query)
    normalized = normalized.strip() if normalized else None
    if not normalized:
        raise NoResultError("query is required")
    return normalized


def target_for(basis: Basis, kind: str) -> str:
    validate_choice("basis", basis, BASIS_VALUES)
    return TARGETS[basis][kind]


def annex_source_type(source: str) -> str:
    validate_choice("source", source, ANNEX_SOURCE_VALUES)
    if source == "law":
        return "law"
    if source == "administrative_rule":
        return "administrative_rule"
    raise AssertionError("validated annex/form source should be reachable")


def annex_target_for(source_type: str) -> str:
    validate_choice("source", source_type, ANNEX_SOURCE_VALUES)
    return ANNEX_FORM_TARGETS[source_type]


def annex_search_scope(search_scope: str) -> int:
    validate_choice("search_scope", search_scope, ANNEX_SEARCH_SCOPE_VALUES)
    return ANNEX_SEARCH_SCOPES[search_scope]


def annex_type_code(source_type: str, annex_type: str) -> str:
    valid_values = tuple(ANNEX_TYPE_CODES[annex_source_type(source_type)])
    validate_choice("annex_type", annex_type, valid_values, context=source_type)
    return ANNEX_TYPE_CODES[source_type][annex_type]


def annex_form_is_table_like(identity: AnnexFormIdentity) -> bool:
    signals = " ".join(
        value
        for value in (identity.annex_type, identity.annex_number, identity.title)
        if value
    )
    if any(token in signals for token in ("서식", "별지")):
        return False
    return any(token in signals for token in ("별표", "기준표", "표", "기준", "부과기준"))

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
from .context_load_gaps import *
from .ranking import *

__all__ = [name for name in globals() if not name.startswith("__")]
