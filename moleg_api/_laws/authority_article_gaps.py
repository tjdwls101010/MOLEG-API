from __future__ import annotations

from .foundation import *
from .config import *

def append_authority_article_mismatch_gaps(
    targets: set[tuple[str, str]],
    *,
    interpretations: list[InterpretationText],
    cases: list[JudicialDecisionText],
    constitutional_decisions: list[JudicialDecisionText],
    gaps: list[ContextGap],
) -> None:
    if not targets:
        return

    target_label = article_ref_label(targets)
    authority_groups: list[tuple[str, str, str, str, list[list[Any]]]] = [
        (
            "interpretation",
            "search_interpretations",
            "Eager-loaded interpretation detail references articles outside",
            "Eager-loaded interpretation detail has no structured article references for",
            [item.referenced_articles for item in interpretations],
        ),
        (
            "case",
            "search_cases",
            "Eager-loaded court-case detail references articles outside",
            "Eager-loaded court-case detail has no structured article references for",
            [item.referenced_articles for item in cases],
        ),
        (
            "constitutional",
            "search_constitutional_decisions",
            "Eager-loaded Constitutional Court detail reviews articles outside",
            "Eager-loaded Constitutional Court detail has no structured reviewed articles for",
            [item.reviewed_articles for item in constitutional_decisions],
        ),
    ]
    for source_type, interface, mismatch_reason_prefix, unverified_reason_prefix, reference_sets in authority_groups:
        if not reference_sets:
            continue
        has_unverified = any(not references for references in reference_sets)
        structured_reference_sets = [references for references in reference_sets if references]
        if has_unverified:
            gaps.append(
                ContextGap(
                    kind="authority_article_unverified",
                    reason=(
                        f"{unverified_reason_prefix} {target_label}; run {interface} or inspect "
                        "source article references before making target-article "
                        f"{source_type} authority claims."
                    ),
                    query=target_label,
                    recommended_interface=interface,
                )
            )
        if not structured_reference_sets:
            continue

        has_mismatch = False
        missing_targets: set[tuple[str, str]] = set()
        for references in structured_reference_sets:
            matched_targets = article_refs_matching_targets([references], targets)
            if not matched_targets:
                has_mismatch = True
                continue
            if matched_targets != targets:
                missing_targets.update(targets - matched_targets)

        if missing_targets:
            missing_target_label = article_ref_label(missing_targets)
            gaps.append(
                ContextGap(
                    kind="authority_article_partial_match",
                    reason=(
                        f"Eager-loaded {source_type} detail matches only some requested articles; "
                        f"run {interface} before making target-article {source_type} authority claims "
                        f"for {missing_target_label}."
                    ),
                    query=missing_target_label,
                    recommended_interface=interface,
                )
            )
        if not has_mismatch:
            continue
        gaps.append(
            ContextGap(
                kind="authority_article_mismatch",
                reason=(
                    f"{mismatch_reason_prefix} {target_label}; run {interface} before making "
                    f"target-article {source_type} authority claims."
                ),
                query=target_label,
                recommended_interface=interface,
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
from .authority_temporal_gaps import *
from .authority_temporal_filters import *
from .followup_basic import *
from .followup_identities import *
from .bridge import *
from .requested_load_gaps import *
from .context_load_gaps import *
from .ranking import *

__all__ = [name for name in globals() if not name.startswith("__")]
