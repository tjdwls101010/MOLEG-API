from __future__ import annotations

from .bundle_candidates import discover_bundle_candidates
from .bundle_eager import load_bundle_eager_details
from .bundle_finalize import finalize_bundle
from .bundle_modes import resolve_bundle_seed
from .bundle_primary import load_bundle_primary_context
from .bundle_state import new_bundle_state
from .institutional_resolution import resolve_institutional_statute
from .support import *


class LegalContextBundleMixin:
    def _resolve_institutional_statute(
        self,
        identifier: str | LawIdentity | LawHit,
        *,
        display: int,
    ) -> InstitutionalStatuteResolution:
        return resolve_institutional_statute(self, identifier, display=display)

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
        request = BundleRequest(
            query=query,
            mode=mode,
            budget=budget,
            articles=list(articles or []),
            promulgation_bridge=dict(promulgation_bridge or {}),
            law_identifier=law_identifier,
            as_of=compact_date(as_of) if as_of else None,
        )
        state = new_bundle_state()
        seed = resolve_bundle_seed(self, request, limits, state)
        primary_identity = load_bundle_primary_context(
            self,
            seed.primary_identity,
            request,
            seed.search_query,
            limits,
            state,
        )
        article_target_queries = discover_bundle_candidates(
            self,
            primary_identity,
            request,
            seed.search_query,
            limits,
            state,
        )
        load_bundle_eager_details(
            self,
            request,
            seed.search_query,
            article_target_queries,
            state,
        )
        return finalize_bundle(request, seed.search_query, state)

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
