from __future__ import annotations

from .support import *

class LawStructureMixin:
    def find_delegated_rules(
        self,
        law_identifier: LawIdentity | LawHit | str,
        *,
        article: str | int | None = None,
    ) -> DelegationGraph:
        """Find delegated lower-rule context for a statute.

        Use when: statute text may delegate details to enforcement decrees,
        enforcement rules, notices, or administrative rules.
        Returns: a `DelegationGraph` rooted at the law identity with normalized
        delegated-rule rows, optionally filtered by source article.
        Raises: `NoResultError` when no delegated rows remain after filtering,
        plus source/parse errors for unusable source data.
        Related: use `search_administrative_rules` and
        `get_administrative_rule` to search or load the lower rules themselves.
        """
        identity = identity_from_identifier(law_identifier, basis="effective")
        params = versioned_law_identity_params(identity)
        payload = self.source.service("lsDelegated", params)
        raw_delegation = unwrap_service_payload(payload, "lsDelegated")
        root_identity = maybe_identity(raw_delegation.get("법령정보"), basis="effective") or identity
        root_identity = self._resolve_identity_name(root_identity)
        rules = normalize_delegated_rules(raw_delegation)
        if article is not None:
            wanted = article_label_for_filter(article)
            rules = [rule for rule in rules if rule.source_article == wanted]
        if not rules:
            raise NoResultError("No delegated rules found")
        return DelegationGraph(identity=root_identity, rules=rules, raw=raw_delegation)

    def get_law_structure(
        self,
        law_identifier: LawIdentity | LawHit | str,
        *,
        depth: int = 0,
    ) -> LawStructure:
        """Load the MOLEG `lsStmd` structural hierarchy for one law.

        Use when: the skill needs the broader 법률 -> 시행령 / 시행규칙 /
        행정규칙 hierarchy around a statute, not article-level delegation text.
        Returns: `LawStructure` with normalized law and administrative-rule
        nodes, preserving nested children up to the requested depth.
        Raises: `UnsupportedFormatError` for negative depth, `NoResultError`
        for an empty hierarchy, and parse/source errors for unusable payloads.
        Related: use `find_delegated_rules` for article-level delegation
        relationships; `lsStmd` does not provide source-article links.
        """
        if depth < 0:
            raise UnsupportedFormatError("Law structure depth must be 0 or greater")
        identity = identity_from_identifier(law_identifier, basis="effective")
        params = versioned_law_identity_params(identity)
        payload = self.source.service("lsStmd", params)
        raw_structure = unwrap_service_payload(payload, "lsStmd")
        structure = normalize_law_structure(raw_structure, max_depth=depth)
        if not structure.instruments:
            raise NoResultError("No law structure instruments found")
        return structure

__all__ = [name for name in globals() if not name.startswith("__")]
