from __future__ import annotations

from .foundation import *
from .config import *

def append_authority_temporal_mismatch_gaps(
    target_articles: list[ArticleText],
    *,
    interpretations: list[InterpretationText],
    cases: list[JudicialDecisionText],
    constitutional_decisions: list[JudicialDecisionText],
    gaps: list[ContextGap],
    deferred: list[DeferredLookup],
    reference_date: str | None = None,
) -> None:
    reference_date = compact_date(reference_date)
    raw_target_effective_dates = {
        (article.identity.name, article.article): compact_date(
            article.effective_date or article.identity.effective_date
        )
        for article in target_articles
        if article.identity.name and article.article
    }
    target_identities = {
        (article.identity.name, article.article): article.identity
        for article in target_articles
        if article.identity.name and article.article
    }
    target_refs = set(raw_target_effective_dates)
    target_effective_dates = {
        target: effective_date
        for target, effective_date in raw_target_effective_dates.items()
        if is_compact_ymd(effective_date)
    }
    if not target_refs:
        return

    authority_groups: list[tuple[str, list[tuple[str | None, list[Any]]]]] = [
        (
            "interpretation",
            [(item.identity.interpretation_date, item.referenced_articles) for item in interpretations],
        ),
        (
            "case",
            [(item.identity.decision_date, item.referenced_articles) for item in cases],
        ),
        (
            "constitutional",
            [(item.identity.decision_date, item.reviewed_articles) for item in constitutional_decisions],
        ),
    ]
    emitted: set[tuple[str, tuple[str, str], str]] = set()
    for source_type, authority_items in authority_groups:
        for authority_date_value, references in authority_items:
            authority_date = compact_date(authority_date_value)
            for reference in references:
                target = (reference.law_name, reference.article)
                if target not in target_refs:
                    continue
                effective_date = target_effective_dates.get(target)
                target_label = article_ref_label({target})
                if not is_compact_ymd(authority_date):
                    if not effective_date and not is_compact_ymd(reference_date):
                        continue
                    key = (source_type, target, "unverified")
                    if key in emitted:
                        continue
                    emitted.add(key)
                    gaps.append(
                        ContextGap(
                            kind="authority_temporal_mismatch",
                            reason=(
                                f"Eager-loaded {source_type} detail for {target_label} has a missing "
                                f"or unparseable authority date, while the loaded article effective date is "
                                f"{effective_date or 'unknown'}"
                                f"{authority_reference_date_phrase(reference_date)}; run trace_law_history "
                                "or inspect the authority-date source before treating it as current "
                                "target-article authority."
                            ),
                            query=target_label,
                            recommended_interface="trace_law_history",
                        )
                    )
                    deferred.append(
                        DeferredLookup(
                            interface="trace_law_history",
                            query=target_label,
                            reason=(
                                f"Check whether {target_label} changed before citing undated {source_type} "
                                f"authority against current effective date {effective_date}."
                            ),
                            source_type="authority_temporal_mismatch",
                            filters=authority_temporal_trace_filters(
                                target_identities.get(target),
                                target,
                                source_type=source_type,
                                authority_date=None,
                                effective_date=effective_date,
                                reference_date=reference_date,
                            ),
                        )
                    )
                    continue
                if is_compact_ymd(reference_date) and authority_date > reference_date:
                    key = (source_type, target, f"after-reference:{authority_date}")
                    if key in emitted:
                        continue
                    emitted.add(key)
                    followup_interface = authority_search_interface(source_type)
                    gaps.append(
                        ContextGap(
                            kind="authority_temporal_mismatch",
                            reason=(
                                f"Eager-loaded {source_type} detail for {target_label} is dated "
                                f"{authority_date}, after the reference date {reference_date}; "
                                "search for authority available on or before the reference date before treating "
                                "it as as-of target-article authority."
                            ),
                            query=target_label,
                            recommended_interface=followup_interface,
                        )
                    )
                    deferred.append(
                        DeferredLookup(
                            interface=followup_interface,
                            query=target_label,
                            reason=(
                                f"Find {source_type} authority for {target_label} that existed on or before "
                                f"reference date {reference_date}; loaded authority date {authority_date} is later."
                            ),
                            source_type="authority_temporal_mismatch",
                            filters={
                                "law_name": target[0],
                                "article": target[1],
                                "authority_source_type": source_type,
                                "authority_date": authority_date,
                                **authority_temporal_filter_dates(effective_date, reference_date),
                            },
                        )
                    )
                    continue
                if not effective_date:
                    continue
                if authority_date >= effective_date:
                    continue
                key = (source_type, target, authority_date)
                if key in emitted:
                    continue
                emitted.add(key)
                gaps.append(
                    ContextGap(
                        kind="authority_temporal_mismatch",
                        reason=(
                            f"Eager-loaded {source_type} detail for {target_label} is dated "
                            f"{authority_date}, before the loaded article's effective date {effective_date}; "
                            "run trace_law_history or load the article as of the authority date before treating "
                            "it as current target-article authority."
                        ),
                        query=target_label,
                        recommended_interface="trace_law_history",
                    )
                )
                deferred.append(
                    DeferredLookup(
                        interface="trace_law_history",
                        query=target_label,
                        reason=(
                            f"Check whether {target_label} changed between {source_type} authority date "
                            f"{authority_date} and current effective date {effective_date}."
                        ),
                        source_type="authority_temporal_mismatch",
                        filters=authority_temporal_trace_filters(
                            target_identities.get(target),
                            target,
                            source_type=source_type,
                            authority_date=authority_date,
                            effective_date=effective_date,
                            reference_date=reference_date,
                        ),
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
from .authority_temporal_filters import *
from .followup_basic import *
from .followup_identities import *
from .bridge import *
from .requested_load_gaps import *
from .context_load_gaps import *
from .ranking import *

__all__ = [name for name in globals() if not name.startswith("__")]
