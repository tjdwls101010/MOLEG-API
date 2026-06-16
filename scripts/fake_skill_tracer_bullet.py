"""Deterministic fake-skill tracer bullet for the pre-skill MOLEG-API gate.

This script is intentionally not a legal reasoning engine. It plays the role of
the future legislative-expert skill just far enough to prove that public
`MolegApi` methods expose source-loading context, candidates, deferred lookups,
authority labels, and WebSearch gaps across the seven consumer-readiness review
archetypes.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from moleg_api import LawIdentity, MolegApi


@dataclass(frozen=True)
class TracerScenarioResult:
    """One fake-skill scenario outcome."""

    archetype: str
    public_interfaces: list[str]
    loaded: list[str] = field(default_factory=list)
    candidates: list[str] = field(default_factory=list)
    deferred: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ScenarioSource:
    """Queue-backed source adapter for deterministic public-interface runs."""

    def __init__(
        self,
        *,
        search_payloads: list[dict[str, Any]] | None = None,
        service_payloads: list[dict[str, Any]] | None = None,
        text_payloads: list[str] | None = None,
        search_html_payloads: list[str] | None = None,
    ) -> None:
        self.search_payloads = list(search_payloads or [])
        self.service_payloads = list(service_payloads or [])
        self.text_payloads = list(text_payloads or [])
        self.search_html_payloads = list(search_html_payloads or [])
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def search(self, target: str, params: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("search", target, dict(params)))
        return self.search_payloads.pop(0)

    def service(self, target: str, params: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("service", target, dict(params)))
        return self.service_payloads.pop(0)

    def post_text(self, path: str, params: dict[str, Any]) -> str:
        self.calls.append(("post_text", path, dict(params)))
        return self.text_payloads.pop(0)

    def search_html(self, target: str, params: dict[str, Any]) -> str:
        self.calls.append(("search_html", target, dict(params)))
        return self.search_html_payloads.pop(0)


def run_fake_skill_tracer_bullet() -> list[TracerScenarioResult]:
    """Run all seven deterministic consumer-readiness archetypes."""

    return [
        _run_sanction_design(),
        _run_delegated_criteria_tracing(),
        _run_statute_evolution(),
        _run_congress_bill_bridge(),
        _run_constitutional_risk_scan(),
        _run_multi_law_concept_assembly(),
        _run_comparative_design(),
    ]


def _run_sanction_design() -> TracerScenarioResult:
    source = ScenarioSource(
        search_payloads=[
            law_search_payload("식품위생법", law_id="001900", mst="270900"),
            term_search_payload("과징금"),
            {"dlytrm": []},
            ai_article_payload("식품위생법", "001900", "75", "과징금"),
            {"aiRltLs": []},
            administrative_rule_search_payload("식품위생 분야 행정처분 기준"),
            interpretation_search_payload("900", "식품위생법 과징금 해석"),
            case_search_payload("901", "과징금 부과처분 취소"),
            constitutional_search_payload("902", "과징금 과잉금지원칙"),
            annex_search_payload("903", "과징금 산정기준", related_name="식품위생법 시행령"),
            {"admbyl": []},
        ],
        service_payloads=[
            {"lstrmRlt": []},
            {"dlytrmRlt": []},
            {"lstrmRltJo": []},
            law_text_payload("식품위생법", "001900", "270900", article="제75조", title="과징금"),
            delegation_payload("식품위생법", "식품위생법 시행령", law_id="001900"),
            interpretation_detail_payload("900", "식품위생법 과징금 해석", related_laws="식품위생법 제75조"),
            case_detail_payload("901", "과징금 부과처분 취소", referenced_statutes="식품위생법 제75조"),
            constitutional_detail_payload("902", "과징금 과잉금지원칙", reviewed_statutes="식품위생법 제75조"),
        ],
        text_payloads=[pipe_table_text()],
    )
    api = MolegApi(source)

    bundle = api.load_legal_context_bundle("식품위생법 과징금 산정기준의 의미와 위헌 위험", budget="standard")
    annex_body = api.get_annex_form_body(bundle.candidates.annex_forms[0].identity)

    return TracerScenarioResult(
        archetype="sanction_design",
        public_interfaces=["load_legal_context_bundle", "get_annex_form_body"],
        loaded=["law", "delegation", "interpretation_detail", "case_detail", "constitutional_detail", "annex_table"],
        candidates=["administrative_rule", "annex_form"],
        deferred=[item.interface for item in bundle.deferred],
        gaps=[gap.recommended_interface or gap.kind for gap in bundle.gaps],
        evidence={
            "primary_law": bundle.loaded.laws[0].identity.name,
            "structured_annex_rows": len(annex_body.structured_data.rows if annex_body.structured_data else []),
            "referenced_articles": [
                ref.article for ref in bundle.loaded.interpretations[0].referenced_articles
            ],
        },
    )


def _run_delegated_criteria_tracing() -> TracerScenarioResult:
    identity = LawIdentity(law_id="001747", name="자동차관리법", basis="effective", mst="270001")
    source = ScenarioSource(
        service_payloads=[
            law_text_payload("자동차관리법", "001747", "270001", article="제26조", title="자동차의 강제처리"),
            law_structure_payload("자동차관리법", "001747", "270001", "자동차관리법 시행령"),
            delegation_payload("자동차관리법", "자동차관리법 시행령", law_id="001747", article="26"),
        ],
        search_payloads=[
            administrative_rule_search_payload("무단방치 자동차 처리 규정"),
            {"ExpcSearch": {"expc": []}},
            {"PrecSearch": {"prec": []}},
            {"DetcSearch": {"detc": []}},
            annex_search_payload("904", "무단방치 자동차 처리 기준", related_name="자동차관리법"),
            {"admbyl": []},
        ],
    )
    bundle = MolegApi(source).load_institutional_system([identity], budget="minimal")

    return TracerScenarioResult(
        archetype="delegated_criteria_tracing",
        public_interfaces=["load_institutional_system"],
        loaded=["law", "law_structure", "delegation"],
        candidates=["administrative_rule", "annex_form"],
        deferred=[item.interface for item in bundle.deferred],
        gaps=[gap.recommended_interface or gap.kind for gap in bundle.gaps],
        evidence={
            "law_structures": len(bundle.loaded.law_structures),
            "delegated_rules": len(bundle.loaded.delegations[0].rules),
            "admin_rule_candidates": len(bundle.candidates.administrative_rules),
        },
    )


def _run_statute_evolution() -> TracerScenarioResult:
    identity = LawIdentity(law_id="001971", name="건축법", basis="effective")
    source = ScenarioSource(
        service_payloads=[
            {
                "lsJoHstInf": {
                    "law": [
                        {
                            "법령ID": "001971",
                            "법령명한글": "건축법",
                            "조문번호": "5",
                            "조문변경일": "20250101",
                            "조문시행일": "20250401",
                            "공포일자": "20250101",
                            "공포번호": "제 20001호",
                            "변경사유": "일부개정",
                            "조문내용": "제5조(적용의 완화) 건축기준을 완화하여 적용할 수 있다.",
                        }
                    ]
                }
            }
        ]
    )

    history = MolegApi(source).trace_law_history(
        identity,
        article="제5조",
        promulgation_bridge={("건축법", "20001", "20250101"): "BILL-20001"},
    )

    return TracerScenarioResult(
        archetype="statute_evolution",
        public_interfaces=["trace_law_history"],
        loaded=["article_history"],
        evidence={
            "event_count": len(history.events),
            "article_text_present": history.events[0].article_text is not None,
            "bill_id": history.events[0].bill_id,
            "promulgation_number": history.events[0].promulgation_number,
        },
    )


def _run_congress_bill_bridge() -> TracerScenarioResult:
    source = ScenarioSource(
        search_payloads=[
            law_search_payload(
                "데이터기본법",
                law_id="111111",
                mst="260001",
                promulgation_number="20000",
                promulgation_date="20250101",
                basis_key="법령명한글",
            ),
            {"AdmRulSearch": {"admrul": []}},
            {"ExpcSearch": {"expc": []}},
            {"PrecSearch": {"prec": []}},
            {"DetcSearch": {"detc": []}},
            {"licbyl": []},
            {"admbyl": []},
        ],
        service_payloads=[
            law_text_payload("데이터기본법", "111111", "270001", article="제1조", title="목적"),
            delegation_payload("데이터기본법", "데이터기본법 시행령", law_id="111111", article="10"),
        ],
    )

    bundle = MolegApi(source).load_legal_context_bundle(
        promulgation_bridge={
            "prom_law_nm": "데이터기본법",
            "prom_no": "20000",
            "promulgation_dt": "2025-01-01",
        },
        mode="promulgated_bill",
        budget="minimal",
    )

    return TracerScenarioResult(
        archetype="congress_bill_to_current_law",
        public_interfaces=["load_legal_context_bundle"],
        loaded=["current_law", "delegation"],
        deferred=[item.interface for item in bundle.deferred],
        gaps=[gap.recommended_interface or gap.kind for gap in bundle.gaps],
        evidence={
            "resolved_law": bundle.loaded.laws[0].identity.name,
            "basis": bundle.loaded.laws[0].identity.basis,
            "has_history_followup": any(item.interface == "trace_law_history" for item in bundle.deferred),
        },
    )


def _run_constitutional_risk_scan() -> TracerScenarioResult:
    source = ScenarioSource(
        search_payloads=[
            {"LawSearch": {"law": []}},
            {"lstrmAI": []},
            {"dlytrm": []},
            {"aiSearch": []},
            {"aiRltLs": []},
            {"AdmRulSearch": {"admrul": []}},
            {"ExpcSearch": {"expc": []}},
            {"PrecSearch": {"prec": []}},
            {
                "DetcSearch": {
                    "detc": [
                        {"헌재결정례일련번호": "300", "사건명": "표현의 자유 제한 위헌확인"},
                        {"헌재결정례일련번호": "301", "사건명": "표현의 자유 과잉금지원칙"},
                        {"헌재결정례일련번호": "302", "사건명": "표현의 자유 기타 사건"},
                    ]
                }
            },
            {"licbyl": []},
            {"admbyl": []},
        ],
        service_payloads=[
            {"lstrmRlt": []},
            {"dlytrmRlt": []},
            {"lstrmRltJo": []},
            constitutional_detail_payload("300", "표현의 자유 제한 위헌확인", reviewed_statutes="헌법 제37조 제2항"),
            constitutional_detail_payload("301", "표현의 자유 과잉금지원칙", reviewed_statutes="헌법 제37조 제2항"),
        ],
    )

    bundle = MolegApi(source).load_legal_context_bundle("표현의 자유 관점에서 위헌인가", budget="broad")

    return TracerScenarioResult(
        archetype="constitutional_risk_scan",
        public_interfaces=["load_legal_context_bundle"],
        loaded=["constitutional_detail"],
        candidates=["constitutional_decision"],
        deferred=[item.interface for item in bundle.deferred],
        gaps=[gap.recommended_interface or gap.kind for gap in bundle.gaps],
        evidence={
            "loaded_constitutional_decisions": len(bundle.loaded.constitutional_decisions),
            "deferred_constitutional_decisions": sum(
                1 for item in bundle.deferred if item.interface == "get_constitutional_decision"
            ),
            "reviewed_articles": [
                ref.article for ref in bundle.loaded.constitutional_decisions[0].reviewed_articles
            ],
        },
    )


def _run_multi_law_concept_assembly() -> TracerScenarioResult:
    identities = [
        LawIdentity(law_id="010000", name="전자금융거래법", basis="effective", mst="280000"),
        LawIdentity(law_id="010001", name="전자금융거래법 시행령", basis="effective", mst="280001"),
    ]
    source = ScenarioSource(
        service_payloads=[
            law_text_payload("전자금융거래법", "010000", "280000", article="제21조", title="안전성 확보의무"),
            law_structure_payload("전자금융거래법", "010000", "280000", "전자금융거래법 시행령"),
            delegation_payload("전자금융거래법", "전자금융거래법 시행령", law_id="010000", article="21"),
            law_text_payload("전자금융거래법 시행령", "010001", "280001", article="제11조", title="안전성 기준"),
            law_structure_payload("전자금융거래법 시행령", "010001", "280001", "전자금융감독규정"),
            delegation_payload("전자금융거래법 시행령", "전자금융감독규정", law_id="010001", article="11"),
        ],
        search_payloads=[
            administrative_rule_search_payload("전자금융감독규정"),
            {"ExpcSearch": {"expc": []}},
            {"PrecSearch": {"prec": []}},
            {"DetcSearch": {"detc": []}},
            {"licbyl": []},
            {"admbyl": []},
            administrative_rule_search_payload("전자금융감독규정 시행세칙"),
            {"ExpcSearch": {"expc": []}},
            {"PrecSearch": {"prec": []}},
            {"DetcSearch": {"detc": []}},
            {"licbyl": []},
            {"admbyl": []},
        ],
    )

    bundle = MolegApi(source).load_institutional_system(identities, budget="minimal")

    return TracerScenarioResult(
        archetype="multi_law_concept_assembly",
        public_interfaces=["load_institutional_system"],
        loaded=["laws", "law_structures", "delegations"],
        candidates=["administrative_rule"],
        deferred=[item.interface for item in bundle.deferred],
        gaps=[gap.recommended_interface or gap.kind for gap in bundle.gaps],
        evidence={
            "loaded_laws": len(bundle.loaded.laws),
            "law_structures": len(bundle.loaded.law_structures),
            "delegation_graphs": len(bundle.loaded.delegations),
            "request_statute_ids": bundle.request.statute_ids,
        },
    )


def _run_comparative_design() -> TracerScenarioResult:
    source = ScenarioSource(
        search_payloads=[
            {
                "aiSearch": [
                    {
                        "법령ID": "001111",
                        "법령명": "독점규제 및 공정거래에 관한 법률",
                        "법령일련번호": "270001",
                        "조문번호": "50",
                        "조문제목": "과징금",
                    },
                    {
                        "법령ID": "002222",
                        "법령명": "전기통신사업법",
                        "법령일련번호": "270002",
                        "조문번호": "53",
                        "조문제목": "과징금",
                    },
                ]
            },
            {
                "aiRltLs": {
                    "법령조문": [
                        {
                            "법령ID": "003333",
                            "법령명": "환경오염시설의 통합관리에 관한 법률",
                            "조문번호": "35",
                            "조문제목": "과징금",
                        }
                    ]
                }
            },
        ],
        service_payloads=[
            {"lstrmRltJo": []},
            {
                "eflawjosub": {
                    "조문": {
                        "조문번호": "50",
                        "조문제목": "과징금",
                        "조문내용": "제50조(과징금) 공정거래위원회는 과징금을 부과할 수 있다.",
                    }
                }
            },
        ],
    )
    api = MolegApi(source)

    candidates = api.find_comparable_mechanisms("과징금", display=3)
    first_article = candidates[0].raw_keys["source_articles"][0]["article"]
    article = api.get_article(candidates[0], first_article)

    return TracerScenarioResult(
        archetype="comparative_design",
        public_interfaces=["find_comparable_mechanisms", "get_article"],
        loaded=["article"],
        candidates=["comparable_law"],
        evidence={
            "candidate_count": len(candidates),
            "discovery_endpoints": candidates[0].raw_keys["discovery_endpoints"],
            "loaded_article": article.article,
        },
    )


def law_search_payload(
    name: str,
    *,
    law_id: str,
    mst: str,
    promulgation_number: str = "20000",
    promulgation_date: str = "20250101",
    basis_key: str = "법령명한글",
) -> dict[str, Any]:
    return {
        "LawSearch": {
            "law": [
                {
                    "법령ID": law_id,
                    basis_key: name,
                    "법령일련번호": mst,
                    "공포번호": promulgation_number,
                    "공포일자": promulgation_date,
                    "시행일자": "20260101",
                    "법령구분명": "법률",
                    "소관부처명": "소관부처",
                }
            ]
        }
    }


def law_text_payload(
    name: str,
    law_id: str,
    mst: str,
    *,
    article: str,
    title: str,
) -> dict[str, Any]:
    article_no = article.removeprefix("제").removesuffix("조")
    return {
        "eflaw": {
            "기본정보": {
                "법령ID": law_id,
                "법령명_한글": name,
                "법령일련번호": mst,
                "시행일자": "20260101",
            },
            "조문": {
                "조문단위": [
                    {
                        "조문번호": article_no,
                        "조문제목": title,
                        "조문내용": f"{article}({title}) 이 조문은 {title}에 관한 기준을 정한다.",
                    }
                ]
            },
        }
    }


def delegation_payload(
    law_name: str,
    delegated_name: str,
    *,
    law_id: str,
    article: str = "75",
) -> dict[str, Any]:
    return {
        "lsDelegated": {
            "법령": {
                "법령정보": {
                    "법령ID": law_id,
                    "법령명": law_name,
                    "법령일련번호": "270001",
                },
                "위임조문정보": [
                    {
                        "조정보": {"조문번호": article, "조문제목": "위임"},
                        "위임정보": {
                            "위임구분": "시행령",
                            "위임법령제목": delegated_name,
                            "라인텍스트": "대통령령으로 정하는 바에 따라",
                        },
                    }
                ],
            }
        }
    }


def law_structure_payload(root_name: str, law_id: str, mst: str, child_name: str) -> dict[str, Any]:
    return {
        "법령체계도": {
            "기본정보": {
                "법령ID": law_id,
                "법령일련번호": mst,
                "법령명": root_name,
                "법종구분": {"content": "법률"},
                "시행일자": "20260101",
            },
            "상하위법": {
                "법률": {
                    "기본정보": {
                        "법령ID": law_id,
                        "법령일련번호": mst,
                        "법령명": root_name,
                        "법종구분": {"content": "법률"},
                        "시행일자": "20260101",
                    },
                    "시행령": {
                        "기본정보": {
                            "법령ID": f"{law_id}1",
                            "법령일련번호": f"{mst}1",
                            "법령명": child_name,
                            "법종구분": {"content": "대통령령"},
                            "시행일자": "20260101",
                        }
                    },
                }
            },
        }
    }


def term_search_payload(term: str) -> dict[str, Any]:
    return {"lstrmAI": [{"법령용어 id": "100", "법령용어명": term}]}


def ai_article_payload(law_name: str, law_id: str, article_no: str, title: str) -> dict[str, Any]:
    return {
        "aiSearch": [
            {
                "법령ID": law_id,
                "법령명": law_name,
                "법령일련번호": "270001",
                "조문번호": article_no,
                "조문제목": title,
            }
        ]
    }


def administrative_rule_search_payload(name: str) -> dict[str, Any]:
    return {
        "AdmRulSearch": {
            "admrul": [
                {
                    "행정규칙 일련번호": "2100000248758",
                    "행정규칙명": name,
                    "행정규칙종류": "고시",
                    "발령일자": "20250101",
                }
            ]
        }
    }


def annex_search_payload(annex_id: str, title: str, *, related_name: str) -> dict[str, Any]:
    return {
        "licbyl": [
            {
                "licbyl id": annex_id,
                "별표명": title,
                "관련법령명": related_name,
                "관련법령ID": "001900",
                "별표종류": "별표",
            }
        ]
    }


def interpretation_search_payload(identifier: str, title: str) -> dict[str, Any]:
    return {"ExpcSearch": {"expc": [{"법령해석례일련번호": identifier, "안건명": title}]}}


def interpretation_detail_payload(identifier: str, title: str, *, related_laws: str) -> dict[str, Any]:
    return {
        "expc": {
            "법령해석례일련번호": identifier,
            "안건명": title,
            "질의요지": f"{title}의 의미는 무엇인가?",
            "회답": "문언과 체계에 따라 판단한다.",
            "이유": "관련 조문과 위임 체계를 함께 보아야 한다.",
            "관련법령": related_laws,
        }
    }


def case_search_payload(identifier: str, title: str) -> dict[str, Any]:
    return {"PrecSearch": {"prec": [{"판례일련번호": identifier, "사건명": title}]}}


def case_detail_payload(identifier: str, title: str, *, referenced_statutes: str) -> dict[str, Any]:
    return {
        "prec": {
            "판례정보일련번호": identifier,
            "사건명": title,
            "참조조문": referenced_statutes,
            "판례내용": f"{title}에 관한 판례 전문",
        }
    }


def constitutional_search_payload(identifier: str, title: str) -> dict[str, Any]:
    return {"DetcSearch": {"detc": [{"헌재결정례일련번호": identifier, "사건명": title}]}}


def constitutional_detail_payload(identifier: str, title: str, *, reviewed_statutes: str) -> dict[str, Any]:
    return {
        "detc": {
            "헌재결정례일련번호": identifier,
            "사건명": title,
            "심판대상조문": reviewed_statutes,
            "전문": f"{title}에 관한 결정 전문",
        }
    }


def pipe_table_text() -> str:
    return "\n".join(
        [
            "■ 식품위생법 시행령 [별표 2]",
            "과징금 산정기준",
            "| 위반행위 | 1차 위반 | 2차 위반 |",
            "| 영업정지 명령 위반 | 50만원 | 100만원 |",
            "| 보고의무 위반 | 10만원 | 20만원 |",
        ]
    )


def main() -> None:
    print(
        json.dumps(
            [result.to_dict() for result in run_fake_skill_tracer_bullet()],
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
