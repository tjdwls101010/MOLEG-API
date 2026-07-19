"""Committee decisions and administrative appeals — agency adjudications.

One family, not two, because the access pattern and the failure mode are the
same: search a body's docket, load one document, and do not let it be mistaken
for a court ruling. The bodies differ (개인정보보호위원회 disposes, 조세심판원
adjudicates an appeal) but the discipline a reader needs is identical, so the
authority label is a field rather than a type.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .followups import FollowUpSearch


@dataclass(frozen=True)
class AdjudicationIdentity:
    """Who decided what, and with what authority.

    `source_type` and `source_authority` are not decoration. A 위원회 결정 is an
    administrative disposition by the agency that regulates the respondent; an
    행정심판 재결 reviews another agency's disposition and can itself be overturned
    in court. Neither is precedent. Citing either as 판례 overstates what it
    settles, which is the specific error this family is most likely to invite.
    """

    decision_id: str
    body: str
    body_name: str
    source_type: str
    source_authority: str
    title: str | None = None
    case_number: str | None = None
    decided_on: str | None = None
    disposition_date: str | None = None
    agency: str | None = None
    review_agency: str | None = None
    respondent_agency: str | None = None
    decision_category: str | None = None
    detail_link: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AdjudicationHit:
    """A search candidate — an identity, never a body to quote from."""

    identity: AdjudicationIdentity
    follow_up: FollowUpSearch | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AdjudicationText:
    """One loaded decision or 재결.

    Field names are normalized across bodies that spell the same concept
    differently — 결정요지 / 재결요지 / 판단요지 / 판정요지 all land in `summary`,
    주문 in `disposition`, 이유 in `reasoning`. Without that, every consumer would
    have to learn twelve agencies' vocabularies to ask one question.
    """

    identity: AdjudicationIdentity
    disposition: str | None = None
    summary: str | None = None
    reasoning: str | None = None
    claim: str | None = None
    background: str | None = None
    applicant: str | None = None
    respondent: str | None = None
    related_laws: str | None = None
    text: str = ""
    raw: dict[str, Any] = field(default_factory=dict)
