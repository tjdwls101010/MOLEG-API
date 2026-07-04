from __future__ import annotations

from .foundation import *
from .config import *

def append_delegated_criteria_annex_source_gaps(
    bundle: LegalContextBundle,
    administrative_rules: list[AdministrativeRuleText],
    annex_forms: list[AnnexFormText],
    gaps: list[ContextGap],
    source_notes: list[str],
) -> None:
    scope = delegated_criteria_annex_target_scope(bundle, administrative_rules)
    if not annex_forms or (not scope["law_names"] and not scope["law_ids"]):
        return
    for annex in annex_forms:
        match_state, source_label = delegated_criteria_annex_source_match_state(annex, scope)
        if match_state == "matched":
            continue
        query = delegated_criteria_scope_label(scope)
        if match_state == "unverified":
            reason = (
                f"{annex.identity.title} was loaded as delegated criteria, but its "
                f"source-law or source-rule reference is missing for {query}; inspect "
                "attached-material metadata before treating it as target operational criteria."
            )
            kind = "delegated_criteria_annex_source_unverified"
        else:
            reason = (
                f"{annex.identity.title} was loaded as delegated criteria, but its explicit "
                f"attached-material source reference ({source_label}) does not match {query}; "
                "do not cite it as target operational criteria without another source."
            )
            kind = "delegated_criteria_annex_source_mismatch"
        gaps.append(
            ContextGap(
                kind=kind,
                reason=reason,
                query=query,
                recommended_interface="search_annex_forms",
            )
        )
        source_notes.append(reason)


def delegated_criteria_annex_target_scope(
    bundle: LegalContextBundle,
    administrative_rules: list[AdministrativeRuleText],
) -> dict[str, set[str]]:
    scope = delegated_criteria_target_scope(bundle)
    scope["administrative_rule_names"] = set()
    scope["administrative_rule_ids"] = set()
    scope["administrative_rule_serial_ids"] = set()
    for rule in administrative_rules:
        match_state, _ = delegated_criteria_source_match_state(rule, scope)
        if match_state != "matched":
            continue
        if rule.identity.name:
            scope["administrative_rule_names"].add(rule.identity.name)
        if rule.identity.rule_id:
            scope["administrative_rule_ids"].add(rule.identity.rule_id)
        if rule.identity.serial_id:
            scope["administrative_rule_serial_ids"].add(rule.identity.serial_id)
    return scope


def delegated_criteria_target_scope(bundle: LegalContextBundle) -> dict[str, set[str]]:
    law_ids: set[str] = set()
    law_msts: set[str] = set()
    law_names: set[str] = set()
    articles: set[str] = {
        comparable_article_label(article)
        for article in bundle.request.articles
        if comparable_article_label(article)
    }
    for law in bundle.loaded.laws:
        if law.identity.law_id:
            law_ids.add(law.identity.law_id)
        if law.identity.mst:
            law_msts.add(law.identity.mst)
        if law.identity.name:
            law_names.add(law.identity.name)
    for article in bundle.loaded.articles:
        if article.identity.law_id:
            law_ids.add(article.identity.law_id)
        if article.identity.mst:
            law_msts.add(article.identity.mst)
        if article.identity.name:
            law_names.add(article.identity.name)
        if article.article:
            articles.add(comparable_article_label(article.article))
    for graph in bundle.loaded.delegations:
        if graph.identity.law_id:
            law_ids.add(graph.identity.law_id)
        if graph.identity.mst:
            law_msts.add(graph.identity.mst)
        if graph.identity.name:
            law_names.add(graph.identity.name)
    return {"law_ids": law_ids, "law_msts": law_msts, "law_names": law_names, "articles": articles}


def flatten_structure_nodes(nodes: list[LawStructureNode]) -> list[LawStructureNode]:
    flat: list[LawStructureNode] = []
    for node in nodes:
        flat.append(node)
        if node.children:
            flat.extend(flatten_structure_nodes(node.children))
    return flat


def delegated_subordinate_rule_names(
    bundle: LegalContextBundle, scope: dict[str, set[str]]
) -> list[str]:
    """Names of subordinate legislation (시행령·시행규칙) delegated from the target
    statute, used to search their own annexes — criteria/amount 별표 live inside
    the lower rules, and lsDelegated never surfaces 별표 pointers.

    Delegations whose source article is in the requested scope are preferred; the
    law-structure 시행령·시행규칙 nodes are always included as a fallback so a bare
    anchor still reaches them.
    """
    names: list[str] = []
    seen: set[str] = set()
    scope_articles = scope.get("articles") or set()

    def add(name: str | None) -> None:
        if not name:
            return
        key = str(name).strip()
        if not key or key in seen:
            return
        seen.add(key)
        names.append(key)

    for graph in bundle.loaded.delegations:
        for rule in graph.rules:
            if not rule.delegated_name:
                continue
            if scope_articles and rule.source_article:
                if comparable_article_label(rule.source_article) not in scope_articles:
                    continue
            add(rule.delegated_name)
    for structure in bundle.loaded.law_structures:
        for node in flatten_structure_nodes(structure.instruments):
            if node.instrument_type in ("enforcement_decree", "enforcement_rule"):
                add(node.name)
    return names


def delegated_criteria_scope_label(scope: dict[str, set[str]]) -> str:
    law_label = ", ".join(sorted(scope["law_names"] or scope["law_ids"]))
    article_label = ", ".join(sorted(scope["articles"]))
    return f"{law_label} {article_label}".strip()

from .validation import *
from .annex_tables import *
from .identity_params import *
from .admin_scope import *
from .temporal_gaps import *
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
