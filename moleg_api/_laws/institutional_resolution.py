from __future__ import annotations

from .support import *


def resolve_institutional_statute(
    api: Any,
    identifier: str | LawIdentity | LawHit,
    *,
    display: int,
) -> InstitutionalStatuteResolution:
    label = statute_identifier_label(identifier)
    if isinstance(identifier, LawHit):
        return InstitutionalStatuteResolution(label, identifier.identity, [identifier.identity])
    if isinstance(identifier, LawIdentity):
        return InstitutionalStatuteResolution(label, identifier, [identifier])

    text = label.strip()
    if not text:
        return InstitutionalStatuteResolution(
            label,
            None,
            [],
            error_kind="no_result",
            message="Blank statute identifier cannot be resolved",
        )
    if text.isdigit():
        identity = LawIdentity(law_id=text, name=text, basis="effective")
        return InstitutionalStatuteResolution(label, identity, [identity])

    hits = api.search_laws(text, display=display)
    identities = dedupe_identities([hit.identity for hit in hits])
    if not identities:
        return InstitutionalStatuteResolution(
            label,
            None,
            [],
            error_kind="no_result",
            message=f"Statute '{text}' was not found",
        )

    exact = [identity for identity in identities if identity.name == text]
    if len(exact) == 1:
        return InstitutionalStatuteResolution(label, exact[0], identities)
    if len(exact) > 1:
        return InstitutionalStatuteResolution(
            label,
            None,
            exact,
            error_kind="ambiguous",
            message=f"Statute identifier '{text}' matched multiple exact law identities",
        )
    if len(identities) == 1:
        return InstitutionalStatuteResolution(label, identities[0], identities)
    return InstitutionalStatuteResolution(
        label,
        None,
        identities,
        error_kind="ambiguous",
        message=f"Statute identifier '{text}' matched multiple law identities",
    )


__all__ = [name for name in globals() if not name.startswith("__")]
