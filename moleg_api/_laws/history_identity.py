from __future__ import annotations

from .foundation import *
from .config import *

def history_row_matches_identity(row: dict[str, Any], identity: LawIdentity) -> bool:
    row_name = str(row.get("법령명한글") or row.get("법령명") or "")
    if row_name == identity.name:
        return True

    row_ministry = str(row.get("소관부처명") or row.get("소관부처") or "")
    row_law_type = str(row.get("법령구분명") or row.get("법령종류") or "")
    return bool(
        identity.ministry
        and identity.law_type
        and row_ministry == identity.ministry
        and row_law_type == identity.law_type
    )


def dedupe_identities(identities: list[LawIdentity]) -> list[LawIdentity]:
    seen: set[tuple[str | None, str | None, str, str | None, str | None]] = set()
    unique: list[LawIdentity] = []
    for identity in identities:
        key = (
            identity.law_id,
            identity.mst,
            identity.name,
            identity.promulgation_number,
            identity.promulgation_date,
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(identity)
    return unique


def article_payload_row(raw_article: dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw_article.get("조문"), dict):
        article = raw_article["조문"]
        article_units = article.get("조문단위")
        if isinstance(article_units, list):
            for row in article_units:
                if isinstance(row, dict) and row.get("조문내용"):
                    return row
            for row in article_units:
                if isinstance(row, dict):
                    return row
        if isinstance(article.get("조문단위"), dict):
            return article["조문단위"]
        return article
    if isinstance(raw_article.get("조문단위"), dict):
        return raw_article["조문단위"]
    return raw_article


def maybe_identity(row: Any, *, basis: Basis) -> LawIdentity | None:
    if not isinstance(row, dict):
        return None
    try:
        return normalize_law_identity(row, basis=basis)
    except Exception:
        return None


def administrative_rule_identity_from_identifier(
    identifier: AdministrativeRuleIdentity | AdministrativeRuleHit | str,
) -> AdministrativeRuleIdentity:
    if isinstance(identifier, AdministrativeRuleHit):
        return identifier.identity
    if isinstance(identifier, AdministrativeRuleIdentity):
        return identifier
    text = str(identifier).strip()
    if not text:
        raise NoResultError("Administrative-rule identifier is required")
    if text.isdigit():
        return AdministrativeRuleIdentity(serial_id=text, name=text)
    return AdministrativeRuleIdentity(serial_id=None, name=text)


def administrative_rule_identity_params(identity: AdministrativeRuleIdentity) -> dict[str, Any]:
    if identity.serial_id:
        return {"ID": identity.serial_id}
    if identity.rule_id:
        return {"LID": identity.rule_id}
    if identity.name:
        return {"LM": identity.name}
    raise NoResultError("Administrative-rule identity has neither ID, LID, nor exact name")


def article_label_for_filter(article: str | int) -> str:
    if isinstance(article, int):
        return f"제{article}조"
    text = str(article).strip()
    if text.startswith("제"):
        return text
    if re.fullmatch(r"\d{6}", text):
        main = int(text[:4])
        branch = int(text[4:])
        return f"제{main}조의{branch}" if branch else f"제{main}조"
    match = re.fullmatch(r"(\d+)\s*조(?:\s*의\s*(\d+))?", text)
    if match:
        main = int(match.group(1))
        branch = int(match.group(2) or 0)
        return f"제{main}조의{branch}" if branch else f"제{main}조"
    if text.isdigit():
        return f"제{int(text)}조"
    return text

from .validation import *
from .annex_tables import *
from .identity_params import *
from .admin_scope import *
from .temporal_gaps import *
from .delegated_scope import *
from .source_matching import *
from .article_gaps import *
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
