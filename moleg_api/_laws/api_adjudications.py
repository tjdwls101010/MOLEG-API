from __future__ import annotations

from .support import *
from .adjudication_registry import appeal_spec, committee_spec

class AdjudicationMixin:
    """Committee decisions and administrative appeals.

    The oversight question this package could not answer was "did the supervising
    body actually act?" — the statute was reachable, the court ruling was
    reachable, but the disposition in between was not. A 개인정보보호위원회
    의결서 or a 조세심판원 재결 is the primary record of an agency applying the law
    it administers, and until now every one of them was outside the surface.

    Search and load are one code path across seventeen bodies because the request
    shape is identical; only the vocabulary differs, and that is normalization's
    job rather than seventeen near-copies of the same method.
    """

    def search_committee_decisions(
        self,
        query: str | None = None,
        *,
        committee: str,
        display: int = 20,
    ) -> list[AdjudicationHit]:
        """Search one committee's decisions.

        Use when: the question is whether a regulator disposed of something — a
        과징금, a 시정명령, a 인권침해 판단 — rather than what a statute says.
        Returns: `AdjudicationHit` candidates carrying the authority label. Never
        quotable; load the decision first.
        Related: `get_committee_decision` loads one;
        `search_administrative_appeals` covers 행정심판 재결 instead.
        """
        return self._search_adjudications(committee_spec(committee), query, display)

    def get_committee_decision(self, decision_id: str, *, committee: str) -> AdjudicationText:
        """Load one committee decision (주문·요지·이유·당사자)."""
        return self._load_adjudication(committee_spec(committee), decision_id)

    def search_administrative_appeals(
        self,
        query: str | None = None,
        *,
        tribunal: str = "decc",
        display: int = 20,
    ) -> list[AdjudicationHit]:
        """Search 행정심판 재결례, general or from a special tribunal.

        Use when: the question is whether someone contested an agency's
        disposition and how the review body ruled — the record of a disposition
        being tested short of court.
        Returns: `AdjudicationHit` candidates carrying the authority label.
        Related: the four special tribunals (`acr`, `adap`, `tt`, `kmst`) hold
        재결 that the general `decc` docket does not, so a 소청·조세·해양안전
        question searched only against `decc` reads as absence.
        """
        return self._search_adjudications(appeal_spec(tribunal), query, display)

    def get_administrative_appeal(self, decision_id: str, *, tribunal: str = "decc") -> AdjudicationText:
        """Load one 행정심판 재결 (주문·재결요지·이유·청구취지)."""
        return self._load_adjudication(appeal_spec(tribunal), decision_id)

    # ---- shared implementation ------------------------------------------ #

    def _search_adjudications(self, spec: dict[str, str], query: str | None, display: int) -> list[AdjudicationHit]:
        params: dict[str, Any] = {"display": display}
        if query and query.strip():
            params["query"] = query.strip()
        payload = self.source.search(spec["target"], params)
        hits: list[AdjudicationHit] = []
        for row in adjudication_rows(payload, spec["target"]):
            identity = normalize_adjudication_identity(row, spec=spec)
            if not identity.decision_id:
                continue
            hits.append(
                AdjudicationHit(
                    identity=identity,
                    follow_up=FollowUpSearch(
                        interface="get_committee_decision"
                        if spec["source_type"] == "committee_decision"
                        else "get_administrative_appeal",
                        query=identity.decision_id,
                        reason="선택한 결정문 본문 로드",
                        filters={"body": spec["code"]},
                    ),
                    raw=row,
                )
            )
        return hits

    def _load_adjudication(self, spec: dict[str, str], decision_id: str) -> AdjudicationText:
        identifier = str(decision_id or "").strip()
        if not identifier:
            raise NoResultError("결정문 일련번호가 필요하다 — search 결과의 decision_id를 넘겨라.")
        payload = self.source.service(spec["target"], {"ID": identifier})
        body = adjudication_detail(payload)
        if not body or not any(_has_content(v) for v in body.values()):
            raise NoResultError(
                f"{spec['name']}에 이 일련번호({identifier})의 결정문 본문이 없다 — "
                "search 결과의 decision_id인지, 기관 코드가 맞는지 확인하라."
            )
        identity = normalize_adjudication_identity(body, spec=spec)
        if not identity.decision_id:
            identity = replace(identity, decision_id=identifier)
        return normalize_adjudication_text(body, identity)


def _has_content(value: Any) -> bool:
    if isinstance(value, str):
        # law.go.kr returns the literal string "null" for absent fields on several
        # of these targets, so an all-"null" body is an empty record, not a hit.
        return bool(value.strip()) and value.strip() != "null"
    return value not in (None, [], {})

__all__ = [name for name in globals() if not name.startswith("__")]
