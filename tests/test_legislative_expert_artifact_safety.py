import json

from scripts.legislative_expert_answer_discipline import run_legislative_expert_answer_discipline
from scripts.legislative_expert_e2e_audit import run_legislative_expert_e2e_audit
from scripts.legislative_expert_prompt_dry_run import (
    RAW_MOLEG_TARGETS,
    run_legislative_expert_prompt_dry_run,
)


SECRET_MARKERS = {
    "MOLEG_OC",
    "CONGRESS_DB_URL",
    "CONGRESS_DB_READONLY_URL",
    "DATABASE_URL",
}


def test_legislative_expert_audit_artifacts_are_json_safe():
    artifacts = [
        [report.to_dict() for report in run_legislative_expert_e2e_audit()],
        [report.to_dict() for report in run_legislative_expert_prompt_dry_run()],
        [report.to_dict() for report in run_legislative_expert_answer_discipline()],
    ]

    for artifact in artifacts:
        encoded = json.dumps(artifact, ensure_ascii=False, sort_keys=True)
        decoded = json.loads(encoded)
        assert decoded == artifact


def test_legislative_expert_audit_artifacts_do_not_expose_secrets_or_raw_targets():
    artifacts = [
        [report.to_dict() for report in run_legislative_expert_e2e_audit()],
        [report.to_dict() for report in run_legislative_expert_prompt_dry_run()],
        [report.to_dict() for report in run_legislative_expert_answer_discipline()],
    ]
    encoded = json.dumps(artifacts, ensure_ascii=False, sort_keys=True)

    assert not any(marker in encoded for marker in SECRET_MARKERS)

    leaked_targets = {
        step["interface"]
        for report in artifacts[1]
        for step in report["planned_steps"]
        if step["source"] == "moleg-api" and step["interface"] in RAW_MOLEG_TARGETS
    }
    assert leaked_targets == set()


def test_candidate_only_context_is_not_promoted_to_citation():
    delegated = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["delegated_criteria_tracing"]

    assert delegated.status == "needs_more_source_loading"
    assert all(citation.source_type != "administrative_rule" for citation in delegated.citations)
    assert all(citation.source_type != "annex" for citation in delegated.citations)
    assert "administrative_rule_candidate_not_loaded" in delegated.risk_flags


