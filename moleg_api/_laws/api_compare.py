from __future__ import annotations

from .support import *

class LawCompareMixin:
    def compare_law_versions(
        self,
        law_identifier: LawIdentity | LawHit | str,
        *,
        before: str | None = None,
        after: str | None = None,
        article: str | int | None = None,
    ) -> LawDiff:
        """Load MOLEG before/after text rows for one statute.

        Use when: the skill needs the source `oldAndNew` comparison surface for
        a candidate law or article. The current implementation rejects arbitrary
        before/after dates because the source does not support that window.
        Returns: `LawDiff` with before and after identities when the source
        exposes them and normalized changed article text.
        Raises: `UnsupportedFormatError` for arbitrary date-window arguments;
        `NoResultError` when the source returns no comparable changes, plus
        source/parse errors for unusable payloads.
        Related: use `trace_law_history` to choose dates or amendment events;
        use `get_law`/`get_article` for current text.
        """
        if before is not None or after is not None:
            raise UnsupportedFormatError(
                "Arbitrary two-date comparison is not supported by law.go.kr oldAndNew; "
                "call compare_law_versions() without before/after to load the source-supplied "
                "before/after pair."
            )

        identity = identity_from_identifier(law_identifier, basis="effective")
        params = identity_params(identity, as_of=None, basis="effective")
        payload = self.source.service("oldAndNew", params)
        raw_diff = unwrap_service_payload(payload, "oldAndNew")
        before_identity = maybe_identity(raw_diff.get("구조문_기본정보"), basis="promulgated")
        after_identity = maybe_identity(raw_diff.get("신조문_기본정보"), basis="effective")
        changes = normalize_diff_changes(raw_diff, article=article)
        if not changes:
            raise NoResultError("No before/after law changes found")
        return LawDiff(
            identity=after_identity or before_identity or identity,
            before_identity=before_identity,
            after_identity=after_identity,
            changes=changes,
            raw=raw_diff,
        )

__all__ = [name for name in globals() if not name.startswith("__")]
