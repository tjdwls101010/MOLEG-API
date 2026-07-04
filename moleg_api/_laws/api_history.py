from __future__ import annotations

from .support import *

class LawHistoryMixin:
    def trace_law_history(
        self,
        law_identifier: LawIdentity | LawHit | str,
        *,
        date_range: tuple[str, str] | None = None,
        article: str | int | None = None,
        promulgation_bridge: dict[tuple[Any, Any, Any], Any] | None = None,
    ) -> LawHistory:
        """Load amendment-history events for a statute or article.

        Use when: the skill needs chronology, amendment reasons, promulgation
        numbers, or effective dates rather than the current text itself.
        Returns: `LawHistory` with normalized `HistoryEvent` records; full-law
        history uses the HTML-only `lsHistory` list parser.
        Raises: `NoResultError` when no matching events exist; parse/source
        errors surface when the source shape is unusable.
        Related: use `compare_law_versions` for before/after text rows and
        `resolve_promulgated_law` before history when starting from a bill.
        """
        identity = identity_from_identifier(law_identifier, basis="effective")
        identity = self._resolve_identity_name(identity)
        bill_id_map = normalize_history_bill_id_map(promulgation_bridge)
        if article is not None:
            params = identity_params(identity, as_of=None, basis="effective")
            params["JO"] = format_article_jo(article)
            payload = self.source.service("lsJoHstInf", params)
        elif date_range is not None:
            start, end = date_range
            params = {"fromRegDt": compact_date(start), "toRegDt": compact_date(end)}
            if identity.law_id:
                params["ID"] = identity.law_id
            payload = self.source.search("lsJoHstInf", params)
        else:
            payload = self._search_full_law_history(identity)

        events = normalize_history_events(payload, identity, bill_id_map=bill_id_map)
        source_failures: list[ContextGap] = []
        if article is not None:
            events = self._populate_article_history_text(
                identity,
                article,
                events,
                source_failures,
            )
        if not events:
            raise NoResultError("No law history events found")
        return LawHistory(identity=identity, events=events, source_failures=source_failures, raw=payload)

    def _populate_article_history_text(
        self,
        identity: LawIdentity,
        article: str | int,
        events: list[HistoryEvent],
        source_failures: list[ContextGap],
    ) -> list[HistoryEvent]:
        article_texts_by_lookup: dict[tuple[str, str], str | None] = {}
        populated: list[HistoryEvent] = []
        for event in events:
            if event.article_text:
                populated.append(event)
                continue
            as_of = event.effective_date or event.changed_date
            if not as_of:
                populated.append(event)
                continue
            event_article = article_label_for_filter(article)
            lookup_key = (str(event_article), as_of)
            if lookup_key not in article_texts_by_lookup:
                try:
                    article_snapshot = self.get_article(identity, event_article, as_of=as_of)
                    article_texts_by_lookup[lookup_key] = article_snapshot.text
                except MolegApiError as exc:
                    append_source_failure_gap(
                        exc,
                        source_failures,
                        query=f"{identity.name} {event_article} {as_of}",
                        recommended_interface="get_article",
                        source_label="Article-history snapshot lookup",
                    )
                    article_texts_by_lookup[lookup_key] = None
            populated.append(replace(event, article_text=article_texts_by_lookup[lookup_key]))
        return populated

__all__ = [name for name in globals() if not name.startswith("__")]