def test_interpretation_authority_labels_are_not_flattened():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["interpretation_authority_distinction"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["interpretation_authority_answer_discipline"]

    assert readiness.evidence["labels"] == [
        ["moleg", "expc", None],
        ["ministry", "dapaCgmExpc", "방위사업청"],
    ]
    assert {citation.authority for citation in readiness.citations} == {
        "MOLEG official interpretation",
        "ministry first-instance interpretation",
    }
    assert any("ministry first-instance" in claim for claim in discipline.forbidden_claims)


def test_followup_loaded_context_can_be_promoted_to_citation():
    loaded = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["delegated_criteria_after_followups"]

    assert loaded.status == "ready_for_reasoning"
    assert {"administrative_rule", "annex"}.issubset(
        {citation.source_type for citation in loaded.citations}
    )
    assert loaded.evidence["structured_annex_rows"] == 2


def test_query_discovered_delegated_criteria_can_be_promoted_after_detail_loading():
    loaded = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["delegated_criteria_query_candidate_discovery"]

    assert loaded.status == "ready_for_reasoning"
    assert "무단방치 자동차 처리 기준" in loaded.evidence["search_queries"]
    assert loaded.evidence["loaded_administrative_rules"] == ["무단방치 자동차 처리 규정"]
    assert loaded.evidence["loaded_annex_forms"] == ["무단방치 자동차 처리 기준"]
    assert {"administrative_rule", "annex"}.issubset(
        {citation.source_type for citation in loaded.citations}
    )
    assert (
        "delegated_criteria_uses_explicit_query_for_candidate_discovery"
        in loaded.risk_flags
    )


def test_moved_destination_query_delegated_criteria_can_be_promoted_after_detail_loading():
    loaded = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["delegated_criteria_moved_article_query_candidate_discovery"]

    assert loaded.status == "ready_for_reasoning"
    assert loaded.evidence["loaded_articles"] == ["제9조", "제12조"]
    assert "자동차관리법 제12조 등록 운영기준" in loaded.evidence["search_queries"]
    assert loaded.evidence["loaded_administrative_rules"] == ["자동차등록 운영규정"]
    assert loaded.evidence["loaded_annex_forms"] == ["자동차등록 기준"]
    assert {"law", "delegation", "administrative_rule", "annex"}.issubset(
        {citation.source_type for citation in loaded.citations}
    )
    assert (
        "delegated_criteria_moved_article_uses_destination_query_for_operational_candidates"
        in loaded.risk_flags
    )


def test_ambiguous_anchor_delegated_criteria_candidates_are_not_promoted_to_operational_criteria():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["delegated_criteria_ambiguous_anchor_guardrail"]

    assert readiness.status == "blocked_for_manual_review"
    assert readiness.citations == []
    assert readiness.evidence["loaded_administrative_rules"] == 0
    assert readiness.evidence["loaded_annex_forms"] == 0
    assert readiness.evidence["service_call_targets"] == []
    assert readiness.evidence["text_call_targets"] == []
    assert "get_administrative_rule" in readiness.evidence["deferred_interfaces"]
    assert "get_annex_form_body" in readiness.evidence["deferred_interfaces"]
    assert (
        "ambiguous_delegated_criteria_anchor_must_not_load_operational_detail"
        in readiness.risk_flags
    )


def test_low_confidence_annex_rows_are_not_promoted_to_threshold_claims():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["low_confidence_annex_body_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["low_confidence_annex_body_answer_discipline"]

    assert readiness.status == "ready_for_reasoning"
    assert readiness.evidence["parsing_confidence"] == "low"
    assert readiness.evidence["structured_rows"] == 0
    assert readiness.evidence["plain_text_contains_threshold"] is True
    assert "empty_structured_rows_do_not_mean_no_annex_criteria" in readiness.risk_flags
    assert any("empty structured rows" in claim for claim in discipline.forbidden_claims)
    assert any("low parsing confidence" in disclosure for disclosure in discipline.required_disclosures)


def test_future_effective_promulgated_law_is_not_promoted_to_current_force_claim():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["future_effective_promulgated_law_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["future_effective_promulgated_law_answer_discipline"]

    assert readiness.status == "ready_for_reasoning"
    assert "not_effective_as_of" in readiness.evidence["gap_kinds"]
    assert discipline.evidence["as_of"] == "20260617"
    assert discipline.evidence["effective_date"] == "20270101"
    assert any("currently in force" in claim for claim in discipline.forbidden_claims)


def test_current_law_bridge_is_not_promoted_to_amendment_delta_claim():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["congress_bill_to_current_law"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["enacted_bill_change_trace_answer_discipline"]

    assert readiness.status == "ready_for_reasoning"
    assert readiness.evidence["resolved_law"] == "데이터기본법"
    assert readiness.evidence["has_history_followup"] is True
    assert "history_not_loaded_until_article_or_date_known" in readiness.risk_flags
    assert discipline.status == "must_load_more_sources"
    assert {"trace_law_history", "compare_law_versions"}.issubset(discipline.required_followups)
    assert any("Current text alone" in claim for claim in discipline.forbidden_claims)
    assert any("bridge resolution" in claim for claim in discipline.forbidden_claims)


def test_loaded_before_after_diff_is_not_promoted_to_legislative_intent():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["loaded_before_after_amendment_delta_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["loaded_before_after_amendment_delta_answer_discipline"]

    assert readiness.status == "ready_for_reasoning"
    assert readiness.evidence["changes"][0]["before_text"] == "종전 목적"
    assert readiness.evidence["changes"][0]["after_text"] == "개정 목적"
    assert {citation.source_type for citation in readiness.citations} == {"law_diff"}
    assert "old_and_new_does_not_prove_legislative_intent" in readiness.risk_flags
    assert discipline.status == "can_answer_with_loaded_sources"
    assert "trace_law_history" in discipline.required_followups
    assert any("before/after wording" in claim for claim in discipline.allowed_claims)
    assert any("legislative intent" in claim for claim in discipline.forbidden_claims)
    assert any("selected article" in disclosure for disclosure in discipline.required_disclosures)


def test_historical_article_is_not_promoted_to_current_law_authority():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["historical_article_as_of_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["historical_repealed_law_answer_discipline"]

    assert readiness.status == "ready_for_reasoning"
    assert readiness.evidence["as_of"] == "20121230"
    assert "폐지" in readiness.evidence["history_statuses"]
    assert "historical_article_not_current_law" in readiness.risk_flags
    assert discipline.status == "can_answer_with_loaded_sources"
    assert any("currently in force" in claim for claim in discipline.forbidden_claims)
    assert any("as-of date" in disclosure for disclosure in discipline.required_disclosures)


def test_future_effective_institutional_system_law_preserves_reference_date_gap():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["institutional_system_future_effective_guardrail"]

    assert readiness.status == "ready_for_reasoning"
    assert readiness.evidence["as_of"] == "20260617"
    assert readiness.evidence["effective_date"] == "20270101"
    assert "not_effective_as_of" in readiness.evidence["gap_kinds"]


def test_institutional_system_bundle_is_not_promoted_to_exhaustive_statute_discovery():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["multi_law_concept_assembly"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["institutional_system_answer_discipline"]

    assert readiness.status == "ready_for_reasoning"
    assert readiness.evidence["request_statute_ids"] == [
        "전자금융거래법",
        "전자금융거래법 시행령",
    ]
    assert "institutional_system_does_not_discover_statute_set" in readiness.risk_flags
    assert discipline.status == "can_answer_with_loaded_sources"
    assert {"expand_legal_query", "search_laws"}.issubset(discipline.required_followups)
    assert any("exhaustive list" in claim for claim in discipline.forbidden_claims)


def test_future_effective_administrative_rule_is_not_promoted_to_current_operational_claim():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["future_effective_administrative_rule_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["future_effective_administrative_rule_answer_discipline"]

    assert readiness.status == "ready_for_reasoning"
    assert readiness.evidence["as_of"] == "20260617"
    assert readiness.evidence["administrative_rule_effective_date"] == "20270101"
    assert "administrative_rule_not_effective_as_of_reference_date" in readiness.risk_flags
    assert discipline.evidence["administrative_rule_effective_date"] == "20270101"
    assert any("current operational criteria" in claim for claim in discipline.forbidden_claims)


def test_moleg_legal_citation_is_not_promoted_to_latest_social_fact_source():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["latest_social_context_websearch_handoff"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["latest_social_context_answer_discipline"]

    assert readiness.status == "needs_more_source_loading"
    assert {citation.source_type for citation in readiness.citations} == {"law"}
    assert readiness.evidence["social_fact_sources_loaded"] == []
    assert "latest_social_facts_require_websearch" in readiness.risk_flags
    assert discipline.status == "must_load_more_sources"
    assert discipline.required_followups == ["websearch.latest_social_facts"]
    assert any("latest statistics" in claim for claim in discipline.forbidden_claims)
    assert any("legal-source citations" in disclosure for disclosure in discipline.required_disclosures)


def test_supplementary_provisions_are_not_flattened_into_main_article_claims():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["supplementary_provision_transition_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["supplementary_transition_answer_discipline"]

    assert readiness.status == "ready_for_reasoning"
    assert readiness.must_have["transition_text_not_in_main_article"] is True
    assert {"law", "supplementary_provision"} == {
        citation.source_type for citation in readiness.citations
    }
    assert "supplementary_provision_required_for_transition_application" in readiness.risk_flags
    assert discipline.status == "can_answer_with_loaded_sources"
    assert any("main article alone" in claim for claim in discipline.forbidden_claims)
    assert any("effective_date metadata" in claim for claim in discipline.forbidden_claims)
    assert any("separately" in disclosure for disclosure in discipline.required_disclosures)


def test_nested_article_units_are_not_flattened_or_omitted_from_definition_claims():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["nested_article_unit_text_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["nested_article_unit_answer_discipline"]

    assert readiness.status == "ready_for_reasoning"
    assert readiness.evidence["line_count"] >= 4
    assert readiness.evidence["contains_terms"]["일반형 승용자동차"] is True
    assert "nested_article_units_required_for_complete_article_text" in readiness.risk_flags
    assert discipline.status == "can_answer_with_loaded_sources"
    assert any("top-level 조문내용 alone" in claim for claim in discipline.forbidden_claims)
    assert any("Nested 호 or 목" in claim for claim in discipline.forbidden_claims)
    assert any("nested 항, 호, or 목 labels" in disclosure for disclosure in discipline.required_disclosures)


def test_deleted_article_status_is_not_promoted_to_current_operational_claim():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["deleted_article_status_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["deleted_article_answer_discipline"]

    assert readiness.status == "ready_for_reasoning"
    assert readiness.evidence["is_deleted"] is True
    assert readiness.evidence["revision_type"] == "삭제"
    assert "deleted_article_is_not_current_operational_text" in readiness.risk_flags
    assert discipline.status == "can_answer_with_loaded_sources"
    assert any("current duty" in claim for claim in discipline.forbidden_claims)
    assert any("substantive article content" in claim for claim in discipline.forbidden_claims)
    assert any("marked deleted" in disclosure for disclosure in discipline.required_disclosures)


def test_moved_article_status_is_not_promoted_to_current_operational_claim():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["moved_article_status_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["moved_article_answer_discipline"]

    assert readiness.status == "ready_for_reasoning"
    assert readiness.evidence["is_deleted"] is False
    assert readiness.evidence["revision_type"] == "이동"
    assert readiness.evidence["moved_to"] == "제12조"
    assert readiness.evidence["current_article"] == "제12조"
    assert {citation.article for citation in readiness.citations} == {"제8조", "제12조"}
    assert "moved_article_destination_loaded_before_current_substance" in readiness.risk_flags
    assert discipline.status == "can_answer_with_loaded_sources"
    assert "get_article" not in discipline.required_followups
    assert any("moved article marker" in claim for claim in discipline.forbidden_claims)
    assert any("moved article" in disclosure for disclosure in discipline.required_disclosures)


def test_context_bundle_article_status_cites_destination_not_deleted_or_moved_marker():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["context_bundle_article_status_guardrail"]

    assert readiness.status == "ready_for_reasoning"
    assert readiness.evidence["article_statuses"][0]["is_deleted"] is True
    assert readiness.evidence["article_statuses"][1]["moved_to"] == "제12조"
    assert "deleted_article" in readiness.evidence["gap_kinds"]
    assert {citation.article for citation in readiness.citations} == {"제12조"}
    assert "context_bundle_deleted_article_not_current_operational_text" in readiness.risk_flags
    assert (
        "context_bundle_moved_article_destination_loaded_before_current_substance"
        in readiness.risk_flags
    )


def test_whole_law_context_bundle_article_status_requires_followup_before_operational_claim():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["context_bundle_whole_law_article_status_guardrail"]

    assert readiness.status == "needs_more_source_loading"
    assert readiness.evidence["article_statuses"][0]["is_deleted"] is True
    assert readiness.evidence["article_statuses"][1]["moved_to"] == "제12조"
    assert "deleted_article" in readiness.evidence["gap_kinds"]
    assert "moved_article" in readiness.evidence["gap_kinds"]
    assert readiness.evidence["deferred"][0]["interface"] == "load_article_context"
    assert {citation.authority for citation in readiness.citations} == {
        "deleted article marker",
        "moved article marker",
    }
    assert "whole_law_deleted_article_is_not_current_operational_text" in readiness.risk_flags
    assert (
        "whole_law_moved_article_requires_article_context_before_current_substance"
        in readiness.risk_flags
    )


def test_context_bundle_moved_authority_uses_destination_article_citations():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["context_bundle_moved_article_destination_authority_search"]

    assert readiness.status == "ready_for_reasoning"
    assert readiness.evidence["loaded_articles"] == ["제9조", "제12조"]
    assert "자동차관리법 제12조 의무의 의미와 위헌 위험" in readiness.evidence["search_queries"]
    assert {citation.article for citation in readiness.citations} == {"제12조"}
    assert not [kind for kind in readiness.evidence["gap_kinds"] if kind.startswith("authority_")]
    assert "context_bundle_moved_article_searches_destination_authority" in readiness.risk_flags


def test_context_bundle_moved_operational_candidates_require_detail_loading():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["context_bundle_moved_article_destination_candidate_search"]

    assert readiness.status == "needs_more_source_loading"
    assert readiness.evidence["administrative_rule_candidates"] == ["자동차등록 운영규정"]
    assert readiness.evidence["annex_form_candidates"] == ["자동차등록 기준", "자동차등록 신청서"]
    assert readiness.evidence["loaded_administrative_rules"] == 0
    assert readiness.evidence["loaded_annex_forms"] == 0
    assert {citation.source_type for citation in readiness.citations} == {"law"}
    assert "get_administrative_rule" in readiness.evidence["deferred_interfaces"]
    assert "get_annex_form_body" in readiness.evidence["deferred_interfaces"]
    assert (
        "administrative_rule_and_annex_candidates_not_loaded_operational_criteria"
        in readiness.risk_flags
    )


def test_query_expansion_candidates_are_not_promoted_to_source_citations():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["query_expansion_candidate_authority_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["query_expansion_candidate_answer_discipline"]

    assert readiness.status == "needs_more_source_loading"
    assert readiness.citations == []
    assert readiness.evidence["citations_loaded"] == 0
    assert "query_expansion_is_not_final_authority" in readiness.risk_flags
    assert discipline.status == "must_load_more_sources"
    assert {"search_laws", "get_article"}.issubset(discipline.required_followups)
    assert any("inspected legal authority" in claim for claim in discipline.forbidden_claims)


def test_law_search_candidates_are_not_promoted_to_law_text_citations():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["law_search_candidate_detail_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["law_search_candidate_answer_discipline"]

    assert readiness.status == "needs_more_source_loading"
    assert readiness.citations == []
    assert readiness.evidence["citations_loaded"] == 0
    assert readiness.evidence["service_call_targets"] == []
    assert "law_search_hit_requires_selected_law_or_article_loading" in readiness.risk_flags
    assert discipline.status == "must_load_more_sources"
    assert "get_article" in discipline.required_followups
    assert any("identity metadata" in claim for claim in discipline.forbidden_claims)


def test_context_bundle_ambiguous_question_candidates_are_not_promoted_to_law_text():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["context_bundle_ambiguous_question_law_candidate_guardrail"]

    assert readiness.status == "blocked_for_manual_review"
    assert readiness.citations == []
    assert readiness.evidence["loaded_laws"] == 0
    assert readiness.evidence["loaded_authority_count"] == 0
    assert "manual_review_required" in readiness.evidence["gap_kinds"]
    assert "search_laws" in readiness.evidence["deferred_interfaces"]
    assert "get_interpretation" in readiness.evidence["deferred_interfaces"]
    assert "get_case" in readiness.evidence["deferred_interfaces"]
    assert "eflaw" not in readiness.evidence["service_call_targets"]
    assert "expc" not in readiness.evidence["service_call_targets"]
    assert "prec" not in readiness.evidence["service_call_targets"]
    assert (
        "ambiguous_question_law_candidates_must_not_be_silently_selected"
        in readiness.risk_flags
    )
    assert (
        "ambiguous_question_law_candidates_block_authority_detail_eager_load"
        in readiness.risk_flags
    )


def test_empty_law_search_is_not_promoted_to_no_legal_source_claim():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["empty_law_search_absence_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["empty_law_search_absence_answer_discipline"]

    assert readiness.status == "needs_more_source_loading"
    assert readiness.evidence["hit_count"] == 0
    assert readiness.citations == []
    assert "empty_law_search_is_not_absence_of_current_law" in readiness.risk_flags
    assert discipline.status == "must_load_more_sources"
    assert "expand_legal_query" in discipline.required_followups
    assert any("No current legal basis exists" in claim for claim in discipline.forbidden_claims)
    assert any("one scoped law search" in disclosure for disclosure in discipline.required_disclosures)


def test_interpretation_search_candidates_are_not_promoted_to_substance_citations():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["interpretation_search_candidate_detail_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["interpretation_search_candidate_answer_discipline"]

    assert readiness.status == "needs_more_source_loading"
    assert readiness.citations == []
    assert readiness.evidence["citations_loaded"] == 0
    assert readiness.evidence["service_call_targets"] == []
    assert "interpretation_search_hit_requires_get_interpretation_detail" in readiness.risk_flags
    assert discipline.status == "must_load_more_sources"
    assert "get_interpretation" in discipline.required_followups
    assert any("search metadata" in claim for claim in discipline.forbidden_claims)


def test_empty_interpretation_search_is_not_promoted_to_no_authority_claim():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["empty_interpretation_search_absence_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["empty_interpretation_search_absence_answer_discipline"]

    assert readiness.status == "needs_more_source_loading"
    assert readiness.evidence["hit_count"] == 0
    assert readiness.citations == []
    assert "empty_interpretation_search_is_not_absence_of_authority" in readiness.risk_flags
    assert discipline.status == "must_load_more_sources"
    assert "expand_legal_query" in discipline.required_followups
    assert "search_interpretations" in discipline.required_followups
    assert any("No relevant interpretation exists" in claim for claim in discipline.forbidden_claims)
    assert any("absence of authority" in claim for claim in discipline.forbidden_claims)


def test_source_access_failure_is_not_promoted_to_no_legal_source_claim():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["source_access_failure_not_no_result_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["source_access_failure_answer_discipline"]

    assert readiness.status == "needs_more_source_loading"
    assert readiness.citations == []
    assert readiness.evidence["hit_count"] is None
    assert readiness.evidence["error_type"] == "RateLimitError"
    assert "source_access_failure_is_not_legal_no_result" in readiness.risk_flags
    assert discipline.status == "must_load_more_sources"
    assert "search_laws" in discipline.required_followups
    assert any("No current legal basis exists" in claim for claim in discipline.forbidden_claims)
    assert any("source-access failure" in disclosure for disclosure in discipline.required_disclosures)


def test_case_search_candidates_are_not_promoted_to_judicial_citations():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["case_search_candidate_detail_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["case_search_candidate_answer_discipline"]

    assert readiness.status == "needs_more_source_loading"
    assert readiness.citations == []
    assert readiness.evidence["citations_loaded"] == 0
    assert readiness.evidence["service_call_targets"] == []
    assert "case_search_hit_requires_get_case_detail" in readiness.risk_flags
    assert discipline.status == "must_load_more_sources"
    assert "get_case" in discipline.required_followups
    assert any("search metadata" in claim for claim in discipline.forbidden_claims)


def test_empty_case_search_is_not_promoted_to_no_precedent_claim():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["empty_case_search_absence_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["empty_case_search_absence_answer_discipline"]

    assert readiness.status == "needs_more_source_loading"
    assert readiness.evidence["hit_count"] == 0
    assert readiness.citations == []
    assert "empty_case_search_is_not_absence_of_judicial_authority" in readiness.risk_flags
    assert discipline.status == "must_load_more_sources"
    assert "search_cases" in discipline.required_followups
    assert any("No relevant precedent exists" in claim for claim in discipline.forbidden_claims)
    assert any("one scoped case search" in disclosure for disclosure in discipline.required_disclosures)


def test_constitutional_search_candidates_are_not_promoted_to_decision_citations():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["constitutional_search_candidate_detail_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["constitutional_search_candidate_answer_discipline"]

    assert readiness.status == "needs_more_source_loading"
    assert readiness.citations == []
    assert readiness.evidence["citations_loaded"] == 0
    assert readiness.evidence["service_call_targets"] == []
    assert (
        "constitutional_search_hit_requires_get_constitutional_decision_detail"
        in readiness.risk_flags
    )
    assert discipline.status == "must_load_more_sources"
    assert "get_constitutional_decision" in discipline.required_followups
    assert any("search metadata" in claim for claim in discipline.forbidden_claims)


def test_empty_constitutional_search_is_not_promoted_to_no_constitutional_risk_claim():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["empty_constitutional_search_absence_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["empty_constitutional_search_absence_answer_discipline"]

    assert readiness.status == "needs_more_source_loading"
    assert readiness.evidence["hit_count"] == 0
    assert readiness.citations == []
    assert (
        "empty_constitutional_search_is_not_absence_of_constitutional_authority"
        in readiness.risk_flags
    )
    assert discipline.status == "must_load_more_sources"
    assert "search_constitutional_decisions" in discipline.required_followups
    assert any("No constitutional decision exists" in claim for claim in discipline.forbidden_claims)
    assert any("one scoped Constitutional Court search" in disclosure for disclosure in discipline.required_disclosures)


def test_moved_authority_context_uses_destination_article_citations():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["authority_context_moved_article_destination_search"]

    assert readiness.status == "ready_for_reasoning"
    assert readiness.evidence["loaded_articles"] == ["제9조", "제12조"]
    assert readiness.evidence["target_articles"] == ["제12조"]
    assert "자동차관리법 제12조" in readiness.evidence["search_queries"]
    assert {citation.article for citation in readiness.citations} == {"제12조"}
    assert "authority_context_moved_article_searches_destination_article" in readiness.risk_flags


def test_mismatched_loaded_authorities_are_not_promoted_to_target_article_citations():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["loaded_authority_article_mismatch_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["authority_article_reference_mismatch_answer_discipline"]

    assert readiness.status == "needs_more_source_loading"
    assert readiness.citations == []
    assert readiness.evidence["citations_loaded"] == 0
    assert readiness.evidence["authority_article_matches"] == {
        "interpretation": False,
        "case": False,
        "constitutional": False,
    }
    assert (
        "loaded_authority_reference_mismatch_not_target_article_authority"
        in readiness.risk_flags
    )
    assert discipline.status == "must_load_more_sources"
    assert discipline.citations == []
    assert "load_authority_context" in discipline.required_followups
    assert any("target article" in claim for claim in discipline.forbidden_claims)


def test_missing_requested_article_is_not_promoted_to_current_article_citation():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["context_bundle_requested_article_not_loaded_guardrail"]

    assert readiness.status == "needs_more_source_loading"
    assert readiness.citations == []
    assert readiness.evidence["citations_loaded"] == 0
    assert readiness.evidence["article_gap_interfaces"] == ["get_article"]
    assert "requested_article_not_loaded" in readiness.evidence["gap_kinds"]
    assert (
        "requested_article_not_loaded_is_not_current_article_text"
        in readiness.risk_flags
    )


def test_missing_requested_law_is_not_promoted_to_current_law_citation():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["context_bundle_requested_law_not_loaded_guardrail"]

    assert readiness.status == "needs_more_source_loading"
    assert readiness.citations == []
    assert readiness.evidence["citations_loaded"] == 0
    assert readiness.evidence["law_gap_interfaces"] == ["get_law"]
    assert "requested_law_not_loaded" in readiness.evidence["gap_kinds"]
    assert "requested_law_not_loaded_is_not_current_law_text" in readiness.risk_flags


def test_context_bundle_authority_mismatch_gaps_are_not_promoted_to_target_article_citations():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["context_bundle_authority_article_mismatch_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["context_bundle_authority_article_mismatch_answer_discipline"]

    assert readiness.status == "needs_more_source_loading"
    assert [citation.source_type for citation in readiness.citations] == ["law"]
    assert readiness.evidence["authority_gap_interfaces"] == [
        "search_interpretations",
        "search_cases",
        "search_constitutional_decisions",
    ]
    assert readiness.evidence["authority_article_matches"] == {
        "interpretation": False,
        "case": False,
        "constitutional": False,
    }
    assert (
        "context_bundle_eager_authority_reference_mismatch_not_target_article_citation"
        in readiness.risk_flags
    )
    assert discipline.status == "must_load_more_sources"
    assert "search_interpretations" in discipline.required_followups
    assert "search_cases" in discipline.required_followups
    assert "search_constitutional_decisions" in discipline.required_followups
    assert any("target article" in claim for claim in discipline.forbidden_claims)


def test_context_bundle_authority_unverified_gaps_are_not_promoted_to_target_article_citations():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["context_bundle_authority_article_unverified_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["context_bundle_authority_article_unverified_answer_discipline"]

    assert readiness.status == "needs_more_source_loading"
    assert [citation.source_type for citation in readiness.citations] == ["law"]
    assert readiness.evidence["authority_gap_interfaces"] == [
        "search_interpretations",
        "search_cases",
        "search_constitutional_decisions",
    ]
    assert readiness.evidence["authority_reference_counts"] == {
        "interpretation": 0,
        "case": 0,
        "constitutional": 0,
    }
    assert (
        "context_bundle_eager_authority_without_structured_refs_not_target_article_citation"
        in readiness.risk_flags
    )
    assert discipline.status == "must_load_more_sources"
    assert "search_interpretations" in discipline.required_followups
    assert "search_cases" in discipline.required_followups
    assert "search_constitutional_decisions" in discipline.required_followups
    assert any("implicit match" in claim for claim in discipline.forbidden_claims)


def test_context_bundle_authority_partial_match_gaps_are_not_broadcast_to_all_requested_articles():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["context_bundle_authority_article_partial_match_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["context_bundle_authority_article_partial_match_answer_discipline"]

    assert readiness.status == "needs_more_source_loading"
    assert [citation.source_type for citation in readiness.citations] == ["law", "law"]
    assert readiness.evidence["authority_gap_interfaces"] == [
        "search_interpretations",
        "search_cases",
        "search_constitutional_decisions",
    ]
    assert readiness.evidence["authority_matched_articles"] == {
        "interpretation": ["제17조"],
        "case": ["제17조"],
        "constitutional": ["제17조"],
    }
    assert readiness.evidence["missing_authority_article"] == "제15조"
    assert (
        "context_bundle_loaded_authority_detail_must_not_be_broadcast_to_all_requested_articles"
        in readiness.risk_flags
    )
    assert discipline.status == "must_load_more_sources"
    assert "search_interpretations" in discipline.required_followups
    assert "search_cases" in discipline.required_followups
    assert "search_constitutional_decisions" in discipline.required_followups
    assert any("제15조" in claim for claim in discipline.forbidden_claims)
    assert any("every requested article" in claim for claim in discipline.forbidden_claims)


def test_context_bundle_authority_temporal_mismatch_is_not_promoted_to_current_authority():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["context_bundle_authority_temporal_mismatch_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["context_bundle_authority_temporal_mismatch_answer_discipline"]

    assert readiness.status == "needs_more_source_loading"
    assert [citation.source_type for citation in readiness.citations] == ["law"]
    assert readiness.evidence["target_article"]["effective_date"] == "20250101"
    assert readiness.evidence["authority_dates"] == {
        "interpretation": "20210115",
        "case": "20210215",
        "constitutional": "20210315",
    }
    assert readiness.evidence["authority_article_matches"] == {
        "interpretation": True,
        "case": True,
        "constitutional": True,
    }
    assert readiness.evidence["authority_gap_interfaces"] == [
        "trace_law_history",
        "trace_law_history",
        "trace_law_history",
    ]
    assert readiness.evidence["authority_deferred_filters"] == [
        {
            "law_name": "개인정보 보호법",
            "article": "제15조",
            "authority_source_type": "interpretation",
            "authority_date": "20210115",
            "current_article_effective_date": "20250101",
        },
        {
            "law_name": "개인정보 보호법",
            "article": "제15조",
            "authority_source_type": "case",
            "authority_date": "20210215",
            "current_article_effective_date": "20250101",
        },
        {
            "law_name": "개인정보 보호법",
            "article": "제15조",
            "authority_source_type": "constitutional",
            "authority_date": "20210315",
            "current_article_effective_date": "20250101",
        },
    ]
    assert (
        "matching_referenced_article_is_not_enough_when_authority_predates_current_wording"
        in readiness.risk_flags
    )
    assert discipline.status == "must_load_more_sources"
    assert {"trace_law_history", "get_article"}.issubset(discipline.required_followups)
    assert any("current target-article authority" in claim for claim in discipline.forbidden_claims)
    assert any("authority_temporal_mismatch" in disclosure for disclosure in discipline.required_disclosures)


def test_context_bundle_authority_after_reference_date_is_not_promoted_to_as_of_authority():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["context_bundle_authority_after_reference_date_guardrail"]

    assert readiness.status == "needs_more_source_loading"
    assert [citation.source_type for citation in readiness.citations] == ["law"]
    assert readiness.evidence["reference_date"] == "20250101"
    assert readiness.evidence["target_article"]["effective_date"] == "20240101"
    assert readiness.evidence["authority_dates"] == {
        "interpretation": "20250615",
        "case": "20250710",
        "constitutional": "20250827",
    }
    assert readiness.evidence["authority_article_matches"] == {
        "interpretation": True,
        "case": True,
        "constitutional": True,
    }
    assert readiness.evidence["authority_gap_interfaces"] == [
        "search_interpretations",
        "search_cases",
        "search_constitutional_decisions",
    ]
    assert (
        "matching_referenced_article_is_not_enough_when_authority_postdates_reference_date"
        in readiness.risk_flags
    )


def test_administrative_rule_search_candidates_are_not_promoted_to_rule_text_citations():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["administrative_rule_search_candidate_detail_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["administrative_rule_search_candidate_answer_discipline"]

    assert readiness.status == "needs_more_source_loading"
    assert readiness.citations == []
    assert readiness.evidence["citations_loaded"] == 0
    assert readiness.evidence["service_call_targets"] == []
    assert (
        "administrative_rule_search_hit_requires_get_administrative_rule_detail"
        in readiness.risk_flags
    )
    assert discipline.status == "must_load_more_sources"
    assert "get_administrative_rule" in discipline.required_followups
    assert any("metadata" in claim for claim in discipline.forbidden_claims)


def test_ambiguous_administrative_rule_name_is_not_promoted_to_rule_text_citation():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["administrative_rule_name_ambiguity_guardrail"]

    assert readiness.status == "blocked_for_manual_review"
    assert readiness.citations == []
    assert readiness.evidence["candidate_ids"] == ["2100000111111", "2100000222222"]
    assert readiness.evidence["service_call_targets"] == []
    assert "administrative_rule_name_must_not_be_silently_selected" in readiness.risk_flags


def test_administrative_rule_issued_on_filter_is_not_promoted_to_as_of_current_effect():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["administrative_rule_issued_on_not_effective_as_of_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["administrative_rule_issued_on_not_effective_as_of_answer_discipline"]

    assert readiness.status == "needs_more_source_loading"
    assert readiness.citations == []
    assert readiness.evidence["candidate"]["issuing_date"] == "20250101"
    assert readiness.evidence["candidate"]["effective_date"] == "20250301"
    assert (
        "administrative_rule_issued_on_filter_is_not_effective_as_of"
        in readiness.risk_flags
    )
    assert discipline.status == "must_load_more_sources"
    assert "get_administrative_rule" in discipline.required_followups
    assert "search_administrative_rules" in discipline.required_followups
    assert any("issued_on" in claim for claim in discipline.forbidden_claims)
    assert any("current_status" in claim for claim in discipline.forbidden_claims)
    assert any("발령일자" in disclosure for disclosure in discipline.required_disclosures)


def test_administrative_rule_article_status_is_not_promoted_to_operational_criteria():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["administrative_rule_article_status_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["administrative_rule_article_status_answer_discipline"]

    assert readiness.status == "ready_for_reasoning"
    assert len(readiness.citations) == 3
    assert readiness.evidence["article_statuses"][0]["is_deleted"] is True
    assert readiness.evidence["article_statuses"][1]["moved_to"] == "제6조"
    assert readiness.evidence["current_article"] == "제6조"
    assert (
        "administrative_rule_deleted_article_is_not_current_operational_criteria"
        in readiness.risk_flags
    )
    assert discipline.status == "can_answer_with_loaded_sources"
    assert any("current operational criteria" in claim for claim in discipline.forbidden_claims)
    assert any("administrative-rule article status" in disclosure for disclosure in discipline.required_disclosures)


def test_administrative_rule_supplementary_provisions_are_not_flattened_into_article_claims():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["administrative_rule_supplementary_transition_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["administrative_rule_supplementary_transition_answer_discipline"]

    assert readiness.status == "ready_for_reasoning"
    assert readiness.must_have["transition_text_not_in_article"] is True
    assert {"administrative_rule", "supplementary_provision"} == {
        citation.source_type for citation in readiness.citations
    }
    assert (
        "administrative_rule_supplementary_provision_required_for_transition_application"
        in readiness.risk_flags
    )
    assert discipline.status == "can_answer_with_loaded_sources"
    assert any("administrative-rule article alone" in claim for claim in discipline.forbidden_claims)
    assert any("effective_date metadata" in claim for claim in discipline.forbidden_claims)
    assert any("separately" in disclosure for disclosure in discipline.required_disclosures)


def test_law_structure_is_not_promoted_to_article_level_delegation_or_rule_body():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["law_structure_hierarchy_candidate_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["law_structure_hierarchy_candidate_answer_discipline"]

    assert readiness.status == "needs_more_source_loading"
    assert {citation.source_type for citation in readiness.citations} == {"law_structure"}
    assert all(citation.source_type != "delegation" for citation in readiness.citations)
    assert all(citation.source_type != "administrative_rule" for citation in readiness.citations)
    assert "law_structure_is_not_article_level_delegation" in readiness.risk_flags
    assert "law_structure_does_not_load_lower_rule_body" in readiness.risk_flags
    assert discipline.status == "must_load_more_sources"
    assert "find_delegated_rules" in discipline.required_followups
    assert any("article-level delegation" in claim for claim in discipline.forbidden_claims)
    assert any("operational criteria" in claim for claim in discipline.forbidden_claims)


def test_law_structure_load_failure_is_not_promoted_to_no_lower_instrument_claim():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["institutional_system_law_structure_not_loaded_guardrail"]

    assert readiness.status == "needs_more_source_loading"
    assert all(citation.source_type != "law_structure" for citation in readiness.citations)
    assert readiness.evidence["law_structure_gap_interfaces"] == ["get_law_structure"]
    assert readiness.evidence["loaded_law_structures"] == 0
    assert "law_structure_not_loaded" in readiness.evidence["gap_kinds"]
    assert "law_structure_not_loaded_is_not_no_lower_instrument" in readiness.risk_flags


def test_empty_delegation_graph_is_not_promoted_to_no_delegated_rule_claim():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["empty_delegation_graph_absence_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["empty_delegation_graph_absence_answer_discipline"]

    assert readiness.status == "needs_more_source_loading"
    assert readiness.evidence["rule_count"] == 0
    assert readiness.citations == []
    assert (
        "empty_delegation_graph_is_not_absence_of_delegated_rules"
        in readiness.risk_flags
    )
    assert discipline.status == "must_load_more_sources"
    assert "find_delegated_rules" in discipline.required_followups
    assert "search_administrative_rules" in discipline.required_followups
    assert any("No delegated rule exists" in claim for claim in discipline.forbidden_claims)
    assert any("one scoped delegation graph" in disclosure for disclosure in discipline.required_disclosures)


def test_delegation_lookup_failure_is_not_promoted_to_no_delegated_rule_claim():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["context_bundle_delegation_lookup_failure_guardrail"]

    assert readiness.status == "needs_more_source_loading"
    assert all(citation.source_type != "delegation" for citation in readiness.citations)
    assert readiness.evidence["delegation_gap_interfaces"] == ["find_delegated_rules"]
    assert readiness.evidence["loaded_delegation_count"] == 0
    assert "source_access_failure" in readiness.evidence["gap_kinds"]
    assert "delegation_lookup_failure_is_not_no_delegated_rule" in readiness.risk_flags


def test_empty_administrative_rule_search_is_not_promoted_to_no_delegated_criteria_claim():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["empty_administrative_rule_search_absence_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["empty_administrative_rule_search_absence_answer_discipline"]

    assert readiness.status == "needs_more_source_loading"
    assert readiness.evidence["hit_count"] == 0
    assert readiness.citations == []
    assert (
        "empty_administrative_rule_search_is_not_absence_of_delegated_criteria"
        in readiness.risk_flags
    )
    assert discipline.status == "must_load_more_sources"
    assert "find_delegated_rules" in discipline.required_followups
    assert any("No delegated operational criteria exist" in claim for claim in discipline.forbidden_claims)
    assert any("one scoped administrative-rule search" in disclosure for disclosure in discipline.required_disclosures)


def test_delegated_criteria_source_mismatch_is_not_promoted_to_operational_criteria():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["delegated_criteria_source_mismatch_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["delegated_criteria_source_mismatch_answer_discipline"]

    assert readiness.status == "needs_more_source_loading"
    assert {citation.source_type for citation in readiness.citations} == {"law", "delegation"}
    assert "delegated_criteria_source_mismatch" in readiness.evidence["gap_kinds"]
    assert readiness.evidence["loaded_source_articles"] == ["제99조"]
    assert (
        "delegated_criteria_source_mismatch_not_target_operational_criteria"
        in readiness.risk_flags
    )
    assert discipline.status == "must_load_more_sources"
    assert "find_delegated_rules" in discipline.required_followups
    assert any("source mismatch" in claim for claim in discipline.forbidden_claims)


def test_delegated_criteria_rule_article_status_is_not_promoted_to_marker_criteria():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["delegated_criteria_administrative_rule_article_status_guardrail"]

    assert readiness.status == "ready_for_reasoning"
    assert readiness.evidence["loaded_administrative_rule_articles"] == ["제6조"]
    assert "deleted_administrative_rule_article" in readiness.evidence["gap_kinds"]
    assert {citation.article for citation in readiness.citations if citation.source_type == "administrative_rule"} == {
        "제6조"
    }
    assert "제3조" not in {
        citation.article for citation in readiness.citations if citation.source_type == "administrative_rule"
    }
    assert "제4조" not in {
        citation.article for citation in readiness.citations if citation.source_type == "administrative_rule"
    }
    assert (
        "delegated_criteria_deleted_administrative_rule_article_not_operational_criteria"
        in readiness.risk_flags
    )
    assert (
        "delegated_criteria_moved_administrative_rule_destination_loaded_before_criteria_claim"
        in readiness.risk_flags
    )


def test_delegated_criteria_annex_source_mismatch_is_not_promoted_to_operational_criteria():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["delegated_criteria_annex_source_mismatch_guardrail"]

    assert readiness.status == "needs_more_source_loading"
    assert "delegated_criteria_annex_source_mismatch" in readiness.evidence["gap_kinds"]
    assert readiness.evidence["annex_related_sources"][0]["related_name"] == "자동차손해배상 보장법"
    assert "annex" not in readiness.evidence["citation_source_types"]
    assert {citation.source_type for citation in readiness.citations} == {
        "law",
        "delegation",
        "administrative_rule",
    }
    assert (
        "delegated_criteria_annex_source_mismatch_not_target_operational_criteria"
        in readiness.risk_flags
    )


def test_missing_administrative_rule_source_reference_is_not_promoted_to_no_authorization():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["administrative_rule_missing_source_reference_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["administrative_rule_missing_source_reference_answer_discipline"]

    assert readiness.status == "ready_for_reasoning"
    assert readiness.evidence["source_law_name"] is None
    assert readiness.evidence["source_article"] is None
    assert (
        "missing_administrative_rule_source_reference_is_unknown_not_no_authorization"
        in readiness.risk_flags
    )
    assert discipline.status == "must_load_more_sources"
    assert "find_delegated_rules" in discipline.required_followups
    assert any("no legal basis" in claim for claim in discipline.forbidden_claims)
    assert any("no delegation" in claim for claim in discipline.forbidden_claims)
    assert any("not exposed" in disclosure for disclosure in discipline.required_disclosures)


def test_comparable_mechanism_candidates_are_not_promoted_to_comparison_citations():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["comparable_mechanism_candidate_detail_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["comparable_mechanism_candidate_answer_discipline"]

    assert readiness.status == "needs_more_source_loading"
    assert readiness.citations == []
    assert readiness.evidence["citations_loaded"] == 0
    assert readiness.evidence["candidate_law_ids"] == ["001111", "002222", "004444", "003333"]
    assert readiness.evidence["article_service_targets"] == []
    assert "comparable_mechanism_candidate_requires_selected_article_loading" in readiness.risk_flags
    assert discipline.status == "must_load_more_sources"
    assert "get_article" in discipline.required_followups
    assert any("candidate metadata" in claim for claim in discipline.forbidden_claims)


def test_annex_form_search_candidates_are_not_promoted_to_attached_criteria_citations():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["annex_form_search_candidate_detail_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["annex_form_search_candidate_answer_discipline"]

    assert readiness.status == "needs_more_source_loading"
    assert readiness.citations == []
    assert readiness.evidence["citations_loaded"] == 0
    assert readiness.evidence["text_call_targets"] == []
    assert "annex_form_search_hit_requires_get_annex_form_body" in readiness.risk_flags
    assert discipline.status == "must_load_more_sources"
    assert "get_annex_form_body" in discipline.required_followups
    assert any("metadata" in claim for claim in discipline.forbidden_claims)


def test_empty_annex_form_search_is_not_promoted_to_no_attached_material_claim():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["empty_annex_form_search_absence_guardrail"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["empty_annex_form_search_absence_answer_discipline"]

    assert readiness.status == "needs_more_source_loading"
    assert readiness.evidence["hit_count"] == 0
    assert readiness.citations == []
    assert (
        "empty_annex_form_search_is_not_absence_of_attached_material"
        in readiness.risk_flags
    )
    assert discipline.status == "must_load_more_sources"
    assert "search_annex_forms" in discipline.required_followups
    assert any("No attached criteria exist" in claim for claim in discipline.forbidden_claims)
    assert any("one scoped annex/form search" in disclosure for disclosure in discipline.required_disclosures)


def test_constitutional_free_text_search_is_not_promoted_to_exhaustive_doctrine_claim():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["constitutional_risk_scan"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["constitutional_risk_answer_discipline"]

    assert readiness.status == "ready_for_reasoning"
    assert readiness.evidence["loaded_constitutional_decisions"] == 2
    assert readiness.evidence["deferred_constitutional_decisions"] == 1
    assert "detc_is_free_text_search_not_doctrine_index" in readiness.risk_flags
    assert any("exhaustive" in claim for claim in discipline.forbidden_claims)
    assert any("source-backed filters" in disclosure for disclosure in discipline.required_disclosures)


def test_context_bundle_loaded_authorities_are_not_promoted_to_exhaustive_survey():
    readiness = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }["sanction_design"]
    discipline = {
        report.scenario: report
        for report in run_legislative_expert_answer_discipline()
    }["context_bundle_authority_answer_discipline"]

    assert readiness.status == "ready_for_reasoning"
    assert readiness.evidence["loaded_authority_detail_types"] == [
        "interpretation_detail",
        "case_detail",
        "constitutional_detail",
    ]
    assert {"administrative_rule", "annex_form"}.issubset(readiness.evidence["candidate_types"])
    assert (
        "context_bundle_is_bounded_first_pass_not_exhaustive_authority_survey"
        in readiness.risk_flags
    )
    assert discipline.status == "must_load_more_sources"
    assert {
        "get_interpretation",
        "get_case",
        "get_constitutional_decision",
        "get_administrative_rule",
        "get_annex_form_body",
    }.issubset(discipline.required_followups)
    assert any("exhaustive authority survey" in claim for claim in discipline.forbidden_claims)
    assert any("administrative-rule" in claim for claim in discipline.forbidden_claims)
    assert any("annex/form" in claim for claim in discipline.forbidden_claims)
