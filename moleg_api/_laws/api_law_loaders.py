from __future__ import annotations

from .support import *

class LawLoadersMixin:
    def get_law(
        self,
        identifier: LawIdentity | LawHit | str,
        *,
        as_of: str | None = None,
        basis: Basis = "effective",
        articles: list[str | int] | None = None,
        include_metadata: bool = True,
    ) -> LawText:
        """Load normalized statute text for one law identity.

        Use when: the skill already has a plausible statute identity and needs
        the effective or promulgated text behind it. Pass a `LawIdentity` or
        `LawHit` when possible; a bare string should be a source identifier.
        Returns: `LawText` with a normalized identity, extracted articles,
        supplementary provisions when present, and optionally preserved raw
        metadata for audit.
        Raises: `NoResultError` for unusable identifiers and source/parse
        errors when law.go.kr cannot provide normalizable statute text.
        Related: use `get_article` for precise article lookup and
        `search_laws` first when the identity is still uncertain.
        """
        if articles is not None and not articles:
            raise NoResultError("articles must contain at least one article when provided")

        identity_hint = identity_from_identifier(identifier, basis=basis)
        target = target_for(basis, "detail")
        params = law_text_identity_params(identity_hint, as_of=as_of, basis=basis)

        try:
            payload = self.source.service(target, params)
            raw_law = unwrap_service_payload(payload, target)
        except (NoResultError, ParseFailureError):
            # ID+efYd cannot select a past version — it returns nothing for a
            # non-current effective date. Load the version directly by MST: an
            # explicit historical MST (eflaw rejects MST without an exact efYd),
            # or the version in force at as_of. Only reached when the fast path
            # failed, so current-law loads keep their single source call.
            mst = identity_hint.mst or (self._resolve_version_mst(identity_hint, as_of) if as_of else None)
            if not mst:
                # No version in force at as_of. If the law has version rows but
                # all postdate the request, the requested date is before
                # law.go.kr's consolidated coverage for this law — a permanent
                # coverage-floor condition, not a transient parse failure.
                if as_of:
                    effs = sorted(
                        e
                        for e in (
                            compact_date(str(row.get("시행일자") or ""))
                            for row in self._law_version_rows(identity_hint)
                        )
                        if e and len(e) == 8
                    )
                    if effs and compact_date(as_of) < effs[0]:
                        raise AsOfBeforeCoverageError(
                            f"요청 시점({compact_date(as_of)})은 law.go.kr이 이 법령의 통합본으로 제공하는 "
                            f"가장 이른 시행일({effs[0]})보다 앞선다 — 그 이전 시점 본문은 통합본으로 제공되지 않는다.",
                            law_id=identity_hint.law_id,
                            earliest_available=effs[0],
                        )
                raise
            raw_law = self._load_versioned_law_raw(identity_hint, mst)
        identity = normalize_law_identity(raw_law, basis=basis)
        law_articles = extract_articles(raw_law, identity)
        supplementary_provisions = extract_supplementary_provisions(raw_law, "law")
        if articles is not None:
            law_articles = select_requested_articles(law_articles, articles)
        return LawText(
            identity=identity,
            articles=law_articles,
            supplementary_provisions=supplementary_provisions,
            raw=raw_law if include_metadata else {},
        )

    def get_article(
        self,
        law_identifier: LawIdentity | LawHit | str,
        article: str | int,
        *,
        as_of: str | None = None,
        basis: Basis = "effective",
    ) -> ArticleText:
        """Load one article by human article notation.

        Use when: the skill needs a specific provision such as `제10조의2`
        without formatting MOLEG's six-digit `JO` value itself.
        Returns: `ArticleText` with the article label, title, text, effective
        date when available, and normalized source identity.
        Raises: `NoResultError` when the article text is absent, plus source or
        parse errors for invalid source payloads.
        Related: use `get_law` for whole-statute context and
        `trace_law_history(article=...)` for article-level history events.
        """
        identity = identity_from_identifier(law_identifier, basis=basis)
        target = target_for(basis, "article")
        params = identity_params(identity, as_of=as_of, basis=basis)
        params["JO"] = format_article_jo(article)

        payload = self.source.service(target, params)
        raw_article = unwrap_service_payload(payload, target)
        if "기본정보" in raw_article:
            article_identity = normalize_law_identity(raw_article, basis=basis)
        else:
            article_identity = identity
        article_row = article_payload_row(raw_article)
        normalized = normalize_article(article_row, article_identity)
        if normalized is None:
            raise NoResultError(f"No article text found for {article}")
        requested_article = article_label_for_filter(article)
        if requested_article.startswith(f"{normalized.article}의"):
            normalized = replace(normalized, article=requested_article)
        # Historical correction: ID+efYd silently returns the current article for
        # a past date. If a past as_of yielded an article effective later than
        # requested, reload the version in force at as_of by MST.
        if as_of and not identity.mst and normalized.effective_date:
            got = compact_date(normalized.effective_date)
            want = compact_date(as_of)
            if got and want and got > want:
                mst = self._resolve_version_mst(identity, as_of)
                corrected = (
                    self._load_versioned_article(identity, mst, article, basis=basis)
                    if mst
                    else None
                )
                if corrected is not None:
                    normalized = corrected
        return normalized

__all__ = [name for name in globals() if not name.startswith("__")]
