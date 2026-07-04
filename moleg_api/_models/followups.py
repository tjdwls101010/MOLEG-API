"""Follow-up and gap model primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class FollowUpSearch:
    """Recommended next search for the legislative-expert skill."""

    interface: str
    query: str
    reason: str
    source_type: str | None = None
    filters: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class DeferredLookup:
    """A bounded follow-up lookup the skill may choose to run later."""

    interface: str
    query: str
    reason: str
    source_type: str | None = None
    filters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Ambiguity:
    """Ambiguity that must not be silently resolved."""

    kind: str
    message: str
    candidates: list[Any] = field(default_factory=list)


@dataclass(frozen=True)
class ContextGap:
    """Context that should be filled by another source or human review."""

    kind: str
    reason: str
    query: str | None = None
    recommended_interface: str | None = None
