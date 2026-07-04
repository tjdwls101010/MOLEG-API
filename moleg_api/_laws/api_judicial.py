from __future__ import annotations

from .support import *

class JudicialDecisionMixin:
    def search_cases(
        self,
        query: str,
        *,
        court: CaseCourt = "all",
        court_name: str | None = None,
        search_body: bool = False,
        decided_on: str | None = None,
        case_number: str | None = None,
        display: int = 20,
    ) -> list[JudicialDecisionHit]:
        """Search ordinary court cases through the MOLEG case source.

        Use when: the skill needs Supreme Court or lower-court precedent,
        holdings, or judicial limits for a statute or issue.
        Returns: `JudicialDecisionHit` rows labeled as `case` with decision ID,
        title, court, case number, decision date, and summary metadata.
        Raises: `UnsupportedFormatError` for unsupported court filters; source
        or parse errors may also propagate. Empty search results return [].
        Related: use `get_case` for detail and
        `search_constitutional_decisions` for Constitutional Court authority.
        """
        query = require_query(query)
        params: dict[str, Any] = {
            "query": query,
            "display": display,
            "search": 2 if search_body else 1,
        }
        court_code = court_filter_code(court)
        if court_code:
            params["org"] = court_code
        if court_name:
            params["curt"] = court_name
        if decided_on:
            params["date"] = compact_date(decided_on)
        if case_number:
            params["nb"] = case_number

        payload = self.source.search("prec", params)
        hits: list[JudicialDecisionHit] = []
        for row in unwrap_search_judicial_decisions(payload, "prec"):
            identity = normalize_judicial_decision_identity(
                row,
                source_type="case",
                source_target="prec",
            )
            hits.append(
                JudicialDecisionHit(
                    identity=identity,
                    raw=row,
                    follow_up=judicial_decision_hit_follow_up(identity),
                )
            )
        return hits

    def get_case(
        self,
        identifier: JudicialDecisionIdentity | JudicialDecisionHit | str,
        *,
        include_metadata: bool = True,
    ) -> JudicialDecisionText:
        """Load one ordinary court case detail.

        Use when: a selected case must be inspected for holdings, summary, full
        text, referenced statutes, or referenced cases.
        Returns: `JudicialDecisionText` labeled as `case`, optionally without
        raw metadata when the caller is budgeting context.
        Raises: `NoResultError` for missing/non-numeric source IDs and
        `UnsupportedFormatError` if a non-case identity is passed here.
        Related: call `search_cases` first; use constitutional loaders for
        `detc` Constitutional Court decisions.
        """
        identity_hint = judicial_decision_identity_from_identifier(
            identifier,
            source_type="case",
            source_target="prec",
        )
        params = judicial_decision_identity_params(identity_hint)
        payload = self.source.service("prec", params)
        raw_case = unwrap_service_payload(payload, "prec")
        text = normalize_judicial_decision_text(
            raw_case,
            source_type="case",
            source_target="prec",
        )
        if include_metadata:
            return text
        return JudicialDecisionText(
            identity=text.identity,
            holdings=text.holdings,
            summary=text.summary,
            full_text=text.full_text,
            referenced_statutes=text.referenced_statutes,
            reviewed_statutes=text.reviewed_statutes,
            referenced_cases=text.referenced_cases,
            referenced_articles=text.referenced_articles,
            reviewed_articles=text.reviewed_articles,
            text=text.text,
            raw={},
        )

    def search_constitutional_decisions(
        self,
        query: str,
        *,
        search_body: bool = False,
        decided_on: str | None = None,
        case_number: str | None = None,
        display: int = 20,
    ) -> list[JudicialDecisionHit]:
        """Search Constitutional Court decisions.

        Use when: the skill needs constitutional-risk context, reviewed
        statutes, holdings, or constitutional reasoning distinct from ordinary
        court precedent.
        Returns: `JudicialDecisionHit` rows labeled as `constitutional` with
        decision ID, case number, decision date, title, and summary metadata.
        Raises: source adapter or parse errors; no-result is an empty list.
        Related: use `get_constitutional_decision` for detail and
        `search_cases` for ordinary Supreme Court/lower-court cases.
        """
        query = require_query(query)
        params: dict[str, Any] = {
            "query": query,
            "display": display,
            "search": 2 if search_body else 1,
        }
        if decided_on:
            params["date"] = compact_date(decided_on)
        if case_number:
            params["nb"] = case_number

        payload = self.source.search("detc", params)
        hits: list[JudicialDecisionHit] = []
        for row in unwrap_search_judicial_decisions(payload, "detc"):
            identity = normalize_judicial_decision_identity(
                row,
                source_type="constitutional",
                source_target="detc",
            )
            hits.append(
                JudicialDecisionHit(
                    identity=identity,
                    raw=row,
                    follow_up=judicial_decision_hit_follow_up(identity),
                )
            )
        return hits

    def get_constitutional_decision(
        self,
        identifier: JudicialDecisionIdentity | JudicialDecisionHit | str,
        *,
        include_metadata: bool = True,
    ) -> JudicialDecisionText:
        """Load one Constitutional Court decision detail.

        Use when: a selected constitutional decision needs holdings, summary,
        full text, reviewed statutes, or referenced authority.
        Returns: `JudicialDecisionText` labeled as `constitutional`, optionally
        without raw metadata for context budgeting.
        Raises: `NoResultError` for missing/non-numeric source IDs and
        `UnsupportedFormatError` if an ordinary case identity is passed here.
        Related: call `search_constitutional_decisions` first; use `get_case`
        for ordinary judicial decisions.
        """
        # The detail endpoint keys on the internal 헌재결정례일련번호 (a pure-digit
        # serial), a different system from the 사건번호 (e.g. 2005헌마1139). When a
        # 사건번호 is passed, resolve it to the serial via search first.
        if isinstance(identifier, str) and _CONSTITUTIONAL_CASE_NUMBER_RE.match(identifier.strip()):
            case_number = identifier.strip()
            resolved = self.search_constitutional_decisions(
                case_number, case_number=case_number, display=1
            )
            if not resolved:
                raise NoResultError(
                    f"No Constitutional Court decision found for case number {case_number!r}"
                )
            identifier = resolved[0].identity
        identity_hint = judicial_decision_identity_from_identifier(
            identifier,
            source_type="constitutional",
            source_target="detc",
        )
        params = judicial_decision_identity_params(identity_hint)
        payload = self.source.service("detc", params)
        raw_decision = unwrap_service_payload(payload, "detc")
        text = normalize_judicial_decision_text(
            raw_decision,
            source_type="constitutional",
            source_target="detc",
        )
        if include_metadata:
            return text
        return JudicialDecisionText(
            identity=text.identity,
            holdings=text.holdings,
            summary=text.summary,
            full_text=text.full_text,
            referenced_statutes=text.referenced_statutes,
            reviewed_statutes=text.reviewed_statutes,
            referenced_cases=text.referenced_cases,
            referenced_articles=text.referenced_articles,
            reviewed_articles=text.reviewed_articles,
            text=text.text,
            raw={},
        )

__all__ = [name for name in globals() if not name.startswith("__")]
