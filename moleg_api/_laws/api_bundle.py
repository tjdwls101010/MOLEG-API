from __future__ import annotations

from .support import *

SIZE_OK = "load_legal_context_bundle is preserved as one method because it is the central compatibility orchestration path"
class LegalContextBundleMixin:
    def _resolve_institutional_statute(
        self,
        identifier: str | LawIdentity | LawHit,
        *,
        display: int,
    ) -> InstitutionalStatuteResolution:
        label = statute_identifier_label(identifier)
        if isinstance(identifier, LawHit):
            return InstitutionalStatuteResolution(label, identifier.identity, [identifier.identity])
        if isinstance(identifier, LawIdentity):
            return InstitutionalStatuteResolution(label, identifier, [identifier])
        text = label.strip()
        if not text:
            return InstitutionalStatuteResolution(
                label,
                None,
                [],
                error_kind="no_result",
                message="Blank statute identifier cannot be resolved",
            )
        if text.isdigit():
            identity = LawIdentity(law_id=text, name=text, basis="effective")
            return InstitutionalStatuteResolution(label, identity, [identity])

        hits = self.search_laws(text, display=display)
        identities = dedupe_identities([hit.identity for hit in hits])
        if not identities:
            return InstitutionalStatuteResolution(
                label,
                None,
                [],
                error_kind="no_result",
                message=f"Statute '{text}' was not found",
            )
        exact = [identity for identity in identities if identity.name == text]
        if len(exact) == 1:
            return InstitutionalStatuteResolution(label, exact[0], identities)
        if len(exact) > 1:
            return InstitutionalStatuteResolution(
                label,
                None,
                exact,
                error_kind="ambiguous",
                message=f"Statute identifier '{text}' matched multiple exact law identities",
            )
        if len(identities) == 1:
            return InstitutionalStatuteResolution(label, identities[0], identities)
        return InstitutionalStatuteResolution(
            label,
            None,
            identities,
            error_kind="ambiguous",
            message=f"Statute identifier '{text}' matched multiple law identities",
        )

    def load_legal_context_bundle(
        self,
        query: str | None = None,
        *,
        promulgation_bridge: dict[str, Any] | None = None,
        law_identifier: LawIdentity | LawHit | str | None = None,
        articles: list[str | int] | None = None,
        mode: BundleMode = "question",
        budget: BundleBudget = "standard",
        as_of: str | None = None,
    ) -> LegalContextBundle:
        """Load a staged legal context bundle for Claude inspection.

        Use when: the question is broad, under-specified, or begins from a
        statute/bill anchor and the skill needs one bounded first pass over
        likely MOLEG sources.
        Returns: `LegalContextBundle` with loaded primary law/article/delegation
        context, bounded candidates, deferred lookups, ambiguities, gaps, and
        source notes. Pass `as_of` for current-force questions that need an
        explicit reference date.
        Raises: `NoResultError` for missing required mode inputs and
        `UnsupportedFormatError` for unsupported mode or budget values; many
        source failures are recorded as `source_notes` instead of aborting.
        Related: the bundle loads sources, not conclusions. Use explicit
        loaders for selected candidates and WebSearch for non-MOLEG facts.
        """
        if articles is not None and not articles:
            raise NoResultError("articles must contain at least one article when provided")

        validate_choice("mode", mode, BUNDLE_MODE_VALUES)
        limits = bundle_limits(budget)
        reference_date = compact_date(as_of) if as_of else None
        request = BundleRequest(
            query=query,
            mode=mode,
            budget=budget,
            articles=list(articles or []),
            promulgation_bridge=dict(promulgation_bridge or {}),
            law_identifier=law_identifier,
            as_of=reference_date,
        )

        source_notes: list[str] = [
            "LegalContextBundle is staged context for Claude inspection, not a legal conclusion."
        ]
        ambiguities: list[Ambiguity] = []
        gaps: list[ContextGap] = []
        deferred: list[DeferredLookup] = []
        loaded_laws: list[LawText] = []
        loaded_articles: list[ArticleText] = []
        authority_target_articles: list[ArticleText] = []
        loaded_delegations: list[DelegationGraph] = []
        loaded_interpretations: list[InterpretationText] = []
        loaded_cases: list[JudicialDecisionText] = []
        loaded_constitutional_decisions: list[JudicialDecisionText] = []
        query_expansion: LegalQueryExpansion | None = None
        law_candidates: list[LawIdentity] = []
        administrative_candidates: list[AdministrativeRuleHit] = []
        annex_form_candidates: list[AnnexFormHit] = []
        interpretation_candidates: list[InterpretationHit] = []
        case_candidates: list[JudicialDecisionHit] = []
        constitutional_candidates: list[JudicialDecisionHit] = []
        loaded_detail_keys: set[tuple[str | None, str]] = set()

        primary_identity: LawIdentity | None = None
        search_query = query

        if mode == "question":
            query = require_query(query)
            search_query = query
            try:
                query_expansion = self.expand_legal_query(query, display=limits["law_candidates"])
                gaps.extend(query_expansion.source_failures)
                if query_expansion.source_failures:
                    deferred.append(
                        DeferredLookup(
                            interface="expand_legal_query",
                            query=query,
                            reason="Retry query expansion after source-access recovery before treating missing planning candidates as legal absence.",
                            source_type="query_expansion",
                        )
                    )
                law_candidates = query_expansion.law_candidates[: limits["law_candidates"]]
                if len(law_candidates) == 1:
                    primary_identity = law_candidates[0]
                elif len(law_candidates) > 1:
                    ambiguities.append(
                        Ambiguity(
                            kind="statute_identity",
                            message=(
                                "Question query matched multiple MOLEG law identities; "
                                "select one LawIdentity or use statute_review before loading statute text."
                            ),
                            candidates=law_candidates,
                        )
                    )
                    gaps.append(
                        ContextGap(
                            kind="manual_review_required",
                            reason="The question matched multiple MOLEG law identities, so no statute text was auto-loaded.",
                            query=query,
                            recommended_interface="search_laws",
                        )
                    )
                    deferred.append(
                        DeferredLookup(
                            interface="search_laws",
                            query=query,
                            reason="Resolve one LawIdentity before loading current statute text.",
                            source_type="law",
                            filters={"basis": "effective"},
                        )
                    )
            except MolegApiError as exc:
                source_notes.append(f"Query expansion skipped: {exc}")
                append_query_expansion_failure_gap(
                    exc,
                    query,
                    gaps,
                    deferred,
                )
        elif mode == "promulgated_bill":
            if not promulgation_bridge:
                raise NoResultError("promulgation_bridge is required for promulgated_bill bundles")
            prom_law_nm = string_value(promulgation_bridge.get("prom_law_nm"))
            prom_no = string_value(promulgation_bridge.get("prom_no"))
            promulgation_dt = string_value(promulgation_bridge.get("promulgation_dt"))
            try:
                primary_identity = self.resolve_promulgated_law(
                    prom_law_nm=prom_law_nm,
                    prom_no=prom_no,
                    promulgation_dt=promulgation_dt,
                )
                law_candidates = [primary_identity]
                search_query = primary_identity.name
            except AmbiguousLawError as exc:
                ambiguities.append(
                    Ambiguity(
                        kind=exc.kind or "promulgation_bridge",
                        message=str(exc),
                        candidates=exc.candidates,
                    )
                )
                gaps.append(
                    ContextGap(
                        kind="manual_review_required",
                        reason="The congress-db promulgation bridge matched multiple MOLEG law identities.",
                        query=prom_law_nm,
                        recommended_interface="resolve_promulgated_law",
                    )
                )
                deferred.append(
                    DeferredLookup(
                        interface="resolve_promulgated_law",
                        query=prom_law_nm or "",
                        reason=(
                            "Resolve the ambiguous congress-db promulgation bridge before "
                            "loading current-law context for this bill."
                        ),
                        source_type="law",
                        filters=promulgation_bridge_filters(
                            prom_law_nm=prom_law_nm,
                            prom_no=prom_no,
                            promulgation_dt=promulgation_dt,
                        ),
                    )
                )
            except NoResultError as exc:
                candidate_hits: list[LawHit] = []
                if prom_law_nm:
                    candidate_hits = safe_list(
                        lambda: self.search_laws(
                            prom_law_nm,
                            basis="promulgated",
                            display=max(2, limits["law_candidates"]),
                        ),
                        source_notes,
                        "Promulgation bridge candidate search",
                        gaps=gaps,
                        deferred=deferred,
                        query=prom_law_nm,
                        recommended_interface="search_laws",
                        source_type="law",
                    )
                law_candidates = dedupe_identities([hit.identity for hit in candidate_hits])
                search_query = prom_law_nm
                if law_candidates:
                    ambiguities.append(
                        Ambiguity(
                            kind="promulgation_bridge_lag",
                            message=(
                                f"{exc}. Law-name candidates exist, but none matched "
                                "`prom_no` and `promulgation_dt` exactly."
                            ),
                            candidates=law_candidates,
                        )
                    )
                    gaps.append(
                        ContextGap(
                            kind="source_lag_or_manual_review_required",
                            reason=(
                                "The congress-db bridge did not exactly resolve in MOLEG. "
                                "This may be source lag or a bridge-field mismatch; do not treat it as proof "
                                "that the bill was not enacted."
                            ),
                            query=prom_law_nm,
                            recommended_interface="resolve_promulgated_law",
                        )
                    )
                    deferred.append(
                        DeferredLookup(
                            interface="resolve_promulgated_law",
                            query=prom_law_nm or "",
                            reason=(
                                "Recheck the strict congress-db promulgation bridge after "
                                "confirming source lag or bridge-field correction; do not "
                                "treat this exact miss as proof the bill was not enacted."
                            ),
                            source_type="law",
                            filters=promulgation_bridge_filters(
                                prom_law_nm=prom_law_nm,
                                prom_no=prom_no,
                                promulgation_dt=promulgation_dt,
                            ),
                        )
                    )
                else:
                    ambiguities.append(Ambiguity(kind="promulgation_bridge", message=str(exc)))
                    gaps.append(
                        ContextGap(
                            kind="manual_review_required",
                            reason="The congress-db promulgation bridge did not resolve to a MOLEG law identity.",
                            query=prom_law_nm,
                            recommended_interface="congress-db",
                        )
                    )
            except MolegApiError as exc:
                source_notes.append(f"Promulgation bridge resolution skipped: {exc}")
                append_promulgation_bridge_resolution_failure_gap(
                    exc,
                    prom_law_nm=prom_law_nm,
                    prom_no=prom_no,
                    promulgation_dt=promulgation_dt,
                    gaps=gaps,
                    deferred=deferred,
                )
                search_query = prom_law_nm
        elif mode == "statute_review":
            if law_identifier is None:
                raise NoResultError("law_identifier is required for statute_review bundles")
            primary_identity = identity_from_identifier(law_identifier, basis="effective")
            law_candidates = [primary_identity]
            search_query = query or primary_identity.name
        else:
            raise UnsupportedFormatError(f"Unsupported legal context bundle mode: {mode}")

        if primary_identity:
            if articles:
                for article in articles[: limits["articles"]]:
                    try:
                        article_context = self.load_article_context(
                            primary_identity,
                            article,
                            as_of=reference_date,
                            basis="effective",
                        )
                        loaded_articles.extend(article_context.loaded_articles)
                        gaps.extend(article_context.gaps)
                        deferred.extend(article_context.deferred)
                        source_notes.extend(article_context.source_notes)
                        if article_context.current_article is not None:
                            authority_target_articles.append(article_context.current_article)
                        for article_text in article_context.loaded_articles:
                            primary_identity = prefer_versioned_law_identity(
                                primary_identity,
                                article_text.identity,
                            )
                            append_not_effective_as_of_gap(
                                article_text.identity,
                                reference_date,
                                gaps,
                                source_notes,
                                query=search_query or primary_identity.name,
                            )
                    except MolegApiError as exc:
                        source_notes.append(f"Article load skipped for {article}: {exc}")
                        append_requested_article_load_gap(
                            exc,
                            primary_identity,
                            article,
                            gaps,
                            deferred,
                            as_of=reference_date,
                        )
            else:
                try:
                    law_text = self.get_law(primary_identity, as_of=reference_date)
                    loaded_laws.append(law_text)
                    primary_identity = law_text.identity
                    append_not_effective_as_of_gap(
                        primary_identity,
                        reference_date,
                        gaps,
                        source_notes,
                        query=search_query or primary_identity.name,
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
                    source_notes.append(f"Primary law load skipped: {exc}")
                    append_requested_law_load_gap(
                        exc,
                        primary_identity,
                        gaps,
                        deferred,
                        as_of=reference_date,
                    )

            if law_identity_has_source_identifier(primary_identity):
                try:
                    graph = self.find_delegated_rules(primary_identity)
                    loaded_delegations.append(limit_delegation_graph(graph, limits["delegations"]))
                except NoResultError:
                    loaded_delegations.append(DelegationGraph(identity=primary_identity, rules=[], raw={}))
                    append_empty_delegation_lookup_gap(
                        primary_identity,
                        gaps,
                        deferred,
                    )
                except MolegApiError as exc:
                    source_notes.append(f"Delegation lookup skipped: {exc}")
                    append_delegation_lookup_failure_gap(
                        exc,
                        primary_identity,
                        gaps,
                        deferred,
                    )

            if mode == "promulgated_bill" and law_identity_has_source_identifier(primary_identity):
                deferred.append(
                    DeferredLookup(
                        interface="trace_law_history",
                        query=primary_identity.name,
                        reason="Trace amendment history once the relevant article or date range is known.",
                        source_type="law_history",
                        filters=law_identity_followup_filters(primary_identity),
                    )
                )
                deferred.append(
                    DeferredLookup(
                        interface="compare_law_versions",
                        query=primary_identity.name,
                        reason="Compare before/after text when the bill's affected articles are identified.",
                        source_type="law_diff",
                        filters=law_identity_followup_filters(primary_identity),
                    )
                )

        article_target_queries = [search_query] if search_query else []
        if search_query:
            if primary_identity is not None:
                article_target_queries = article_target_search_queries(
                    primary_identity,
                    list(articles or []),
                    authority_target_articles,
                    ranking_query=search_query,
                )
            administrative_candidates = dedupe_candidates(
                [
                    candidate
                    for candidate_query in article_target_queries
                    for candidate in safe_list(
                        lambda candidate_query=candidate_query: self.search_administrative_rules(
                            candidate_query,
                            display=limits["administrative_rules"],
                        ),
                        source_notes,
                        "Administrative-rule search",
                        gaps=gaps,
                        deferred=deferred,
                        query=candidate_query,
                        recommended_interface="search_administrative_rules",
                        source_type="administrative_rule",
                    )
                ]
            )[: limits["administrative_rules"]]
            interpretation_candidates = dedupe_candidates(
                [
                    candidate
                    for candidate_query in article_target_queries
                    for candidate in safe_list(
                        lambda candidate_query=candidate_query: self.search_interpretations(
                            candidate_query,
                            display=limits["interpretations"],
                        ),
                        source_notes,
                        "Interpretation search",
                        gaps=gaps,
                        deferred=deferred,
                        query=candidate_query,
                        recommended_interface="search_interpretations",
                        source_type="interpretation",
                    )
                ]
            )
            case_candidates = dedupe_candidates(
                [
                    candidate
                    for candidate_query in article_target_queries
                    for candidate in safe_list(
                        lambda candidate_query=candidate_query: self.search_cases(
                            candidate_query,
                            display=limits["cases"],
                        ),
                        source_notes,
                        "Case search",
                        gaps=gaps,
                        deferred=deferred,
                        query=candidate_query,
                        recommended_interface="search_cases",
                        source_type="case",
                    )
                ]
            )
            constitutional_candidates = dedupe_candidates(
                [
                    candidate
                    for candidate_query in article_target_queries
                    for candidate in safe_list(
                        lambda candidate_query=candidate_query: self.search_constitutional_decisions(
                            candidate_query,
                            display=limits["constitutional_decisions"],
                        ),
                        source_notes,
                        "Constitutional decision search",
                        gaps=gaps,
                        deferred=deferred,
                        query=candidate_query,
                        recommended_interface="search_constitutional_decisions",
                        source_type="constitutional",
                    )
                ]
            )
            annex_form_limit = limits["annex_forms"]
            law_annex_limit = (annex_form_limit + 1) // 2
            admin_annex_limit = max(1, annex_form_limit - law_annex_limit)
            annex_form_candidates = [
                *dedupe_candidates(
                    [
                        candidate
                        for candidate_query in article_target_queries
                        for candidate in safe_list(
                            lambda candidate_query=candidate_query: self.search_annex_forms(
                                candidate_query,
                                source="law",
                                search_scope="source",
                                display=law_annex_limit,
                            ),
                            source_notes,
                            "Law annex/form search",
                            gaps=gaps,
                            deferred=deferred,
                            query=candidate_query,
                            recommended_interface="search_annex_forms",
                            source_type="annex_form",
                            filters={"source": "law", "search_scope": "source"},
                        )
                    ]
                )[:law_annex_limit],
                *dedupe_candidates(
                    [
                        candidate
                        for candidate_query in article_target_queries
                        for candidate in safe_list(
                            lambda candidate_query=candidate_query: self.search_annex_forms(
                                candidate_query,
                                source="administrative_rule",
                                search_scope="source",
                                display=admin_annex_limit,
                            ),
                            source_notes,
                            "Administrative-rule annex/form search",
                            gaps=gaps,
                            deferred=deferred,
                            query=candidate_query,
                            recommended_interface="search_annex_forms",
                            source_type="annex_form",
                            filters={"source": "administrative_rule", "search_scope": "source"},
                        )
                    ]
                )[:admin_annex_limit],
            ][:annex_form_limit]

        eager_detail_limits = bundle_eager_detail_limits(search_query, mode=mode, budget=budget)
        if any(item.kind == "statute_identity" for item in ambiguities):
            eager_detail_limits = {key: 0 for key in eager_detail_limits}
            source_notes.append(
                "Eager authority detail loading skipped until statute identity ambiguity is resolved."
            )
        authority_ranking_query = " ".join(article_target_queries) if search_query else search_query
        eager_text_budget = BUNDLE_EAGER_TEXT_CHAR_LIMITS[budget]
        eager_text_used = 0
        if any(eager_detail_limits.values()):
            source_notes.append(
                "Eager detail loading triggered for "
                + ", ".join(key for key, value in eager_detail_limits.items() if value)
                + "."
            )

        for candidate in ranked_candidates(
            interpretation_candidates,
            authority_ranking_query,
            limit=eager_detail_limits["interpretations"],
        ):
            key = candidate_identity_key(candidate)
            try:
                text = self.get_interpretation(candidate.identity, include_metadata=False)
            except MolegApiError as exc:
                source_notes.append(f"Eager interpretation detail load skipped: {exc}")
                append_eager_detail_failure_gap(
                    exc,
                    gaps,
                    candidate=candidate,
                    recommended_interface="get_interpretation",
                    source_label="Eager interpretation detail load",
                )
                continue
            text_length = len(text.text)
            if eager_text_used + text_length > eager_text_budget:
                source_notes.append("Eager interpretation detail load skipped: text budget exceeded")
                continue
            eager_text_used += text_length
            loaded_interpretations.append(text)
            loaded_detail_keys.add(key)

        for candidate in ranked_candidates(
            case_candidates,
            authority_ranking_query,
            limit=eager_detail_limits["cases"],
        ):
            key = candidate_identity_key(candidate)
            try:
                text = self.get_case(candidate.identity, include_metadata=False)
            except MolegApiError as exc:
                source_notes.append(f"Eager case detail load skipped: {exc}")
                append_eager_detail_failure_gap(
                    exc,
                    gaps,
                    candidate=candidate,
                    recommended_interface="get_case",
                    source_label="Eager case detail load",
                )
                continue
            text_length = len(text.text)
            if eager_text_used + text_length > eager_text_budget:
                source_notes.append("Eager case detail load skipped: text budget exceeded")
                continue
            eager_text_used += text_length
            loaded_cases.append(text)
            loaded_detail_keys.add(key)

        for candidate in ranked_candidates(
            constitutional_candidates,
            authority_ranking_query,
            limit=eager_detail_limits["constitutional_decisions"],
        ):
            key = candidate_identity_key(candidate)
            try:
                text = self.get_constitutional_decision(candidate.identity, include_metadata=False)
            except MolegApiError as exc:
                source_notes.append(f"Eager constitutional detail load skipped: {exc}")
                append_eager_detail_failure_gap(
                    exc,
                    gaps,
                    candidate=candidate,
                    recommended_interface="get_constitutional_decision",
                    source_label="Eager constitutional detail load",
                )
                continue
            text_length = len(text.text)
            if eager_text_used + text_length > eager_text_budget:
                source_notes.append("Eager constitutional detail load skipped: text budget exceeded")
                continue
            eager_text_used += text_length
            loaded_constitutional_decisions.append(text)
            loaded_detail_keys.add(key)

        append_authority_article_mismatch_gaps(
            target_article_refs_from_loaded_articles(authority_target_articles),
            interpretations=loaded_interpretations,
            cases=loaded_cases,
            constitutional_decisions=loaded_constitutional_decisions,
            gaps=gaps,
        )
        append_authority_temporal_mismatch_gaps(
            authority_target_articles,
            interpretations=loaded_interpretations,
            cases=loaded_cases,
            constitutional_decisions=loaded_constitutional_decisions,
            gaps=gaps,
            deferred=deferred,
            reference_date=reference_date,
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
        deferred.extend(
            deferred_from_candidates(
                unloaded_candidates(interpretation_candidates, loaded_detail_keys),
                "get_interpretation",
                "interpretation",
            )
        )
        deferred.extend(
            deferred_from_candidates(
                unloaded_candidates(case_candidates, loaded_detail_keys),
                "get_case",
                "case",
            )
        )
        deferred.extend(
            deferred_from_candidates(
                unloaded_candidates(constitutional_candidates, loaded_detail_keys),
                "get_constitutional_decision",
                "constitutional",
            )
        )

        if search_query:
            gaps.append(
                ContextGap(
                    kind="websearch_required",
                    reason="Use WebSearch for latest social facts, statistics, policy announcements, news, or non-MOLEG background.",
                    query=search_query,
                    recommended_interface="websearch",
                )
            )

        return LegalContextBundle(
            request=request,
            loaded=LoadedContext(
                laws=loaded_laws,
                articles=loaded_articles,
                delegations=loaded_delegations,
                interpretations=loaded_interpretations,
                cases=loaded_cases,
                constitutional_decisions=loaded_constitutional_decisions,
            ),
            candidates=CandidateContext(
                query_expansion=query_expansion,
                laws=law_candidates,
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

    def _service_rows(
        self,
        target: str,
        params: dict[str, Any],
        raw: dict[str, Any],
        empty_sources: list[str],
        *,
        source_failures: list[ContextGap] | None = None,
        source_label: str | None = None,
    ) -> list[dict[str, Any]]:
        try:
            payload = self.source.service(target, params)
        except MolegApiError as exc:
            if source_failures is not None:
                append_source_failure_gap(
                    exc,
                    source_failures,
                    query=string_value(params.get("query")),
                    recommended_interface="expand_legal_query",
                    source_label=source_label or f"Query-expansion {target} lookup",
                )
            return []
        raw[target] = payload
        rows = unwrap_target_rows(payload, target)
        if not rows:
            empty_sources.append(target)
        return rows

__all__ = [name for name in globals() if not name.startswith("__")]
