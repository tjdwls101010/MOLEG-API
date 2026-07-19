from __future__ import annotations

from .support import *

class RevisionReasonMixin:
    """Loads the 「개정이유 및 주요내용」 text law.go.kr already ships but drops.

    A statute's detail response carries `법령.제개정이유.제개정이유내용` — the
    drafter's account of the problem an amendment answers — alongside
    `법령.개정문.개정문내용`, the promulgation text. Normalization discarded both,
    so the only trace of an amendment's rationale anywhere in the package was
    `HistoryEvent.revision_type`, a bare 일부개정/본조신설 label. The download was
    already paid for; only the parse was missing.
    """

    def get_revision_reason(
        self,
        law_identifier: LawIdentity | LawHit | str,
        *,
        mst: str | None = None,
        as_of: str | None = None,
        include_metadata: bool = True,
    ) -> RevisionReason:
        """Load one version's amendment rationale and promulgation text.

        Use when: the question is *why* a statute changed, not what it now says
        — the stated problem, scope, and intent behind an amendment.
        Version selection: `mst` pins an exact version (take it from
        `trace_law_history` events, whose `identity.mst` is this value); `as_of`
        picks the version in force on that date; neither selects the newest
        version on file, which is the most recent amendment even when its
        effective date has not arrived yet.
        Returns: `RevisionReason` with the reason text, the promulgation text,
        and the `mst` the text belongs to.
        Raises: `NoResultError` when the version carries neither block — common
        for older versions, where law.go.kr simply has no reason on file.
        Related: `trace_law_history` lists the versions worth asking about;
        `compare_law_versions` shows what the wording actually became.
        """
        identity = identity_from_identifier(law_identifier, basis="effective")
        resolved_mst = mst or identity.mst
        if not resolved_mst:
            resolved_mst = (
                self._resolve_version_mst(identity, as_of)
                if as_of
                else self._latest_version_mst(identity)
            )
        if not resolved_mst:
            raise NoResultError(
                "이 법령의 버전 목록을 찾지 못해 개정이유를 특정할 수 없다 — "
                "trace-law-history로 버전(mst)을 확인한 뒤 --mst로 지정하라."
            )

        raw_law = self._load_versioned_law_raw(identity, resolved_mst)
        version_identity = normalize_law_identity(raw_law, basis="effective")
        if not version_identity.mst:
            version_identity = replace(version_identity, mst=resolved_mst)

        reason = _revision_block_text(raw_law, "제개정이유", "제개정이유내용")
        promulgation = _revision_block_text(raw_law, "개정문", "개정문내용")
        if not reason and not promulgation:
            raise NoResultError(
                f"이 버전(mst={resolved_mst})에는 개정이유·공포문이 실려 있지 않다 — "
                "오래된 버전은 원천에 없는 경우가 많다."
            )

        return RevisionReason(
            identity=version_identity,
            mst=resolved_mst,
            reason=reason,
            promulgation_text=promulgation,
            raw=raw_law if include_metadata else {},
        )

    def _latest_version_mst(self, identity: LawIdentity) -> str | None:
        """MST of the newest version on file, by 시행일.

        Deliberately not "the version in force today": the newest amendment is
        often promulgated with a future effective date, and its reason is exactly
        the one a reader asking "왜 바뀌었나" wants. The temporal flag on the
        envelope is what keeps that from being misread as current law.
        """
        best: tuple[str, str, str] | None = None
        for row in self._law_version_rows(identity):
            row_mst = row.get("법령일련번호")
            effective = compact_date(str(row.get("시행일자") or ""))
            if not row_mst or not effective:
                continue
            key = (effective, str(row.get("공포번호") or ""), str(row_mst))
            if best is None or key > best:
                best = key
        return best[2] if best else None


def _revision_block_text(raw_law: dict[str, Any], block: str, field_name: str) -> str | None:
    """Flatten law.go.kr's nested string arrays into one readable block.

    The JSON form nests two levels deep (a list of paragraph lists) and the XML
    form wraps the same content in CDATA. Blank entries are dropped rather than
    joined, so an empty block reads as absent instead of as a run of newlines.
    """
    container = raw_law.get(block)
    if not isinstance(container, dict):
        return None
    lines = _flatten_strings(container.get(field_name))
    return "\n".join(lines) or None


def _flatten_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, (list, tuple)):
        out: list[str] = []
        for item in value:
            out.extend(_flatten_strings(item))
        return out
    return []

__all__ = [name for name in globals() if not name.startswith("__")]
