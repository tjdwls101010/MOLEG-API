from __future__ import annotations

from .support import *

class LawTocMixin:
    """Builds a statute's article map without its article text.

    law.go.kr has no table-of-contents endpoint; the map is derived from the same
    article list `get_law` already loads. So this costs one identical fetch and
    saves the caller from carrying the text — a full 개인정보 보호법 is ~174,000
    characters, of which the map is under 4%.
    """

    def get_law_toc(
        self,
        law_identifier: LawIdentity | LawHit | str,
        *,
        as_of: str | None = None,
        basis: Basis = "effective",
        include_metadata: bool = False,
    ) -> LawToc:
        """List a statute's chapter headings and article titles, without text.

        Use when: the question is "what does this law cover" or "which article
        governs X" and loading every article to find out would cost more than the
        answer is worth.
        Returns: `LawToc` — heading rows in document order interleaved with
        article stubs carrying number, title, and deleted/moved status.
        Related: `get_law(articles=[...])` loads the ones you picked;
        `get_law_structure` maps *instruments* below a statute (decrees, rules),
        which is a different hierarchy from this one.
        """
        law = self.get_law(law_identifier, as_of=as_of, basis=basis, include_metadata=include_metadata)
        return LawToc(
            identity=law.identity,
            entries=[_toc_entry(article) for article in law.articles],
            article_count=sum(1 for a in law.articles if _is_article_row(a)),
            raw=law.raw if include_metadata else {},
        )


def _is_article_row(article: Any) -> bool:
    # law.go.kr threads chapter/section headings through the same article list,
    # tagged 전문 and carrying the neighbouring article's number. Counting those
    # as articles would inflate the count a caller uses to judge the load.
    return getattr(article, "article_kind", None) != "전문"


def _toc_entry(article: Any) -> LawTocEntry:
    if not _is_article_row(article):
        return LawTocEntry(
            heading=(getattr(article, "text", "") or "").strip() or None,
            entry_kind="heading",
        )
    moved_to = getattr(article, "moved_to", None)
    return LawTocEntry(
        article=getattr(article, "article", None),
        title=getattr(article, "title", None),
        entry_kind="article",
        is_deleted=bool(getattr(article, "is_deleted", False)),
        # 제0조 is the source's placeholder for "no real destination"; passing it
        # through would send a caller chasing an article that does not exist.
        moved_to=moved_to if moved_to and moved_to != "제0조" else None,
    )

__all__ = [name for name in globals() if not name.startswith("__")]
