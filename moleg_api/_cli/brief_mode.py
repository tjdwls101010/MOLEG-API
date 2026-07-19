from __future__ import annotations

from dataclasses import replace
from typing import Any

# A decision detail ships the same reasoning twice over: `text` and `full_text`
# are different sections of the document, not duplicates, but between them they
# are ~82% of the payload (29,321 of 35,866 characters on decision 193332). The
# structured extract — 판시사항, 결정요지, referenced authority — is what a reader
# needs to decide whether the decision is even on point. Loading 82,700 bytes to
# find out costs more than the answer is worth.
#
# Brief mode drops the full-body fields and keeps the extract. It does *not* drop
# `summary`: 요지 is the entire reason to ask for a brief, and cutting it would
# shrink the payload further while removing the only thing brief mode is for.
_BRIEF_DROPPED_FIELDS = ("text", "full_text")


def to_brief(result: Any) -> Any:
    """Blank the full-body fields on a loaded authority document.

    Returns the same type rather than a narrower one, so the model, the kind, and
    every consumer's field access stay valid — the difference is signalled on the
    envelope, not encoded in a second shape of the same thing.
    """
    blanked = {}
    for name in _BRIEF_DROPPED_FIELDS:
        if not hasattr(result, name):
            continue
        current = getattr(result, name)
        blanked[name] = "" if isinstance(current, str) else None
    return replace(result, **blanked) if blanked else result


def brief_dropped(result: Any) -> list[str]:
    """Which full-body fields this document actually carried, for the flag.

    Reported rather than assumed: a decision with no `full_text` on file must not
    claim brief mode withheld one, or the caller will go looking for a section
    that never existed.
    """
    return [
        name
        for name in _BRIEF_DROPPED_FIELDS
        if getattr(result, name, None)
    ]

__all__ = [name for name in globals() if not name.startswith("__")]
