from __future__ import annotations

from .support import *

class AnnexMixin:
    def search_administrative_rules(
        self,
        query: str,
        *,
        ministry: str | None = None,
        rule_type: str | None = None,
        issued_on: str | None = None,
        include_history: bool = False,
        display: int = 20,
    ) -> list[AdministrativeRuleHit]:
        """Search notices, directives, established rules, and other admin rules.

        Use when: delegated or practical execution criteria may live outside
        statute text, especially in ministry-level administrative rules.
        Returns: a list of `AdministrativeRuleHit` values with normalized
        serial ID, rule ID, issuing/effective dates, ministry, and status.
        Raises: source adapter or parse errors; no-result is an empty list.
        Related: use `find_delegated_rules` from a known statute and
        `get_administrative_rule` to load a selected rule body.
        """
        query = require_query(query)
        params: dict[str, Any] = {
            "query": query,
            "display": display,
            "nw": 2 if include_history else 1,
        }
        if ministry:
            params["org"] = ministry
        if rule_type:
            params["knd"] = rule_type
        if issued_on:
            params["date"] = compact_date(issued_on)

        payload = self.source.search("admrul", params)
        hits: list[AdministrativeRuleHit] = []
        for row in unwrap_search_administrative_rules(payload):
            identity = normalize_administrative_rule_identity(row)
            hits.append(
                AdministrativeRuleHit(
                    identity=identity,
                    raw=row,
                    follow_up=administrative_rule_hit_follow_up(identity),
                )
            )
        return hits

    def search_annex_forms(
        self,
        query: str,
        *,
        source: AnnexFormSource = "law",
        search_scope: AnnexSearchScope = "title",
        annex_type: AnnexType | None = None,
        ministry: str | None = None,
        display: int = 20,
    ) -> list[AnnexFormHit]:
        """Search statute or administrative-rule annex/form candidates.

        Use when: operative content may be in 별표ㆍ서식 material such as
        tables, thresholds, criteria, amounts, or required forms.
        Returns: a list of `AnnexFormHit` values with source law/rule identity,
        annex title/number/type, dates, ministry, and file/detail links.
        Raises: `UnsupportedFormatError` for unsupported source, scope, or
        annex type values; source/parse errors may also propagate.
        Related: call `get_annex_form_body` for a selected candidate before
        treating attached material as inspected.
        """
        query = require_query(query)
        source_type = annex_source_type(source)
        target = annex_target_for(source_type)
        params: dict[str, Any] = {
            "query": query,
            "display": display,
            "search": annex_search_scope(search_scope),
        }
        if annex_type:
            params["knd"] = annex_type_code(source_type, annex_type)
        if ministry:
            params["org"] = ministry

        payload = self.source.search(target, params)
        hits: list[AnnexFormHit] = []
        for row in unwrap_target_rows(payload, target):
            identity = normalize_annex_form_identity(
                row,
                source_type=source_type,
                source_target=target,
            )
            hits.append(
                AnnexFormHit(
                    identity=identity,
                    raw=row,
                    follow_up=annex_form_hit_follow_up(identity),
                )
            )
        return hits

    def get_annex_form_body(
        self,
        identifier: AnnexFormIdentity | AnnexFormHit | str,
        *,
        source: AnnexFormSource = "law",
        title: str | None = None,
        include_metadata: bool = True,
        attempt_structuring: bool = True,
    ) -> AnnexFormText:
        """Load text for one selected law or administrative-rule annex/form.

        Use when: an annex/form candidate may carry operative criteria and the
        skill needs the body text before citing or reasoning from it.
        Returns: `AnnexFormText` with text/plain content, source identity,
        extraction method, confidence, and optional metadata.
        Raises: `NoResultError` when the identity lacks a source ID or returns
        empty text; `UnsupportedFormatError` for unsupported source targets.
        Related: call `search_annex_forms` first; direct HWP/PDF parsing is
        outside this interface.
        """
        identity = annex_form_identity_from_identifier(identifier, source=source, title=title)
        if not identity.annex_id:
            raise NoResultError("Annex/form identity has no source ID")
        try:
            endpoint = ANNEX_FORM_TEXT_ENDPOINTS[identity.source_target]
        except KeyError as exc:
            raise UnsupportedFormatError(
                f"{identity.source_target} annex/form body loading is not supported"
            ) from exc

        text = self.source.post_text(
            endpoint,
            {
                "bylSeq": identity.annex_id,
                "title": identity.title,
                "mode": "0",
            },
        )
        if not text.strip():
            raise NoResultError("No annex/form body text returned")
        # A bare-id identity keeps the numeric id as its title (and no
        # related_name/annex_type); recover the authoritative label from the
        # body header before deciding on structuring or returning the identity.
        identity = enrich_annex_identity_from_body(identity, text)
        structured_data = (
            structure_annex_form_text(text, identity)
            if attempt_structuring and annex_form_is_table_like(identity)
            else None
        )
        return AnnexFormText(
            identity=identity,
            text=text,
            file_type="text/plain",
            extraction_method=endpoint,
            extraction_confidence="high",
            structured_data=structured_data,
            raw={
                "endpoint": endpoint,
                "source_target": identity.source_target,
                "annex_id": identity.annex_id,
            }
            if include_metadata
            else {},
        )

__all__ = [name for name in globals() if not name.startswith("__")]
