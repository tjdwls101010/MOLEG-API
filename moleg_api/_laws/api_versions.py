from __future__ import annotations

from .support import *

class LawVersionMixin:
    def _search_full_law_history(self, identity: LawIdentity) -> dict[str, Any]:
        # The lsHistory list search matches on the law *name*; a bare law_id
        # identity carries the id as its name, which returns a "no results"
        # table and a parse failure. Recover the real name first.
        identity = self._resolve_identity_name(identity)
        rows: list[dict[str, Any]] = []
        page = 1
        pages_seen = 0
        total_count: int | None = None
        while page <= LAW_HISTORY_HTML_MAX_PAGES:
            params = {
                "query": identity.name,
                "display": LAW_HISTORY_HTML_DISPLAY,
                "page": page,
            }
            html = self.source.search_html("lsHistory", params)
            pages_seen += 1
            page_rows = parse_law_history_html(html)
            if total_count is None:
                total_count = parse_law_history_total_count(html)
            rows.extend(page_rows)
            if not page_rows:
                break
            if total_count is not None and len(rows) >= total_count:
                break
            page += 1

        matched_rows = [row for row in rows if history_row_matches_identity(row, identity)]
        if not matched_rows and rows:
            raise NoResultError(
                "No full law history rows matched the requested law identity; "
                "try an article/date_range history query or inspect lsHistory candidates manually"
            )
        return {
            "lsHistory": matched_rows,
            "source_target": "lsHistory",
            "source_total_count": total_count,
            "source_rows_seen": len(rows),
            "source_pages_seen": pages_seen,
        }

    # ---- version resolution (historical / effective-date loading) --------- #
    #
    # law.go.kr's ID+efYd detail lookups do not select a historical version —
    # they silently return current text. The version-specific master sequence
    # (MST, 법령일련번호) is the only key that pins a version. These helpers list
    # a statute's version rows (eflaw) and resolve the version in force at a past
    # date, so the loaders below can reload the correct version by MST.

    def _law_version_rows(self, identity: LawIdentity) -> list[dict[str, Any]]:
        """List a statute's effective-date version rows via the `eflaw` catalog.

        Each row carries 법령일련번호(=MST), 시행일자, 공포번호, and 법령명한글.
        Used to resolve a historical version MST and to recover a real law name
        from a bare law_id. Returns an empty list on any lookup failure.
        """
        if identity.law_id:
            params: dict[str, Any] = {"LID": identity.law_id, "display": "100"}
        elif identity.name and not str(identity.name).isdigit():
            params = {"query": identity.name, "display": "100"}
        else:
            return []
        try:
            payload = self.source.search("eflaw", params)
        except MolegApiError:
            return []
        search = payload.get("LawSearch", {}) if isinstance(payload, dict) else {}
        raw = search.get("law", []) if isinstance(search, dict) else []
        if isinstance(raw, dict):
            raw = [raw]
        rows: list[dict[str, Any]] = []
        for row in raw:
            if not isinstance(row, dict):
                continue
            row_id = str(row.get("법령ID") or "")
            if identity.law_id and row_id and row_id != str(identity.law_id):
                continue
            rows.append(row)
        return rows

    def _resolve_version_mst(self, identity: LawIdentity, as_of: str) -> str | None:
        """MST of the version in force at `as_of` (latest 시행일 ≤ as_of)."""
        target = compact_date(as_of)
        best: tuple[str, str, str] | None = None
        for row in self._law_version_rows(identity):
            mst = row.get("법령일련번호")
            effective = compact_date(str(row.get("시행일자") or ""))
            if not mst or not effective or effective > target:
                continue
            key = (effective, str(row.get("공포번호") or ""), str(mst))
            if best is None or key > best:
                best = key
        return best[2] if best else None

    def _law_name_for(self, identity: LawIdentity) -> str | None:
        """Recover the real statute name for a bare-law_id identity."""
        for row in self._law_version_rows(identity):
            name = row.get("법령명한글") or row.get("법령명")
            if name:
                return str(name)
        return None

    def _resolve_identity_name(self, identity: LawIdentity) -> LawIdentity:
        """Backfill the real statute name when an identity still carries a bare
        law_id as its name (degrades to the input unchanged on lookup failure)."""
        if not identity.name or str(identity.name).isdigit():
            resolved_name = self._law_name_for(identity)
            if resolved_name:
                return replace(identity, name=resolved_name)
        return identity

    def _load_versioned_law_raw(self, identity: LawIdentity, mst: str) -> dict[str, Any]:
        """Load one statute version's raw payload by MST (promulgated detail)."""
        versioned = replace(identity, mst=mst)
        payload = self.source.service("law", versioned_law_identity_params(versioned))
        return unwrap_service_payload(payload, "law")

    def _load_versioned_article(
        self, identity: LawIdentity, mst: str, article: str | int, *, basis: Basis
    ) -> ArticleText | None:
        """Load one article of a specific version by MST (promulgated article)."""
        versioned = replace(identity, mst=mst)
        params = versioned_law_identity_params(versioned)
        params["JO"] = format_article_jo(article)
        payload = self.source.service("lawjosub", params)
        raw_article = unwrap_service_payload(payload, "lawjosub")
        if "기본정보" in raw_article:
            article_identity = normalize_law_identity(raw_article, basis=basis)
        else:
            article_identity = versioned
        normalized = normalize_article(article_payload_row(raw_article), article_identity)
        if normalized is None:
            return None
        requested_article = article_label_for_filter(article)
        if requested_article.startswith(f"{normalized.article}의"):
            normalized = replace(normalized, article=requested_article)
        return normalized

__all__ = [name for name in globals() if not name.startswith("__")]
