from __future__ import annotations

from .support import *

class ArticleContextMixin:
    def load_article_context(
        self,
        law_identifier: LawIdentity | LawHit | str,
        article: str | int,
        *,
        as_of: str | None = None,
        basis: Basis = "effective",
        follow_moved: bool = True,
    ) -> ArticleContext:
        """Load an article and resolve moved-article source state.

        Use when: the skill needs current/as-of article substance and should
        not mistake a moved or deleted article marker for operative text.
        Returns: `ArticleContext` with the requested article, the current
        destination article when one is safely loaded, all loaded article rows,
        and any gaps/deferred lookups needed before a substance claim.
        Raises: source and parse errors from the initial requested article load;
        destination-load failures are preserved as context gaps instead.
        Related: use `get_article` for a single source row and
        `trace_law_history` when the movement event or prior wording matters.
        """
        requested = self.get_article(law_identifier, article, as_of=as_of, basis=basis)
        loaded_articles = [requested]
        gaps: list[ContextGap] = []
        deferred: list[DeferredLookup] = []
        source_notes: list[str] = []

        if requested.is_deleted:
            append_deleted_article_gap(requested, gaps, source_notes)
            return ArticleContext(
                requested_article=requested,
                current_article=None,
                loaded_articles=loaded_articles,
                deferred=deferred,
                gaps=gaps,
                source_notes=source_notes,
            )

        current_article: ArticleText | None = requested
        seen_articles = {requested.article}
        followups_remaining = 5
        while follow_moved and current_article and current_article.moved_to:
            destination = current_article.moved_to
            if destination in seen_articles:
                gaps.append(
                    ContextGap(
                        kind="article_movement_cycle",
                        reason=(
                            f"{current_article.identity.name} movement chain loops at {destination}; "
                            "manual review is required before making a current-substance claim."
                        ),
                        query=f"{current_article.identity.name} {destination}",
                        recommended_interface="get_article",
                    )
                )
                current_article = None
                break
            if followups_remaining <= 0:
                append_moved_destination_lookup_gap(
                    NoResultError("Moved-article chain exceeded follow-up limit"),
                    current_article.identity,
                    destination,
                    gaps,
                    deferred,
                    as_of=as_of,
                    basis=basis,
                )
                current_article = None
                break
            followups_remaining -= 1
            try:
                destination_article = self.get_article(
                    current_article.identity,
                    destination,
                    as_of=as_of,
                    basis=basis,
                )
            except MolegApiError as exc:
                append_moved_destination_lookup_gap(
                    exc,
                    current_article.identity,
                    destination,
                    gaps,
                    deferred,
                    as_of=as_of,
                    basis=basis,
                )
                current_article = None
                break

            loaded_articles.append(destination_article)
            seen_articles.add(destination_article.article)
            current_article = destination_article
            if current_article.is_deleted:
                append_deleted_article_gap(current_article, gaps, source_notes)
                current_article = None
                break

        if current_article and current_article.moved_to:
            current_article = None

        if requested.moved_to and not follow_moved:
            append_moved_destination_deferred(
                requested.identity,
                requested.moved_to,
                deferred,
                as_of=as_of,
                basis=basis,
            )
            current_article = None

        return ArticleContext(
            requested_article=requested,
            current_article=current_article,
            loaded_articles=loaded_articles,
            deferred=deferred,
            gaps=gaps,
            source_notes=source_notes,
        )

__all__ = [name for name in globals() if not name.startswith("__")]
