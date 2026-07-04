from __future__ import annotations

from .foundation import *
from .config import *

def matches_bridge(
    identity: LawIdentity,
    *,
    prom_no: str | None,
    promulgation_dt: str | None,
) -> bool:
    if prom_no and (
        compact_promulgation_number(identity.promulgation_number) != compact_promulgation_number(prom_no)
    ):
        return False
    if promulgation_dt and compact_date(identity.promulgation_date) != compact_date(promulgation_dt):
        return False
    return True


def append_not_effective_as_of_gap(
    identity: LawIdentity,
    as_of: str | None,
    gaps: list[ContextGap],
    source_notes: list[str],
    *,
    query: str | None,
) -> None:
    effective_date = compact_date(identity.effective_date)
    reference_date = compact_date(as_of)
    if not is_compact_ymd(effective_date) or not is_compact_ymd(reference_date):
        return
    if effective_date <= reference_date:
        return
    gaps.append(
        ContextGap(
            kind="not_effective_as_of",
            reason=(
                f"{identity.name} has effective date {effective_date}, "
                f"so it is not effective as of {reference_date}."
            ),
            query=query or identity.name,
            recommended_interface="load_legal_context_bundle",
        )
    )
    source_notes.append(
        f"{identity.name} is promulgated/source-loadable but not effective as of {reference_date}; "
        f"effective date is {effective_date}."
    )


def append_administrative_rule_not_effective_as_of_gap(
    identity: AdministrativeRuleIdentity,
    as_of: str | None,
    gaps: list[ContextGap],
    source_notes: list[str],
    *,
    query: str | None,
) -> None:
    effective_date = compact_date(identity.effective_date)
    reference_date = compact_date(as_of)
    if not is_compact_ymd(effective_date) or not is_compact_ymd(reference_date):
        return
    if effective_date <= reference_date:
        return
    gaps.append(
        ContextGap(
            kind="not_effective_as_of",
            reason=(
                f"{identity.name} has administrative-rule effective date {effective_date}, "
                f"so it is not effective as of {reference_date}."
            ),
            query=query or identity.name,
            recommended_interface="load_delegated_criteria",
        )
    )
    source_notes.append(
        f"{identity.name} is loaded but not effective as of {reference_date}; "
        f"administrative-rule effective date is {effective_date}."
    )


def append_delegated_criteria_source_gaps(
    bundle: LegalContextBundle,
    administrative_rules: list[AdministrativeRuleText],
    gaps: list[ContextGap],
    source_notes: list[str],
) -> None:
    scope = delegated_criteria_target_scope(bundle)
    if not administrative_rules or (not scope["law_names"] and not scope["law_ids"]):
        return
    for rule in administrative_rules:
        match_state, source_label = delegated_criteria_source_match_state(rule, scope)
        if match_state == "matched":
            continue
        query = delegated_criteria_scope_label(scope)
        if match_state == "unverified":
            reason = (
                f"{rule.identity.name} was loaded as delegated criteria, but its source-law "
                f"or source-article reference is missing for {query}; inspect delegation "
                "metadata before treating it as target operational criteria."
            )
            kind = "delegated_criteria_source_unverified"
        else:
            reason = (
                f"{rule.identity.name} was loaded as delegated criteria, but its explicit "
                f"source reference ({source_label}) does not match {query}; do not cite it "
                "as target operational criteria without another delegation source."
            )
            kind = "delegated_criteria_source_mismatch"
        gaps.append(
            ContextGap(
                kind=kind,
                reason=reason,
                query=query,
                recommended_interface="find_delegated_rules",
            )
        )
        source_notes.append(reason)

from .validation import *
from .annex_tables import *
from .identity_params import *
from .admin_scope import *
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
