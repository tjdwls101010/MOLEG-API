from __future__ import annotations

from .foundation import *
from .config import *

def build_follow_up_searches(
    query: str,
    *,
    law_candidates: list[LawIdentity],
    term_candidates: list[LegalTermCandidate],
    related_laws: list[LegalLawCandidate],
    include_websearch_hint: bool,
) -> list[FollowUpSearch]:
    searches: list[FollowUpSearch] = [
        FollowUpSearch(
            interface="search_laws",
            query=query,
            reason="Find current-law candidates before loading legal text.",
            source_type="law",
            filters={"basis": "effective"},
        ),
        FollowUpSearch(
            interface="search_administrative_rules",
            query=query,
            reason="Check practical execution criteria in notices, directives, and established rules.",
            source_type="administrative_rule",
            filters={"include_history": False},
        ),
        FollowUpSearch(
            interface="search_annex_forms",
            query=query,
            reason="Check attached tables, thresholds, amounts, criteria, and forms that may carry operative details.",
            source_type="annex_form",
            filters={"sources": ["law", "administrative_rule"], "search_scope": "source"},
        ),
        FollowUpSearch(
            interface="search_interpretations",
            query=query,
            reason="Check MOLEG official interpretation constraints.",
            source_type="interpretation",
            filters={"source": "moleg", "search_body": False},
        ),
        FollowUpSearch(
            interface="search_cases",
            query=query,
            reason="Check judicial interpretation and limits.",
            source_type="case",
            filters={"court": "all", "search_body": False},
        ),
        FollowUpSearch(
            interface="search_constitutional_decisions",
            query=query,
            reason="Check constitutional-risk context.",
            source_type="constitutional",
            filters={"search_body": False},
        ),
    ]
    planned_law_loads: set[tuple[str, str]] = set()

    for identity in law_candidates[:3]:
        if law_identity_has_source_identifier(identity):
            key = law_load_followup_key(identity.law_id, identity.mst)
            if key:
                planned_law_loads.add(key)
            searches.append(
                FollowUpSearch(
                    interface="get_law",
                    query=identity.name,
                    reason="Load the current effective text for a candidate law.",
                    source_type="law",
                    filters=law_identity_followup_filters(identity, include_basis=True),
                )
            )
    for term in term_candidates[:5]:
        searches.append(
            FollowUpSearch(
                interface="search_laws",
                query=term.term,
                reason="Use an expanded legal or everyday term as a law-search candidate.",
                source_type=term.source_type,
                filters={"basis": "effective"},
            )
        )
    for law in related_laws[:5]:
        filters = {"article": law.article} if law.article else {}
        if law.source_type == "law":
            filters = {"basis": "effective", **filters}
        elif law.source_type == "administrative_rule":
            filters = {"include_history": False, **filters}
        searches.append(
            FollowUpSearch(
                interface="search_laws" if law.source_type == "law" else "search_administrative_rules",
                query=law.name,
                reason="Follow a related law candidate discovered by query expansion.",
                source_type=law.source_type,
                filters=filters,
            )
        )
        if law.source_type == "law" and law.article and (law.law_id or law.mst):
            article_filters: dict[str, Any] = {"article": law.article, "basis": "effective"}
            if law.law_id:
                article_filters["law_id"] = law.law_id
            if law.mst:
                article_filters["mst"] = law.mst
            searches.append(
                FollowUpSearch(
                    interface="load_article_context",
                    query=law.name,
                    reason="Load the related article text before using this query-expansion candidate as legal authority.",
                    source_type="law_article",
                    filters=article_filters,
                )
            )
        if law.source_type == "law" and not law.article and (law.law_id or law.mst):
            key = law_load_followup_key(law.law_id, law.mst)
            if key and key not in planned_law_loads:
                law_filters: dict[str, Any] = {"basis": "effective"}
                if law.law_id:
                    law_filters["law_id"] = law.law_id
                if law.mst:
                    law_filters["mst"] = law.mst
                searches.append(
                    FollowUpSearch(
                        interface="get_law",
                        query=law.name,
                        reason="Load the related law text before using this query-expansion candidate as legal authority.",
                        source_type="law",
                        filters=law_filters,
                    )
                )
                planned_law_loads.add(key)
    if include_websearch_hint:
        searches.append(
            FollowUpSearch(
                interface="websearch",
                query=query,
                reason="Use for latest social facts, statistics, news, policy announcements, and non-MOLEG background.",
                source_type="web",
            )
        )
    return searches

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
