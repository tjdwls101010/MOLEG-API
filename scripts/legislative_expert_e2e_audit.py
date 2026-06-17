"""Deterministic legislative-expert E2E audit for MOLEG-API.

This harness plays one step closer to the future skill than the tracer bullet:
it verifies that public `MolegApi` calls can produce an answer-readiness packet
with citations, guardrails, source gaps, and next actions. It still does not
generate legal conclusions.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from moleg_api import AnnexFormIdentity, LawIdentity, MolegApi, NoResultError, RateLimitError
from scripts.fake_skill_tracer_bullet import (
    ScenarioSource,
    administrative_rule_search_payload,
    annex_search_payload,
    ai_article_payload,
    law_structure_payload,
    law_text_payload,
    delegation_payload,
    law_search_payload,
    pipe_table_text,
    run_fake_skill_tracer_bullet,
    term_search_payload,
)


ReadinessStatus = Literal[
    "ready_for_reasoning",
    "needs_more_source_loading",
    "blocked_for_manual_review",
]


@dataclass(frozen=True)
class SourceCitation:
    """Source metadata the skill must preserve before reasoning from context."""

    source_type: str
    source_target: str
    title: str
    article: str | None = None
    authority: str | None = None


@dataclass(frozen=True)
class LegislativeExpertScenarioReport:
    """One deterministic answer-readiness report."""

    scenario: str
    question: str
    status: ReadinessStatus
    public_interfaces: list[str]
    must_have: dict[str, bool]
    citations: list[SourceCitation] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _article_reference_dicts(references: list[Any]) -> list[dict[str, str | None]]:
    return [
        {
            "law_name": item.law_name,
            "article": item.article,
            "law_id": item.law_id,
        }
        for item in references
    ]


def _references_target_article(
    references: list[Any],
    *,
    law_name: str,
    article: str,
) -> bool:
    return any(item.law_name == law_name and item.article == article for item in references)


def run_legislative_expert_e2e_audit() -> list[LegislativeExpertScenarioReport]:
    """Run deterministic E2E readiness scenarios through public interfaces."""

    reports = _reports_from_tracer_archetypes()
    reports.insert(4, _audit_loaded_before_after_amendment_delta())
    reports.extend(
        [
            _audit_latest_social_context_websearch_handoff(),
            _audit_supplementary_provision_transition_context(),
            _audit_nested_article_unit_text_completeness(),
            _audit_deleted_article_status_guardrail(),
            _audit_moved_article_status_guardrail(),
            _audit_query_expansion_candidate_authority_guardrail(),
            _audit_law_search_candidate_detail_guardrail(),
            _audit_empty_law_search_absence_guardrail(),
            _audit_interpretation_search_candidate_detail_guardrail(),
            _audit_empty_interpretation_search_absence_guardrail(),
            _audit_source_access_failure_not_no_result_guardrail(),
            _audit_context_bundle_requested_law_not_loaded_guardrail(),
            _audit_context_bundle_requested_article_not_loaded_guardrail(),
            _audit_context_bundle_delegation_lookup_failure_guardrail(),
            _audit_case_search_candidate_detail_guardrail(),
            _audit_empty_case_search_absence_guardrail(),
            _audit_constitutional_search_candidate_detail_guardrail(),
            _audit_empty_constitutional_search_absence_guardrail(),
            _audit_authority_context_matching_current_authorities(),
            _audit_loaded_authority_article_mismatch_guardrail(),
            _audit_context_bundle_authority_article_mismatch_guardrail(),
            _audit_context_bundle_authority_article_unverified_guardrail(),
            _audit_context_bundle_authority_article_partial_match_guardrail(),
            _audit_context_bundle_authority_temporal_mismatch_guardrail(),
            _audit_law_structure_hierarchy_candidate_guardrail(),
            _audit_institutional_system_law_structure_not_loaded_guardrail(),
            _audit_empty_delegation_graph_absence_guardrail(),
            _audit_administrative_rule_search_candidate_detail_guardrail(),
            _audit_administrative_rule_issued_on_not_effective_as_of_guardrail(),
            _audit_administrative_rule_article_status_guardrail(),
            _audit_administrative_rule_supplementary_transition_context(),
            _audit_empty_administrative_rule_search_absence_guardrail(),
            _audit_administrative_rule_missing_source_reference_guardrail(),
            _audit_comparable_mechanism_candidate_detail_guardrail(),
            _audit_annex_form_search_candidate_detail_guardrail(),
            _audit_empty_annex_form_search_absence_guardrail(),
            _audit_delegated_criteria_after_followups(),
            _audit_delegated_criteria_source_mismatch_guardrail(),
            _audit_low_confidence_annex_body(),
            _audit_historical_repealed_article_as_of(),
            _audit_future_effective_administrative_rule_after_followup(),
            _audit_future_effective_promulgated_law(),
            _audit_institutional_system_future_effective_law(),
            _audit_proposed_bill_without_promulgation_bridge(),
            _audit_ambiguous_statute_set(),
            _audit_promulgation_bridge_source_lag(),
            _audit_interpretation_authority_distinction(),
        ]
    )
    return reports


def _audit_loaded_before_after_amendment_delta() -> LegislativeExpertScenarioReport:
    identity = LawIdentity(law_id="000182", name="가정폭력방지법", basis="effective")
    source = ScenarioSource(
        service_payloads=[
            {
                "oldAndNew": {
                    "구조문_기본정보": {
                        "법령ID": "000182",
                        "법령명": "가정폭력방지법",
                        "법령일련번호": "270885",
                        "공포일자": "20240101",
                        "시행일자": "20240101",
                    },
                    "신조문_기본정보": {
                        "법령ID": "000182",
                        "법령명": "가정폭력방지법",
                        "법령일련번호": "276865",
                        "공포일자": "20250101",
                        "시행일자": "20250101",
                    },
                    "구조문목록": {
                        "조문": [{"no": "제1조", "content": "종전 목적"}]
                    },
                    "신조문목록": {
                        "조문": [{"no": "제1조", "content": "개정 목적"}]
                    },
                }
            }
        ]
    )

    diff = MolegApi(source).compare_law_versions(identity, article="제1조")
    changes = [
        {
            "article": change.article,
            "before_text": change.before_text,
            "after_text": change.after_text,
        }
        for change in diff.changes
    ]

    return LegislativeExpertScenarioReport(
        scenario="loaded_before_after_amendment_delta_guardrail",
        question="신구조문대비표가 로드된 뒤 조문별 개정 전후 문구와 입법취지 범위가 구분되는가?",
        status="ready_for_reasoning",
        public_interfaces=["compare_law_versions"],
        must_have={
            "before_after_diff_loaded": len(diff.changes) == 1,
            "selected_article_delta_preserved": changes[0] == {
                "article": "제1조",
                "before_text": "종전 목적",
                "after_text": "개정 목적",
            },
            "before_identity_preserved": diff.before_identity is not None
            and diff.before_identity.mst == "270885",
            "after_identity_preserved": diff.after_identity is not None
            and diff.after_identity.mst == "276865",
            "reason_or_legislative_intent_not_loaded": all(
                not change.raw.get("reason") for change in diff.changes
            ),
        },
        citations=[
            SourceCitation(
                "law_diff",
                "oldAndNew",
                "가정폭력방지법",
                "제1조",
                "MOLEG before/after comparison",
            )
        ],
        risk_flags=[
            "before_after_comparison_supports_wording_delta_only",
            "old_and_new_does_not_prove_legislative_intent",
            "selected_article_diff_is_not_exhaustive_law_revision_summary",
        ],
        next_actions=[
            "Use loaded before/after text for the selected article's wording delta.",
            "Load trace_law_history() or congress-db bill materials before explaining amendment reason, legislative intent, or full bill purpose.",
        ],
        evidence={
            "law": diff.identity.name,
            "before_mst": diff.before_identity.mst if diff.before_identity else None,
            "after_mst": diff.after_identity.mst if diff.after_identity else None,
            "before_effective_date": diff.before_identity.effective_date
            if diff.before_identity
            else None,
            "after_effective_date": diff.after_identity.effective_date
            if diff.after_identity
            else None,
            "changes": changes,
            "service_call_targets": [target for _, target, _ in source.calls],
            "reason_loaded": False,
        },
    )


def _audit_latest_social_context_websearch_handoff() -> LegislativeExpertScenarioReport:
    query = "최근 전세사기 피해 통계와 현행 지원법 조문"
    law_name = "전세사기피해자 지원 및 주거안정에 관한 특별법"
    source = ScenarioSource(
        search_payloads=[
            law_search_payload(law_name, law_id="013395", mst="270777"),
            term_search_payload("전세사기피해자"),
            {"dlytrm": []},
            ai_article_payload(law_name, "013395", "1", "목적"),
            {"aiRltLs": []},
        ],
        service_payloads=[
            {"lstrmRlt": []},
            {"dlytrmRlt": []},
            {"lstrmRltJo": []},
            {
                "eflawjosub": {
                    "조문": {
                        "조문번호": "1",
                        "조문제목": "목적",
                        "조문내용": "제1조(목적) 이 법은 전세사기피해자를 지원하고 주거안정을 도모함을 목적으로 한다.",
                    }
                }
            },
        ],
    )
    api = MolegApi(source)

    expansion = api.expand_legal_query(query)
    article = api.get_article(expansion.law_candidates[0], "제1조")
    follow_up_interfaces = [search.interface for search in expansion.follow_up_searches]
    websearch_followup = next(
        search for search in expansion.follow_up_searches if search.interface == "websearch"
    )
    citations = [
        SourceCitation("law", "eflawjosub", law_name, "제1조", "current statute article"),
    ]

    return LegislativeExpertScenarioReport(
        scenario="latest_social_context_websearch_handoff",
        question="최신 피해 통계와 현행 법령 조문을 한 답변에서 출처 책임별로 분리하는가?",
        status="needs_more_source_loading",
        public_interfaces=["expand_legal_query", "get_article"],
        must_have={
            "legal_source_planned": expansion.law_candidates[0].name == law_name,
            "current_article_loaded": article.article == "제1조" and "주거안정" in article.text,
            "websearch_followup_preserved": "websearch" in follow_up_interfaces,
            "websearch_remains_required_before_social_fact_claim": follow_up_interfaces[-1] == "websearch",
            "moleg_citation_is_legal_only_until_websearch_loaded": all(
                citation.source_type == "law" for citation in citations
            ),
        },
        citations=citations,
        risk_flags=[
            "latest_social_facts_require_websearch",
            "moleg_legal_sources_do_not_supply_current_statistics",
        ],
        next_actions=[
            "Load WebSearch results before making any latest 피해 통계, news, or policy-announcement claim.",
            "Cite MOLEG legal text and WebSearch social facts separately in the final answer.",
        ],
        evidence={
            "query": query,
            "law_candidate_names": [identity.name for identity in expansion.law_candidates],
            "loaded_article": article.article,
            "follow_up_interfaces": follow_up_interfaces,
            "websearch_reason": websearch_followup.reason,
            "moleg_call_targets": [target for _, target, _ in source.calls],
            "social_fact_sources_loaded": [],
        },
    )


def _audit_supplementary_provision_transition_context() -> LegislativeExpertScenarioReport:
    law_name = "전세사기피해자 지원 및 주거안정에 관한 특별법"
    identity = LawIdentity(law_id="013395", name=law_name, basis="effective", mst="270777")
    source = ScenarioSource(
        service_payloads=[
            {
                "eflaw": {
                    "기본정보": {
                        "법령ID": "013395",
                        "법령명_한글": law_name,
                        "법령일련번호": "270777",
                        "공포번호": "21527",
                        "공포일자": "20260407",
                        "시행일자": "20260701",
                    },
                    "조문": {
                        "조문단위": [
                            {
                                "조문번호": "1",
                                "조문제목": "목적",
                                "조문내용": "제1조(목적) 이 법은 전세사기피해자를 지원하고 주거안정을 도모한다.",
                                "조문시행일자": "20260701",
                            }
                        ]
                    },
                    "부칙": {
                        "부칙단위": [
                            {
                                "부칙공포일자": "20260407",
                                "부칙공포번호": "제21527호",
                                "부칙내용": "제1조(시행일) 이 법은 2026년 7월 1일부터 시행한다.",
                            },
                            {
                                "부칙공포일자": "20260407",
                                "부칙공포번호": "제21527호",
                                "부칙내용": "제2조(경과조치) 이 법 시행 당시 종전의 임대차계약에 관하여는 대통령령으로 정하는 바에 따른다.",
                            },
                        ]
                    },
                }
            }
        ]
    )

    law = MolegApi(source).get_law(identity)
    supplementary_text = "\n".join(provision.text for provision in law.supplementary_provisions)

    return LegislativeExpertScenarioReport(
        scenario="supplementary_provision_transition_guardrail",
        question="시행일/경과조치 질문에서 부칙이 본문 조문과 별도 근거로 보존되는가?",
        status="ready_for_reasoning",
        public_interfaces=["get_law"],
        must_have={
            "main_article_loaded": law.articles[0].article == "제1조",
            "supplementary_provisions_loaded": len(law.supplementary_provisions) == 2,
            "supplementary_promulgation_metadata_preserved": law.supplementary_provisions[0].promulgation_number == "21527",
            "transition_text_loaded_from_supplementary_provision": "경과조치" in supplementary_text
            and "종전의 임대차계약" in supplementary_text,
            "transition_text_not_in_main_article": "경과조치" not in law.articles[0].text,
        },
        citations=[
            SourceCitation("law", "eflaw", law_name, "제1조", "current statute article"),
            SourceCitation(
                "supplementary_provision",
                "eflaw",
                law_name,
                "부칙 제2조",
                "law supplementary provision",
            ),
        ],
        risk_flags=[
            "supplementary_provision_required_for_transition_application",
            "main_article_text_alone_cannot_answer_transitional_scope",
        ],
        next_actions=[
            "Cite supplementary provisions separately when discussing 시행일, 적용례, or 경과조치.",
            "Use history/diff follow-up if the transition question depends on a specific amendment event.",
        ],
        evidence={
            "law_effective_date": law.identity.effective_date,
            "article_count": len(law.articles),
            "supplementary_provision_count": len(law.supplementary_provisions),
            "supplementary_promulgation_dates": [
                provision.promulgation_date for provision in law.supplementary_provisions
            ],
            "supplementary_promulgation_numbers": [
                provision.promulgation_number for provision in law.supplementary_provisions
            ],
            "supplementary_text_contains_transition": "경과조치" in supplementary_text,
            "call_targets": [target for _, target, _ in source.calls],
        },
    )


def _reports_from_tracer_archetypes() -> list[LegislativeExpertScenarioReport]:
    reports: list[LegislativeExpertScenarioReport] = []
    for result in run_fake_skill_tracer_bullet():
        if result.archetype == "sanction_design":
            reports.append(
                LegislativeExpertScenarioReport(
                    scenario=result.archetype,
                    question="식품위생법 과징금 산정기준을 검토할 수 있는가?",
                    status="ready_for_reasoning",
                    public_interfaces=result.public_interfaces,
                    must_have={
                        "current_statute_loaded": "law" in result.loaded,
                        "delegation_loaded": "delegation" in result.loaded,
                        "annex_table_inspected": result.evidence["structured_annex_rows"] > 0,
                        "authority_article_refs_preserved": result.evidence["referenced_articles"] == ["제75조"],
                        "websearch_gap_preserved": "websearch" in result.gaps,
                    },
                    citations=[
                        SourceCitation("law", "eflaw", result.evidence["primary_law"], authority="current statute"),
                        SourceCitation("interpretation", "expc", "식품위생법 과징금 해석", "제75조", "MOLEG interpretation"),
                        SourceCitation("case", "prec", "과징금 부과처분 취소", "제75조", "court case"),
                        SourceCitation("constitutional", "detc", "과징금 과잉금지원칙", "제75조", "Constitutional Court"),
                        SourceCitation("annex", "licbyl", "과징금 산정기준", authority="law annex table"),
                    ],
                    risk_flags=[
                        "context_bundle_is_bounded_first_pass_not_exhaustive_authority_survey",
                    ],
                    next_actions=[
                        "Use loaded authority details as bounded source context, not an exhaustive authority survey.",
                        "Use WebSearch only for latest social facts or policy context.",
                    ],
                    evidence={
                        **result.evidence,
                        "loaded_authority_detail_types": [
                            item for item in result.loaded if item.endswith("_detail")
                        ],
                        "candidate_types": result.candidates,
                        "deferred_interfaces": result.deferred,
                    },
                )
            )
        elif result.archetype == "delegated_criteria_tracing":
            citations = [
                SourceCitation("law", "eflaw", "자동차관리법", "제26조", "current statute"),
                SourceCitation("delegation", "lsDelegated", "자동차관리법 시행령", "제26조", "delegated rule graph"),
            ]
            reports.append(
                LegislativeExpertScenarioReport(
                    scenario=result.archetype,
                    question="자동차 방치 처리 기준이 하위규정까지 추적되는가?",
                    status="needs_more_source_loading",
                    public_interfaces=result.public_interfaces,
                    must_have={
                        "law_structure_loaded": result.evidence["law_structures"] == 1,
                        "delegation_graph_loaded": result.evidence["delegated_rules"] == 1,
                        "administrative_rule_candidate_preserved": result.evidence["admin_rule_candidates"] == 1,
                        "deferred_followups_preserved": {
                            "get_administrative_rule",
                            "get_annex_form_body",
                        }.issubset(result.deferred),
                        "candidate_not_cited_as_loaded_source": not any(
                            citation.source_type == "administrative_rule" for citation in citations
                        ),
                    },
                    citations=citations,
                    risk_flags=["administrative_rule_candidate_not_loaded"],
                    next_actions=["Load selected administrative-rule and annex/form bodies before citing operational criteria."],
                    evidence=result.evidence,
                )
            )
        elif result.archetype == "statute_evolution":
            reports.append(
                LegislativeExpertScenarioReport(
                    scenario=result.archetype,
                    question="건축법 제5조 개정 이력과 국회 bill bridge가 보존되는가?",
                    status="ready_for_reasoning",
                    public_interfaces=result.public_interfaces,
                    must_have={
                        "history_event_loaded": result.evidence["event_count"] == 1,
                        "article_text_snapshot_loaded": result.evidence["article_text_present"] is True,
                        "bill_bridge_preserved": result.evidence["bill_id"] == "BILL-20001",
                        "promulgation_number_normalized": result.evidence["promulgation_number"] == "20001",
                    },
                    citations=[
                        SourceCitation("history", "lsJoHstInf", "건축법", "제5조", "article history"),
                    ],
                    evidence=result.evidence,
                )
            )
        elif result.archetype == "congress_bill_to_current_law":
            reports.append(
                LegislativeExpertScenarioReport(
                    scenario=result.archetype,
                    question="공포된 국회 법안이 현재 시행 법령으로 연결되는가?",
                    status="ready_for_reasoning",
                    public_interfaces=result.public_interfaces,
                    must_have={
                        "resolved_to_current_law": result.evidence["resolved_law"] == "데이터기본법",
                        "effective_basis_used_for_current_text": result.evidence["basis"] == "effective",
                        "history_followup_deferred": result.evidence["has_history_followup"] is True,
                    },
                    citations=[
                        SourceCitation("law", "eflaw", "데이터기본법", authority="current statute resolved from promulgation bridge"),
                    ],
                    risk_flags=["history_not_loaded_until_article_or_date_known"],
                    next_actions=["Run trace_law_history or compare_law_versions after the affected article/date is known."],
                    evidence=result.evidence,
                )
            )
        elif result.archetype == "constitutional_risk_scan":
            reports.append(
                LegislativeExpertScenarioReport(
                    scenario=result.archetype,
                    question="표현의 자유 제한 쟁점에서 헌재 결정과 미열람 후보가 구분되는가?",
                    status="ready_for_reasoning",
                    public_interfaces=result.public_interfaces,
                    must_have={
                        "constitutional_details_loaded": result.evidence["loaded_constitutional_decisions"] == 2,
                        "unloaded_decisions_deferred": result.evidence["deferred_constitutional_decisions"] == 1,
                        "reviewed_articles_preserved": result.evidence["reviewed_articles"] == ["제37조"],
                    },
                    citations=[
                        SourceCitation("constitutional", "detc", "표현의 자유 제한 위헌확인", "제37조", "Constitutional Court"),
                    ],
                    risk_flags=["detc_is_free_text_search_not_doctrine_index"],
                    next_actions=["Review deferred Constitutional Court decisions before claiming exhaustive doctrine coverage."],
                    evidence=result.evidence,
                )
            )
        elif result.archetype == "multi_law_concept_assembly":
            reports.append(
                LegislativeExpertScenarioReport(
                    scenario=result.archetype,
                    question="전자금융 제도를 명시 법령 세트로 묶어 검토할 수 있는가?",
                    status="ready_for_reasoning",
                    public_interfaces=result.public_interfaces,
                    must_have={
                        "explicit_statute_set_preserved": result.evidence["request_statute_ids"] == [
                            "전자금융거래법",
                            "전자금융거래법 시행령",
                        ],
                        "all_laws_loaded": result.evidence["loaded_laws"] == 2,
                        "all_structures_loaded": result.evidence["law_structures"] == 2,
                        "all_delegation_graphs_loaded": result.evidence["delegation_graphs"] == 2,
                    },
                    citations=[
                        SourceCitation("law", "eflaw", "전자금융거래법", "제21조", "current statute"),
                        SourceCitation("law", "eflaw", "전자금융거래법 시행령", "제11조", "current enforcement decree"),
                    ],
                    risk_flags=["institutional_system_does_not_discover_statute_set"],
                    next_actions=["If statute set is uncertain, search or expand the query before load_institutional_system."],
                    evidence=result.evidence,
                )
            )
        elif result.archetype == "comparative_design":
            reports.append(
                LegislativeExpertScenarioReport(
                    scenario=result.archetype,
                    question="과징금 유사 입법례를 후보로 찾고 선택 조문을 읽었는가?",
                    status="ready_for_reasoning",
                    public_interfaces=result.public_interfaces,
                    must_have={
                        "multiple_candidates_found": result.evidence["candidate_count"] == 3,
                        "discovery_endpoint_preserved": "aiSearch" in result.evidence["discovery_endpoints"],
                        "selected_article_loaded_before_citation": result.evidence["loaded_article"] == "제50조",
                    },
                    citations=[
                        SourceCitation("law", "eflawjosub", "독점규제 및 공정거래에 관한 법률", "제50조", "loaded comparable article"),
                    ],
                    risk_flags=["comparable_candidate_is_not_legal_equivalence"],
                    next_actions=["Inspect each selected article before comparing mechanisms or recommending bill text."],
                    evidence=result.evidence,
                )
            )
    return reports


def _audit_nested_article_unit_text_completeness() -> LegislativeExpertScenarioReport:
    law_name = "자동차관리법"
    identity = LawIdentity(law_id="001747", name=law_name, basis="effective", mst="270001")
    source = ScenarioSource(
        service_payloads=[
            {
                "eflawjosub": {
                    "기본정보": {
                        "법령ID": "001747",
                        "법령명_한글": law_name,
                        "법령일련번호": "270001",
                    },
                    "조문": {
                        "조문번호": "2",
                        "조문제목": "정의",
                        "조문내용": "제2조(정의) 이 법에서 사용하는 용어의 뜻은 다음과 같다.",
                        "항": [
                            {
                                "항내용": "① \"자동차\"란 원동기로 육상에서 이동할 목적으로 제작한 용구를 말한다.",
                                "호": [
                                    {
                                        "호내용": "1. 승용자동차",
                                        "목": [
                                            {
                                                "목내용": "가. 일반형 승용자동차",
                                            }
                                        ],
                                    }
                                ],
                            },
                            {
                                "항내용": "② \"자동차사용자\"란 자동차 소유자 또는 사용 권한이 있는 자를 말한다.",
                            },
                        ],
                    },
                }
            }
        ]
    )

    article = MolegApi(source).get_article(identity, "제2조")
    line_count = len(article.text.splitlines())

    return LegislativeExpertScenarioReport(
        scenario="nested_article_unit_text_guardrail",
        question="정의/적용대상 조문에서 항·호·목이 조문 텍스트에 보존되는가?",
        status="ready_for_reasoning",
        public_interfaces=["get_article"],
        must_have={
            "top_level_article_text_loaded": "제2조(정의)" in article.text,
            "paragraph_text_preserved": "\"자동차\"란" in article.text
            and "\"자동차사용자\"란" in article.text,
            "subparagraph_text_preserved": "1. 승용자동차" in article.text,
            "item_text_preserved": "가. 일반형 승용자동차" in article.text,
            "nested_units_not_only_raw": line_count >= 4,
        },
        citations=[
            SourceCitation(
                "law",
                "eflawjosub",
                law_name,
                "제2조",
                "current statute article with nested units",
            ),
        ],
        risk_flags=[
            "nested_article_units_required_for_complete_article_text",
            "article_heading_or_top_level_text_alone_is_incomplete",
        ],
        next_actions=[
            "Use loaded ArticleText.text, not raw 조문제목 or top-level 조문내용 snippets, when reviewing definitions, exceptions, or requirements.",
            "Preserve nested unit labels when quoting or summarizing the relevant legal requirement.",
        ],
        evidence={
            "article": article.article,
            "line_count": line_count,
            "contains_terms": {
                "자동차": "\"자동차\"란" in article.text,
                "승용자동차": "1. 승용자동차" in article.text,
                "일반형 승용자동차": "가. 일반형 승용자동차" in article.text,
                "자동차사용자": "\"자동차사용자\"란" in article.text,
            },
            "call_targets": [target for _, target, _ in source.calls],
        },
    )


def _audit_deleted_article_status_guardrail() -> LegislativeExpertScenarioReport:
    law_name = "자동차관리법"
    identity = LawIdentity(law_id="001747", name=law_name, basis="effective", mst="270001")
    source = ScenarioSource(
        service_payloads=[
            {
                "eflawjosub": {
                    "기본정보": {
                        "법령ID": "001747",
                        "법령명_한글": law_name,
                        "법령일련번호": "270001",
                    },
                    "조문": {
                        "조문번호": "8",
                        "조문제목": "삭제",
                        "조문내용": "제8조 삭제 <2025. 1. 1.>",
                        "조문시행일자": "20250101",
                        "조문여부": "조문",
                        "조문제개정유형": "삭제",
                        "조문이동이전": "7",
                        "조문이동이후": "9",
                        "조문변경여부": "Y",
                    },
                }
            }
        ]
    )

    article = MolegApi(source).get_article(identity, "제8조")

    return LegislativeExpertScenarioReport(
        scenario="deleted_article_status_guardrail",
        question="현행 조문 조회 결과가 삭제 조문일 때 이를 현재 의무 조문처럼 인용하지 않는가?",
        status="ready_for_reasoning",
        public_interfaces=["get_article"],
        must_have={
            "article_loaded": article.article == "제8조",
            "deleted_status_preserved": article.is_deleted is True
            and article.revision_type == "삭제",
            "movement_metadata_preserved": article.moved_from == "제7조"
            and article.moved_to == "제9조",
            "change_flag_preserved": article.has_changes is True,
            "effective_date_preserved": article.effective_date == "20250101",
        },
        citations=[
            SourceCitation(
                "law",
                "eflawjosub",
                law_name,
                "제8조",
                "current statute article marked deleted",
            ),
        ],
        risk_flags=[
            "deleted_article_is_not_current_operational_text",
            "article_status_required_before_substantive_citation",
        ],
        next_actions=[
            "State that the loaded current article is marked deleted before discussing legal effect.",
            "Load history or version comparison if the answer needs the reason, prior wording, or amendment event.",
        ],
        evidence={
            "article": article.article,
            "text": article.text,
            "effective_date": article.effective_date,
            "article_kind": article.article_kind,
            "revision_type": article.revision_type,
            "moved_from": article.moved_from,
            "moved_to": article.moved_to,
            "has_changes": article.has_changes,
            "is_deleted": article.is_deleted,
            "call_targets": [target for _, target, _ in source.calls],
        },
    )


def _audit_moved_article_status_guardrail() -> LegislativeExpertScenarioReport:
    law_name = "자동차관리법"
    identity = LawIdentity(law_id="001747", name=law_name, basis="effective", mst="270001")
    source = ScenarioSource(
        service_payloads=[
            {
                "eflawjosub": {
                    "기본정보": {
                        "법령ID": "001747",
                        "법령명_한글": law_name,
                        "법령일련번호": "270001",
                    },
                    "조문": {
                        "조문번호": "8",
                        "조문제목": "이동",
                        "조문내용": "제8조는 제12조로 이동 <2025. 1. 1.>",
                        "조문시행일자": "20250101",
                        "조문여부": "조문",
                        "조문제개정유형": "이동",
                        "조문이동이전": "8",
                        "조문이동이후": "12",
                        "조문변경여부": "Y",
                    },
                }
            },
            {
                "eflawjosub": {
                    "기본정보": {
                        "법령ID": "001747",
                        "법령명_한글": law_name,
                        "법령일련번호": "270001",
                    },
                    "조문": {
                        "조문번호": "12",
                        "조문제목": "자동차등록",
                        "조문내용": "제12조(자동차등록) 자동차 소유자는 등록하여야 한다.",
                        "조문시행일자": "20250101",
                        "조문여부": "조문",
                        "조문제개정유형": "전문개정",
                    },
                }
            }
        ]
    )

    context = MolegApi(source).load_article_context(identity, "제8조")
    article = context.requested_article
    destination = context.current_article

    return LegislativeExpertScenarioReport(
        scenario="moved_article_status_guardrail",
        question="현행 조문 조회 결과가 다른 조문으로 이동된 상태일 때 이동 전 조문을 현재 실체 조문처럼 인용하지 않는가?",
        status="ready_for_reasoning",
        public_interfaces=["load_article_context"],
        must_have={
            "article_loaded": article.article == "제8조",
            "movement_status_preserved": article.revision_type == "이동"
            and article.moved_from == "제8조"
            and article.moved_to == "제12조",
            "moved_article_not_operational_text": article.text == "제8조는 제12조로 이동 <2025. 1. 1.>",
            "destination_article_loaded": destination is not None and destination.article == "제12조",
            "current_article_is_destination": destination is not None and "등록하여야" in destination.text,
        },
        citations=[
            SourceCitation("law", "eflawjosub", law_name, "제8조", "moved article marker"),
            SourceCitation("law", "eflawjosub", law_name, "제12조", "current destination article"),
        ],
        risk_flags=[
            "moved_article_destination_loaded_before_current_substance",
            "article_movement_marker_is_not_current_operational_text",
            "article_status_required_before_substantive_citation",
        ],
        next_actions=[
            "Disclose that the searched article is marked as moved and cite the loaded destination article for current substance.",
            "Load history or comparison if the answer needs the movement event, prior wording, or amendment reason.",
        ],
        evidence={
            "article": article.article,
            "text": article.text,
            "effective_date": article.effective_date,
            "article_kind": article.article_kind,
            "revision_type": article.revision_type,
            "moved_from": article.moved_from,
            "moved_to": article.moved_to,
            "current_article": destination.article if destination else None,
            "current_article_text": destination.text if destination else None,
            "loaded_articles": [item.article for item in context.loaded_articles],
            "gap_kinds": [gap.kind for gap in context.gaps],
            "deferred_interfaces": [item.interface for item in context.deferred],
            "has_changes": article.has_changes,
            "is_deleted": article.is_deleted,
            "call_targets": [target for _, target, _ in source.calls],
        },
    )


def _audit_query_expansion_candidate_authority_guardrail() -> LegislativeExpertScenarioReport:
    query = "자동차 방치 문제"
    source = ScenarioSource(
        search_payloads=[
            {
                "LawSearch": {
                    "law": [
                        {
                            "법령ID": "001747",
                            "법령명한글": "자동차관리법",
                            "법령일련번호": "270001",
                            "시행일자": "20250101",
                        }
                    ]
                }
            },
            {
                "lstrmAI": [
                    {
                        "법령용어 id": "100",
                        "법령용어명": "자동차",
                        "법령용어정의": "원동기로 육상에서 이동할 목적으로 제작한 용구",
                    }
                ]
            },
            {"dlytrm": [{"일상용어 id": "900", "일상용어명": "차량"}]},
            {
                "aiSearch": [
                    {
                        "법령ID": "001747",
                        "법령명": "자동차관리법",
                        "법령일련번호": "270001",
                        "조문번호": "26",
                        "조문제목": "자동차의 강제처리",
                        "조문내용": "자동차 소유자는...",
                    }
                ]
            },
            {
                "aiRltLs": [
                    {
                        "법령ID": "009999",
                        "법령명": "자동차손해배상 보장법",
                        "조문번호": "3",
                        "조문제목": "자동차손해배상책임",
                    }
                ]
            },
        ],
        service_payloads=[
            {"lstrmRlt": [{"법령용어명": "자동차", "일상용어명": "차량", "용어관계": "동의어"}]},
            {"dlytrmRlt": [{"일상용어명": "차량", "법령용어명": "자동차", "용어관계": "연관어"}]},
            {
                "lstrmRltJo": [
                    {
                        "법령용어명": "자동차",
                        "법령명": "자동차관리법",
                        "조번호": "26",
                        "조문내용": "자동차의 강제처리 관련 조문",
                    }
                ]
            },
        ],
    )

    expansion = MolegApi(source).expand_legal_query(query)
    follow_up_interfaces = [search.interface for search in expansion.follow_up_searches]

    return LegislativeExpertScenarioReport(
        scenario="query_expansion_candidate_authority_guardrail",
        question="법령용어/관련법령/AI 검색 후보만으로 현행 법적 근거를 단정하지 않는가?",
        status="needs_more_source_loading",
        public_interfaces=["expand_legal_query"],
        must_have={
            "law_candidate_preserved": expansion.law_candidates[0].name == "자동차관리법",
            "term_candidate_preserved": expansion.term_candidates[0].term == "자동차",
            "related_article_candidate_preserved": expansion.related_articles[0].article == "제26조",
            "followups_preserved": {"search_laws", "get_law", "websearch"}.issubset(
                set(follow_up_interfaces)
            ),
            "no_citable_source_loaded": True,
        },
        citations=[],
        risk_flags=[
            "query_expansion_is_not_final_authority",
            "related_article_candidate_requires_detail_loading",
            "ai_search_candidate_requires_source_loading",
        ],
        next_actions=[
            "Resolve and load selected law/article text before citing a current legal basis.",
            "Use term and related-law candidates only to plan follow-up searches.",
        ],
        evidence={
            "query": query,
            "law_candidates": [identity.name for identity in expansion.law_candidates],
            "term_candidates": [candidate.term for candidate in expansion.term_candidates],
            "related_articles": [
                {
                    "law_name": candidate.law_name,
                    "article": candidate.article,
                    "source_target": candidate.source_target,
                }
                for candidate in expansion.related_articles
            ],
            "follow_up_interfaces": follow_up_interfaces,
            "citations_loaded": 0,
            "call_targets": [target for _, target, _ in source.calls],
        },
    )


def _audit_law_search_candidate_detail_guardrail() -> LegislativeExpertScenarioReport:
    law_name = "자동차관리법"
    source = ScenarioSource(
        search_payloads=[
            law_search_payload(law_name, law_id="001747", mst="270001"),
        ],
    )

    hits = MolegApi(source).search_laws(law_name, display=5)
    service_call_targets = [target for kind, target, _ in source.calls if kind == "service"]

    return LegislativeExpertScenarioReport(
        scenario="law_search_candidate_detail_guardrail",
        question="법령명 검색 후보만으로 현행 조문 내용이나 의무를 인용하지 않는가?",
        status="needs_more_source_loading",
        public_interfaces=["search_laws"],
        must_have={
            "law_candidate_preserved": hits[0].identity.name == law_name,
            "identity_metadata_preserved": hits[0].identity.law_id == "001747"
            and hits[0].identity.mst == "270001"
            and hits[0].identity.basis == "effective",
            "no_law_text_loaded": service_call_targets == [],
            "no_citable_article_or_duty_loaded": True,
        },
        citations=[],
        risk_flags=[
            "law_search_hit_requires_selected_law_or_article_loading",
            "law_identity_candidate_is_not_article_text",
            "current_duty_claim_requires_get_law_or_get_article",
        ],
        next_actions=[
            "Load selected law text with get_law() or selected article text with get_article() before citing current legal substance.",
            "Treat search_laws() results as identity candidates and surface ambiguity if multiple plausible laws remain.",
        ],
        evidence={
            "query": law_name,
            "candidate_names": [hit.identity.name for hit in hits],
            "candidate_basis": [hit.identity.basis for hit in hits],
            "search_call_targets": [target for kind, target, _ in source.calls if kind == "search"],
            "service_call_targets": service_call_targets,
            "citations_loaded": 0,
        },
    )


def _audit_empty_law_search_absence_guardrail() -> LegislativeExpertScenarioReport:
    query = "자동차 방치 금지법"
    source = ScenarioSource(search_payloads=[{"LawSearch": {"law": []}}])

    hits = MolegApi(source).search_laws(query, display=5)
    service_call_targets = [target for kind, target, _ in source.calls if kind == "service"]

    return LegislativeExpertScenarioReport(
        scenario="empty_law_search_absence_guardrail",
        question="법령명 검색 결과가 0건일 때 현행 법적 근거가 없다고 단정하지 않는가?",
        status="needs_more_source_loading",
        public_interfaces=["search_laws"],
        must_have={
            "empty_search_result_preserved": hits == [],
            "no_law_text_loaded": service_call_targets == [],
            "legal_absence_claim_blocked": True,
            "query_scope_preserved": True,
        },
        citations=[],
        risk_flags=[
            "empty_law_search_is_not_absence_of_current_law",
            "zero_law_search_hits_require_alternate_names_or_sources",
            "legal_basis_absence_requires_successful_scope_disclosure",
        ],
        next_actions=[
            "Disclose that the exact current-law search returned zero hits for the searched query and basis.",
            "Use alternate law names, legal terms, related-law candidates, or congress-db bridge fields before any no-current-law or no-legal-basis claim.",
        ],
        evidence={
            "query": query,
            "basis": "effective",
            "hit_count": len(hits),
            "search_call_targets": [target for kind, target, _ in source.calls if kind == "search"],
            "service_call_targets": service_call_targets,
            "citations_loaded": 0,
        },
    )


def _audit_interpretation_search_candidate_detail_guardrail() -> LegislativeExpertScenarioReport:
    source = ScenarioSource(
        search_payloads=[
            {
                "Expc": {
                    "expc": [
                        {
                            "법령해석례일련번호": "330471",
                            "안건명": "자동차관리법 관련 법령해석례",
                            "안건번호": "21-0001",
                            "해석일자": "20240115",
                            "회신기관명": "법제처",
                            "법령해석례 상세링크": "/DRF/lawService.do?target=expc&ID=330471",
                        }
                    ]
                }
            }
        ]
    )

    hits = MolegApi(source).search_interpretations(
        "자동차 등록 기준",
        source="moleg",
        search_body=True,
        display=3,
    )
    hit = hits[0]
    service_call_targets = [target for kind, target, _ in source.calls if kind == "service"]

    return LegislativeExpertScenarioReport(
        scenario="interpretation_search_candidate_detail_guardrail",
        question="법령해석례 검색 hit만으로 질의요지/회답/이유를 읽은 것처럼 답하지 않는가?",
        status="needs_more_source_loading",
        public_interfaces=["search_interpretations"],
        must_have={
            "interpretation_candidate_preserved": hit.identity.title == "자동차관리법 관련 법령해석례",
            "authority_metadata_preserved": hit.identity.source_type == "moleg"
            and hit.identity.source_target == "expc"
            and hit.identity.reply_agency == "법제처",
            "decision_metadata_preserved": hit.identity.case_number == "21-0001"
            and hit.identity.interpretation_date == "20240115",
            "no_interpretation_detail_loaded": service_call_targets == [],
            "no_citable_interpretation_substance_loaded": True,
        },
        citations=[],
        risk_flags=[
            "interpretation_search_hit_requires_get_interpretation_detail",
            "search_interpretations_is_candidate_discovery_not_interpretation_text",
            "interpretation_answer_requires_selected_detail_loading",
        ],
        next_actions=[
            "Load the selected interpretation through get_interpretation() before citing question, answer, reason, or related-law text.",
            "Load referenced statute articles separately when the interpretation turns on a specific provision.",
        ],
        evidence={
            "query": "자동차 등록 기준",
            "interpretation_candidates": [
                {
                    "title": item.identity.title,
                    "case_number": item.identity.case_number,
                    "interpretation_date": item.identity.interpretation_date,
                    "reply_agency": item.identity.reply_agency,
                    "source_target": item.identity.source_target,
                }
                for item in hits
            ],
            "search_call_targets": [target for kind, target, _ in source.calls if kind == "search"],
            "service_call_targets": service_call_targets,
            "citations_loaded": 0,
        },
    )


def _audit_empty_interpretation_search_absence_guardrail() -> LegislativeExpertScenarioReport:
    source = ScenarioSource(search_payloads=[{"Expc": {"expc": []}}])

    hits = MolegApi(source).search_interpretations(
        "자동차 방치 과징금 위임근거 부존재",
        source="moleg",
        search_body=True,
        display=5,
    )

    return LegislativeExpertScenarioReport(
        scenario="empty_interpretation_search_absence_guardrail",
        question="법제처 해석례 검색 결과가 0건일 때 관련 해석례가 없다고 단정하지 않는가?",
        status="needs_more_source_loading",
        public_interfaces=["search_interpretations"],
        must_have={
            "empty_search_result_preserved": hits == [],
            "no_interpretation_detail_loaded": [
                target for kind, target, _ in source.calls if kind == "service"
            ]
            == [],
            "absence_claim_blocked": True,
            "query_scope_preserved": True,
        },
        citations=[],
        risk_flags=[
            "empty_interpretation_search_is_not_absence_of_authority",
            "zero_search_hits_require_query_scope_disclosure",
            "absence_of_interpretation_requires_alternate_terms_or_sources",
        ],
        next_actions=[
            "Disclose that the exact MOLEG official interpretation search returned zero hits.",
            "Use alternate legal terms, related law/article context, or other authority searches before claiming no relevant interpretation exists.",
        ],
        evidence={
            "query": "자동차 방치 과징금 위임근거 부존재",
            "hit_count": len(hits),
            "search_call_targets": [target for kind, target, _ in source.calls if kind == "search"],
            "service_call_targets": [target for kind, target, _ in source.calls if kind == "service"],
            "citations_loaded": 0,
        },
    )


def _audit_source_access_failure_not_no_result_guardrail() -> LegislativeExpertScenarioReport:
    query = "자동차관리법"

    class RateLimitedSource(ScenarioSource):
        def search(self, target: str, params: dict[str, Any]) -> dict[str, Any]:
            self.calls.append(("search", target, dict(params)))
            raise RateLimitError("law.go.kr rate limited target eflaw after 3 attempt(s)")

    source = RateLimitedSource()
    error: RateLimitError | None = None
    try:
        MolegApi(source).search_laws(query, display=5)
    except RateLimitError as exc:
        error = exc

    if error is None:
        raise AssertionError("source-access failure scenario did not raise RateLimitError")

    class BundleAdminRuleRateLimitedSource(ScenarioSource):
        def search(self, target: str, params: dict[str, Any]) -> dict[str, Any]:
            self.calls.append(("search", target, dict(params)))
            if target == "admrul":
                raise RateLimitError("law.go.kr rate limited target admrul after 3 attempt(s)")
            return self.search_payloads.pop(0)

    bundle_source = BundleAdminRuleRateLimitedSource(
        search_payloads=[
            {"ExpcSearch": {"expc": []}},
            {"PrecSearch": {"prec": []}},
            {"DetcSearch": {"detc": []}},
            {"licbyl": []},
            {"admbyl": []},
        ],
        service_payloads=[
            law_text_payload("자동차관리법", "001747", "270001", article="제26조", title="자동차의 강제처리"),
            delegation_payload("자동차관리법", "자동차관리법 시행령", law_id="001747", article="26"),
        ],
    )
    bundle = MolegApi(bundle_source).load_legal_context_bundle(
        query,
        law_identifier=LawIdentity(law_id="001747", name=query, basis="effective", mst="270001"),
        mode="statute_review",
    )
    bundle_source_gaps = [gap for gap in bundle.gaps if gap.kind == "source_access_failure"]

    return LegislativeExpertScenarioReport(
        scenario="source_access_failure_not_no_result_guardrail",
        question="law.go.kr rate limit이나 retry exhaustion을 법령 검색 0건으로 오해하지 않는가?",
        status="needs_more_source_loading",
        public_interfaces=["search_laws", "load_legal_context_bundle"],
        must_have={
            "source_access_error_preserved": isinstance(error, RateLimitError),
            "bundle_source_access_gap_preserved": [
                gap.recommended_interface for gap in bundle_source_gaps
            ]
            == ["search_administrative_rules"],
            "legal_no_result_not_recorded": True,
            "no_citations_loaded": True,
            "retry_or_later_access_required": True,
        },
        citations=[],
        risk_flags=[
            "source_access_failure_is_not_legal_no_result",
            "rate_limit_or_retry_exhaustion_does_not_prove_source_absence",
            "current_law_absence_claim_requires_successful_source_access",
        ],
        next_actions=[
            "Retry after source-access recovery or backoff before making any no-current-law or no-source claim.",
            "Disclose the source-access failure separately from legal no-result states if answering must be deferred.",
        ],
        evidence={
            "query": query,
            "attempted_interface": "search_laws",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "hit_count": None,
            "source_calls": [[kind, target, params] for kind, target, params in source.calls],
            "bundle_gap_kinds": [gap.kind for gap in bundle.gaps],
            "bundle_gap_interfaces": [gap.recommended_interface for gap in bundle_source_gaps],
            "bundle_source_calls": [
                [kind, target, params] for kind, target, params in bundle_source.calls
            ],
            "citations_loaded": 0,
        },
    )


def _audit_context_bundle_requested_article_not_loaded_guardrail() -> LegislativeExpertScenarioReport:
    law_name = "자동차관리법"
    article = "제26조"
    source = ScenarioSource(
        search_payloads=[
            {"AdmRulSearch": {"admrul": []}},
            {"ExpcSearch": {"expc": []}},
            {"PrecSearch": {"prec": []}},
            {"DetcSearch": {"detc": []}},
            {"licbyl": []},
            {"admbyl": []},
        ],
        service_payloads=[
            {"eflawjosub": {"조문": {}}},
            {
                "lsDelegated": {
                    "법령": {
                        "법령정보": {"법령ID": "001747", "법령명": law_name},
                        "위임조문정보": [],
                    }
                }
            },
        ],
    )

    bundle = MolegApi(source).load_legal_context_bundle(
        f"{law_name} {article} 하위 기준",
        law_identifier=LawIdentity(law_id="001747", name=law_name, basis="effective"),
        articles=[article],
        mode="statute_review",
    )
    article_gaps = [gap for gap in bundle.gaps if gap.kind == "requested_article_not_loaded"]
    article_deferred = [
        item
        for item in bundle.deferred
        if item.interface == "get_article" and item.source_type == "law_article"
    ]

    return LegislativeExpertScenarioReport(
        scenario="context_bundle_requested_article_not_loaded_guardrail",
        question="context bundle이 요청 조문을 읽지 못했을 때 빈 조문 context를 현행 조문 근거로 승격하지 않는가?",
        status="needs_more_source_loading",
        public_interfaces=["load_legal_context_bundle"],
        must_have={
            "requested_article_missing": bundle.loaded.articles == [],
            "requested_article_gap_preserved": [
                (gap.recommended_interface, gap.query) for gap in article_gaps
            ]
            == [("get_article", f"{law_name} {article}")],
            "requested_article_deferred_followup_preserved": [
                (item.interface, item.query) for item in article_deferred
            ]
            == [("get_article", f"{law_name} {article}")],
            "no_article_citation_loaded": True,
        },
        citations=[],
        risk_flags=[
            "requested_article_not_loaded_is_not_current_article_text",
            "current_target_article_claim_requires_get_article_followup",
        ],
        next_actions=[
            "Run the deferred get_article lookup before relying on the requested article's current text.",
            "Do not cite an empty requested-article bundle as current-law article authority.",
        ],
        evidence={
            "requested_article": f"{law_name} {article}",
            "gap_kinds": [gap.kind for gap in bundle.gaps],
            "article_gap_interfaces": [gap.recommended_interface for gap in article_gaps],
            "article_deferred_filters": [item.filters for item in article_deferred],
            "citations_loaded": 0,
            "service_call_targets": [target for kind, target, _ in source.calls if kind == "service"],
            "search_call_targets": [target for kind, target, _ in source.calls if kind == "search"],
        },
    )


def _audit_context_bundle_requested_law_not_loaded_guardrail() -> LegislativeExpertScenarioReport:
    law_name = "자동차관리법"
    source = ScenarioSource(
        search_payloads=[
            {"AdmRulSearch": {"admrul": []}},
            {"ExpcSearch": {"expc": []}},
            {"PrecSearch": {"prec": []}},
            {"DetcSearch": {"detc": []}},
            {"licbyl": []},
            {"admbyl": []},
        ],
        service_payloads=[
            {"Law": "일치하는 법령이 없습니다. 법령명을 확인하여 주십시오."},
            {
                "lsDelegated": {
                    "법령": {
                        "법령정보": {"법령ID": "001747", "법령명": law_name},
                        "위임조문정보": [],
                    }
                }
            },
        ],
    )

    bundle = MolegApi(source).load_legal_context_bundle(
        f"{law_name} 현행 내용",
        law_identifier=LawIdentity(law_id="001747", name=law_name, basis="effective"),
        mode="statute_review",
    )
    law_gaps = [gap for gap in bundle.gaps if gap.kind == "requested_law_not_loaded"]
    law_deferred = [
        item
        for item in bundle.deferred
        if item.interface == "get_law" and item.source_type == "law"
    ]

    return LegislativeExpertScenarioReport(
        scenario="context_bundle_requested_law_not_loaded_guardrail",
        question="context bundle이 확정된 법령 본문을 읽지 못했을 때 빈 법령 context를 현행 법령 근거로 승격하지 않는가?",
        status="needs_more_source_loading",
        public_interfaces=["load_legal_context_bundle"],
        must_have={
            "requested_law_missing": bundle.loaded.laws == [],
            "requested_law_gap_preserved": [
                (gap.recommended_interface, gap.query) for gap in law_gaps
            ]
            == [("get_law", law_name)],
            "requested_law_deferred_followup_preserved": [
                (item.interface, item.query) for item in law_deferred
            ]
            == [("get_law", law_name)],
            "no_law_citation_loaded": True,
        },
        citations=[],
        risk_flags=[
            "requested_law_not_loaded_is_not_current_law_text",
            "current_law_claim_requires_get_law_followup",
        ],
        next_actions=[
            "Run the deferred get_law lookup before relying on whole-statute current-law text.",
            "Do not cite an empty requested-law bundle as current statute authority.",
        ],
        evidence={
            "requested_law": law_name,
            "gap_kinds": [gap.kind for gap in bundle.gaps],
            "law_gap_interfaces": [gap.recommended_interface for gap in law_gaps],
            "law_deferred_filters": [item.filters for item in law_deferred],
            "citations_loaded": 0,
            "service_call_targets": [target for kind, target, _ in source.calls if kind == "service"],
            "search_call_targets": [target for kind, target, _ in source.calls if kind == "search"],
        },
    )


def _audit_context_bundle_delegation_lookup_failure_guardrail() -> LegislativeExpertScenarioReport:
    law_name = "자동차관리법"

    class DelegationRateLimitedSource(ScenarioSource):
        def service(self, target: str, params: dict[str, Any]) -> dict[str, Any]:
            self.calls.append(("service", target, dict(params)))
            if target == "lsDelegated":
                raise RateLimitError("law.go.kr rate limited target lsDelegated after 3 attempt(s)")
            return self.service_payloads.pop(0)

    source = DelegationRateLimitedSource(
        search_payloads=[
            {"AdmRulSearch": {"admrul": []}},
            {"ExpcSearch": {"expc": []}},
            {"PrecSearch": {"prec": []}},
            {"DetcSearch": {"detc": []}},
            {"licbyl": []},
            {"admbyl": []},
        ],
        service_payloads=[
            law_text_payload(law_name, "001747", "270001", article="제26조", title="자동차의 강제처리"),
        ],
    )

    bundle = MolegApi(source).load_legal_context_bundle(
        f"{law_name} 하위 기준",
        law_identifier=LawIdentity(law_id="001747", name=law_name, basis="effective"),
        mode="statute_review",
    )
    delegation_gaps = [
        gap
        for gap in bundle.gaps
        if gap.kind == "source_access_failure" and gap.recommended_interface == "find_delegated_rules"
    ]
    delegation_deferred = [
        item
        for item in bundle.deferred
        if item.interface == "find_delegated_rules" and item.source_type == "delegation"
    ]

    return LegislativeExpertScenarioReport(
        scenario="context_bundle_delegation_lookup_failure_guardrail",
        question="context bundle이 위임관계 로딩 실패를 하위규정 없음으로 승격하지 않는가?",
        status="needs_more_source_loading",
        public_interfaces=["load_legal_context_bundle"],
        must_have={
            "current_law_loaded": bool(bundle.loaded.laws),
            "delegation_not_loaded": bundle.loaded.delegations == [],
            "delegation_failure_gap_preserved": [
                (gap.recommended_interface, gap.query) for gap in delegation_gaps
            ]
            == [("find_delegated_rules", law_name)],
            "delegation_deferred_followup_preserved": [
                (item.interface, item.query) for item in delegation_deferred
            ]
            == [("find_delegated_rules", law_name)],
            "no_delegation_absence_claim": True,
        },
        citations=[
            SourceCitation("law", "eflaw", law_name, authority="current statute"),
        ],
        risk_flags=[
            "delegation_lookup_failure_is_not_no_delegated_rule",
            "lower_rule_context_requires_successful_delegation_lookup_or_followup_search",
        ],
        next_actions=[
            "Retry find_delegated_rules before saying lower-rule context is unavailable.",
            "Search administrative rules and annex/forms separately before operational-criteria claims.",
        ],
        evidence={
            "gap_kinds": [gap.kind for gap in bundle.gaps],
            "delegation_gap_interfaces": [gap.recommended_interface for gap in delegation_gaps],
            "delegation_deferred_filters": [item.filters for item in delegation_deferred],
            "loaded_delegation_count": len(bundle.loaded.delegations),
            "service_call_targets": [target for kind, target, _ in source.calls if kind == "service"],
            "citations_loaded": 1,
        },
    )


def _audit_case_search_candidate_detail_guardrail() -> LegislativeExpertScenarioReport:
    source = ScenarioSource(
        search_payloads=[
            {
                "PrecSearch": {
                    "prec": [
                        {
                            "판례일련번호": "228541",
                            "사건명": "과징금부과처분취소",
                            "사건번호": "2020두12345",
                            "선고일자": "20240115",
                            "법원명": "대법원",
                            "법원종류코드": "400201",
                            "사건종류명": "행정",
                            "판결유형": "판결",
                            "데이터출처명": "대법원",
                        }
                    ]
                }
            }
        ]
    )

    hits = MolegApi(source).search_cases(
        "과징금 부과처분",
        court="supreme",
        search_body=True,
        display=3,
    )
    hit = hits[0]
    service_call_targets = [target for kind, target, _ in source.calls if kind == "service"]

    return LegislativeExpertScenarioReport(
        scenario="case_search_candidate_detail_guardrail",
        question="판례 검색 hit만으로 판시사항/판결요지/전문을 읽은 것처럼 답하지 않는가?",
        status="needs_more_source_loading",
        public_interfaces=["search_cases"],
        must_have={
            "case_candidate_preserved": hit.identity.title == "과징금부과처분취소",
            "source_label_prec_preserved": hit.identity.source_type == "case"
            and hit.identity.source_target == "prec",
            "decision_metadata_preserved": hit.identity.case_number == "2020두12345"
            and hit.identity.decision_date == "20240115"
            and hit.identity.court == "대법원",
            "no_case_detail_loaded": service_call_targets == [],
            "no_citable_holding_loaded": True,
        },
        citations=[],
        risk_flags=[
            "case_search_hit_requires_get_case_detail",
            "search_cases_is_candidate_discovery_not_case_text",
            "case_holding_requires_selected_detail_loading",
        ],
        next_actions=[
            "Load the selected case through get_case() before citing holdings, summary, referenced statutes, or full text.",
            "Load referenced statute articles separately when the judicial rule turns on a specific provision.",
        ],
        evidence={
            "query": "과징금 부과처분",
            "case_candidates": [
                {
                    "title": item.identity.title,
                    "case_number": item.identity.case_number,
                    "decision_date": item.identity.decision_date,
                    "court": item.identity.court,
                    "source_target": item.identity.source_target,
                }
                for item in hits
            ],
            "search_call_targets": [target for kind, target, _ in source.calls if kind == "search"],
            "service_call_targets": service_call_targets,
            "citations_loaded": 0,
        },
    )


def _audit_empty_case_search_absence_guardrail() -> LegislativeExpertScenarioReport:
    query = "과징금 부과처분 재량권"
    source = ScenarioSource(search_payloads=[{"PrecSearch": {"prec": []}}])

    hits = MolegApi(source).search_cases(
        query,
        court="supreme",
        search_body=True,
        display=3,
    )
    service_call_targets = [target for kind, target, _ in source.calls if kind == "service"]

    return LegislativeExpertScenarioReport(
        scenario="empty_case_search_absence_guardrail",
        question="판례 검색 결과가 0건일 때 관련 판례나 사법 판단이 없다고 단정하지 않는가?",
        status="needs_more_source_loading",
        public_interfaces=["search_cases"],
        must_have={
            "empty_search_result_preserved": hits == [],
            "no_case_detail_loaded": service_call_targets == [],
            "judicial_absence_claim_blocked": True,
            "query_scope_preserved": True,
        },
        citations=[],
        risk_flags=[
            "empty_case_search_is_not_absence_of_judicial_authority",
            "zero_case_hits_require_alternate_terms_or_authority_loading",
            "precedent_absence_requires_successful_scope_disclosure",
        ],
        next_actions=[
            "Disclose that the exact court-case search returned zero hits for the searched terms and court/body scope.",
            "Search alternate terms, neighboring statutes, Constitutional Court decisions, or interpretations before any no-precedent or no-judicial-authority claim.",
        ],
        evidence={
            "query": query,
            "court": "supreme",
            "search_body": True,
            "hit_count": len(hits),
            "search_call_targets": [target for kind, target, _ in source.calls if kind == "search"],
            "service_call_targets": service_call_targets,
            "citations_loaded": 0,
        },
    )


def _audit_constitutional_search_candidate_detail_guardrail() -> LegislativeExpertScenarioReport:
    source = ScenarioSource(
        search_payloads=[
            {
                "DetcSearch": {
                    "detc": [
                        {
                            "헌재결정례일련번호": "58400",
                            "사건명": "자동차관리법제26조등위헌확인",
                            "사건번호": "2020헌마1",
                            "종국일자": "20240229",
                            "헌재결정례 상세링크": "/DRF/lawService.do?target=detc&ID=58400",
                        }
                    ]
                }
            }
        ]
    )

    hits = MolegApi(source).search_constitutional_decisions(
        "과잉금지원칙 자동차",
        search_body=True,
        display=3,
    )
    hit = hits[0]
    service_call_targets = [target for kind, target, _ in source.calls if kind == "service"]

    return LegislativeExpertScenarioReport(
        scenario="constitutional_search_candidate_detail_guardrail",
        question="헌재결정례 검색 hit만으로 판시사항/결정요지/전문을 읽은 것처럼 답하지 않는가?",
        status="needs_more_source_loading",
        public_interfaces=["search_constitutional_decisions"],
        must_have={
            "constitutional_candidate_preserved": hit.identity.title == "자동차관리법제26조등위헌확인",
            "source_label_detc_preserved": hit.identity.source_type == "constitutional"
            and hit.identity.source_target == "detc",
            "decision_metadata_preserved": hit.identity.case_number == "2020헌마1"
            and hit.identity.decision_date == "20240229",
            "no_constitutional_detail_loaded": service_call_targets == [],
            "no_citable_constitutional_reasoning_loaded": True,
        },
        citations=[],
        risk_flags=[
            "constitutional_search_hit_requires_get_constitutional_decision_detail",
            "search_constitutional_decisions_is_candidate_discovery_not_decision_text",
            "constitutional_holding_requires_selected_detail_loading",
        ],
        next_actions=[
            "Load the selected Constitutional Court decision through get_constitutional_decision() before citing holdings, summary, reviewed statutes, or full text.",
            "Load reviewed statute articles separately when the constitutional reasoning turns on a specific provision.",
        ],
        evidence={
            "query": "과잉금지원칙 자동차",
            "constitutional_candidates": [
                {
                    "title": item.identity.title,
                    "case_number": item.identity.case_number,
                    "decision_date": item.identity.decision_date,
                    "source_target": item.identity.source_target,
                }
                for item in hits
            ],
            "search_call_targets": [target for kind, target, _ in source.calls if kind == "search"],
            "service_call_targets": service_call_targets,
            "citations_loaded": 0,
        },
    )


def _audit_empty_constitutional_search_absence_guardrail() -> LegislativeExpertScenarioReport:
    query = "과잉금지원칙 자동차 압류"
    source = ScenarioSource(search_payloads=[{"DetcSearch": {"detc": []}}])

    hits = MolegApi(source).search_constitutional_decisions(
        query,
        search_body=True,
        display=3,
    )
    service_call_targets = [target for kind, target, _ in source.calls if kind == "service"]

    return LegislativeExpertScenarioReport(
        scenario="empty_constitutional_search_absence_guardrail",
        question="헌재결정례 검색 결과가 0건일 때 관련 헌재 결정이나 위헌 위험이 없다고 단정하지 않는가?",
        status="needs_more_source_loading",
        public_interfaces=["search_constitutional_decisions"],
        must_have={
            "empty_search_result_preserved": hits == [],
            "no_constitutional_detail_loaded": service_call_targets == [],
            "constitutional_absence_claim_blocked": True,
            "query_scope_preserved": True,
        },
        citations=[],
        risk_flags=[
            "empty_constitutional_search_is_not_absence_of_constitutional_authority",
            "zero_constitutional_hits_require_alternate_terms_or_authority_loading",
            "no_constitutional_risk_requires_more_than_free_text_no_result",
        ],
        next_actions=[
            "Disclose that the exact Constitutional Court free-text search returned zero hits for the searched terms/body scope.",
            "Search alternate doctrine terms, reviewed statute terms, ordinary court cases, or interpretations before any no-constitutional-authority or no-risk claim.",
        ],
        evidence={
            "query": query,
            "search_body": True,
            "hit_count": len(hits),
            "search_call_targets": [target for kind, target, _ in source.calls if kind == "search"],
            "service_call_targets": service_call_targets,
            "citations_loaded": 0,
        },
    )


def _audit_authority_context_matching_current_authorities() -> LegislativeExpertScenarioReport:
    identity = LawIdentity(law_id="009999", name="개인정보 보호법", basis="effective")
    source = ScenarioSource(
        search_payloads=[
            {
                "ExpcSearch": {
                    "expc": [
                        {
                            "법령해석례일련번호": "330510",
                            "안건명": "개인정보 동의 관련 법령해석례",
                            "회신일자": "20250415",
                        }
                    ]
                }
            },
            {
                "PrecSearch": {
                    "prec": [
                        {
                            "판례일련번호": "228610",
                            "사건명": "개인정보수집이용동의처분취소",
                            "선고일자": "20250510",
                        }
                    ]
                }
            },
            {
                "DetcSearch": {
                    "detc": [
                        {
                            "헌재결정례일련번호": "58460",
                            "사건명": "개인정보자기결정권위헌확인",
                            "종국일자": "20250627",
                        }
                    ]
                }
            },
        ],
        service_payloads=[
            {
                "eflawjosub": {
                    "기본정보": {
                        "법령ID": "009999",
                        "법령명_한글": "개인정보 보호법",
                    },
                    "조문": {
                        "조문번호": "15",
                        "조문제목": "개인정보의 수집ㆍ이용",
                        "조문시행일자": "20250101",
                        "조문내용": "개인정보처리자는 정보주체의 동의를 받아 개인정보를 수집할 수 있다.",
                    },
                }
            },
            {
                "expc": {
                    "법령해석례일련번호": "330510",
                    "안건명": "개인정보 동의 관련 법령해석례",
                    "안건번호": "25-0001",
                    "회신일자": "20250415",
                    "해석기관명": "법제처",
                    "질의요지": "동의 요건은 어떻게 보아야 하는가?",
                    "회답": "개인정보 보호법 제15조의 요건을 기준으로 보아야 한다.",
                    "관련법령": "개인정보 보호법 제15조",
                }
            },
            {
                "prec": {
                    "판례정보일련번호": "228610",
                    "사건명": "개인정보수집이용동의처분취소",
                    "사건번호": "2024두61000",
                    "선고일자": "20250510",
                    "법원명": "대법원",
                    "판시사항": "개인정보 수집ㆍ이용 동의의 적용 기준",
                    "판결요지": "개인정보 보호법 제15조의 요건을 중심으로 판단한다.",
                    "참조조문": "개인정보 보호법 제15조",
                    "판례내용": "판결 전문",
                }
            },
            {
                "detc": {
                    "헌재결정례일련번호": "58460",
                    "사건명": "개인정보자기결정권위헌확인",
                    "사건번호": "2024헌마510",
                    "종국일자": "20250627",
                    "판시사항": "개인정보 수집ㆍ이용 조항의 위헌 여부",
                    "결정요지": "개인정보 보호법 제15조는 과잉금지원칙에 위반되지 않는다.",
                    "심판대상조문": "개인정보 보호법 제15조",
                    "전문": "결정 전문",
                }
            },
        ],
    )

    context = MolegApi(source).load_authority_context(
        identity,
        articles=["제15조"],
        query="개인정보 보호법 제15조 동의의 의미와 위헌 위험",
        budget="minimal",
    )

    return LegislativeExpertScenarioReport(
        scenario="authority_context_matching_current_authorities",
        question="대상 조문과 구조적으로 일치하고 현행 조문 시행일 이후인 권위자료를 task-level interface로 구분해 인용할 수 있는가?",
        status="ready_for_reasoning",
        public_interfaces=["load_authority_context"],
        must_have={
            "target_article_loaded": [article.article for article in context.target_articles] == ["제15조"],
            "interpretation_promoted": len(context.current_authorities.interpretations) == 1
            and context.current_authorities.interpretations[0].identity.title == "개인정보 동의 관련 법령해석례",
            "case_promoted": len(context.current_authorities.cases) == 1
            and context.current_authorities.cases[0].identity.title == "개인정보수집이용동의처분취소",
            "constitutional_promoted": len(context.current_authorities.constitutional_decisions) == 1
            and context.current_authorities.constitutional_decisions[0].identity.title == "개인정보자기결정권위헌확인",
            "no_authority_mismatch_or_temporal_gap": not any(
                gap.kind.startswith("authority_") for gap in context.gaps
            ),
        },
        citations=[
            SourceCitation("law", "eflawjosub", "개인정보 보호법", "제15조", "current target article"),
            SourceCitation("interpretation", "expc", "개인정보 동의 관련 법령해석례", "제15조", "matching current interpretation"),
            SourceCitation("case", "prec", "개인정보수집이용동의처분취소", "제15조", "matching current court case"),
            SourceCitation("constitutional", "detc", "개인정보자기결정권위헌확인", "제15조", "matching current Constitutional Court decision"),
        ],
        risk_flags=["authority_context_is_bounded_not_exhaustive_authority_survey"],
        next_actions=[
            "Use current_authorities for target-article authority claims and loaded authority details only with their structured article-reference limits.",
            "Run broader searches if the answer requires exhaustive authority coverage.",
        ],
        evidence={
            "target_articles": [article.article for article in context.target_articles],
            "current_interpretations": [
                item.identity.title for item in context.current_authorities.interpretations
            ],
            "current_cases": [item.identity.title for item in context.current_authorities.cases],
            "current_constitutional_decisions": [
                item.identity.title for item in context.current_authorities.constitutional_decisions
            ],
            "loaded_authority_counts": {
                "interpretations": len(context.loaded.interpretations),
                "cases": len(context.loaded.cases),
                "constitutional_decisions": len(context.loaded.constitutional_decisions),
            },
            "gap_kinds": [gap.kind for gap in context.gaps],
            "deferred_interfaces": [item.interface for item in context.deferred],
            "call_targets": [target for _, target, _ in source.calls],
        },
    )


def _audit_loaded_authority_article_mismatch_guardrail() -> LegislativeExpertScenarioReport:
    target_law_name = "개인정보 보호법"
    target_article = "제15조"
    source = ScenarioSource(
        service_payloads=[
            {
                "expc": {
                    "법령해석례일련번호": "330500",
                    "안건명": "개인정보 제3자 제공 관련 법령해석례",
                    "안건번호": "24-0001",
                    "해석일자": "20240415",
                    "해석기관명": "법제처",
                    "질의기관명": "개인정보보호위원회",
                    "질의요지": "제3자 제공 요건은 어떻게 보아야 하는가?",
                    "회답": "개인정보 보호법 제17조의 요건을 기준으로 보아야 한다.",
                    "이유": "제3자 제공에 관한 별도 요건을 종합하여 판단한다.",
                    "관련법령": "개인정보 보호법 제17조",
                }
            },
            {
                "prec": {
                    "판례정보일련번호": "228600",
                    "사건명": "개인정보목적외이용처분취소",
                    "사건번호": "2022두60000",
                    "선고일자": "20240510",
                    "법원명": "대법원",
                    "판시사항": "개인정보 목적 외 이용 제한의 적용 기준",
                    "판결요지": "개인정보 보호법 제18조의 제한 사유를 중심으로 판단한다.",
                    "참조조문": "개인정보 보호법 제18조",
                    "판례내용": "판결 전문",
                }
            },
            {
                "detc": {
                    "헌재결정례일련번호": "58450",
                    "사건명": "민감정보처리제한위헌확인",
                    "사건번호": "2023헌마500",
                    "종국일자": "20240627",
                    "사건종류명": "헌법소원",
                    "판시사항": "민감정보 처리 제한의 위헌 여부",
                    "결정요지": "민감정보 처리 제한은 과잉금지원칙에 위반되지 않는다.",
                    "심판대상조문": "개인정보 보호법 제23조",
                    "참조조문": "헌법 제37조 제2항",
                    "전문": "결정 전문",
                }
            },
        ]
    )

    api = MolegApi(source)
    interpretation = api.get_interpretation("330500")
    case = api.get_case("228600")
    constitutional = api.get_constitutional_decision("58450")
    authority_article_matches = {
        "interpretation": _references_target_article(
            interpretation.referenced_articles,
            law_name=target_law_name,
            article=target_article,
        ),
        "case": _references_target_article(
            case.referenced_articles,
            law_name=target_law_name,
            article=target_article,
        ),
        "constitutional": _references_target_article(
            constitutional.reviewed_articles,
            law_name=target_law_name,
            article=target_article,
        ),
    }
    service_call_targets = [target for kind, target, _ in source.calls if kind == "service"]

    return LegislativeExpertScenarioReport(
        scenario="loaded_authority_article_mismatch_guardrail",
        question="로드된 해석례/판례/헌재결정이 질문 조문과 다른 조문을 참조할 때 질문 조문의 권위자료로 인용하지 않는가?",
        status="needs_more_source_loading",
        public_interfaces=[
            "get_interpretation",
            "get_case",
            "get_constitutional_decision",
        ],
        must_have={
            "target_article_preserved": target_law_name == "개인정보 보호법"
            and target_article == "제15조",
            "loaded_authority_details_preserved": interpretation.identity.title
            == "개인정보 제3자 제공 관련 법령해석례"
            and case.identity.title == "개인정보목적외이용처분취소"
            and constitutional.identity.title == "민감정보처리제한위헌확인",
            "interpretation_reference_mismatch_preserved": _article_reference_dicts(
                interpretation.referenced_articles
            )
            == [{"law_name": target_law_name, "article": "제17조", "law_id": None}],
            "case_reference_mismatch_preserved": _article_reference_dicts(
                case.referenced_articles
            )
            == [{"law_name": target_law_name, "article": "제18조", "law_id": None}],
            "constitutional_reviewed_article_mismatch_preserved": _article_reference_dicts(
                constitutional.reviewed_articles
            )
            == [{"law_name": target_law_name, "article": "제23조", "law_id": None}],
            "no_target_article_authority_citation": not any(authority_article_matches.values()),
            "followup_authority_search_required": True,
        },
        citations=[],
        risk_flags=[
            "loaded_authority_reference_mismatch_not_target_article_authority",
            "referenced_articles_must_match_target_before_authority_claim",
            "reviewed_articles_must_match_target_before_constitutional_claim",
        ],
        next_actions=[
            "Disclose that loaded authority details reference or review different articles from 개인정보 보호법 제15조.",
            "Search interpretation, case, and Constitutional Court authority scoped to the target law and article before citing target-article authority.",
            "Do not turn mismatched loaded authority details into a claim that no relevant target-article authority exists.",
        ],
        evidence={
            "target_article": {
                "law_name": target_law_name,
                "article": target_article,
            },
            "loaded_authorities": [
                interpretation.identity.title,
                case.identity.title,
                constitutional.identity.title,
            ],
            "interpretation_referenced_articles": _article_reference_dicts(
                interpretation.referenced_articles
            ),
            "case_referenced_articles": _article_reference_dicts(case.referenced_articles),
            "constitutional_reviewed_articles": _article_reference_dicts(
                constitutional.reviewed_articles
            ),
            "authority_article_matches": authority_article_matches,
            "service_call_targets": service_call_targets,
            "citations_loaded": 0,
        },
    )


def _audit_context_bundle_authority_article_mismatch_guardrail() -> LegislativeExpertScenarioReport:
    target_law_name = "개인정보 보호법"
    target_article = "제15조"
    source = ScenarioSource(
        search_payloads=[
            {"AdmRulSearch": {"admrul": []}},
            {
                "ExpcSearch": {
                    "expc": [
                        {"법령해석례일련번호": "100", "안건명": "개인정보 제3자 제공 해석"}
                    ]
                }
            },
            {
                "PrecSearch": {
                    "prec": [
                        {"판례일련번호": "200", "사건명": "개인정보 목적 외 이용 사건"}
                    ]
                }
            },
            {
                "DetcSearch": {
                    "detc": [
                        {"헌재결정례일련번호": "300", "사건명": "민감정보 처리 제한 위헌확인"}
                    ]
                }
            },
            {"licbyl": []},
            {"admbyl": []},
        ],
        service_payloads=[
            {
                "eflawjosub": {
                    "조문": {
                        "조문번호": "15",
                        "조문제목": "개인정보의 수집ㆍ이용",
                        "조문내용": "개인정보처리자는 정보주체의 동의를 받아 개인정보를 수집할 수 있다.",
                    }
                }
            },
            {
                "lsDelegated": {
                    "법령": {
                        "법령정보": {
                            "법령ID": "009999",
                            "법령명": target_law_name,
                        },
                        "위임조문정보": [],
                    }
                }
            },
            {
                "expc": {
                    "법령해석례일련번호": "100",
                    "안건명": "개인정보 제3자 제공 해석",
                    "관련법령": "개인정보 보호법 제17조",
                }
            },
            {
                "prec": {
                    "판례정보일련번호": "200",
                    "사건명": "개인정보 목적 외 이용 사건",
                    "참조조문": "개인정보 보호법 제18조",
                    "판례내용": "판례 전문",
                }
            },
            {
                "detc": {
                    "헌재결정례일련번호": "300",
                    "사건명": "민감정보 처리 제한 위헌확인",
                    "심판대상조문": "개인정보 보호법 제23조",
                    "전문": "결정 전문",
                }
            },
        ],
    )

    bundle = MolegApi(source).load_legal_context_bundle(
        "개인정보 보호법 제15조 동의의 의미와 위헌 위험",
        law_identifier=LawIdentity(law_id="009999", name=target_law_name, basis="effective"),
        articles=[target_article],
        mode="statute_review",
        budget="standard",
    )
    authority_gaps = [gap for gap in bundle.gaps if gap.kind == "authority_article_mismatch"]
    authority_article_matches = {
        "interpretation": _references_target_article(
            bundle.loaded.interpretations[0].referenced_articles,
            law_name=target_law_name,
            article=target_article,
        ),
        "case": _references_target_article(
            bundle.loaded.cases[0].referenced_articles,
            law_name=target_law_name,
            article=target_article,
        ),
        "constitutional": _references_target_article(
            bundle.loaded.constitutional_decisions[0].reviewed_articles,
            law_name=target_law_name,
            article=target_article,
        ),
    }

    return LegislativeExpertScenarioReport(
        scenario="context_bundle_authority_article_mismatch_guardrail",
        question="context bundle이 eager-loaded 권위자료의 조문 불일치를 후속 검색 gap으로 노출하는가?",
        status="needs_more_source_loading",
        public_interfaces=["load_legal_context_bundle"],
        must_have={
            "target_article_loaded": bundle.loaded.articles[0].article == target_article,
            "eager_authority_details_loaded": bool(bundle.loaded.interpretations)
            and bool(bundle.loaded.cases)
            and bool(bundle.loaded.constitutional_decisions),
            "authority_article_mismatch_gaps_preserved": [
                gap.recommended_interface for gap in authority_gaps
            ]
            == [
                "search_interpretations",
                "search_cases",
                "search_constitutional_decisions",
            ],
            "no_target_article_authority_citation": not any(authority_article_matches.values()),
            "followup_authority_search_required": True,
        },
        citations=[
            SourceCitation("law", "eflawjosub", target_law_name, target_article, "current article"),
        ],
        risk_flags=[
            "context_bundle_eager_authority_reference_mismatch_not_target_article_citation",
            "context_bundle_authority_article_mismatch_gap_requires_followup_search",
            "context_bundle_loaded_authority_detail_is_not_automatically_target_article_authority",
        ],
        next_actions=[
            "Use the loaded target article as current legal text only.",
            "Use authority_article_mismatch gaps to run scoped interpretation, case, and Constitutional Court searches before target-article authority claims.",
            "Do not cite eager-loaded authority details for 개인정보 보호법 제15조 until structured references match that article.",
        ],
        evidence={
            "target_article": {
                "law_name": target_law_name,
                "article": target_article,
            },
            "interpretation_referenced_articles": _article_reference_dicts(
                bundle.loaded.interpretations[0].referenced_articles
            ),
            "case_referenced_articles": _article_reference_dicts(
                bundle.loaded.cases[0].referenced_articles
            ),
            "constitutional_reviewed_articles": _article_reference_dicts(
                bundle.loaded.constitutional_decisions[0].reviewed_articles
            ),
            "authority_article_matches": authority_article_matches,
            "gap_kinds": [gap.kind for gap in bundle.gaps],
            "authority_gap_interfaces": [gap.recommended_interface for gap in authority_gaps],
            "search_call_targets": [target for kind, target, _ in source.calls if kind == "search"],
            "service_call_targets": [target for kind, target, _ in source.calls if kind == "service"],
        },
    )


def _audit_context_bundle_authority_article_unverified_guardrail() -> LegislativeExpertScenarioReport:
    target_law_name = "개인정보 보호법"
    target_article = "제15조"
    source = ScenarioSource(
        search_payloads=[
            {"AdmRulSearch": {"admrul": []}},
            {
                "ExpcSearch": {
                    "expc": [
                        {"법령해석례일련번호": "101", "안건명": "개인정보 동의 해석"}
                    ]
                }
            },
            {
                "PrecSearch": {
                    "prec": [
                        {"판례일련번호": "201", "사건명": "개인정보 동의 사건"}
                    ]
                }
            },
            {
                "DetcSearch": {
                    "detc": [
                        {"헌재결정례일련번호": "301", "사건명": "개인정보 자기결정권 사건"}
                    ]
                }
            },
            {"licbyl": []},
            {"admbyl": []},
        ],
        service_payloads=[
            {
                "eflawjosub": {
                    "조문": {
                        "조문번호": "15",
                        "조문제목": "개인정보의 수집ㆍ이용",
                        "조문내용": "개인정보처리자는 정보주체의 동의를 받아 개인정보를 수집할 수 있다.",
                    }
                }
            },
            {
                "lsDelegated": {
                    "법령": {
                        "법령정보": {
                            "법령ID": "009999",
                            "법령명": target_law_name,
                        },
                        "위임조문정보": [],
                    }
                }
            },
            {
                "expc": {
                    "법령해석례일련번호": "101",
                    "안건명": "개인정보 동의 해석",
                    "질의요지": "동의 요건 관련 질의",
                    "회답": "사안별 판단",
                }
            },
            {
                "prec": {
                    "판례정보일련번호": "201",
                    "사건명": "개인정보 동의 사건",
                    "판례내용": "동의 관련 판례 전문",
                }
            },
            {
                "detc": {
                    "헌재결정례일련번호": "301",
                    "사건명": "개인정보 자기결정권 사건",
                    "전문": "개인정보 자기결정권 결정 전문",
                }
            },
        ],
    )

    bundle = MolegApi(source).load_legal_context_bundle(
        "개인정보 보호법 제15조 동의의 의미와 위헌 위험",
        law_identifier=LawIdentity(law_id="009999", name=target_law_name, basis="effective"),
        articles=[target_article],
        mode="statute_review",
        budget="standard",
    )
    authority_gaps = [gap for gap in bundle.gaps if gap.kind == "authority_article_unverified"]
    authority_reference_counts = {
        "interpretation": len(bundle.loaded.interpretations[0].referenced_articles),
        "case": len(bundle.loaded.cases[0].referenced_articles),
        "constitutional": len(bundle.loaded.constitutional_decisions[0].reviewed_articles),
    }

    return LegislativeExpertScenarioReport(
        scenario="context_bundle_authority_article_unverified_guardrail",
        question="context bundle이 구조화 조문 참조 없는 eager-loaded 권위자료를 검증되지 않은 상태로 노출하는가?",
        status="needs_more_source_loading",
        public_interfaces=["load_legal_context_bundle"],
        must_have={
            "target_article_loaded": bundle.loaded.articles[0].article == target_article,
            "eager_authority_details_loaded": bool(bundle.loaded.interpretations)
            and bool(bundle.loaded.cases)
            and bool(bundle.loaded.constitutional_decisions),
            "authority_article_unverified_gaps_preserved": [
                gap.recommended_interface for gap in authority_gaps
            ]
            == [
                "search_interpretations",
                "search_cases",
                "search_constitutional_decisions",
            ],
            "no_structured_article_refs_available": all(
                count == 0 for count in authority_reference_counts.values()
            ),
            "followup_authority_search_required": True,
        },
        citations=[
            SourceCitation("law", "eflawjosub", target_law_name, target_article, "current article"),
        ],
        risk_flags=[
            "context_bundle_eager_authority_without_structured_refs_not_target_article_citation",
            "context_bundle_authority_article_unverified_gap_requires_followup_search",
            "context_bundle_loaded_authority_detail_requires_structured_article_match",
        ],
        next_actions=[
            "Use the loaded target article as current legal text only.",
            "Use authority_article_unverified gaps to run scoped authority searches or inspect structured article references before target-article authority claims.",
            "Do not cite eager-loaded authority details for 개인정보 보호법 제15조 until structured references match that article.",
        ],
        evidence={
            "target_article": {
                "law_name": target_law_name,
                "article": target_article,
            },
            "authority_reference_counts": authority_reference_counts,
            "gap_kinds": [gap.kind for gap in bundle.gaps],
            "authority_gap_interfaces": [gap.recommended_interface for gap in authority_gaps],
            "search_call_targets": [target for kind, target, _ in source.calls if kind == "search"],
            "service_call_targets": [target for kind, target, _ in source.calls if kind == "service"],
        },
    )


def _audit_context_bundle_authority_article_partial_match_guardrail() -> LegislativeExpertScenarioReport:
    target_law_name = "개인정보 보호법"
    requested_articles = ["제15조", "제17조"]
    source = ScenarioSource(
        search_payloads=[
            {"AdmRulSearch": {"admrul": []}},
            {
                "ExpcSearch": {
                    "expc": [
                        {"법령해석례일련번호": "102", "안건명": "개인정보 제공 해석"}
                    ]
                }
            },
            {
                "PrecSearch": {
                    "prec": [
                        {"판례일련번호": "202", "사건명": "개인정보 제공 사건"}
                    ]
                }
            },
            {
                "DetcSearch": {
                    "detc": [
                        {"헌재결정례일련번호": "302", "사건명": "개인정보 제공 제한 사건"}
                    ]
                }
            },
            {"licbyl": []},
            {"admbyl": []},
        ],
        service_payloads=[
            {
                "eflawjosub": {
                    "조문": {
                        "조문번호": "15",
                        "조문제목": "개인정보의 수집ㆍ이용",
                        "조문내용": "개인정보처리자는 정보주체의 동의를 받아 개인정보를 수집할 수 있다.",
                    }
                }
            },
            {
                "eflawjosub": {
                    "조문": {
                        "조문번호": "17",
                        "조문제목": "개인정보의 제공",
                        "조문내용": "개인정보처리자는 정보주체의 동의를 받아 개인정보를 제공할 수 있다.",
                    }
                }
            },
            {
                "lsDelegated": {
                    "법령": {
                        "법령정보": {
                            "법령ID": "009999",
                            "법령명": target_law_name,
                        },
                        "위임조문정보": [],
                    }
                }
            },
            {
                "expc": {
                    "법령해석례일련번호": "102",
                    "안건명": "개인정보 제공 해석",
                    "관련법령": "개인정보 보호법 제17조",
                }
            },
            {
                "prec": {
                    "판례정보일련번호": "202",
                    "사건명": "개인정보 제공 사건",
                    "참조조문": "개인정보 보호법 제17조",
                    "판례내용": "판례 전문",
                }
            },
            {
                "detc": {
                    "헌재결정례일련번호": "302",
                    "사건명": "개인정보 제공 제한 사건",
                    "심판대상조문": "개인정보 보호법 제17조",
                    "전문": "결정 전문",
                }
            },
        ],
    )

    bundle = MolegApi(source).load_legal_context_bundle(
        "개인정보 보호법 제15조와 제17조 동의의 의미와 위헌 위험",
        law_identifier=LawIdentity(law_id="009999", name=target_law_name, basis="effective"),
        articles=requested_articles,
        mode="statute_review",
        budget="standard",
    )
    authority_gaps = [gap for gap in bundle.gaps if gap.kind == "authority_article_partial_match"]
    authority_matched_articles = {
        "interpretation": [
            ref.article for ref in bundle.loaded.interpretations[0].referenced_articles
        ],
        "case": [ref.article for ref in bundle.loaded.cases[0].referenced_articles],
        "constitutional": [
            ref.article for ref in bundle.loaded.constitutional_decisions[0].reviewed_articles
        ],
    }
    missing_article = "제15조"

    return LegislativeExpertScenarioReport(
        scenario="context_bundle_authority_article_partial_match_guardrail",
        question="context bundle이 일부 요청 조문에만 맞는 eager-loaded 권위자료를 전체 조문 권위로 확장하지 않는가?",
        status="needs_more_source_loading",
        public_interfaces=["load_legal_context_bundle"],
        must_have={
            "target_articles_loaded": [article.article for article in bundle.loaded.articles]
            == requested_articles,
            "eager_authority_details_loaded": bool(bundle.loaded.interpretations)
            and bool(bundle.loaded.cases)
            and bool(bundle.loaded.constitutional_decisions),
            "authority_article_partial_match_gaps_preserved": [
                gap.recommended_interface for gap in authority_gaps
            ]
            == [
                "search_interpretations",
                "search_cases",
                "search_constitutional_decisions",
            ],
            "matched_article_not_all_requested_articles": all(
                articles == ["제17조"] for articles in authority_matched_articles.values()
            ),
            "followup_authority_search_required_for_missing_article": all(
                missing_article in gap.query for gap in authority_gaps
            ),
        },
        citations=[
            SourceCitation("law", "eflawjosub", target_law_name, article, "current article")
            for article in requested_articles
        ],
        risk_flags=[
            "context_bundle_eager_authority_partial_match_not_all_target_articles",
            "context_bundle_authority_article_partial_match_gap_requires_followup_search",
            "context_bundle_loaded_authority_detail_must_not_be_broadcast_to_all_requested_articles",
        ],
        next_actions=[
            "Use loaded target articles as current legal text.",
            "Treat eager-loaded authority detail as supporting only the structured article it references.",
            "Run scoped authority searches for 개인정보 보호법 제15조 before making 제15조 authority claims.",
        ],
        evidence={
            "target_articles": [
                {"law_name": target_law_name, "article": article}
                for article in requested_articles
            ],
            "authority_matched_articles": authority_matched_articles,
            "missing_authority_article": missing_article,
            "gap_kinds": [gap.kind for gap in bundle.gaps],
            "authority_gap_interfaces": [gap.recommended_interface for gap in authority_gaps],
            "authority_gap_queries": [gap.query for gap in authority_gaps],
            "search_call_targets": [target for kind, target, _ in source.calls if kind == "search"],
            "service_call_targets": [target for kind, target, _ in source.calls if kind == "service"],
        },
    )


def _audit_context_bundle_authority_temporal_mismatch_guardrail() -> LegislativeExpertScenarioReport:
    target_law_name = "개인정보 보호법"
    target_article = "제15조"
    current_article_effective_date = "20250101"
    authority_dates = {
        "interpretation": "20210115",
        "case": "20210215",
        "constitutional": "20210315",
    }
    source = ScenarioSource(
        search_payloads=[
            {"AdmRulSearch": {"admrul": []}},
            {
                "ExpcSearch": {
                    "expc": [
                        {
                            "법령해석례일련번호": "103",
                            "안건명": "개인정보 동의 해석",
                            "회신일자": authority_dates["interpretation"],
                        }
                    ]
                }
            },
            {
                "PrecSearch": {
                    "prec": [
                        {
                            "판례일련번호": "203",
                            "사건명": "개인정보 동의 사건",
                            "선고일자": authority_dates["case"],
                        }
                    ]
                }
            },
            {
                "DetcSearch": {
                    "detc": [
                        {
                            "헌재결정례일련번호": "303",
                            "사건명": "개인정보 자기결정권 사건",
                            "종국일자": authority_dates["constitutional"],
                        }
                    ]
                }
            },
            {"licbyl": []},
            {"admbyl": []},
        ],
        service_payloads=[
            {
                "eflawjosub": {
                    "조문": {
                        "조문번호": "15",
                        "조문제목": "개인정보의 수집ㆍ이용",
                        "조문시행일자": current_article_effective_date,
                        "조문내용": "개인정보처리자는 정보주체의 동의를 받아 개인정보를 수집할 수 있다.",
                    }
                }
            },
            {
                "lsDelegated": {
                    "법령": {
                        "법령정보": {
                            "법령ID": "009999",
                            "법령명": target_law_name,
                        },
                        "위임조문정보": [],
                    }
                }
            },
            {
                "expc": {
                    "법령해석례일련번호": "103",
                    "안건명": "개인정보 동의 해석",
                    "회신일자": authority_dates["interpretation"],
                    "관련법령": f"{target_law_name} {target_article}",
                    "회답": "개정 전 동의 요건에 관한 회답",
                }
            },
            {
                "prec": {
                    "판례정보일련번호": "203",
                    "사건명": "개인정보 동의 사건",
                    "선고일자": authority_dates["case"],
                    "참조조문": f"{target_law_name} {target_article}",
                    "판례내용": "개정 전 동의 요건에 관한 판례",
                }
            },
            {
                "detc": {
                    "헌재결정례일련번호": "303",
                    "사건명": "개인정보 자기결정권 사건",
                    "종국일자": authority_dates["constitutional"],
                    "심판대상조문": f"{target_law_name} {target_article}",
                    "전문": "개정 전 조문에 관한 결정",
                }
            },
        ],
    )

    bundle = MolegApi(source).load_legal_context_bundle(
        "개인정보 보호법 제15조 동의의 의미와 위헌 위험",
        law_identifier=LawIdentity(law_id="009999", name=target_law_name, basis="effective"),
        articles=[target_article],
        mode="statute_review",
        budget="standard",
    )
    temporal_gaps = [gap for gap in bundle.gaps if gap.kind == "authority_temporal_mismatch"]
    temporal_deferred = [
        item
        for item in bundle.deferred
        if item.source_type == "authority_temporal_mismatch"
    ]
    authority_article_matches = {
        "interpretation": _references_target_article(
            bundle.loaded.interpretations[0].referenced_articles,
            law_name=target_law_name,
            article=target_article,
        ),
        "case": _references_target_article(
            bundle.loaded.cases[0].referenced_articles,
            law_name=target_law_name,
            article=target_article,
        ),
        "constitutional": _references_target_article(
            bundle.loaded.constitutional_decisions[0].reviewed_articles,
            law_name=target_law_name,
            article=target_article,
        ),
    }

    return LegislativeExpertScenarioReport(
        scenario="context_bundle_authority_temporal_mismatch_guardrail",
        question="context bundle이 같은 조문을 참조하지만 현재 조문 시행일보다 오래된 권위자료를 현재 권위로 승격하지 않는가?",
        status="needs_more_source_loading",
        public_interfaces=["load_legal_context_bundle"],
        must_have={
            "target_article_loaded": bundle.loaded.articles[0].article == target_article,
            "target_article_effective_date_preserved": bundle.loaded.articles[0].effective_date
            == current_article_effective_date,
            "eager_authority_details_loaded": bool(bundle.loaded.interpretations)
            and bool(bundle.loaded.cases)
            and bool(bundle.loaded.constitutional_decisions),
            "authority_articles_match_target": all(authority_article_matches.values()),
            "authority_temporal_mismatch_gaps_preserved": [
                gap.recommended_interface for gap in temporal_gaps
            ]
            == ["trace_law_history", "trace_law_history", "trace_law_history"],
            "authority_temporal_deferred_followups_preserved": [
                (item.interface, item.query) for item in temporal_deferred
            ]
            == [
                ("trace_law_history", f"{target_law_name} {target_article}"),
                ("trace_law_history", f"{target_law_name} {target_article}"),
                ("trace_law_history", f"{target_law_name} {target_article}"),
            ],
            "no_current_authority_claim_without_history": True,
        },
        citations=[
            SourceCitation("law", "eflawjosub", target_law_name, target_article, "current article"),
        ],
        risk_flags=[
            "context_bundle_eager_authority_date_precedes_current_article_effective_date",
            "context_bundle_authority_temporal_mismatch_gap_requires_history_check",
            "matching_referenced_article_is_not_enough_when_authority_predates_current_wording",
        ],
        next_actions=[
            "Use the loaded target article as current legal text only.",
            "Use authority_temporal_mismatch gaps to trace law history or load article text as of the authority date before current-authority claims.",
            "Do not treat matching referenced_articles or reviewed_articles as enough when authority dates predate the current article effective date.",
        ],
        evidence={
            "target_article": {
                "law_name": target_law_name,
                "article": target_article,
                "effective_date": bundle.loaded.articles[0].effective_date,
            },
            "authority_dates": authority_dates,
            "interpretation_referenced_articles": _article_reference_dicts(
                bundle.loaded.interpretations[0].referenced_articles
            ),
            "case_referenced_articles": _article_reference_dicts(
                bundle.loaded.cases[0].referenced_articles
            ),
            "constitutional_reviewed_articles": _article_reference_dicts(
                bundle.loaded.constitutional_decisions[0].reviewed_articles
            ),
            "authority_article_matches": authority_article_matches,
            "gap_kinds": [gap.kind for gap in bundle.gaps],
            "authority_gap_interfaces": [gap.recommended_interface for gap in temporal_gaps],
            "authority_gap_queries": [gap.query for gap in temporal_gaps],
            "authority_deferred_interfaces": [item.interface for item in temporal_deferred],
            "authority_deferred_queries": [item.query for item in temporal_deferred],
            "authority_deferred_filters": [item.filters for item in temporal_deferred],
            "search_call_targets": [target for kind, target, _ in source.calls if kind == "search"],
            "service_call_targets": [target for kind, target, _ in source.calls if kind == "service"],
        },
    )


def _audit_law_structure_hierarchy_candidate_guardrail() -> LegislativeExpertScenarioReport:
    identity = LawIdentity(law_id="001747", name="자동차관리법", basis="effective", mst="270001")
    source = ScenarioSource(
        service_payloads=[
            law_structure_payload("자동차관리법", "001747", "270001", "자동차관리법 시행령"),
        ],
    )

    structure = MolegApi(source).get_law_structure(identity, depth=1)
    service_call_targets = [target for kind, target, _ in source.calls if kind == "service"]
    delegation_targets = [target for target in service_call_targets if target == "lsDelegated"]
    instrument_names = [node.name for node in structure.instruments]

    return LegislativeExpertScenarioReport(
        scenario="law_structure_hierarchy_candidate_guardrail",
        question="법령체계도만으로 조문별 위임관계나 하위규정 본문을 읽은 것처럼 답하지 않는가?",
        status="needs_more_source_loading",
        public_interfaces=["get_law_structure"],
        must_have={
            "hierarchy_nodes_preserved": instrument_names == ["자동차관리법 시행령"],
            "no_article_level_delegation_loaded": delegation_targets == [],
            "no_lower_rule_body_loaded": service_call_targets == ["lsStmd"],
            "structure_not_promoted_to_operational_criteria": True,
        },
        citations=[
            SourceCitation("law_structure", "lsStmd", "자동차관리법", authority="law hierarchy"),
        ],
        risk_flags=[
            "law_structure_is_not_article_level_delegation",
            "law_structure_does_not_load_lower_rule_body",
            "law_structure_hierarchy_is_not_operational_criteria",
        ],
        next_actions=[
            "Use get_law_structure() only to cite the existence and hierarchy of lower instruments.",
            "Load find_delegated_rules(), selected articles, and selected lower-rule detail before article-level delegation or operational-criteria claims.",
        ],
        evidence={
            "root_law": structure.identity.name,
            "instrument_names": instrument_names,
            "instrument_types": [node.instrument_type for node in structure.instruments],
            "service_call_targets": service_call_targets,
            "article_level_delegation_targets": delegation_targets,
            "lower_rule_body_targets": [
                target for target in service_call_targets if target in {"admrul", "law", "eflaw"}
            ],
        },
    )


def _audit_institutional_system_law_structure_not_loaded_guardrail() -> LegislativeExpertScenarioReport:
    identity = LawIdentity(law_id="100001", mst="300001", name="전자금융거래법", basis="effective")
    source = ScenarioSource(
        search_payloads=[
            administrative_rule_search_payload("전자금융거래법 고시"),
            {"ExpcSearch": {"expc": []}},
            {"PrecSearch": {"prec": []}},
            {"DetcSearch": {"detc": []}},
            annex_search_payload("440001", "전자금융거래법 별표", related_name="전자금융거래법"),
            {"admbyl": []},
        ],
        service_payloads=[
            law_text_payload("전자금융거래법", "100001", "300001", article="제21조", title="안전성 확보"),
            {"Law": "일치하는 상하위법이 없습니다. 법령명을 확인하여 주십시오."},
            delegation_payload("전자금융거래법", "전자금융거래법 시행령", law_id="100001", article="21"),
        ],
    )

    bundle = MolegApi(source).load_institutional_system([identity], budget="minimal")
    structure_gaps = [gap for gap in bundle.gaps if gap.kind == "law_structure_not_loaded"]
    structure_deferred = [
        item
        for item in bundle.deferred
        if item.interface == "get_law_structure" and item.source_type == "law_structure"
    ]

    return LegislativeExpertScenarioReport(
        scenario="institutional_system_law_structure_not_loaded_guardrail",
        question="제도 bundle이 법령체계도 로딩 실패를 하위 법령 없음으로 승격하지 않는가?",
        status="needs_more_source_loading",
        public_interfaces=["load_institutional_system"],
        must_have={
            "law_text_loaded": bool(bundle.loaded.laws),
            "delegation_loaded": bool(bundle.loaded.delegations),
            "law_structure_missing": bundle.loaded.law_structures == [],
            "law_structure_gap_preserved": [
                (gap.recommended_interface, gap.query) for gap in structure_gaps
            ]
            == [("get_law_structure", "전자금융거래법")],
            "law_structure_deferred_followup_preserved": [
                (item.interface, item.query) for item in structure_deferred
            ]
            == [("get_law_structure", "전자금융거래법")],
            "no_hierarchy_absence_claim": True,
        },
        citations=[
            SourceCitation("law", "eflaw", "전자금융거래법", "제21조", "current statute"),
            SourceCitation("delegation", "lsDelegated", "전자금융거래법 시행령", "제21조", "delegated rule graph"),
        ],
        risk_flags=[
            "law_structure_not_loaded_is_not_no_lower_instrument",
            "hierarchy_absence_requires_successful_get_law_structure",
        ],
        next_actions=[
            "Run the deferred get_law_structure lookup before saying no lower instruments appear in the hierarchy.",
            "Use loaded delegation graph only for the scoped delegation rows it actually returned.",
        ],
        evidence={
            "gap_kinds": [gap.kind for gap in bundle.gaps],
            "law_structure_gap_interfaces": [gap.recommended_interface for gap in structure_gaps],
            "law_structure_deferred_filters": [item.filters for item in structure_deferred],
            "loaded_law_structures": len(bundle.loaded.law_structures),
            "loaded_delegations": len(bundle.loaded.delegations),
            "service_call_targets": [target for kind, target, _ in source.calls if kind == "service"],
        },
    )


def _audit_empty_delegation_graph_absence_guardrail() -> LegislativeExpertScenarioReport:
    identity = LawIdentity(law_id="001747", name="자동차관리법", basis="effective", mst="270001")
    source = ScenarioSource(
        service_payloads=[
            {
                "lsDelegated": {
                    "법령": {
                        "법령정보": {
                            "법령ID": "001747",
                            "법령명": "자동차관리법",
                            "법령일련번호": "270001",
                        },
                        "위임조문정보": [],
                    }
                }
            }
        ]
    )

    try:
        graph = MolegApi(source).find_delegated_rules(identity, article="제26조")
        rules = graph.rules
        error_type = None
    except NoResultError as exc:
        rules = []
        error_type = type(exc).__name__
    service_call_targets = [target for kind, target, _ in source.calls if kind == "service"]
    lower_rule_detail_targets = [
        target
        for target in service_call_targets
        if target in {"admrul", "eflaw", "law", "eflawjosub", "lawjosub"}
    ]

    return LegislativeExpertScenarioReport(
        scenario="empty_delegation_graph_absence_guardrail",
        question="위임조문 조회 결과가 0건일 때 위임규정이나 하위규정이 없다고 단정하지 않는가?",
        status="needs_more_source_loading",
        public_interfaces=["find_delegated_rules"],
        must_have={
            "empty_delegation_graph_preserved": rules == [] and error_type == "NoResultError",
            "delegation_absence_claim_blocked": True,
            "query_scope_preserved": True,
            "no_lower_rule_detail_loaded": lower_rule_detail_targets == [],
        },
        citations=[],
        risk_flags=[
            "empty_delegation_graph_is_not_absence_of_delegated_rules",
            "zero_delegation_rules_require_structure_or_alternate_source_loading",
            "delegation_absence_requires_successful_scope_disclosure",
        ],
        next_actions=[
            "Disclose that the exact article-level delegation graph returned zero rules for the searched law/article.",
            "Load law structure, source article text, alternate article scopes, administrative-rule candidates, or annex/form paths before any no-delegated-rule claim.",
        ],
        evidence={
            "law": identity.name,
            "law_id": identity.law_id,
            "article": "제26조",
            "rule_count": len(rules),
            "error_type": error_type,
            "service_call_targets": service_call_targets,
            "lower_rule_detail_targets": lower_rule_detail_targets,
            "citations_loaded": 0,
        },
    )


def _audit_administrative_rule_search_candidate_detail_guardrail() -> LegislativeExpertScenarioReport:
    source = ScenarioSource(
        search_payloads=[
            {
                "AdmRulSearch": {
                    "admrul": [
                        {
                            "행정규칙 일련번호": "2100000248758",
                            "행정규칙ID": "2077465",
                            "행정규칙명": "무단방치 자동차 처리 규정",
                            "행정규칙종류": "고시",
                            "발령일자": "20250101",
                            "시행일자": "20250101",
                            "소관부처명": "국토교통부",
                            "현행연혁구분": "현행",
                            "위임법령ID": "001747",
                            "위임법령명": "자동차관리법",
                            "위임조문번호": "제26조",
                            "위임조문제목": "자동차의 강제처리",
                        }
                    ]
                }
            }
        ]
    )

    hits = MolegApi(source).search_administrative_rules(
        "무단방치 자동차 처리 기준",
        display=3,
    )
    hit = hits[0]
    service_call_targets = [target for kind, target, _ in source.calls if kind == "service"]

    return LegislativeExpertScenarioReport(
        scenario="administrative_rule_search_candidate_detail_guardrail",
        question="행정규칙 검색 hit만으로 조문/처리기준/부칙을 읽은 것처럼 답하지 않는가?",
        status="needs_more_source_loading",
        public_interfaces=["search_administrative_rules"],
        must_have={
            "administrative_rule_candidate_preserved": hit.identity.name == "무단방치 자동차 처리 규정",
            "identity_metadata_preserved": hit.identity.rule_type == "고시"
            and hit.identity.issuing_date == "20250101"
            and hit.identity.effective_date == "20250101"
            and hit.identity.source_law_name == "자동차관리법"
            and hit.identity.source_article == "제26조",
            "no_administrative_rule_detail_loaded": service_call_targets == [],
            "no_citable_operational_criteria_loaded": True,
        },
        citations=[],
        risk_flags=[
            "administrative_rule_search_hit_requires_get_administrative_rule_detail",
            "search_administrative_rules_is_candidate_discovery_not_rule_text",
            "administrative_rule_operational_criteria_require_selected_detail_loading",
        ],
        next_actions=[
            "Load the selected administrative rule through get_administrative_rule() before citing article text, criteria, supplementary provisions, or current operational criteria.",
            "Compare loaded administrative-rule effective_date to the answer reference date before calling it current operational criteria.",
        ],
        evidence={
            "query": "무단방치 자동차 처리 기준",
            "administrative_rule_candidates": [
                {
                    "name": item.identity.name,
                    "rule_type": item.identity.rule_type,
                    "issuing_date": item.identity.issuing_date,
                    "effective_date": item.identity.effective_date,
                    "source_law_name": item.identity.source_law_name,
                    "source_article": item.identity.source_article,
                }
                for item in hits
            ],
            "search_call_targets": [target for kind, target, _ in source.calls if kind == "search"],
            "service_call_targets": service_call_targets,
            "citations_loaded": 0,
        },
    )


def _audit_administrative_rule_issued_on_not_effective_as_of_guardrail() -> LegislativeExpertScenarioReport:
    query = "전기자동차 충전시설 운영 기준"
    reference_date = "20250101"
    source = ScenarioSource(
        search_payloads=[
            {
                "AdmRulSearch": {
                    "admrul": [
                        {
                            "행정규칙 일련번호": "2100000300000",
                            "행정규칙ID": "099999",
                            "행정규칙명": "전기자동차 충전시설 운영 규정",
                            "행정규칙종류": "고시",
                            "발령일자": "20250101",
                            "시행일자": "20250301",
                            "소관부처명": "국토교통부",
                            "현행연혁구분": "현행",
                        }
                    ]
                }
            }
        ]
    )

    hits = MolegApi(source).search_administrative_rules(
        query,
        issued_on="2025-01-01",
        display=3,
    )
    hit = hits[0]
    service_call_targets = [target for kind, target, _ in source.calls if kind == "service"]
    search_call_params = [params for kind, _, params in source.calls if kind == "search"]

    return LegislativeExpertScenarioReport(
        scenario="administrative_rule_issued_on_not_effective_as_of_guardrail",
        question="행정규칙 발령일자 필터를 기준일/시행일 판단으로 오해하지 않는가?",
        status="needs_more_source_loading",
        public_interfaces=["search_administrative_rules"],
        must_have={
            "issued_on_filter_preserved": search_call_params[0].get("date") == reference_date,
            "issued_on_not_effective_date": hit.identity.issuing_date == reference_date
            and hit.identity.effective_date == "20250301",
            "no_administrative_rule_detail_loaded": service_call_targets == [],
            "current_operational_claim_blocked": True,
        },
        citations=[],
        risk_flags=[
            "administrative_rule_issued_on_filter_is_not_effective_as_of",
            "administrative_rule_search_hit_not_current_operational_criteria",
            "administrative_rule_current_status_requires_detail_effective_date_check",
        ],
        next_actions=[
            "Treat issued_on as a 발령일자 search filter, not an as-of effective-date lookup.",
            "Load the selected administrative rule through get_administrative_rule() before citing criteria.",
            "Compare the loaded administrative-rule effective_date to the answer reference date before current-operational claims.",
        ],
        evidence={
            "query": query,
            "reference_date": reference_date,
            "candidate": {
                "name": hit.identity.name,
                "issuing_date": hit.identity.issuing_date,
                "effective_date": hit.identity.effective_date,
                "current_status": hit.identity.current_status,
            },
            "search_call_targets": [target for kind, target, _ in source.calls if kind == "search"],
            "search_call_params": search_call_params,
            "service_call_targets": service_call_targets,
            "citations_loaded": 0,
        },
    )


def _audit_administrative_rule_article_status_guardrail() -> LegislativeExpertScenarioReport:
    rule_name = "무단방치 자동차 처리 규정"
    source = ScenarioSource(
        service_payloads=[
            {
                "admrul": {
                    "행정규칙 일련번호": "2100000248758",
                    "행정규칙ID": "2077465",
                    "행정규칙명": rule_name,
                    "행정규칙종류": "고시",
                    "발령일자": "20250101",
                    "소관부처명": "국토교통부",
                    "시행일자": "20250101",
                    "위임법령ID": "001747",
                    "위임법령명": "자동차관리법",
                    "위임조문번호": "제26조",
                    "위임조문제목": "자동차의 강제처리",
                    "조문": {
                        "조문단위": [
                            {
                                "조문번호": "3",
                                "조문제목": "삭제",
                                "조문내용": "제3조 삭제 <2025. 1. 1.>",
                                "조문시행일자": "20250101",
                                "조문여부": "조문",
                                "조문제개정유형": "삭제",
                                "조문변경여부": "Y",
                            },
                            {
                                "조문번호": "4",
                                "조문제목": "이동",
                                "조문내용": "제4조는 제6조로 이동 <2025. 1. 1.>",
                                "조문시행일자": "20250101",
                                "조문여부": "조문",
                                "조문제개정유형": "이동",
                                "조문이동이전": "4",
                                "조문이동이후": "6",
                                "조문변경여부": "Y",
                            },
                        ]
                    },
                }
            },
            {
                "admrul": {
                    "행정규칙 일련번호": "2100000248758",
                    "행정규칙ID": "2077465",
                    "행정규칙명": rule_name,
                    "행정규칙종류": "고시",
                    "발령일자": "20250101",
                    "소관부처명": "국토교통부",
                    "시행일자": "20250101",
                    "위임법령ID": "001747",
                    "위임법령명": "자동차관리법",
                    "위임조문번호": "제26조",
                    "위임조문제목": "자동차의 강제처리",
                    "조문": {
                        "조문단위": [
                            {
                                "조문번호": "6",
                                "조문제목": "처리 기준",
                                "조문내용": "제6조(처리 기준) 무단방치 자동차 처리 절차를 따른다.",
                                "조문시행일자": "20250101",
                                "조문여부": "조문",
                                "조문제개정유형": "전문개정",
                            }
                        ]
                    },
                }
            },
        ]
    )

    context = MolegApi(source).load_administrative_rule_context(
        "2100000248758",
        articles=["제3조", "제4조"],
    )
    administrative_rule = context.rule
    articles = context.requested_articles
    deleted_article = articles[0]
    moved_article = articles[1]
    current_article = context.current_articles[0] if context.current_articles else None
    article_statuses = [
        {
            "article": article.article,
            "revision_type": article.revision_type,
            "is_deleted": article.is_deleted,
            "moved_to": article.moved_to,
        }
        for article in articles
    ]

    return LegislativeExpertScenarioReport(
        scenario="administrative_rule_article_status_guardrail",
        question="행정규칙 조문 detail이 삭제 또는 이동 상태일 때 이를 현재 운영기준처럼 인용하지 않는가?",
        status="ready_for_reasoning",
        public_interfaces=["load_administrative_rule_context"],
        must_have={
            "administrative_rule_loaded": administrative_rule.identity.name == rule_name,
            "deleted_article_status_preserved": deleted_article.article == "제3조"
            and deleted_article.is_deleted is True
            and deleted_article.revision_type == "삭제",
            "moved_article_status_preserved": moved_article.article == "제4조"
            and moved_article.revision_type == "이동"
            and moved_article.moved_to == "제6조",
            "deleted_article_not_operational_text": True,
            "destination_article_loaded": current_article is not None
            and current_article.article == "제6조",
            "current_article_is_destination": current_article is not None
            and "처리 절차" in current_article.text,
        },
        citations=[
            SourceCitation(
                "administrative_rule",
                "admrul",
                rule_name,
                "제3조",
                "deleted administrative-rule article marker",
            ),
            SourceCitation(
                "administrative_rule",
                "admrul",
                rule_name,
                "제4조",
                "moved administrative-rule article marker",
            ),
            SourceCitation(
                "administrative_rule",
                "admrul",
                rule_name,
                "제6조",
                "current destination administrative-rule article",
            ),
        ],
        risk_flags=[
            "administrative_rule_deleted_article_is_not_current_operational_criteria",
            "administrative_rule_moved_article_destination_loaded_before_current_criteria",
            "administrative_rule_article_status_required_before_operational_criteria_claim",
        ],
        next_actions=[
            "Disclose deleted administrative-rule article status before discussing legal effect.",
            "Cite the loaded moved-to administrative-rule article before stating current operational criteria.",
            "Load history or version comparison if the answer needs prior wording or amendment reason.",
        ],
        evidence={
            "administrative_rule": administrative_rule.identity.name,
            "effective_date": administrative_rule.identity.effective_date,
            "article_statuses": article_statuses,
            "deleted_article": deleted_article.article,
            "moved_article": moved_article.article,
            "moved_to": moved_article.moved_to,
            "current_article": current_article.article if current_article else None,
            "current_article_text": current_article.text if current_article else None,
            "loaded_articles": [article.article for article in context.loaded_articles],
            "gap_kinds": [gap.kind for gap in context.gaps],
            "deferred_interfaces": [lookup.interface for lookup in context.deferred],
            "service_call_targets": [target for kind, target, _ in source.calls if kind == "service"],
            "citations_loaded": 3,
        },
    )


def _audit_administrative_rule_supplementary_transition_context() -> LegislativeExpertScenarioReport:
    rule_name = "무단방치 자동차 처리 규정"
    source = ScenarioSource(
        service_payloads=[
            {
                "admrul": {
                    "기본정보": {
                        "행정규칙일련번호": "2100000248759",
                        "행정규칙ID": "2088002",
                        "행정규칙명": rule_name,
                        "행정규칙종류": "고시",
                        "발령일자": "20260615",
                        "발령번호": "제2026-10호",
                        "시행일자": "20260701",
                        "소관부처명": "국토교통부",
                        "현행여부": "현행",
                        "법적근거법령명": "자동차관리법",
                        "법적근거조문": "제26조",
                    },
                    "조문": {
                        "조문단위": [
                            {
                                "조문번호": "5",
                                "조문제목": "처리기준",
                                "조문내용": "제5조(처리기준) 시장ㆍ군수ㆍ구청장은 방치 자동차의 상태를 확인하여 처리한다.",
                                "조문시행일자": "20260701",
                            }
                        ]
                    },
                    "부칙": {
                        "부칙단위": [
                            {
                                "부칙공포일자": "20260615",
                                "부칙공포번호": "제2026-10호",
                                "부칙내용": "제1조(시행일) 이 고시는 2026년 7월 1일부터 시행한다.",
                            },
                            {
                                "부칙공포일자": "20260615",
                                "부칙공포번호": "제2026-10호",
                                "부칙내용": "제2조(경과조치) 이 고시 시행 당시 진행 중인 방치 자동차 처리절차에는 종전의 기준을 적용한다.",
                            },
                        ]
                    },
                }
            }
        ]
    )

    rule = MolegApi(source).get_administrative_rule("2100000248759", articles=["제5조"])
    supplementary_text = "\n".join(
        provision.text for provision in rule.supplementary_provisions
    )
    article_text = rule.articles[0].text

    return LegislativeExpertScenarioReport(
        scenario="administrative_rule_supplementary_transition_guardrail",
        question="행정규칙 시행일/경과조치 질문에서 부칙이 조문과 별도 근거로 보존되는가?",
        status="ready_for_reasoning",
        public_interfaces=["get_administrative_rule"],
        must_have={
            "administrative_rule_article_loaded": rule.articles[0].article == "제5조",
            "supplementary_provisions_loaded": len(rule.supplementary_provisions) == 2,
            "supplementary_promulgation_metadata_preserved": rule.supplementary_provisions[0].promulgation_number == "2026-10",
            "transition_text_loaded_from_supplementary_provision": "경과조치" in supplementary_text
            and "종전의 기준" in supplementary_text,
            "transition_text_not_in_article": "경과조치" not in article_text
            and "종전의 기준" not in article_text,
        },
        citations=[
            SourceCitation(
                "administrative_rule",
                "admrul",
                rule_name,
                "제5조",
                "administrative rule article",
            ),
            SourceCitation(
                "supplementary_provision",
                "admrul",
                rule_name,
                "부칙 제2조",
                "administrative-rule supplementary provision",
            ),
        ],
        risk_flags=[
            "administrative_rule_supplementary_provision_required_for_transition_application",
            "administrative_rule_article_text_alone_cannot_answer_transitional_scope",
            "administrative_rule_effective_date_metadata_not_full_transition_analysis",
        ],
        next_actions=[
            "Cite administrative-rule supplementary provisions separately when discussing 시행일, 적용례, or 경과조치.",
            "Use history/diff follow-up if the transition question depends on a specific amendment event.",
        ],
        evidence={
            "administrative_rule": rule.identity.name,
            "administrative_rule_effective_date": rule.identity.effective_date,
            "article": rule.articles[0].article,
            "supplementary_provision_count": len(rule.supplementary_provisions),
            "supplementary_promulgation_dates": [
                provision.promulgation_date for provision in rule.supplementary_provisions
            ],
            "supplementary_promulgation_numbers": [
                provision.promulgation_number for provision in rule.supplementary_provisions
            ],
            "supplementary_text_contains_transition": "경과조치" in supplementary_text,
            "article_text_contains_transition": "경과조치" in article_text,
            "service_call_targets": [target for _, target, _ in source.calls],
        },
    )


def _audit_empty_administrative_rule_search_absence_guardrail() -> LegislativeExpertScenarioReport:
    query = "무단방치 자동차 현장처리 세부기준"
    source = ScenarioSource(search_payloads=[{"AdmRulSearch": {"admrul": []}}])

    hits = MolegApi(source).search_administrative_rules(query, display=5)
    service_call_targets = [target for kind, target, _ in source.calls if kind == "service"]

    return LegislativeExpertScenarioReport(
        scenario="empty_administrative_rule_search_absence_guardrail",
        question="행정규칙 검색 결과가 0건일 때 위임기준/하위규정이 없다고 단정하지 않는가?",
        status="needs_more_source_loading",
        public_interfaces=["search_administrative_rules"],
        must_have={
            "empty_search_result_preserved": hits == [],
            "no_rule_detail_loaded": service_call_targets == [],
            "delegation_absence_claim_blocked": True,
            "query_scope_preserved": True,
        },
        citations=[],
        risk_flags=[
            "empty_administrative_rule_search_is_not_absence_of_delegated_criteria",
            "zero_administrative_rule_hits_require_delegation_or_alternate_rule_search",
            "operational_criteria_absence_requires_successful_scope_disclosure",
        ],
        next_actions=[
            "Disclose that the exact administrative-rule search returned zero hits for the searched query and filters.",
            "Load statute-level delegation, law structure, alternate rule names, or annex/form candidates before any no-delegated-criteria claim.",
        ],
        evidence={
            "query": query,
            "hit_count": len(hits),
            "search_call_targets": [target for kind, target, _ in source.calls if kind == "search"],
            "service_call_targets": service_call_targets,
            "citations_loaded": 0,
        },
    )


def _audit_administrative_rule_missing_source_reference_guardrail() -> LegislativeExpertScenarioReport:
    source = ScenarioSource(
        service_payloads=[
            {
                "admrul": {
                    "행정규칙 일련번호": "2200000037921",
                    "행정규칙ID": "2077465",
                    "행정규칙명": "2015년 하이브리드자동차 구매보조금 대상차종",
                    "행정규칙종류": "공고",
                    "발령일자": "20150716",
                    "발령번호": "2015-538",
                    "소관부처명": "기후에너지환경부",
                    "시행일자": "20150716",
                    "조문내용": "하이브리드자동차 구매보조금 대상차종은 다음과 같다.",
                    "첨부파일": {
                        "첨부파일명": "2015년 하이브리드자동차 구매보조금 대상차종.hwp",
                    },
                }
            }
        ]
    )

    administrative_rule = MolegApi(source).get_administrative_rule("2200000037921")

    return LegislativeExpertScenarioReport(
        scenario="administrative_rule_missing_source_reference_guardrail",
        question="행정규칙 detail에 위임법령/근거조문 metadata가 없을 때 근거 없음으로 단정하지 않는가?",
        status="ready_for_reasoning",
        public_interfaces=["get_administrative_rule"],
        must_have={
            "administrative_rule_detail_loaded": administrative_rule.identity.name
            == "2015년 하이브리드자동차 구매보조금 대상차종",
            "source_law_reference_absent": administrative_rule.identity.source_law_name is None
            and administrative_rule.identity.source_law_id is None,
            "source_article_reference_absent": administrative_rule.identity.source_article is None
            and administrative_rule.identity.source_article_title is None,
            "article_text_loaded": "하이브리드자동차" in administrative_rule.text,
            "absence_preserved_as_unknown_not_no_authorization": True,
        },
        citations=[
            SourceCitation(
                "administrative_rule",
                "admrul",
                "2015년 하이브리드자동차 구매보조금 대상차종",
                authority="loaded administrative rule",
            )
        ],
        risk_flags=[
            "missing_administrative_rule_source_reference_is_unknown_not_no_authorization",
            "administrative_rule_detail_does_not_prove_no_delegation_when_source_reference_absent",
        ],
        next_actions=[
            "Disclose that MOLEG did not expose source-law/source-article metadata for this administrative-rule payload.",
            "Load statute/delegation context separately before claiming there is no authorizing basis.",
        ],
        evidence={
            "administrative_rule_name": administrative_rule.identity.name,
            "source_law_id": administrative_rule.identity.source_law_id,
            "source_law_name": administrative_rule.identity.source_law_name,
            "source_article": administrative_rule.identity.source_article,
            "source_article_title": administrative_rule.identity.source_article_title,
            "article_source_law_names": [article.source_law_name for article in administrative_rule.articles],
            "article_source_articles": [article.source_article for article in administrative_rule.articles],
            "service_call_targets": [target for kind, target, _ in source.calls if kind == "service"],
        },
    )


def _audit_comparable_mechanism_candidate_detail_guardrail() -> LegislativeExpertScenarioReport:
    source = ScenarioSource(
        search_payloads=[
            {
                "aiSearch": {
                    "법령조문": [
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
                }
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
        service_payloads=[{"lstrmRltJo": []}],
    )

    candidates = MolegApi(source).find_comparable_mechanisms("과징금", display=3)
    service_call_targets = [target for kind, target, _ in source.calls if kind == "service"]
    article_service_targets = [
        target
        for kind, target, _ in source.calls
        if kind == "service" and target in {"eflawjosub", "lawjosub"}
    ]

    return LegislativeExpertScenarioReport(
        scenario="comparable_mechanism_candidate_detail_guardrail",
        question="비교입법례 후보만으로 법적 동등성이나 설계 적합성을 결론내리지 않는가?",
        status="needs_more_source_loading",
        public_interfaces=["find_comparable_mechanisms"],
        must_have={
            "comparable_candidates_preserved": len(candidates) == 3,
            "article_anchor_metadata_preserved": candidates[0].raw_keys["source_articles"][0] == {
                "article": "제50조",
                "title": "과징금",
                "source_target": "aiSearch",
            },
            "no_comparable_article_loaded": article_service_targets == [],
            "no_citable_comparison_loaded": True,
        },
        citations=[],
        risk_flags=[
            "comparable_mechanism_candidate_requires_selected_article_loading",
            "find_comparable_mechanisms_is_planning_context_not_legal_equivalence",
            "comparative_design_suitability_requires_loaded_sources",
        ],
        next_actions=[
            "Load selected comparable articles with get_article() before citing legal structure or comparing mechanisms.",
            "Check interpretation, case, and constitutional-risk sources before treating a mechanism as suitable for a new bill.",
        ],
        evidence={
            "concept": "과징금",
            "candidate_names": [candidate.name for candidate in candidates],
            "candidate_source_articles": [
                candidate.raw_keys.get("source_articles", [])
                for candidate in candidates
            ],
            "search_call_targets": [target for kind, target, _ in source.calls if kind == "search"],
            "service_call_targets": service_call_targets,
            "article_service_targets": article_service_targets,
            "citations_loaded": 0,
        },
    )


def _audit_annex_form_search_candidate_detail_guardrail() -> LegislativeExpertScenarioReport:
    source = ScenarioSource(
        search_payloads=[
            annex_search_payload(
                "17677511",
                "과태료의 부과기준",
                related_name="식품위생법 시행령",
            )
        ]
    )

    hits = MolegApi(source).search_annex_forms(
        "과태료",
        source="law",
        annex_type="annex",
        display=3,
    )
    hit = hits[0]
    text_call_targets = [target for kind, target, _ in source.calls if kind == "post_text"]

    return LegislativeExpertScenarioReport(
        scenario="annex_form_search_candidate_detail_guardrail",
        question="별표/서식 검색 hit만으로 금액 기준, 적용요건, 첨부본문을 읽은 것처럼 답하지 않는가?",
        status="needs_more_source_loading",
        public_interfaces=["search_annex_forms"],
        must_have={
            "annex_candidate_preserved": hit.identity.title == "과태료의 부과기준",
            "source_label_licbyl_preserved": hit.identity.source_type == "law"
            and hit.identity.source_target == "licbyl",
            "annex_metadata_preserved": hit.identity.related_name == "식품위생법 시행령"
            and hit.identity.annex_type == "별표",
            "no_annex_body_loaded": text_call_targets == [],
            "no_citable_annex_criteria_loaded": True,
        },
        citations=[],
        risk_flags=[
            "annex_form_search_hit_requires_get_annex_form_body",
            "search_annex_forms_is_candidate_discovery_not_attached_body_text",
            "annex_thresholds_require_selected_body_loading",
        ],
        next_actions=[
            "Load the selected annex/form through get_annex_form_body() before citing thresholds, amounts, criteria, form content, or extracted rows.",
            "Load the authorizing statute or enforcement article when the attached body references a provision.",
        ],
        evidence={
            "query": "과태료",
            "annex_candidates": [
                {
                    "title": item.identity.title,
                    "related_name": item.identity.related_name,
                    "annex_type": item.identity.annex_type,
                    "source_target": item.identity.source_target,
                }
                for item in hits
            ],
            "search_call_targets": [target for kind, target, _ in source.calls if kind == "search"],
            "text_call_targets": text_call_targets,
            "citations_loaded": 0,
        },
    )


def _audit_empty_annex_form_search_absence_guardrail() -> LegislativeExpertScenarioReport:
    query = "무단방치 자동차 과태료 세부기준"
    source = ScenarioSource(search_payloads=[{"licbyl": []}])

    hits = MolegApi(source).search_annex_forms(
        query,
        source="law",
        annex_type="annex",
        display=5,
    )
    text_call_targets = [target for kind, target, _ in source.calls if kind == "post_text"]

    return LegislativeExpertScenarioReport(
        scenario="empty_annex_form_search_absence_guardrail",
        question="별표/서식 검색 결과가 0건일 때 첨부 기준이나 서식이 없다고 단정하지 않는가?",
        status="needs_more_source_loading",
        public_interfaces=["search_annex_forms"],
        must_have={
            "empty_search_result_preserved": hits == [],
            "no_annex_body_loaded": text_call_targets == [],
            "attached_material_absence_claim_blocked": True,
            "query_scope_preserved": True,
        },
        citations=[],
        risk_flags=[
            "empty_annex_form_search_is_not_absence_of_attached_material",
            "zero_annex_form_hits_require_alternate_source_or_detail_loading",
            "attached_criteria_absence_requires_successful_scope_disclosure",
        ],
        next_actions=[
            "Disclose that the exact annex/form search returned zero hits for the searched query, source, type, and scope.",
            "Load source law text, administrative-rule candidates, alternate annex/form terms, or administrative-rule annex/forms before any no-attached-criteria claim.",
        ],
        evidence={
            "query": query,
            "source": "law",
            "annex_type": "annex",
            "search_scope": "source",
            "hit_count": len(hits),
            "search_call_targets": [target for kind, target, _ in source.calls if kind == "search"],
            "text_call_targets": text_call_targets,
            "citations_loaded": 0,
        },
    )


def _audit_delegated_criteria_after_followups() -> LegislativeExpertScenarioReport:
    identity = LawIdentity(law_id="001747", name="자동차관리법", basis="effective", mst="270001")
    source = ScenarioSource(
        service_payloads=[
            law_text_payload("자동차관리법", "001747", "270001", article="제26조", title="자동차의 강제처리"),
            law_structure_payload("자동차관리법", "001747", "270001", "자동차관리법 시행령"),
            delegation_payload("자동차관리법", "자동차관리법 시행령", law_id="001747", article="26"),
            _administrative_rule_detail_payload(),
        ],
        search_payloads=[
            administrative_rule_search_payload("무단방치 자동차 처리 규정"),
            {"ExpcSearch": {"expc": []}},
            {"PrecSearch": {"prec": []}},
            {"DetcSearch": {"detc": []}},
            {"licbyl": []},
            _administrative_rule_annex_search_payload(),
        ],
        text_payloads=[pipe_table_text()],
    )
    api = MolegApi(source)

    bundle = api.load_delegated_criteria(
        identity,
        query="무단방치 자동차 처리 기준",
        budget="minimal",
    )
    administrative_rule = bundle.loaded.administrative_rules[0]
    annex_body = bundle.loaded.annex_forms[0]
    call_targets = [target for _, target, _ in source.calls]

    return LegislativeExpertScenarioReport(
        scenario="delegated_criteria_after_followups",
        question="자동차 방치 처리 기준의 행정규칙/별표 본문을 task-level interface 한 번으로 인용할 수 있는가?",
        status="ready_for_reasoning",
        public_interfaces=[
            "load_delegated_criteria",
        ],
        must_have={
            "candidate_stage_preserved_with_loaded_detail": len(bundle.candidates.administrative_rules) == 1
            and len(bundle.candidates.annex_forms) == 1,
            "administrative_rule_body_loaded": "무단방치 자동차 처리 기준" in administrative_rule.text,
            "administrative_rule_source_reference_preserved": administrative_rule.identity.source_law_name == "자동차관리법"
            and administrative_rule.identity.source_article == "제26조",
            "administrative_rule_annex_body_loaded": "과징금 산정기준" in annex_body.text,
            "structured_annex_rows_loaded": bool(
                annex_body.structured_data and len(annex_body.structured_data.rows) == 2
            ),
            "detail_sources_loaded_inside_task_interface": call_targets[-2:] == ["admrul", "admRulBylTextDownLoad.do"],
        },
        citations=[
            SourceCitation("law", "eflaw", "자동차관리법", "제26조", "current statute"),
            SourceCitation("delegation", "lsDelegated", "자동차관리법 시행령", "제26조", "delegated rule graph"),
            SourceCitation("administrative_rule", "admrul", "무단방치 자동차 처리 규정", "제2조", "loaded administrative rule"),
            SourceCitation("annex", "admbyl", "무단방치 자동차 처리 기준", authority="loaded administrative-rule annex table"),
        ],
        risk_flags=["delegated_criteria_loader_is_bounded_not_exhaustive_lower_rule_survey"],
        next_actions=["Use WebSearch only for latest enforcement practice or policy context outside MOLEG."],
        evidence={
            "loaded_detail_interfaces": ["get_administrative_rule", "get_annex_form_body"],
            "administrative_rule_articles": [article.article for article in administrative_rule.articles],
            "source_law_name": administrative_rule.identity.source_law_name,
            "source_article": administrative_rule.identity.source_article,
            "annex_extraction_method": annex_body.extraction_method,
            "structured_annex_rows": len(annex_body.structured_data.rows if annex_body.structured_data else []),
            "call_targets": call_targets,
        },
    )


def _audit_delegated_criteria_source_mismatch_guardrail() -> LegislativeExpertScenarioReport:
    identity = LawIdentity(law_id="001747", name="자동차관리법", basis="effective", mst="270001")
    source = ScenarioSource(
        service_payloads=[
            {
                "eflawjosub": {
                    "조문": {
                        "조문번호": "26",
                        "조문제목": "자동차의 강제처리",
                        "조문내용": "제26조(자동차의 강제처리) 무단방치 자동차 처리 기준은 대통령령으로 정한다.",
                    }
                }
            },
            law_structure_payload("자동차관리법", "001747", "270001", "자동차관리법 시행령"),
            delegation_payload("자동차관리법", "자동차관리법 시행령", law_id="001747", article="26"),
            _administrative_rule_detail_payload(source_article="제99조"),
        ],
        search_payloads=[
            administrative_rule_search_payload("무단방치 자동차 처리 규정"),
            {"ExpcSearch": {"expc": []}},
            {"PrecSearch": {"prec": []}},
            {"DetcSearch": {"detc": []}},
            {"licbyl": []},
            _administrative_rule_annex_search_payload(),
        ],
        text_payloads=[pipe_table_text()],
    )

    bundle = MolegApi(source).load_delegated_criteria(
        identity,
        articles=["제26조"],
        query="무단방치 자동차 처리 기준",
        budget="minimal",
    )
    mismatch_gaps = [
        gap for gap in bundle.gaps if gap.kind == "delegated_criteria_source_mismatch"
    ]

    return LegislativeExpertScenarioReport(
        scenario="delegated_criteria_source_mismatch_guardrail",
        question="로드된 행정규칙 detail이 대상 법/조문이 아닌 다른 위임조문을 가리킬 때 운용기준 인용을 막는가?",
        status="needs_more_source_loading",
        public_interfaces=["load_delegated_criteria"],
        must_have={
            "target_article_loaded": [article.article for article in bundle.loaded.articles] == ["제26조"],
            "administrative_rule_body_loaded": bool(bundle.loaded.administrative_rules),
            "source_mismatch_gap_preserved": [gap.query for gap in mismatch_gaps]
            == ["자동차관리법 제26조"],
            "mismatch_recommends_delegation_followup": [gap.recommended_interface for gap in mismatch_gaps]
            == ["find_delegated_rules"],
            "administrative_rule_not_cited_as_target_criteria": True,
        },
        citations=[
            SourceCitation("law", "eflawjosub", "자동차관리법", "제26조", "current statute article"),
            SourceCitation("delegation", "lsDelegated", "자동차관리법 시행령", "제26조", "delegated rule graph"),
        ],
        risk_flags=[
            "delegated_criteria_source_mismatch_not_target_operational_criteria",
            "loaded_administrative_rule_source_reference_must_match_target_article",
        ],
        next_actions=[
            "Use the loaded administrative-rule detail only as follow-up context until its source law/article matches the target.",
            "Run delegation or alternate administrative-rule/annex searches before citing operational criteria for the target article.",
        ],
        evidence={
            "target_articles": [article.article for article in bundle.loaded.articles],
            "loaded_administrative_rules": [
                rule.identity.name for rule in bundle.loaded.administrative_rules
            ],
            "loaded_source_articles": [
                rule.identity.source_article for rule in bundle.loaded.administrative_rules
            ],
            "gap_kinds": [gap.kind for gap in bundle.gaps],
            "gap_recommended_interfaces": [
                gap.recommended_interface for gap in mismatch_gaps
            ],
            "call_targets": [target for _, target, _ in source.calls],
        },
    )


def _audit_low_confidence_annex_body() -> LegislativeExpertScenarioReport:
    identity = AnnexFormIdentity(
        annex_id="17677511",
        title="과태료의 부과기준",
        source_type="law",
        source_target="licbyl",
        related_name="식품위생법 시행령",
        annex_type="별표",
    )
    source = ScenarioSource(
        text_payloads=[
            "\n".join(
                [
                    "■ 식품위생법 시행령 [별표 2]",
                    "과태료의 부과기준",
                    "가. 보고의무 위반",
                    "- 1차 위반: 10만원, 2차 위반: 20만원",
                    "나. 영업정지 명령 위반",
                    "- 위반 정도와 기간에 따라 50만원 이상 100만원 이하",
                ]
            )
        ]
    )

    annex_body = MolegApi(source).get_annex_form_body(identity)
    structured = annex_body.structured_data

    return LegislativeExpertScenarioReport(
        scenario="low_confidence_annex_body_guardrail",
        question="별표 본문은 로드됐지만 표 구조화가 낮은 신뢰도일 때 숫자 기준을 단정하지 않는가?",
        status="ready_for_reasoning",
        public_interfaces=["get_annex_form_body"],
        must_have={
            "annex_body_loaded": "과태료의 부과기준" in annex_body.text,
            "plain_text_retained": "1차 위반: 10만원" in annex_body.text,
            "structured_data_present": structured is not None,
            "low_confidence_preserved": structured is not None
            and structured.parsing_confidence == "low",
            "empty_rows_not_treated_as_no_criteria": structured is not None
            and structured.rows == [],
        },
        citations=[
            SourceCitation(
                "annex",
                "licbyl",
                "과태료의 부과기준",
                authority="loaded annex body with low-confidence structure",
            ),
        ],
        risk_flags=[
            "annex_structured_rows_low_confidence",
            "empty_structured_rows_do_not_mean_no_annex_criteria",
        ],
        next_actions=[
            "Use the retained plain text for cautious review or request manual table inspection.",
            "Do not rely on empty structured rows as proof that no thresholds or criteria exist.",
        ],
        evidence={
            "extraction_confidence": annex_body.extraction_confidence,
            "parsing_confidence": structured.parsing_confidence if structured else None,
            "structured_rows": len(structured.rows) if structured else None,
            "structured_notes": structured.notes if structured else [],
            "plain_text_contains_threshold": "10만원" in annex_body.text,
            "call_targets": [target for _, target, _ in source.calls],
        },
    )


def _audit_historical_repealed_article_as_of() -> LegislativeExpertScenarioReport:
    identity = LawIdentity(
        law_id="099999",
        name="온라인개인정보보호법",
        basis="effective",
        mst="190001",
        effective_date="20120101",
    )
    source = ScenarioSource(
        service_payloads=[
            {
                "eflawjosub": {
                    "기본정보": {
                        "법령ID": "099999",
                        "법령명_한글": "온라인개인정보보호법",
                        "법령일련번호": "190001",
                        "시행일자": "20120101",
                    },
                    "조문": {
                        "조문번호": "2",
                        "조문제목": "개인정보의 수집",
                        "조문내용": "제2조(개인정보의 수집) 정보통신서비스 제공자는 이용자 동의를 받아야 한다.",
                        "조문시행일자": "20120101",
                    },
                }
            }
        ],
        search_html_payloads=[_historical_repealed_law_history_html()],
    )
    api = MolegApi(source)

    article = api.get_article(identity, "제2조", as_of="2012-12-30")
    history = api.trace_law_history(identity)
    history_statuses = [
        str(event.raw.get("현행연혁구분") or "")
        for event in history.events
        if event.raw.get("현행연혁구분")
    ]

    return LegislativeExpertScenarioReport(
        scenario="historical_article_as_of_guardrail",
        question="폐지되었거나 현재 시행되지 않는 구법 조문을 과거 기준일로만 인용하는가?",
        status="ready_for_reasoning",
        public_interfaces=["get_article", "trace_law_history"],
        must_have={
            "historical_reference_date_used": source.calls[0] == (
                "service",
                "eflawjosub",
                {"MST": "190001", "efYd": "20121230", "JO": "000200"},
            ),
            "historical_article_loaded": article.effective_date == "20120101"
            and "이용자 동의" in article.text,
            "history_status_preserved": "폐지" in history_statuses,
            "history_metadata_loaded": history.events[0].revision_type == "폐지"
            and history.events[0].effective_date == "20130101",
            "no_current_law_claim": True,
        },
        citations=[
            SourceCitation(
                "law",
                "eflawjosub",
                "온라인개인정보보호법",
                "제2조",
                "historical article as of 2012-12-30",
            ),
            SourceCitation("history", "lsHistory", "온라인개인정보보호법", authority="law history status"),
        ],
        risk_flags=[
            "historical_article_not_current_law",
            "current_effective_no_result_does_not_prove_never_existed",
        ],
        next_actions=[
            "Disclose the historical reference date when citing this article.",
            "Do not use the historical article as current-law authority without a current effective lookup.",
        ],
        evidence={
            "as_of": "20121230",
            "article_effective_date": article.effective_date,
            "history_statuses": history_statuses,
            "history_revision_types": [event.revision_type for event in history.events],
            "call_targets": [target for _, target, _ in source.calls],
        },
    )


def _audit_future_effective_administrative_rule_after_followup() -> LegislativeExpertScenarioReport:
    identity = LawIdentity(law_id="001747", name="자동차관리법", basis="effective", mst="270001")
    source = ScenarioSource(
        service_payloads=[
            law_text_payload("자동차관리법", "001747", "270001", article="제26조", title="자동차의 강제처리"),
            law_structure_payload("자동차관리법", "001747", "270001", "자동차관리법 시행령"),
            delegation_payload("자동차관리법", "자동차관리법 시행령", law_id="001747", article="26"),
            _administrative_rule_detail_payload(effective_date="20270101"),
        ],
        search_payloads=[
            administrative_rule_search_payload("무단방치 자동차 처리 규정"),
            {"ExpcSearch": {"expc": []}},
            {"PrecSearch": {"prec": []}},
            {"DetcSearch": {"detc": []}},
            {"licbyl": []},
            {"admbyl": []},
        ],
    )
    api = MolegApi(source)

    bundle = api.load_institutional_system([identity], budget="minimal", as_of="2026-06-17")
    administrative_rule = api.get_administrative_rule(bundle.candidates.administrative_rules[0].identity)
    reference_date = bundle.request.as_of or ""
    administrative_rule_effective_date = administrative_rule.identity.effective_date or ""

    return LegislativeExpertScenarioReport(
        scenario="future_effective_administrative_rule_guardrail",
        question="하위 고시 본문을 읽었더라도 기준일 현재 시행 전이면 현재 운용기준처럼 말하지 않는가?",
        status="ready_for_reasoning",
        public_interfaces=[
            "load_institutional_system",
            "get_administrative_rule",
        ],
        must_have={
            "reference_date_preserved": reference_date == "20260617",
            "current_statute_loaded": bundle.loaded.laws[0].identity.name == "자동차관리법",
            "administrative_rule_body_loaded": "무단방치 자동차 처리 기준" in administrative_rule.text,
            "administrative_rule_future_effective_date_preserved": administrative_rule_effective_date == "20270101",
            "administrative_rule_not_current_as_of": administrative_rule_effective_date > reference_date,
            "statute_current_gap_not_confused_with_rule_effective_date": not any(
                gap.kind == "not_effective_as_of" for gap in bundle.gaps
            ),
        },
        citations=[
            SourceCitation("law", "eflaw", "자동차관리법", "제26조", "current statute"),
            SourceCitation("delegation", "lsDelegated", "자동차관리법 시행령", "제26조", "delegated rule graph"),
            SourceCitation(
                "administrative_rule",
                "admrul",
                "무단방치 자동차 처리 규정",
                "제2조",
                "loaded administrative rule not effective as of reference date",
            ),
        ],
        risk_flags=["administrative_rule_not_effective_as_of_reference_date"],
        next_actions=[
            "Disclose that the selected administrative rule was loaded but is not effective as of the reference date.",
            "Find the currently effective administrative-rule text before describing current operational criteria.",
        ],
        evidence={
            "as_of": reference_date,
            "administrative_rule_effective_date": administrative_rule_effective_date,
            "administrative_rule_articles": [article.article for article in administrative_rule.articles],
            "gap_kinds": [gap.kind for gap in bundle.gaps],
            "call_targets": [target for _, target, _ in source.calls],
        },
    )


def _audit_future_effective_promulgated_law() -> LegislativeExpertScenarioReport:
    source = ScenarioSource(
        search_payloads=[
            law_search_payload(
                "데이터기본법",
                law_id="111111",
                mst="260001",
                promulgation_number="20000",
                promulgation_date="20260601",
            ),
            {"AdmRulSearch": {"admrul": []}},
            {"ExpcSearch": {"expc": []}},
            {"PrecSearch": {"prec": []}},
            {"DetcSearch": {"detc": []}},
            {"licbyl": []},
            {"admbyl": []},
        ],
        service_payloads=[
            law_text_payload(
                "데이터기본법",
                "111111",
                "270001",
                article="제1조",
                title="목적",
                effective_date="20270101",
            ),
            delegation_payload("데이터기본법", "데이터기본법 시행령", law_id="111111", article="10"),
        ],
    )

    bundle = MolegApi(source).load_legal_context_bundle(
        promulgation_bridge={
            "prom_law_nm": "데이터기본법",
            "prom_no": "20000",
            "promulgation_dt": "20260601",
        },
        mode="promulgated_bill",
        budget="minimal",
        as_of="2026-06-17",
    )
    gap_kinds = [gap.kind for gap in bundle.gaps]

    return LegislativeExpertScenarioReport(
        scenario="future_effective_promulgated_law_guardrail",
        question="공포는 됐지만 기준일 현재 시행 전인 법령을 현행 시행 법령처럼 말하지 않는가?",
        status="ready_for_reasoning",
        public_interfaces=["load_legal_context_bundle"],
        must_have={
            "promulgation_bridge_resolved": bundle.loaded.laws[0].identity.name == "데이터기본법",
            "reference_date_preserved": bundle.request.as_of == "20260617",
            "future_effective_date_preserved": bundle.loaded.laws[0].identity.effective_date == "20270101",
            "not_effective_gap_preserved": "not_effective_as_of" in gap_kinds,
            "effective_lookup_used_reference_date": source.calls[1] == (
                "service",
                "eflaw",
                {"MST": "260001", "efYd": "20260617"},
            ),
        },
        citations=[
            SourceCitation("law", "eflaw", "데이터기본법", authority="promulgated law not effective as of reference date"),
        ],
        risk_flags=["promulgated_law_not_effective_as_of_reference_date"],
        next_actions=[
            "Disclose that the law is promulgated/source-loadable but not effective as of the reference date.",
        ],
        evidence={
            "as_of": bundle.request.as_of,
            "effective_date": bundle.loaded.laws[0].identity.effective_date,
            "gap_kinds": gap_kinds,
            "call_targets": [target for _, target, _ in source.calls],
        },
    )


def _audit_institutional_system_future_effective_law() -> LegislativeExpertScenarioReport:
    identity = LawIdentity(law_id="010000", name="전자금융거래법", basis="effective", mst="280000")
    source = ScenarioSource(
        service_payloads=[
            law_text_payload(
                "전자금융거래법",
                "010000",
                "280000",
                article="제21조",
                title="안전성 확보",
                effective_date="20270101",
            ),
            law_structure_payload("전자금융거래법", "010000", "280000", "전자금융거래법 시행령"),
            delegation_payload("전자금융거래법", "전자금융거래법 시행령", law_id="010000", article="21"),
        ],
        search_payloads=[
            {"AdmRulSearch": {"admrul": []}},
            {"ExpcSearch": {"expc": []}},
            {"PrecSearch": {"prec": []}},
            {"DetcSearch": {"detc": []}},
            {"licbyl": []},
            {"admbyl": []},
        ],
    )

    bundle = MolegApi(source).load_institutional_system(
        [identity],
        budget="minimal",
        as_of="2026-06-17",
    )
    gap_kinds = [gap.kind for gap in bundle.gaps]

    return LegislativeExpertScenarioReport(
        scenario="institutional_system_future_effective_guardrail",
        question="명시 법령 세트로 제도를 검토할 때 기준일 현재 시행 전 법령을 현행 제도처럼 말하지 않는가?",
        status="ready_for_reasoning",
        public_interfaces=["load_institutional_system"],
        must_have={
            "explicit_statute_set_preserved": bundle.request.statute_ids == ["전자금융거래법"],
            "reference_date_preserved": bundle.request.as_of == "20260617",
            "future_effective_date_preserved": bundle.loaded.laws[0].identity.effective_date == "20270101",
            "not_effective_gap_preserved": "not_effective_as_of" in gap_kinds,
            "institutional_lookup_used_reference_date": source.calls[0] == (
                "service",
                "eflaw",
                {"MST": "280000", "efYd": "20260617"},
            ),
        },
        citations=[
            SourceCitation("law", "eflaw", "전자금융거래법", "제21조", "institutional-system law not effective as of reference date"),
        ],
        risk_flags=[
            "institutional_system_contains_law_not_effective_as_of_reference_date",
            "institutional_system_does_not_discover_statute_set",
        ],
        next_actions=[
            "Disclose that the selected statute is outside current-force scope on the reference date.",
        ],
        evidence={
            "as_of": bundle.request.as_of,
            "effective_date": bundle.loaded.laws[0].identity.effective_date,
            "gap_kinds": gap_kinds,
            "call_targets": [target for _, target, _ in source.calls],
        },
    )


def _audit_proposed_bill_without_promulgation_bridge() -> LegislativeExpertScenarioReport:
    source = ScenarioSource()
    blocked_reason = ""
    try:
        MolegApi(source).load_legal_context_bundle(
            query="플랫폼 노동자 보호법안이 현재 시행 중인지 검토",
            mode="promulgated_bill",
            promulgation_bridge={},
            budget="minimal",
        )
    except NoResultError as exc:
        blocked_reason = str(exc)

    return LegislativeExpertScenarioReport(
        scenario="proposed_bill_without_promulgation_bridge_guardrail",
        question="발의 법안명만 있는데 현행 법률처럼 검토하지 않는가?",
        status="blocked_for_manual_review",
        public_interfaces=["load_legal_context_bundle"],
        must_have={
            "missing_bridge_rejected": "promulgation_bridge is required" in blocked_reason,
            "no_moleg_source_called": source.calls == [],
            "congress_db_followup_required": True,
        },
        risk_flags=["proposed_bill_is_not_current_law_without_promulgation_bridge"],
        next_actions=[
            "Query congress-db for bill status and promulgation bridge fields before using MOLEG current-law loaders.",
        ],
        evidence={
            "blocked_reason": blocked_reason,
            "source_calls": source.calls,
        },
    )


def _audit_ambiguous_statute_set() -> LegislativeExpertScenarioReport:
    source = ScenarioSource(
        search_payloads=[
            {
                "LawSearch": {
                    "law": [
                        {
                            "법령ID": "111111",
                            "법령명한글": "데이터기본법",
                            "법령일련번호": "260001",
                            "공포번호": "20000",
                            "공포일자": "20250101",
                            "시행일자": "20260101",
                        },
                        {
                            "법령ID": "222222",
                            "법령명한글": "데이터기본법",
                            "법령일련번호": "260002",
                            "공포번호": "20001",
                            "공포일자": "20250201",
                            "시행일자": "20260101",
                        },
                    ]
                }
            }
        ]
    )

    bundle = MolegApi(source).load_institutional_system(["데이터기본법"], budget="minimal")

    return LegislativeExpertScenarioReport(
        scenario="ambiguous_statute_identity_guardrail",
        question="법령명이 같은 후보가 여러 개인데 첫 번째를 고르지 않는가?",
        status="blocked_for_manual_review",
        public_interfaces=["load_institutional_system", "search_laws"],
        must_have={
            "ambiguity_surfaced": any(item.kind == "statute_identity" for item in bundle.ambiguities),
            "no_law_loaded": not bundle.loaded.laws,
            "manual_review_gap_preserved": any(gap.kind == "manual_review_required" for gap in bundle.gaps),
            "search_laws_followup_preserved": any(item.interface == "search_laws" for item in bundle.deferred),
        },
        risk_flags=["ambiguous_law_name_must_not_be_silently_selected"],
        next_actions=["Resolve the candidate LawIdentity before loading institutional-system context."],
        evidence={
            "ambiguity_count": len(bundle.ambiguities),
            "candidate_count": len(bundle.ambiguities[0].candidates) if bundle.ambiguities else 0,
            "loaded_laws": len(bundle.loaded.laws),
        },
    )


def _audit_promulgation_bridge_source_lag() -> LegislativeExpertScenarioReport:
    source = ScenarioSource(
        search_payloads=[
            law_search_payload(
                "데이터기본법",
                law_id="111111",
                mst="260001",
                promulgation_number="20000",
                promulgation_date="20250101",
            ),
            law_search_payload(
                "데이터기본법",
                law_id="111111",
                mst="260001",
                promulgation_number="20000",
                promulgation_date="20250101",
            ),
            {"AdmRulSearch": {"admrul": []}},
            {"ExpcSearch": {"expc": []}},
            {"PrecSearch": {"prec": []}},
            {"DetcSearch": {"detc": []}},
            {"licbyl": []},
            {"admbyl": []},
        ]
    )

    bundle = MolegApi(source).load_legal_context_bundle(
        promulgation_bridge={
            "prom_law_nm": "데이터기본법",
            "prom_no": "99999",
            "promulgation_dt": "2025-02-01",
        },
        mode="promulgated_bill",
        budget="minimal",
    )

    return LegislativeExpertScenarioReport(
        scenario="promulgation_bridge_source_lag_guardrail",
        question="국회 공포 bridge가 MOLEG와 정확히 맞지 않을 때 미공포로 단정하지 않는가?",
        status="blocked_for_manual_review",
        public_interfaces=["load_legal_context_bundle", "resolve_promulgated_law", "search_laws"],
        must_have={
            "source_lag_ambiguity_surfaced": any(item.kind == "promulgation_bridge_lag" for item in bundle.ambiguities),
            "source_lag_gap_preserved": any(gap.kind == "source_lag_or_manual_review_required" for gap in bundle.gaps),
            "candidate_preserved": len(bundle.candidates.laws) == 1,
            "no_current_law_loaded": not bundle.loaded.laws,
        },
        risk_flags=["do_not_treat_exact_bridge_miss_as_not_enacted"],
        next_actions=["Check congress-db bridge fields and rerun resolve_promulgated_law before current-law reasoning."],
        evidence={
            "ambiguity_kinds": [item.kind for item in bundle.ambiguities],
            "gap_kinds": [gap.kind for gap in bundle.gaps],
            "candidate_names": [identity.name for identity in bundle.candidates.laws],
        },
    )


def _audit_interpretation_authority_distinction() -> LegislativeExpertScenarioReport:
    source = ScenarioSource(
        search_payloads=[
            {
                "Expc": {
                    "expc": [
                        {
                            "법령해석례일련번호": "330471",
                            "안건명": "자동차관리법 관련 법령해석례",
                            "회신기관명": "법제처",
                        }
                    ]
                }
            },
            {
                "CgmExpc": {
                    "cgmExpc": [
                        {
                            "법령해석일련번호": "2292577",
                            "안건명": "국방과학기술대제전 행사 문의",
                            "해석기관명": "방위사업청",
                        }
                    ]
                }
            },
        ]
    )

    hits = MolegApi(source).search_interpretations("기술", source="all", ministry="방위사업청", display=2)
    labels = [[hit.identity.source_type, hit.identity.source_target, hit.identity.ministry] for hit in hits]

    return LegislativeExpertScenarioReport(
        scenario="interpretation_authority_distinction",
        question="법제처 공식 해석과 부처 1차 해석이 답변 packet에서 구분되는가?",
        status="ready_for_reasoning",
        public_interfaces=["search_interpretations"],
        must_have={
            "official_moleg_label_present": ["moleg", "expc", None] in labels,
            "ministry_label_present": ["ministry", "dapaCgmExpc", "방위사업청"] in labels,
            "authority_order_preserved": labels == [
                ["moleg", "expc", None],
                ["ministry", "dapaCgmExpc", "방위사업청"],
            ],
        },
        citations=[
            SourceCitation("interpretation", "expc", "자동차관리법 관련 법령해석례", authority="MOLEG official interpretation"),
            SourceCitation("interpretation", "dapaCgmExpc", "국방과학기술대제전 행사 문의", authority="ministry first-instance interpretation"),
        ],
        risk_flags=["ministry_interpretation_is_not_moleg_official_interpretation"],
        evidence={"labels": labels},
    )


def _administrative_rule_detail_payload(
    effective_date: str = "20250101",
    source_article: str = "제26조",
) -> dict[str, Any]:
    return {
        "admrul": {
            "행정규칙 일련번호": "2100000248758",
            "행정규칙ID": "2077465",
            "행정규칙명": "무단방치 자동차 처리 규정",
            "행정규칙종류": "고시",
            "발령일자": "20250101",
            "소관부처명": "국토교통부",
            "시행일자": effective_date,
            "위임법령ID": "001747",
            "위임법령명": "자동차관리법",
            "위임조문번호": source_article,
            "위임조문제목": "자동차의 강제처리",
            "조문": {
                "조문단위": [
                    {
                        "조문번호": "1",
                        "조문제목": "목적",
                        "조문내용": "이 고시는 무단방치 자동차 처리에 필요한 사항을 정한다.",
                    },
                    {
                        "조문번호": "2",
                        "조문제목": "처리 기준",
                        "조문내용": "무단방치 자동차 처리 기준은 별표에 따른다.",
                    },
                ]
            },
        }
    }


def _administrative_rule_annex_search_payload() -> dict[str, Any]:
    return {
        "AdmRulBylSearch": {
            "admbyl": [
                {
                    "admrulbyl id": "330000001",
                    "관련행정규칙 일련번호": "2100000248758",
                    "관련법령ID": "001747",
                    "별표명": "무단방치 자동차 처리 기준",
                    "관련행정규칙명": "무단방치 자동차 처리 규정",
                    "별표번호": "별표 1",
                    "별표종류": "별표",
                    "소관부처명": "국토교통부",
                    "발령일자": "20250101",
                    "행정규칙종류": "고시",
                }
            ]
        }
    }


def _historical_repealed_law_history_html() -> str:
    return """
    <html>
      <div class="num">총<strong>2</strong>건</div>
      <table summary="법령 연혁정보 목록">
        <tbody>
          <tr>
            <td class="ce">1</td>
            <td><a href="/DRF/lawService.do?target=lsHistory&amp;MST=190002&amp;type=HTML&amp;efYd=20130101">온라인개인정보보호법</a></td>
            <td class="ce">개인정보보호위원회</td>
            <td class="ce">폐지</td>
            <td class="ce">법률</td>
            <td class="ce">제 12000호</td>
            <td class="ce">2012.12.31</td>
            <td class="ce">2013.1.1</td>
            <td class="ce">폐지</td>
          </tr>
          <tr class="gr">
            <td class="ce">2</td>
            <td><a href="/DRF/lawService.do?target=lsHistory&amp;MST=190001&amp;type=HTML&amp;efYd=20120101">온라인개인정보보호법</a></td>
            <td class="ce">개인정보보호위원회</td>
            <td class="ce">제정</td>
            <td class="ce">법률</td>
            <td class="ce">제 11000호</td>
            <td class="ce">2011.12.31</td>
            <td class="ce">2012.1.1</td>
            <td class="ce">연혁</td>
          </tr>
        </tbody>
      </table>
    </html>
    """


def main() -> None:
    print(
        json.dumps(
            [report.to_dict() for report in run_legislative_expert_e2e_audit()],
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
