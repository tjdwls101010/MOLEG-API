from __future__ import annotations

from .support import *

SIZE_OK = "load_followup is a compatibility dispatch table kept intact to preserve follow-up routing"
class FollowupMixin:
    def __init__(self, source: MolegSource | None = None) -> None:
        self.source = source or LawGoKrClient()

    def load_followup(self, lookup: DeferredLookup | FollowUpSearch) -> Any:
        """Execute one staged follow-up lookup through the public interface.

        Use when: the skill receives a `DeferredLookup` or `FollowUpSearch`
        from query expansion or a context bundle and wants MOLEG-API to turn it
        into the right task-level loader without exposing source target names,
        `ID`/`MST` rules, or article formatting.
        Returns: the same value returned by the routed public method, such as a
        law text, article text, search-hit list, or context bundle.
        Raises: `UnsupportedFormatError` for WebSearch handoffs or unknown
        interfaces; routed method errors propagate unchanged.
        Related: `expand_legal_query`, `load_legal_context_bundle`, and
        `load_institutional_system` produce follow-up records this method can
        execute.
        """
        interface = followup_interface(lookup)
        filters = followup_filters(lookup)
        query = followup_query(lookup)

        if interface == "websearch" or interface.startswith("websearch."):
            raise UnsupportedFormatError(
                "websearch follow-up is outside MOLEG-API; use WebSearch for latest or non-MOLEG facts."
            )
        if interface == "congress-db" or interface.startswith("congress-db."):
            raise UnsupportedFormatError(
                "congress-db follow-up is outside MOLEG-API; use congress-db for National Assembly bill facts and promulgation bridge fields."
            )
        if interface == "expand_legal_query":
            return self.expand_legal_query(
                query,
                display=followup_int(filters, "display", 5),
                include_websearch_hint=followup_bool(filters, "include_websearch_hint", True),
            )
        if interface == "find_comparable_mechanisms":
            return self.find_comparable_mechanisms(query, display=followup_int(filters, "display", 5))
        if interface == "resolve_promulgated_law":
            return self.resolve_promulgated_law(
                prom_law_nm=followup_str(filters, "prom_law_nm", "law_name") or query,
                prom_no=followup_str(filters, "prom_no", "promulgation_number"),
                promulgation_dt=followup_str(filters, "promulgation_dt", "promulgation_date"),
            )
        if interface == "search_laws":
            return self.search_laws(
                query,
                as_of=followup_str(filters, "as_of"),
                basis=followup_basis(filters),
                law_type=followup_str(filters, "law_type"),
                ministry=followup_str(filters, "ministry"),
                display=followup_int(filters, "display", 20),
            )
        if interface == "get_law":
            basis = followup_basis(filters)
            return self.get_law(
                followup_law_identity(lookup, filters, basis=basis),
                as_of=followup_str(filters, "as_of"),
                basis=basis,
                articles=followup_articles(filters),
                include_metadata=followup_bool(filters, "include_metadata", True),
            )
        if interface == "get_article":
            basis = followup_basis(filters)
            return self.get_article(
                followup_law_identity(lookup, filters, basis=basis),
                followup_article(filters, query),
                as_of=followup_str(filters, "as_of"),
                basis=basis,
            )
        if interface == "load_article_context":
            basis = followup_basis(filters)
            as_of = followup_str(filters, "as_of")
            article = followup_article(filters, query)
            follow_moved = followup_bool(filters, "follow_moved", True)
            context = self.load_article_context(
                followup_law_identity(lookup, filters, basis=basis),
                article,
                as_of=as_of,
                basis=basis,
                follow_moved=follow_moved,
            )
            moved_to = followup_str(filters, "moved_to")
            if (
                not moved_to
                or not follow_moved
                or context.requested_article.moved_to
                or context.current_article is None
            ):
                return context
            destination = article_label_for_filter(moved_to)
            requested = replace(context.requested_article, moved_to=destination)
            try:
                destination_article = self.get_article(
                    requested.identity,
                    destination,
                    as_of=as_of,
                    basis=basis,
                )
            except MolegApiError as exc:
                gaps = list(context.gaps)
                deferred = list(context.deferred)
                append_moved_destination_lookup_gap(
                    exc,
                    requested.identity,
                    destination,
                    gaps,
                    deferred,
                    as_of=as_of,
                    basis=basis,
                )
                return replace(
                    context,
                    requested_article=requested,
                    current_article=None,
                    gaps=gaps,
                    deferred=deferred,
                )
            return replace(
                context,
                requested_article=requested,
                current_article=destination_article,
                loaded_articles=[*context.loaded_articles, destination_article],
            )
        if interface == "trace_law_history":
            return self.trace_law_history(
                followup_law_identity(lookup, filters, basis="effective"),
                date_range=followup_date_range(filters),
                article=followup_optional_article(filters, query),
                promulgation_bridge=followup_promulgation_bridge(filters),
            )
        if interface == "compare_law_versions":
            return self.compare_law_versions(
                followup_law_identity(lookup, filters, basis="effective"),
                before=followup_str(filters, "before"),
                after=followup_str(filters, "after"),
                article=followup_optional_article(filters, query),
            )
        if interface == "find_delegated_rules":
            return self.find_delegated_rules(
                followup_law_identity(lookup, filters, basis="effective"),
                article=followup_optional_article(filters, query),
            )
        if interface == "get_law_structure":
            return self.get_law_structure(
                followup_law_identity(lookup, filters, basis="effective"),
                depth=followup_int(filters, "depth", 0),
            )
        if interface == "search_administrative_rules":
            return self.search_administrative_rules(
                followup_query_with_article(query, filters),
                ministry=followup_str(filters, "ministry"),
                rule_type=followup_str(filters, "rule_type"),
                issued_on=followup_str(filters, "issued_on"),
                include_history=followup_bool(filters, "include_history", False),
                display=followup_int(filters, "display", 20),
            )
        if interface == "get_administrative_rule":
            return self.get_administrative_rule(
                followup_administrative_rule_identity(lookup, filters),
                articles=followup_articles(filters),
                include_metadata=followup_bool(filters, "include_metadata", True),
            )
        if interface == "load_administrative_rule_context":
            return self.load_administrative_rule_context(
                followup_administrative_rule_identity(lookup, filters),
                articles=followup_articles(filters),
                include_metadata=followup_bool(filters, "include_metadata", True),
                follow_moved=followup_bool(filters, "follow_moved", True),
            )
        if interface == "search_annex_forms":
            hits: list[AnnexFormHit] = []
            for source in followup_annex_sources(filters):
                hits.extend(
                    self.search_annex_forms(
                        followup_query_with_article(query, filters),
                        source=source,
                        search_scope=followup_annex_search_scope(filters),
                        annex_type=followup_str(filters, "annex_type"),
                        ministry=followup_str(filters, "ministry"),
                        display=followup_int(filters, "display", 20),
                    )
                )
            return hits
        if interface == "get_annex_form_body":
            source = followup_annex_source(filters)
            return self.get_annex_form_body(
                followup_annex_form_identity(lookup, filters, source=source),
                source=source,
                title=followup_str(filters, "title"),
                include_metadata=followup_bool(filters, "include_metadata", True),
                attempt_structuring=followup_bool(filters, "attempt_structuring", True),
            )
        if interface == "search_interpretations":
            return self.search_interpretations(
                query,
                source=followup_interpretation_source(filters),
                ministry=followup_str(filters, "ministry"),
                search_body=followup_bool(filters, "search_body", False),
                interpreted_on=followup_str(filters, "interpreted_on"),
                display=followup_int(filters, "display", 20),
            )
        if interface == "get_interpretation":
            return self.get_interpretation(
                followup_detail_id(lookup, filters, "interpretation_id", "id"),
                source=followup_str(filters, "source"),
                ministry=followup_str(filters, "ministry"),
                include_metadata=followup_bool(filters, "include_metadata", True),
            )
        if interface == "search_cases":
            return self.search_cases(
                query,
                court=followup_case_court(filters),
                court_name=followup_str(filters, "court_name"),
                search_body=followup_bool(filters, "search_body", False),
                decided_on=followup_str(filters, "decided_on"),
                case_number=followup_str(filters, "case_number"),
                display=followup_int(filters, "display", 20),
            )
        if interface == "get_case":
            return self.get_case(
                followup_detail_id(lookup, filters, "decision_id", "case_id", "id"),
                include_metadata=followup_bool(filters, "include_metadata", True),
            )
        if interface == "search_constitutional_decisions":
            return self.search_constitutional_decisions(
                query,
                search_body=followup_bool(filters, "search_body", False),
                decided_on=followup_str(filters, "decided_on"),
                case_number=followup_str(filters, "case_number"),
                display=followup_int(filters, "display", 20),
            )
        if interface == "get_constitutional_decision":
            return self.get_constitutional_decision(
                followup_detail_id(lookup, filters, "decision_id", "case_id", "id"),
                include_metadata=followup_bool(filters, "include_metadata", True),
            )
        if interface == "load_authority_context":
            return self.load_authority_context(
                followup_law_identity(lookup, filters, basis="effective"),
                articles=followup_required_articles(filters),
                query=followup_str(filters, "authority_query") or query or None,
                budget=followup_budget(filters),
                as_of=followup_str(filters, "as_of"),
            )
        if interface == "load_legal_context_bundle":
            return self.load_legal_context_bundle(
                query or None,
                promulgation_bridge=followup_promulgation_bridge(filters),
                law_identifier=followup_optional_law_identity(lookup, filters),
                articles=followup_articles(filters),
                mode=followup_bundle_mode(filters),
                budget=followup_budget(filters),
                as_of=followup_str(filters, "as_of"),
            )
        if interface == "load_institutional_system":
            return self.load_institutional_system(
                followup_statute_identifiers(lookup, filters),
                articles=followup_articles(filters),
                budget=followup_budget(filters),
                as_of=followup_str(filters, "as_of"),
            )
        if interface == "load_delegated_criteria":
            return self.load_delegated_criteria(
                followup_law_identity(lookup, filters, basis="effective"),
                articles=followup_articles(filters),
                query=followup_str(filters, "criteria_query") or query or None,
                budget=followup_budget(filters),
                as_of=followup_str(filters, "as_of"),
            )
        raise UnsupportedFormatError(f"Unsupported follow-up interface: {interface}")

__all__ = [name for name in globals() if not name.startswith("__")]
