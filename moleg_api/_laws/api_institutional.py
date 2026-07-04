from __future__ import annotations

from .support import *

SIZE_OK = "load_institutional_system is preserved as one method to avoid changing staged bundle semantics"
class InstitutionalSystemMixin:
    def load_institutional_system(
        self,
        statute_identifiers: list[str | LawIdentity | LawHit],
        *,
        articles: list[str | int] | None = None,
        budget: BundleBudget = "standard",
        as_of: str | None = None,
    ) -> LegalContextBundle:
        """Load one explicit multi-statute institutional system.

        Use when: the skill has already selected the statute set for a 제도 and
        needs one staged source bundle across those statutes.
        Returns: `LegalContextBundle` with `request.mode="institutional_system"`,
        `request.statute_ids`, loaded law/article text, law structures,
        delegation graphs, candidates, deferred lookups, ambiguities, and gaps.
        Pass `as_of` when the statute set is being reviewed for current force
        on a specific reference date.
        Raises: `NoResultError` for an empty statute set and budget validation
        errors from the normal bundle limits; per-statute failures are recorded
        in the returned bundle instead of aborting the whole load.
        Related: use `search_laws` or `expand_legal_query` before this method
        when the statute set itself is uncertain.
        """
        if not statute_identifiers:
            raise NoResultError("statute_identifiers is required for institutional-system bundles")
        if articles is not None and not articles:
            raise NoResultError("articles must contain at least one article when provided")

        limits = bundle_limits(budget)
        reference_date = compact_date(as_of) if as_of else None
        request = BundleRequest(
            query=None,
            mode="institutional_system",
            budget=budget,
            articles=list(articles or []),
            statute_ids=[statute_identifier_label(identifier) for identifier in statute_identifiers],
            as_of=reference_date,
        )
        source_notes: list[str] = [
            "Institutional-system bundle is staged source context, not a legal conclusion."
        ]
        ambiguities: list[Ambiguity] = []
        gaps: list[ContextGap] = []
        deferred: list[DeferredLookup] = []
        loaded_laws: list[LawText] = []
        loaded_articles: list[ArticleText] = []
        loaded_delegations: list[DelegationGraph] = []
        law_structures: list[LawStructure] = []
        law_candidates: list[LawIdentity] = []
        administrative_candidates: list[AdministrativeRuleHit] = []
        annex_form_candidates: list[AnnexFormHit] = []
        interpretation_candidates: list[InterpretationHit] = []
        case_candidates: list[JudicialDecisionHit] = []
        constitutional_candidates: list[JudicialDecisionHit] = []

        for statute_identifier in statute_identifiers:
            try:
                resolution = self._resolve_institutional_statute(
                    statute_identifier,
                    display=max(2, limits["law_candidates"]),
                )
            except MolegApiError as exc:
                label = statute_identifier_label(statute_identifier)
                source_notes.append(f"Statute resolution skipped for {label}: {exc}")
                append_institutional_statute_resolution_failure_gap(
                    exc,
                    label,
                    gaps,
                    deferred,
                )
                continue
            law_candidates.extend(resolution.candidates)
            if resolution.identity is None:
                if resolution.error_kind == "ambiguous":
                    ambiguities.append(
                        Ambiguity(
                            kind="statute_identity",
                            message=resolution.message
                            or f"Statute identifier is ambiguous: {resolution.identifier}",
                            candidates=resolution.candidates,
                        )
                    )
                else:
                    source_notes.append(
                        resolution.message or f"Statute '{resolution.identifier}' was not found"
                    )
                gaps.append(
                    ContextGap(
                        kind="manual_review_required",
                        reason="A statute identifier could not be resolved to one MOLEG law identity.",
                        query=resolution.identifier,
                        recommended_interface="search_laws",
                    )
                )
                deferred.append(
                    DeferredLookup(
                        interface="search_laws",
                        query=resolution.identifier,
                        reason="Resolve the statute identity before loading this part of the institutional system.",
                        source_type="law",
                        filters={"basis": "effective"},
                    )
                )
                continue

            identity = resolution.identity
            if articles:
                for article in articles[: limits["articles"]]:
                    try:
                        article_context = self.load_article_context(
                            identity,
                            article,
                            as_of=reference_date,
                            basis="effective",
                        )
                        loaded_articles.extend(article_context.loaded_articles)
                        gaps.extend(article_context.gaps)
                        deferred.extend(article_context.deferred)
                        source_notes.extend(article_context.source_notes)
                        for article_text in article_context.loaded_articles:
                            identity = prefer_versioned_law_identity(identity, article_text.identity)
                            append_not_effective_as_of_gap(
                                article_text.identity,
                                reference_date,
                                gaps,
                                source_notes,
                                query=identity.name,
                            )
                    except MolegApiError as exc:
                        source_notes.append(f"Article load skipped for {identity.name} {article}: {exc}")
                        append_requested_article_load_gap(
                            exc,
                            identity,
                            article,
                            gaps,
                            deferred,
                            as_of=reference_date,
                        )
            else:
                try:
                    law_text = self.get_law(identity, as_of=reference_date)
                    loaded_laws.append(law_text)
                    identity = law_text.identity
                    law_candidates.append(identity)
                    append_not_effective_as_of_gap(
                        identity,
                        reference_date,
                        gaps,
                        source_notes,
                        query=identity.name,
                    )
                    append_whole_law_article_status_gaps(
                        law_text,
                        gaps,
                        deferred,
                        source_notes,
                        as_of=reference_date,
                        basis="effective",
                    )
                except MolegApiError as exc:
                    source_notes.append(f"Law load skipped for {identity.name}: {exc}")
                    append_requested_law_load_gap(
                        exc,
                        identity,
                        gaps,
                        deferred,
                        as_of=reference_date,
                    )

            try:
                law_structures.append(self.get_law_structure(identity, depth=1))
            except MolegApiError as exc:
                source_notes.append(f"Law-structure lookup skipped for {identity.name}: {exc}")
                append_law_structure_load_gap(
                    exc,
                    identity,
                    gaps,
                    deferred,
                )

            try:
                graph = self.find_delegated_rules(identity)
                loaded_delegations.append(limit_delegation_graph(graph, limits["delegations"]))
            except NoResultError:
                loaded_delegations.append(DelegationGraph(identity=identity, rules=[], raw={}))
                append_empty_delegation_lookup_gap(
                    identity,
                    gaps,
                    deferred,
                    recommended_interface="search_administrative_rules",
                    deferred_interface=None,
                )
            except MolegApiError as exc:
                source_notes.append(f"Delegation lookup skipped for {identity.name}: {exc}")
                append_delegation_lookup_failure_gap(
                    exc,
                    identity,
                    gaps,
                    deferred,
                )

            administrative_candidates.extend(
                safe_list(
                    lambda identity=identity: self.search_administrative_rules(
                        identity.name,
                        display=limits["administrative_rules"],
                    ),
                    source_notes,
                    f"Administrative-rule search for {identity.name}",
                    gaps=gaps,
                    deferred=deferred,
                    query=identity.name,
                    recommended_interface="search_administrative_rules",
                    source_type="administrative_rule",
                )
            )
            interpretation_candidates.extend(
                safe_list(
                    lambda identity=identity: self.search_interpretations(
                        identity.name,
                        display=limits["interpretations"],
                    ),
                    source_notes,
                    f"Interpretation search for {identity.name}",
                    gaps=gaps,
                    deferred=deferred,
                    query=identity.name,
                    recommended_interface="search_interpretations",
                    source_type="interpretation",
                )
            )
            case_candidates.extend(
                safe_list(
                    lambda identity=identity: self.search_cases(
                        identity.name,
                        display=limits["cases"],
                    ),
                    source_notes,
                    f"Case search for {identity.name}",
                    gaps=gaps,
                    deferred=deferred,
                    query=identity.name,
                    recommended_interface="search_cases",
                    source_type="case",
                )
            )
            constitutional_candidates.extend(
                safe_list(
                    lambda identity=identity: self.search_constitutional_decisions(
                        identity.name,
                        display=limits["constitutional_decisions"],
                    ),
                    source_notes,
                    f"Constitutional decision search for {identity.name}",
                    gaps=gaps,
                    deferred=deferred,
                    query=identity.name,
                    recommended_interface="search_constitutional_decisions",
                    source_type="constitutional",
                )
            )

            annex_form_limit = limits["annex_forms"]
            law_annex_limit = (annex_form_limit + 1) // 2
            admin_annex_limit = max(1, annex_form_limit - law_annex_limit)
            annex_form_candidates.extend(
                [
                    *safe_list(
                        lambda identity=identity: self.search_annex_forms(
                            identity.name,
                            source="law",
                            search_scope="source",
                            display=law_annex_limit,
                        ),
                        source_notes,
                        f"Law annex/form search for {identity.name}",
                        gaps=gaps,
                        deferred=deferred,
                        query=identity.name,
                        recommended_interface="search_annex_forms",
                        source_type="annex_form",
                        filters={"source": "law", "search_scope": "source"},
                    ),
                    *safe_list(
                        lambda identity=identity: self.search_annex_forms(
                            identity.name,
                            source="administrative_rule",
                            search_scope="source",
                            display=admin_annex_limit,
                        ),
                        source_notes,
                        f"Administrative-rule annex/form search for {identity.name}",
                        gaps=gaps,
                        deferred=deferred,
                        query=identity.name,
                        recommended_interface="search_annex_forms",
                        source_type="annex_form",
                        filters={"source": "administrative_rule", "search_scope": "source"},
                    ),
                ]
            )
            gaps.append(
                ContextGap(
                    kind="websearch_required",
                    reason="Use WebSearch for latest social facts, statistics, policy announcements, news, or non-MOLEG background.",
                    query=identity.name,
                    recommended_interface="websearch",
                )
            )

        deferred.extend(
            deferred_from_candidates(
                administrative_candidates,
                "get_administrative_rule",
                "administrative_rule",
            )
        )
        deferred.extend(
            deferred_from_candidates(
                annex_form_candidates,
                "get_annex_form_body",
                "annex_form",
            )
        )
        deferred.extend(deferred_from_candidates(interpretation_candidates, "get_interpretation", "interpretation"))
        deferred.extend(deferred_from_candidates(case_candidates, "get_case", "case"))
        deferred.extend(
            deferred_from_candidates(
                constitutional_candidates,
                "get_constitutional_decision",
                "constitutional",
            )
        )

        return LegalContextBundle(
            request=request,
            loaded=LoadedContext(
                laws=loaded_laws,
                articles=loaded_articles,
                delegations=loaded_delegations,
                law_structures=law_structures,
            ),
            candidates=CandidateContext(
                laws=dedupe_identities(law_candidates),
                administrative_rules=administrative_candidates,
                annex_forms=annex_form_candidates,
                interpretations=interpretation_candidates,
                cases=case_candidates,
                constitutional_decisions=constitutional_candidates,
            ),
            deferred=deferred,
            ambiguities=ambiguities,
            gaps=gaps,
            source_notes=source_notes,
        )

__all__ = [name for name in globals() if not name.startswith("__")]
