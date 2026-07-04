from __future__ import annotations

from .support import *

class AdministrativeRuleMixin:
    def get_administrative_rule(
        self,
        identifier: AdministrativeRuleIdentity | AdministrativeRuleHit | str,
        *,
        articles: list[str | int] | None = None,
        include_metadata: bool = True,
    ) -> AdministrativeRuleText:
        """Load one administrative-rule body by identity, ID, or exact name.

        Use when: the skill selected a notice, directive, established rule, or
        similar administrative rule and needs inspectable text.
        Returns: `AdministrativeRuleText` with normalized identity, full joined
        text, structured articles when available, supplementary provisions when
        present, and optional raw metadata.
        Raises: `NoResultError` when the identity cannot locate text or article
        filtering removes all rows; source/parse errors may also propagate.
        Related: use `search_administrative_rules` for discovery and
        `find_delegated_rules` when starting from a statute.
        """
        if articles is not None and not articles:
            raise NoResultError("articles must contain at least one article when provided")

        identity_hint = self._resolve_administrative_rule_identifier(identifier)
        params = administrative_rule_identity_params(identity_hint)
        payload = self.source.service("admrul", params)
        raw_rule = unwrap_service_payload(payload, "admrul")
        identity = normalize_administrative_rule_identity(raw_rule)
        rule_articles = extract_administrative_rule_articles(raw_rule, identity)
        supplementary_provisions = extract_supplementary_provisions(raw_rule, "administrative_rule")
        if articles is not None:
            rule_articles = select_requested_administrative_rule_articles(rule_articles, articles)
        if not rule_articles:
            raise NoResultError("No administrative-rule text found")
        text = administrative_rule_text_from_articles(rule_articles)
        return AdministrativeRuleText(
            identity=identity,
            text=text,
            articles=rule_articles,
            supplementary_provisions=supplementary_provisions,
            raw=raw_rule if include_metadata else {},
        )

    def _resolve_administrative_rule_identifier(
        self,
        identifier: AdministrativeRuleIdentity | AdministrativeRuleHit | str,
    ) -> AdministrativeRuleIdentity:
        identity = administrative_rule_identity_from_identifier(identifier)
        if identity.serial_id or identity.rule_id:
            return identity
        if not identity.name:
            raise NoResultError("Administrative-rule identity has neither ID, LID, nor exact name")

        hits = self.search_administrative_rules(identity.name)
        exact = [
            hit.identity
            for hit in hits
            if hit.identity.name == identity.name
        ]
        unique: list[AdministrativeRuleIdentity] = []
        seen: set[tuple[str | None, str | None, str]] = set()
        for item in exact:
            key = (item.serial_id, item.rule_id, item.name)
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)

        if len(unique) == 1:
            return unique[0]
        if len(unique) > 1:
            raise AmbiguousLawError(
                f"Administrative-rule name {identity.name!r} matched multiple identities",
                kind="administrative_rule_identity",
                candidates=unique,
            )
        raise NoResultError(f"No administrative-rule identity matched exact name: {identity.name}")

    def load_administrative_rule_context(
        self,
        identifier: AdministrativeRuleIdentity | AdministrativeRuleHit | str,
        *,
        articles: list[str | int] | None = None,
        include_metadata: bool = True,
        follow_moved: bool = True,
    ) -> AdministrativeRuleContext:
        """Load administrative-rule text and resolve moved/deleted articles.

        Use when: the skill needs current operational criteria from a selected
        notice, directive, established rule, or similar administrative rule and
        should not mistake deleted/moved article markers for operative text.
        Returns: `AdministrativeRuleContext` with requested articles,
        current-citable articles, all loaded article rows, and any
        gaps/deferred lookups needed before a criteria claim.
        Raises: source and parse errors from the initial selected rule load;
        moved-destination failures are preserved as context gaps instead.
        Related: use `search_administrative_rules` for discovery and
        `get_administrative_rule` when the caller only needs source text rows.
        """
        rule = self.get_administrative_rule(
            identifier,
            articles=articles,
            include_metadata=include_metadata,
        )
        requested_articles = list(rule.articles)
        loaded_articles = list(requested_articles)
        current_articles: list[AdministrativeRuleArticleText] = []
        deferred: list[DeferredLookup] = []
        gaps: list[ContextGap] = []
        source_notes: list[str] = []

        for requested in requested_articles:
            if requested.is_deleted:
                append_deleted_administrative_rule_article_gap(requested, gaps, source_notes)
                continue

            current_article: AdministrativeRuleArticleText | None = requested
            seen_articles = {requested.article} if requested.article else set()
            followups_remaining = 5
            while follow_moved and current_article and current_article.moved_to:
                destination = current_article.moved_to
                source_notes.append(
                    f"{current_article.identity.name} {current_article.article} is moved to "
                    f"{destination}; current operational criteria must come from the destination article."
                )
                if destination in seen_articles:
                    gaps.append(
                        ContextGap(
                            kind="administrative_rule_article_movement_cycle",
                            reason=(
                                f"{current_article.identity.name} movement chain loops at {destination}; "
                                "manual review is required before making a current operational-criteria claim."
                            ),
                            query=f"{current_article.identity.name} {destination}",
                            recommended_interface="load_administrative_rule_context",
                        )
                    )
                    current_article = None
                    break
                if followups_remaining <= 0:
                    append_moved_administrative_rule_destination_lookup_gap(
                        NoResultError("Moved administrative-rule article chain exceeded follow-up limit"),
                        current_article.identity,
                        destination,
                        gaps,
                        deferred,
                    )
                    current_article = None
                    break
                followups_remaining -= 1
                try:
                    destination_rule = self.get_administrative_rule(
                        current_article.identity,
                        articles=[destination],
                        include_metadata=include_metadata,
                    )
                except MolegApiError as exc:
                    append_moved_administrative_rule_destination_lookup_gap(
                        exc,
                        current_article.identity,
                        destination,
                        gaps,
                        deferred,
                    )
                    current_article = None
                    break

                destination_article = destination_rule.articles[0]
                loaded_articles.append(destination_article)
                if destination_article.article:
                    seen_articles.add(destination_article.article)
                current_article = destination_article
                if current_article.is_deleted:
                    append_deleted_administrative_rule_article_gap(
                        current_article,
                        gaps,
                        source_notes,
                    )
                    current_article = None
                    break

            if current_article and current_article.moved_to:
                current_article = None

            if requested.moved_to and not follow_moved:
                append_moved_administrative_rule_destination_deferred(
                    requested.identity,
                    requested.moved_to,
                    deferred,
                )
                current_article = None

            if current_article is not None:
                current_articles.append(current_article)

        return AdministrativeRuleContext(
            rule=rule,
            requested_articles=requested_articles,
            current_articles=current_articles,
            loaded_articles=loaded_articles,
            deferred=deferred,
            gaps=gaps,
            source_notes=source_notes,
        )

__all__ = [name for name in globals() if not name.startswith("__")]
