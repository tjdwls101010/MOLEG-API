from __future__ import annotations

from .foundation import *
from .config import *

def delegated_criteria_source_match_state(
    rule: AdministrativeRuleText,
    scope: dict[str, set[str]],
) -> tuple[str, str]:
    references = administrative_rule_source_references(rule)
    if not references:
        return ("unverified", "missing source reference")
    matching_law_refs = [
        reference
        for reference in references
        if source_law_matches_scope(reference, scope)
    ]
    if not matching_law_refs:
        return ("mismatch", administrative_rule_source_reference_label(references))
    if not scope["articles"]:
        return ("matched", administrative_rule_source_reference_label(matching_law_refs))
    article_refs = [
        reference
        for reference in matching_law_refs
        if reference["article"]
    ]
    if not article_refs:
        return ("unverified", administrative_rule_source_reference_label(matching_law_refs))
    if any(
        articles_overlap(reference["article"], target_article)
        for reference in article_refs
        for target_article in scope["articles"]
    ):
        return ("matched", administrative_rule_source_reference_label(article_refs))
    return ("mismatch", administrative_rule_source_reference_label(article_refs))


def delegated_criteria_annex_source_match_state(
    annex: AnnexFormText,
    scope: dict[str, set[str]],
) -> tuple[str, str]:
    reference = annex_form_source_reference(annex.identity)
    if not annex_form_has_related_source_reference(reference):
        return ("unverified", "missing attached-material source reference")
    source_label = annex_form_source_reference_label(reference)
    if annex.identity.source_type == "law":
        if annex_law_reference_matches_scope(reference, scope):
            return ("matched", source_label)
        return ("mismatch", source_label)
    if annex.identity.source_type == "administrative_rule":
        if not (
            scope["administrative_rule_names"]
            or scope["administrative_rule_ids"]
            or scope["administrative_rule_serial_ids"]
        ):
            return ("unverified", source_label)
        if annex_administrative_rule_reference_matches_scope(reference, scope):
            return ("matched", source_label)
        return ("mismatch", source_label)
    return ("unverified", source_label)


def annex_form_source_reference(identity: AnnexFormIdentity) -> dict[str, str | None]:
    return {
        "source_type": identity.source_type,
        "related_name": identity.related_name,
        "related_id": identity.related_id,
        "related_serial_id": identity.related_serial_id,
    }


def annex_form_has_related_source_reference(reference: dict[str, str | None]) -> bool:
    return bool(
        reference["related_name"]
        or reference["related_id"]
        or reference["related_serial_id"]
    )


def annex_law_reference_matches_scope(
    reference: dict[str, str | None],
    scope: dict[str, set[str]],
) -> bool:
    return bool(
        (reference["related_id"] and reference["related_id"] in scope["law_ids"])
        or (
            reference["related_serial_id"]
            and reference["related_serial_id"] in scope["law_msts"]
        )
        or (reference["related_name"] and reference["related_name"] in scope["law_names"])
    )


def annex_administrative_rule_reference_matches_scope(
    reference: dict[str, str | None],
    scope: dict[str, set[str]],
) -> bool:
    return bool(
        (
            reference["related_id"]
            and reference["related_id"] in scope["administrative_rule_ids"]
        )
        or (
            reference["related_serial_id"]
            and reference["related_serial_id"] in scope["administrative_rule_serial_ids"]
        )
        or (
            reference["related_name"]
            and reference["related_name"] in scope["administrative_rule_names"]
        )
    )


def annex_form_source_reference_label(reference: dict[str, str | None]) -> str:
    parts = [
        value
        for value in (
            reference["source_type"],
            reference["related_name"],
            reference["related_id"],
            reference["related_serial_id"],
        )
        if value
    ]
    return " ".join(parts) if parts else "missing source reference"


def administrative_rule_source_references(rule: AdministrativeRuleText) -> list[dict[str, str | None]]:
    references: list[dict[str, str | None]] = []
    raw_references = [
        {
            "law_id": rule.identity.source_law_id,
            "law_name": rule.identity.source_law_name,
            "article": rule.identity.source_article,
        },
        *[
            {
                "law_id": article.source_law_id,
                "law_name": article.source_law_name,
                "article": article.source_article,
            }
            for article in rule.articles
        ],
    ]
    seen: set[tuple[str | None, str | None, str | None]] = set()
    for reference in raw_references:
        if not any(reference.values()):
            continue
        normalized = {
            "law_id": reference["law_id"],
            "law_name": reference["law_name"],
            "article": comparable_article_label(reference["article"]),
        }
        key = (normalized["law_id"], normalized["law_name"], normalized["article"])
        if key in seen:
            continue
        seen.add(key)
        references.append(normalized)
    return references


def source_law_matches_scope(
    reference: dict[str, str | None],
    scope: dict[str, set[str]],
) -> bool:
    return bool(
        (reference["law_id"] and reference["law_id"] in scope["law_ids"])
        or (reference["law_name"] and reference["law_name"] in scope["law_names"])
    )


def administrative_rule_source_reference_label(
    references: list[dict[str, str | None]],
) -> str:
    return ", ".join(
        " ".join(
            part
            for part in (
                reference["law_name"] or reference["law_id"] or "unknown law",
                reference["article"],
            )
            if part
        )
        for reference in references
    )


def comparable_article_label(value: Any) -> str:
    if value in (None, ""):
        return ""
    return re.sub(r"\s+", "", article_label_for_filter(value))


def articles_overlap(first: str | None, second: str | None) -> bool:
    left = comparable_article_label(first)
    right = comparable_article_label(second)
    if not left or not right:
        return False
    return (
        left == right
        or (left.startswith(right) and left[len(right):].startswith("제"))
        or (right.startswith(left) and right[len(left):].startswith("제"))
    )

from .validation import *
from .annex_tables import *
from .identity_params import *
from .admin_scope import *
from .temporal_gaps import *
from .delegated_scope import *
from .article_gaps import *
from .history_identity import *
from .authority_sources import *
from .candidates import *
from .followup_searches import *
from .followup_hits import *
from .limits_intents import *
from .authority_article_gaps import *
from .authority_temporal_gaps import *
from .authority_temporal_filters import *
from .followup_basic import *
from .followup_identities import *
from .bridge import *
from .requested_load_gaps import *
from .context_load_gaps import *
from .ranking import *

__all__ = [name for name in globals() if not name.startswith("__")]
