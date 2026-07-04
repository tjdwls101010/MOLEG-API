from __future__ import annotations

from .support import *

class InterpretationMixin:
    def search_interpretations(
        self,
        query: str,
        *,
        source: InterpretationSearchSource = "moleg",
        ministry: str | None = None,
        search_body: bool = False,
        interpreted_on: str | None = None,
        display: int = 20,
    ) -> list[InterpretationHit]:
        """Search MOLEG and ministry first-instance legal interpretations.

        Use when: the skill needs official or ministry interpretation context
        about how a statute is applied, distinct from court decisions. Use
        `source="all"` for MOLEG plus one specified ministry; use
        `source="all_ministries"` only for deep institutional analysis that
        justifies registry-wide fan-out.
        Returns: `InterpretationHit` rows with normalized source authority
        labels, ministry where relevant, case number, title, and date.
        Raises: `NoResultError` when ministry search lacks a ministry;
        `UnsupportedFormatError` for unsupported source/ministry values.
        Related: use `search_cases` for ordinary judicial decisions and
        `search_constitutional_decisions` for Constitutional Court decisions.
        """
        query = require_query(query)
        specs = interpretation_sources_for(source, ministry)
        aggregate_search = len(specs) > 1
        hits: list[InterpretationHit] = []
        source_failures: list[ContextGap] = []
        first_failure: MolegApiError | None = None
        for spec in specs:
            params: dict[str, Any] = {
                "query": query,
                "display": display,
                "search": 2 if search_body else 1,
            }
            if interpreted_on:
                params["explYd"] = compact_date(interpreted_on)
            try:
                payload = self.source.search(spec.target, params)
            except MolegApiError as exc:
                if not aggregate_search:
                    raise
                if first_failure is None:
                    first_failure = exc
                append_source_failure_gap(
                    exc,
                    source_failures,
                    query=query,
                    recommended_interface="search_interpretations",
                    source_label=f"Interpretation search for {spec.ministry or spec.target}",
                )
                continue
            for row in unwrap_search_interpretations(payload, spec.target):
                identity = normalize_interpretation_identity(
                    row,
                    source_type=spec.source_type,
                    source_target=spec.target,
                    ministry=spec.ministry,
                )
                hits.append(
                    InterpretationHit(
                        identity=identity,
                        raw=row,
                        follow_up=interpretation_hit_follow_up(identity),
                    )
                )
        if not hits and first_failure is not None:
            raise first_failure
        if source_failures:
            hits = attach_interpretation_source_failures(hits, source_failures)
        return hits

    def get_interpretation(
        self,
        identifier: InterpretationIdentity | InterpretationHit | str,
        *,
        source: InterpretationSearchSource | None = None,
        ministry: str | None = None,
        include_metadata: bool = True,
    ) -> InterpretationText:
        """Load one MOLEG or ministry interpretation detail.

        Use when: a selected interpretation needs question, answer, reason, and
        related-law text before the skill cites or reasons from it.
        Returns: `InterpretationText` with preserved source authority labels,
        agencies, case number, interpretation date, and optional raw metadata.
        Raises: `NoResultError` for missing source IDs and
        `UnsupportedFormatError` for sources without cataloged detail support.
        Related: call `search_interpretations` first; use judicial loaders for
        cases or constitutional decisions, not this method.
        """
        spec = interpretation_source_for_identifier(identifier, source=source, ministry=ministry)
        if not spec.can_get:
            raise UnsupportedFormatError(
                f"{spec.ministry or spec.target} interpretation source has no cataloged detail endpoint"
            )
        identity_hint = interpretation_identity_from_identifier(identifier, spec)
        params = interpretation_identity_params(identity_hint)
        payload = self.source.service(spec.target, params)
        raw_interpretation = unwrap_service_payload(payload, spec.target)
        text = normalize_interpretation_text(
            raw_interpretation,
            source_type=spec.source_type,
            source_target=spec.target,
            ministry=spec.ministry,
        )
        if not include_metadata:
            return InterpretationText(
                identity=text.identity,
                question=text.question,
                answer=text.answer,
                reason=text.reason,
                related_laws=text.related_laws,
                referenced_articles=text.referenced_articles,
                text=text.text,
                raw={},
            )
        return text

__all__ = [name for name in globals() if not name.startswith("__")]
