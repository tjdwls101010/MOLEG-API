from scripts.legislative_expert_e2e_audit import run_legislative_expert_e2e_audit


def test_legislative_expert_e2e_audit_covers_answer_readiness_scenarios():
    reports = run_legislative_expert_e2e_audit()

    assert [report.scenario for report in reports] == [
        "sanction_design",
        "delegated_criteria_tracing",
        "statute_evolution",
        "congress_bill_to_current_law",
        "loaded_before_after_amendment_delta_guardrail",
        "constitutional_risk_scan",
        "multi_law_concept_assembly",
        "comparative_design",
        "latest_social_context_websearch_handoff",
        "supplementary_provision_transition_guardrail",
        "nested_article_unit_text_guardrail",
        "deleted_article_status_guardrail",
        "moved_article_status_guardrail",
        "query_expansion_candidate_authority_guardrail",
        "law_search_candidate_detail_guardrail",
        "empty_law_search_absence_guardrail",
        "interpretation_search_candidate_detail_guardrail",
        "empty_interpretation_search_absence_guardrail",
        "source_access_failure_not_no_result_guardrail",
        "context_bundle_requested_law_not_loaded_guardrail",
        "context_bundle_requested_article_not_loaded_guardrail",
        "context_bundle_delegation_lookup_failure_guardrail",
        "case_search_candidate_detail_guardrail",
        "empty_case_search_absence_guardrail",
        "constitutional_search_candidate_detail_guardrail",
        "empty_constitutional_search_absence_guardrail",
        "authority_context_matching_current_authorities",
        "loaded_authority_article_mismatch_guardrail",
        "context_bundle_authority_article_mismatch_guardrail",
        "context_bundle_authority_article_unverified_guardrail",
        "context_bundle_authority_article_partial_match_guardrail",
        "context_bundle_authority_temporal_mismatch_guardrail",
        "law_structure_hierarchy_candidate_guardrail",
        "institutional_system_law_structure_not_loaded_guardrail",
        "empty_delegation_graph_absence_guardrail",
        "administrative_rule_search_candidate_detail_guardrail",
        "administrative_rule_issued_on_not_effective_as_of_guardrail",
        "administrative_rule_article_status_guardrail",
        "administrative_rule_supplementary_transition_guardrail",
        "empty_administrative_rule_search_absence_guardrail",
        "administrative_rule_missing_source_reference_guardrail",
        "comparable_mechanism_candidate_detail_guardrail",
        "annex_form_search_candidate_detail_guardrail",
        "empty_annex_form_search_absence_guardrail",
        "delegated_criteria_after_followups",
        "low_confidence_annex_body_guardrail",
        "historical_article_as_of_guardrail",
        "future_effective_administrative_rule_guardrail",
        "future_effective_promulgated_law_guardrail",
        "institutional_system_future_effective_guardrail",
        "proposed_bill_without_promulgation_bridge_guardrail",
        "ambiguous_statute_identity_guardrail",
        "promulgation_bridge_source_lag_guardrail",
        "interpretation_authority_distinction",
    ]
    assert all(report.public_interfaces for report in reports)
    assert all(report.must_have for report in reports)
    assert all(all(report.must_have.values()) for report in reports)


def test_legislative_expert_e2e_audit_marks_blocking_guardrails():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    proposed_bill = by_scenario["proposed_bill_without_promulgation_bridge_guardrail"]
    assert proposed_bill.status == "blocked_for_manual_review"
    assert proposed_bill.must_have["missing_bridge_rejected"] is True
    assert proposed_bill.must_have["no_moleg_source_called"] is True
    assert proposed_bill.evidence["source_calls"] == []
    assert "proposed_bill_is_not_current_law_without_promulgation_bridge" in proposed_bill.risk_flags

    ambiguous = by_scenario["ambiguous_statute_identity_guardrail"]
    assert ambiguous.status == "blocked_for_manual_review"
    assert ambiguous.evidence["candidate_count"] == 2
    assert ambiguous.evidence["loaded_laws"] == 0
    assert "ambiguous_law_name_must_not_be_silently_selected" in ambiguous.risk_flags

    source_lag = by_scenario["promulgation_bridge_source_lag_guardrail"]
    assert source_lag.status == "blocked_for_manual_review"
    assert source_lag.evidence["ambiguity_kinds"] == ["promulgation_bridge_lag"]
    assert "source_lag_or_manual_review_required" in source_lag.evidence["gap_kinds"]
    assert source_lag.evidence["candidate_names"] == ["데이터기본법"]
    assert "do_not_treat_exact_bridge_miss_as_not_enacted" in source_lag.risk_flags


def test_legislative_expert_e2e_audit_marks_candidate_only_context_as_more_loading_needed():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    delegated = by_scenario["delegated_criteria_tracing"]
    assert delegated.status == "needs_more_source_loading"
    assert delegated.must_have["administrative_rule_candidate_preserved"] is True
    assert delegated.must_have["deferred_followups_preserved"] is True
    assert delegated.must_have["candidate_not_cited_as_loaded_source"] is True
    assert {citation.source_type for citation in delegated.citations} == {"law", "delegation"}
    assert "administrative_rule_candidate_not_loaded" in delegated.risk_flags


def test_legislative_expert_e2e_audit_preserves_loaded_before_after_amendment_delta():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    delta = by_scenario["loaded_before_after_amendment_delta_guardrail"]

    assert delta.status == "ready_for_reasoning"
    assert delta.public_interfaces == ["compare_law_versions"]
    assert delta.must_have["before_after_diff_loaded"] is True
    assert delta.must_have["selected_article_delta_preserved"] is True
    assert delta.must_have["before_identity_preserved"] is True
    assert delta.must_have["after_identity_preserved"] is True
    assert delta.must_have["reason_or_legislative_intent_not_loaded"] is True
    assert delta.evidence["before_mst"] == "270885"
    assert delta.evidence["after_mst"] == "276865"
    assert delta.evidence["changes"] == [
        {
            "article": "제1조",
            "before_text": "종전 목적",
            "after_text": "개정 목적",
        }
    ]
    assert {citation.source_type for citation in delta.citations} == {"law_diff"}
    assert "before_after_comparison_supports_wording_delta_only" in delta.risk_flags
    assert "old_and_new_does_not_prove_legislative_intent" in delta.risk_flags


def test_legislative_expert_e2e_audit_preserves_websearch_gap_for_latest_social_context():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    latest = by_scenario["latest_social_context_websearch_handoff"]

    assert latest.status == "needs_more_source_loading"
    assert latest.public_interfaces == ["expand_legal_query", "get_article"]
    assert latest.must_have["legal_source_planned"] is True
    assert latest.must_have["current_article_loaded"] is True
    assert latest.must_have["websearch_followup_preserved"] is True
    assert latest.must_have["websearch_remains_required_before_social_fact_claim"] is True
    assert latest.evidence["social_fact_sources_loaded"] == []
    assert latest.evidence["follow_up_interfaces"][-1] == "websearch"
    assert {citation.source_type for citation in latest.citations} == {"law"}
    assert "latest_social_facts_require_websearch" in latest.risk_flags
    assert "moleg_legal_sources_do_not_supply_current_statistics" in latest.risk_flags


def test_legislative_expert_e2e_audit_preserves_supplementary_transition_context():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    transition = by_scenario["supplementary_provision_transition_guardrail"]

    assert transition.status == "ready_for_reasoning"
    assert transition.public_interfaces == ["get_law"]
    assert transition.must_have["main_article_loaded"] is True
    assert transition.must_have["supplementary_provisions_loaded"] is True
    assert transition.must_have["transition_text_loaded_from_supplementary_provision"] is True
    assert transition.must_have["transition_text_not_in_main_article"] is True
    assert transition.evidence["supplementary_provision_count"] == 2
    assert transition.evidence["supplementary_promulgation_numbers"] == ["21527", "21527"]
    assert {"law", "supplementary_provision"} == {
        citation.source_type for citation in transition.citations
    }
    assert "supplementary_provision_required_for_transition_application" in transition.risk_flags


def test_legislative_expert_e2e_audit_preserves_nested_article_units():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    nested = by_scenario["nested_article_unit_text_guardrail"]

    assert nested.status == "ready_for_reasoning"
    assert nested.public_interfaces == ["get_article"]
    assert nested.must_have["top_level_article_text_loaded"] is True
    assert nested.must_have["paragraph_text_preserved"] is True
    assert nested.must_have["subparagraph_text_preserved"] is True
    assert nested.must_have["item_text_preserved"] is True
    assert nested.evidence["line_count"] >= 4
    assert nested.evidence["contains_terms"] == {
        "자동차": True,
        "승용자동차": True,
        "일반형 승용자동차": True,
        "자동차사용자": True,
    }
    assert {citation.source_type for citation in nested.citations} == {"law"}
    assert "nested_article_units_required_for_complete_article_text" in nested.risk_flags


def test_legislative_expert_e2e_audit_preserves_deleted_article_status():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    deleted = by_scenario["deleted_article_status_guardrail"]

    assert deleted.status == "ready_for_reasoning"
    assert deleted.public_interfaces == ["get_article"]
    assert deleted.must_have["article_loaded"] is True
    assert deleted.must_have["deleted_status_preserved"] is True
    assert deleted.must_have["movement_metadata_preserved"] is True
    assert deleted.must_have["change_flag_preserved"] is True
    assert deleted.evidence["is_deleted"] is True
    assert deleted.evidence["revision_type"] == "삭제"
    assert deleted.evidence["moved_from"] == "제7조"
    assert deleted.evidence["moved_to"] == "제9조"
    assert {citation.source_type for citation in deleted.citations} == {"law"}
    assert "deleted_article_is_not_current_operational_text" in deleted.risk_flags


def test_legislative_expert_e2e_audit_preserves_moved_article_status():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    moved = by_scenario["moved_article_status_guardrail"]

    assert moved.status == "ready_for_reasoning"
    assert moved.public_interfaces == ["load_article_context"]
    assert moved.must_have["article_loaded"] is True
    assert moved.must_have["movement_status_preserved"] is True
    assert moved.must_have["moved_article_not_operational_text"] is True
    assert moved.must_have["destination_article_loaded"] is True
    assert moved.must_have["current_article_is_destination"] is True
    assert moved.evidence["is_deleted"] is False
    assert moved.evidence["revision_type"] == "이동"
    assert moved.evidence["moved_from"] == "제8조"
    assert moved.evidence["moved_to"] == "제12조"
    assert moved.evidence["current_article"] == "제12조"
    assert moved.evidence["loaded_articles"] == ["제8조", "제12조"]
    assert {citation.article for citation in moved.citations} == {"제8조", "제12조"}
    assert "moved_article_destination_loaded_before_current_substance" in moved.risk_flags


def test_legislative_expert_e2e_audit_keeps_query_expansion_as_planning_context():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    expansion = by_scenario["query_expansion_candidate_authority_guardrail"]

    assert expansion.status == "needs_more_source_loading"
    assert expansion.public_interfaces == ["expand_legal_query"]
    assert expansion.must_have["law_candidate_preserved"] is True
    assert expansion.must_have["term_candidate_preserved"] is True
    assert expansion.must_have["related_article_candidate_preserved"] is True
    assert expansion.must_have["followups_preserved"] is True
    assert expansion.evidence["citations_loaded"] == 0
    assert expansion.citations == []
    assert "query_expansion_is_not_final_authority" in expansion.risk_flags
    assert "related_article_candidate_requires_detail_loading" in expansion.risk_flags


def test_legislative_expert_e2e_audit_keeps_law_search_hits_as_candidates():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    law_search = by_scenario["law_search_candidate_detail_guardrail"]

    assert law_search.status == "needs_more_source_loading"
    assert law_search.public_interfaces == ["search_laws"]
    assert law_search.must_have["law_candidate_preserved"] is True
    assert law_search.must_have["identity_metadata_preserved"] is True
    assert law_search.must_have["no_law_text_loaded"] is True
    assert law_search.must_have["no_citable_article_or_duty_loaded"] is True
    assert law_search.citations == []
    assert law_search.evidence["citations_loaded"] == 0
    assert law_search.evidence["service_call_targets"] == []
    assert "law_search_hit_requires_selected_law_or_article_loading" in law_search.risk_flags


def test_legislative_expert_e2e_audit_treats_empty_law_search_as_scoped_not_absence():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    empty_law = by_scenario["empty_law_search_absence_guardrail"]

    assert empty_law.status == "needs_more_source_loading"
    assert empty_law.public_interfaces == ["search_laws"]
    assert empty_law.must_have["empty_search_result_preserved"] is True
    assert empty_law.must_have["no_law_text_loaded"] is True
    assert empty_law.must_have["legal_absence_claim_blocked"] is True
    assert empty_law.must_have["query_scope_preserved"] is True
    assert empty_law.citations == []
    assert empty_law.evidence["hit_count"] == 0
    assert empty_law.evidence["search_call_targets"] == ["eflaw"]
    assert empty_law.evidence["service_call_targets"] == []
    assert "empty_law_search_is_not_absence_of_current_law" in empty_law.risk_flags


def test_legislative_expert_e2e_audit_keeps_law_structure_as_hierarchy_not_delegation_detail():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    structure = by_scenario["law_structure_hierarchy_candidate_guardrail"]

    assert structure.status == "needs_more_source_loading"
    assert structure.public_interfaces == ["get_law_structure"]
    assert structure.must_have["hierarchy_nodes_preserved"] is True
    assert structure.must_have["no_article_level_delegation_loaded"] is True
    assert structure.must_have["no_lower_rule_body_loaded"] is True
    assert structure.must_have["structure_not_promoted_to_operational_criteria"] is True
    assert {citation.source_type for citation in structure.citations} == {"law_structure"}
    assert structure.evidence["instrument_names"] == ["자동차관리법 시행령"]
    assert structure.evidence["service_call_targets"] == ["lsStmd"]
    assert structure.evidence["article_level_delegation_targets"] == []
    assert "law_structure_is_not_article_level_delegation" in structure.risk_flags
    assert "law_structure_does_not_load_lower_rule_body" in structure.risk_flags


def test_legislative_expert_e2e_audit_marks_institutional_law_structure_not_loaded():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    missing_structure = by_scenario["institutional_system_law_structure_not_loaded_guardrail"]

    assert missing_structure.status == "needs_more_source_loading"
    assert missing_structure.public_interfaces == ["load_institutional_system"]
    assert missing_structure.must_have["law_text_loaded"] is True
    assert missing_structure.must_have["delegation_loaded"] is True
    assert missing_structure.must_have["law_structure_missing"] is True
    assert missing_structure.must_have["law_structure_gap_preserved"] is True
    assert missing_structure.must_have["law_structure_deferred_followup_preserved"] is True
    assert missing_structure.must_have["no_hierarchy_absence_claim"] is True
    assert {citation.source_type for citation in missing_structure.citations} == {"law", "delegation"}
    assert "law_structure_not_loaded" in missing_structure.evidence["gap_kinds"]
    assert missing_structure.evidence["law_structure_gap_interfaces"] == ["get_law_structure"]
    assert missing_structure.evidence["law_structure_deferred_filters"] == [
        {"depth": 1, "law_id": "100001"}
    ]
    assert missing_structure.evidence["loaded_law_structures"] == 0
    assert "lsStmd" in missing_structure.evidence["service_call_targets"]
    assert "law_structure_not_loaded_is_not_no_lower_instrument" in missing_structure.risk_flags


def test_legislative_expert_e2e_audit_treats_empty_delegation_graph_as_scoped_not_absence():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    empty_delegation = by_scenario["empty_delegation_graph_absence_guardrail"]

    assert empty_delegation.status == "needs_more_source_loading"
    assert empty_delegation.public_interfaces == ["find_delegated_rules"]
    assert empty_delegation.must_have["empty_delegation_graph_preserved"] is True
    assert empty_delegation.must_have["delegation_absence_claim_blocked"] is True
    assert empty_delegation.must_have["query_scope_preserved"] is True
    assert empty_delegation.must_have["no_lower_rule_detail_loaded"] is True
    assert empty_delegation.citations == []
    assert empty_delegation.evidence["rule_count"] == 0
    assert empty_delegation.evidence["service_call_targets"] == ["lsDelegated"]
    assert empty_delegation.evidence["lower_rule_detail_targets"] == []
    assert (
        "empty_delegation_graph_is_not_absence_of_delegated_rules"
        in empty_delegation.risk_flags
    )


def test_legislative_expert_e2e_audit_treats_source_access_failure_as_not_legal_no_result():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    failure = by_scenario["source_access_failure_not_no_result_guardrail"]

    assert failure.status == "needs_more_source_loading"
    assert failure.public_interfaces == ["search_laws", "load_legal_context_bundle"]
    assert failure.must_have["source_access_error_preserved"] is True
    assert failure.must_have["bundle_source_access_gap_preserved"] is True
    assert failure.must_have["legal_no_result_not_recorded"] is True
    assert failure.must_have["no_citations_loaded"] is True
    assert failure.must_have["retry_or_later_access_required"] is True
    assert failure.citations == []
    assert failure.evidence["error_type"] == "RateLimitError"
    assert failure.evidence["hit_count"] is None
    assert failure.evidence["source_calls"] == [["search", "eflaw", {"query": "자동차관리법", "display": 5}]]
    assert "source_access_failure" in failure.evidence["bundle_gap_kinds"]
    assert failure.evidence["bundle_gap_interfaces"] == ["search_administrative_rules"]
    assert ["search", "admrul", {"query": "자동차관리법", "display": 5, "nw": 1}] in failure.evidence[
        "bundle_source_calls"
    ]
    assert "source_access_failure_is_not_legal_no_result" in failure.risk_flags


def test_legislative_expert_e2e_audit_marks_requested_article_not_loaded():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    missing_article = by_scenario["context_bundle_requested_article_not_loaded_guardrail"]

    assert missing_article.status == "needs_more_source_loading"
    assert missing_article.public_interfaces == ["load_legal_context_bundle"]
    assert missing_article.must_have["requested_article_missing"] is True
    assert missing_article.must_have["requested_article_gap_preserved"] is True
    assert missing_article.must_have["requested_article_deferred_followup_preserved"] is True
    assert missing_article.must_have["no_article_citation_loaded"] is True
    assert missing_article.citations == []
    assert missing_article.evidence["requested_article"] == "자동차관리법 제26조"
    assert "requested_article_not_loaded" in missing_article.evidence["gap_kinds"]
    assert missing_article.evidence["article_gap_interfaces"] == ["get_article"]
    assert missing_article.evidence["article_deferred_filters"] == [
        {"law_id": "001747", "article": "제26조"}
    ]
    assert "eflawjosub" in missing_article.evidence["service_call_targets"]
    assert (
        "current_target_article_claim_requires_get_article_followup"
        in missing_article.risk_flags
    )


def test_legislative_expert_e2e_audit_marks_requested_law_not_loaded():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    missing_law = by_scenario["context_bundle_requested_law_not_loaded_guardrail"]

    assert missing_law.status == "needs_more_source_loading"
    assert missing_law.public_interfaces == ["load_legal_context_bundle"]
    assert missing_law.must_have["requested_law_missing"] is True
    assert missing_law.must_have["requested_law_gap_preserved"] is True
    assert missing_law.must_have["requested_law_deferred_followup_preserved"] is True
    assert missing_law.must_have["no_law_citation_loaded"] is True
    assert missing_law.citations == []
    assert missing_law.evidence["requested_law"] == "자동차관리법"
    assert "requested_law_not_loaded" in missing_law.evidence["gap_kinds"]
    assert missing_law.evidence["law_gap_interfaces"] == ["get_law"]
    assert missing_law.evidence["law_deferred_filters"] == [
        {"basis": "effective", "law_id": "001747"}
    ]
    assert "eflaw" in missing_law.evidence["service_call_targets"]
    assert "current_law_claim_requires_get_law_followup" in missing_law.risk_flags


def test_legislative_expert_e2e_audit_marks_delegation_lookup_failure():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    delegation_failure = by_scenario["context_bundle_delegation_lookup_failure_guardrail"]

    assert delegation_failure.status == "needs_more_source_loading"
    assert delegation_failure.public_interfaces == ["load_legal_context_bundle"]
    assert delegation_failure.must_have["current_law_loaded"] is True
    assert delegation_failure.must_have["delegation_not_loaded"] is True
    assert delegation_failure.must_have["delegation_failure_gap_preserved"] is True
    assert delegation_failure.must_have["delegation_deferred_followup_preserved"] is True
    assert delegation_failure.must_have["no_delegation_absence_claim"] is True
    assert [citation.source_type for citation in delegation_failure.citations] == ["law"]
    assert "source_access_failure" in delegation_failure.evidence["gap_kinds"]
    assert delegation_failure.evidence["delegation_gap_interfaces"] == ["find_delegated_rules"]
    assert delegation_failure.evidence["delegation_deferred_filters"] == [
        {"law_id": "001747"}
    ]
    assert delegation_failure.evidence["loaded_delegation_count"] == 0
    assert "lsDelegated" in delegation_failure.evidence["service_call_targets"]
    assert (
        "delegation_lookup_failure_is_not_no_delegated_rule"
        in delegation_failure.risk_flags
    )


def test_legislative_expert_e2e_audit_keeps_interpretation_search_hits_as_candidates():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    interpretation = by_scenario["interpretation_search_candidate_detail_guardrail"]

    assert interpretation.status == "needs_more_source_loading"
    assert interpretation.public_interfaces == ["search_interpretations"]
    assert interpretation.must_have["interpretation_candidate_preserved"] is True
    assert interpretation.must_have["authority_metadata_preserved"] is True
    assert interpretation.must_have["no_interpretation_detail_loaded"] is True
    assert interpretation.must_have["no_citable_interpretation_substance_loaded"] is True
    assert interpretation.citations == []
    assert interpretation.evidence["citations_loaded"] == 0
    assert interpretation.evidence["service_call_targets"] == []
    assert "interpretation_search_hit_requires_get_interpretation_detail" in interpretation.risk_flags


def test_legislative_expert_e2e_audit_keeps_case_search_hits_as_candidates():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    case = by_scenario["case_search_candidate_detail_guardrail"]

    assert case.status == "needs_more_source_loading"
    assert case.public_interfaces == ["search_cases"]
    assert case.must_have["case_candidate_preserved"] is True
    assert case.must_have["decision_metadata_preserved"] is True
    assert case.must_have["no_case_detail_loaded"] is True
    assert case.must_have["no_citable_holding_loaded"] is True
    assert case.citations == []
    assert case.evidence["citations_loaded"] == 0
    assert case.evidence["service_call_targets"] == []
    assert "case_search_hit_requires_get_case_detail" in case.risk_flags


def test_legislative_expert_e2e_audit_treats_empty_case_search_as_scoped_not_absence():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    empty_case = by_scenario["empty_case_search_absence_guardrail"]

    assert empty_case.status == "needs_more_source_loading"
    assert empty_case.public_interfaces == ["search_cases"]
    assert empty_case.must_have["empty_search_result_preserved"] is True
    assert empty_case.must_have["no_case_detail_loaded"] is True
    assert empty_case.must_have["judicial_absence_claim_blocked"] is True
    assert empty_case.must_have["query_scope_preserved"] is True
    assert empty_case.citations == []
    assert empty_case.evidence["hit_count"] == 0
    assert empty_case.evidence["search_call_targets"] == ["prec"]
    assert empty_case.evidence["service_call_targets"] == []
    assert "empty_case_search_is_not_absence_of_judicial_authority" in empty_case.risk_flags


def test_legislative_expert_e2e_audit_keeps_constitutional_search_hits_as_candidates():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    constitutional = by_scenario["constitutional_search_candidate_detail_guardrail"]

    assert constitutional.status == "needs_more_source_loading"
    assert constitutional.public_interfaces == ["search_constitutional_decisions"]
    assert constitutional.must_have["constitutional_candidate_preserved"] is True
    assert constitutional.must_have["decision_metadata_preserved"] is True
    assert constitutional.must_have["no_constitutional_detail_loaded"] is True
    assert constitutional.must_have["no_citable_constitutional_reasoning_loaded"] is True
    assert constitutional.citations == []
    assert constitutional.evidence["citations_loaded"] == 0
    assert constitutional.evidence["service_call_targets"] == []
    assert (
        "constitutional_search_hit_requires_get_constitutional_decision_detail"
        in constitutional.risk_flags
    )


def test_legislative_expert_e2e_audit_treats_empty_constitutional_search_as_scoped_not_absence():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    empty_constitutional = by_scenario["empty_constitutional_search_absence_guardrail"]

    assert empty_constitutional.status == "needs_more_source_loading"
    assert empty_constitutional.public_interfaces == ["search_constitutional_decisions"]
    assert empty_constitutional.must_have["empty_search_result_preserved"] is True
    assert empty_constitutional.must_have["no_constitutional_detail_loaded"] is True
    assert empty_constitutional.must_have["constitutional_absence_claim_blocked"] is True
    assert empty_constitutional.must_have["query_scope_preserved"] is True
    assert empty_constitutional.citations == []
    assert empty_constitutional.evidence["hit_count"] == 0
    assert empty_constitutional.evidence["search_call_targets"] == ["detc"]
    assert empty_constitutional.evidence["service_call_targets"] == []
    assert (
        "empty_constitutional_search_is_not_absence_of_constitutional_authority"
        in empty_constitutional.risk_flags
    )


def test_legislative_expert_e2e_audit_loads_matching_authority_context():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    authority = by_scenario["authority_context_matching_current_authorities"]

    assert authority.status == "ready_for_reasoning"
    assert authority.public_interfaces == ["load_authority_context"]
    assert authority.must_have["target_article_loaded"] is True
    assert authority.must_have["interpretation_promoted"] is True
    assert authority.must_have["case_promoted"] is True
    assert authority.must_have["constitutional_promoted"] is True
    assert authority.must_have["no_authority_mismatch_or_temporal_gap"] is True
    assert {citation.source_type for citation in authority.citations} == {
        "law",
        "interpretation",
        "case",
        "constitutional",
    }
    assert authority.evidence["target_articles"] == ["제15조"]
    assert authority.evidence["gap_kinds"] == []
    assert authority.evidence["deferred_interfaces"] == []
    assert "authority_context_is_bounded_not_exhaustive_authority_survey" in authority.risk_flags


def test_legislative_expert_e2e_audit_blocks_mismatched_loaded_authority_articles():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    mismatch = by_scenario["loaded_authority_article_mismatch_guardrail"]

    assert mismatch.status == "needs_more_source_loading"
    assert mismatch.public_interfaces == [
        "get_interpretation",
        "get_case",
        "get_constitutional_decision",
    ]
    assert mismatch.must_have["target_article_preserved"] is True
    assert mismatch.must_have["loaded_authority_details_preserved"] is True
    assert mismatch.must_have["interpretation_reference_mismatch_preserved"] is True
    assert mismatch.must_have["case_reference_mismatch_preserved"] is True
    assert mismatch.must_have["constitutional_reviewed_article_mismatch_preserved"] is True
    assert mismatch.must_have["no_target_article_authority_citation"] is True
    assert mismatch.must_have["followup_authority_search_required"] is True
    assert mismatch.citations == []
    assert mismatch.evidence["target_article"] == {
        "law_name": "개인정보 보호법",
        "article": "제15조",
    }
    assert mismatch.evidence["interpretation_referenced_articles"] == [
        {"law_name": "개인정보 보호법", "article": "제17조", "law_id": None}
    ]
    assert mismatch.evidence["case_referenced_articles"] == [
        {"law_name": "개인정보 보호법", "article": "제18조", "law_id": None}
    ]
    assert mismatch.evidence["constitutional_reviewed_articles"] == [
        {"law_name": "개인정보 보호법", "article": "제23조", "law_id": None}
    ]
    assert mismatch.evidence["authority_article_matches"] == {
        "interpretation": False,
        "case": False,
        "constitutional": False,
    }
    assert mismatch.evidence["service_call_targets"] == ["expc", "prec", "detc"]
    assert (
        "loaded_authority_reference_mismatch_not_target_article_authority"
        in mismatch.risk_flags
    )
    assert (
        "referenced_articles_must_match_target_before_authority_claim"
        in mismatch.risk_flags
    )
    assert (
        "reviewed_articles_must_match_target_before_constitutional_claim"
        in mismatch.risk_flags
    )


def test_legislative_expert_e2e_audit_marks_context_bundle_authority_article_mismatches():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    mismatch = by_scenario["context_bundle_authority_article_mismatch_guardrail"]

    assert mismatch.status == "needs_more_source_loading"
    assert mismatch.public_interfaces == ["load_legal_context_bundle"]
    assert mismatch.must_have["target_article_loaded"] is True
    assert mismatch.must_have["eager_authority_details_loaded"] is True
    assert mismatch.must_have["authority_article_mismatch_gaps_preserved"] is True
    assert mismatch.must_have["no_target_article_authority_citation"] is True
    assert mismatch.must_have["followup_authority_search_required"] is True
    assert [citation.source_type for citation in mismatch.citations] == ["law"]
    assert mismatch.evidence["target_article"] == {
        "law_name": "개인정보 보호법",
        "article": "제15조",
    }
    assert mismatch.evidence["gap_kinds"] == [
        "authority_article_mismatch",
        "authority_article_mismatch",
        "authority_article_mismatch",
        "websearch_required",
    ]
    assert mismatch.evidence["authority_gap_interfaces"] == [
        "search_interpretations",
        "search_cases",
        "search_constitutional_decisions",
    ]
    assert mismatch.evidence["authority_article_matches"] == {
        "interpretation": False,
        "case": False,
        "constitutional": False,
    }
    assert (
        "context_bundle_eager_authority_reference_mismatch_not_target_article_citation"
        in mismatch.risk_flags
    )
    assert (
        "context_bundle_authority_article_mismatch_gap_requires_followup_search"
        in mismatch.risk_flags
    )


def test_legislative_expert_e2e_audit_marks_context_bundle_authority_without_article_refs_unverified():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    unverified = by_scenario["context_bundle_authority_article_unverified_guardrail"]

    assert unverified.status == "needs_more_source_loading"
    assert unverified.public_interfaces == ["load_legal_context_bundle"]
    assert unverified.must_have["target_article_loaded"] is True
    assert unverified.must_have["eager_authority_details_loaded"] is True
    assert unverified.must_have["authority_article_unverified_gaps_preserved"] is True
    assert unverified.must_have["no_structured_article_refs_available"] is True
    assert unverified.must_have["followup_authority_search_required"] is True
    assert [citation.source_type for citation in unverified.citations] == ["law"]
    assert unverified.evidence["target_article"] == {
        "law_name": "개인정보 보호법",
        "article": "제15조",
    }
    assert unverified.evidence["gap_kinds"] == [
        "authority_article_unverified",
        "authority_article_unverified",
        "authority_article_unverified",
        "websearch_required",
    ]
    assert unverified.evidence["authority_gap_interfaces"] == [
        "search_interpretations",
        "search_cases",
        "search_constitutional_decisions",
    ]
    assert unverified.evidence["authority_reference_counts"] == {
        "interpretation": 0,
        "case": 0,
        "constitutional": 0,
    }
    assert (
        "context_bundle_eager_authority_without_structured_refs_not_target_article_citation"
        in unverified.risk_flags
    )
    assert (
        "context_bundle_authority_article_unverified_gap_requires_followup_search"
        in unverified.risk_flags
    )


def test_legislative_expert_e2e_audit_marks_context_bundle_authority_partial_article_matches():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    partial = by_scenario["context_bundle_authority_article_partial_match_guardrail"]

    assert partial.status == "needs_more_source_loading"
    assert partial.public_interfaces == ["load_legal_context_bundle"]
    assert partial.must_have["target_articles_loaded"] is True
    assert partial.must_have["eager_authority_details_loaded"] is True
    assert partial.must_have["authority_article_partial_match_gaps_preserved"] is True
    assert partial.must_have["matched_article_not_all_requested_articles"] is True
    assert partial.must_have["followup_authority_search_required_for_missing_article"] is True
    assert [citation.source_type for citation in partial.citations] == ["law", "law"]
    assert partial.evidence["target_articles"] == [
        {"law_name": "개인정보 보호법", "article": "제15조"},
        {"law_name": "개인정보 보호법", "article": "제17조"},
    ]
    assert partial.evidence["gap_kinds"] == [
        "authority_article_partial_match",
        "authority_article_partial_match",
        "authority_article_partial_match",
        "websearch_required",
    ]
    assert partial.evidence["authority_gap_interfaces"] == [
        "search_interpretations",
        "search_cases",
        "search_constitutional_decisions",
    ]
    assert partial.evidence["authority_matched_articles"] == {
        "interpretation": ["제17조"],
        "case": ["제17조"],
        "constitutional": ["제17조"],
    }
    assert partial.evidence["missing_authority_article"] == "제15조"
    assert (
        "context_bundle_eager_authority_partial_match_not_all_target_articles"
        in partial.risk_flags
    )
    assert (
        "context_bundle_authority_article_partial_match_gap_requires_followup_search"
        in partial.risk_flags
    )


def test_legislative_expert_e2e_audit_marks_context_bundle_authority_temporal_mismatches():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    temporal = by_scenario["context_bundle_authority_temporal_mismatch_guardrail"]

    assert temporal.status == "needs_more_source_loading"
    assert temporal.public_interfaces == ["load_legal_context_bundle"]
    assert temporal.must_have["target_article_loaded"] is True
    assert temporal.must_have["target_article_effective_date_preserved"] is True
    assert temporal.must_have["eager_authority_details_loaded"] is True
    assert temporal.must_have["authority_articles_match_target"] is True
    assert temporal.must_have["authority_temporal_mismatch_gaps_preserved"] is True
    assert temporal.must_have["authority_temporal_deferred_followups_preserved"] is True
    assert temporal.must_have["no_current_authority_claim_without_history"] is True
    assert [citation.source_type for citation in temporal.citations] == ["law"]
    assert temporal.evidence["target_article"] == {
        "law_name": "개인정보 보호법",
        "article": "제15조",
        "effective_date": "20250101",
    }
    assert temporal.evidence["authority_dates"] == {
        "interpretation": "20210115",
        "case": "20210215",
        "constitutional": "20210315",
    }
    assert temporal.evidence["authority_article_matches"] == {
        "interpretation": True,
        "case": True,
        "constitutional": True,
    }
    assert temporal.evidence["gap_kinds"] == [
        "authority_temporal_mismatch",
        "authority_temporal_mismatch",
        "authority_temporal_mismatch",
        "websearch_required",
    ]
    assert temporal.evidence["authority_gap_interfaces"] == [
        "trace_law_history",
        "trace_law_history",
        "trace_law_history",
    ]
    assert temporal.evidence["authority_gap_queries"] == [
        "개인정보 보호법 제15조",
        "개인정보 보호법 제15조",
        "개인정보 보호법 제15조",
    ]
    assert temporal.evidence["authority_deferred_interfaces"] == [
        "trace_law_history",
        "trace_law_history",
        "trace_law_history",
    ]
    assert temporal.evidence["authority_deferred_queries"] == [
        "개인정보 보호법 제15조",
        "개인정보 보호법 제15조",
        "개인정보 보호법 제15조",
    ]
    assert temporal.evidence["authority_deferred_filters"] == [
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
        "context_bundle_authority_temporal_mismatch_gap_requires_history_check"
        in temporal.risk_flags
    )
    assert (
        "matching_referenced_article_is_not_enough_when_authority_predates_current_wording"
        in temporal.risk_flags
    )


def test_legislative_expert_e2e_audit_keeps_administrative_rule_search_hits_as_candidates():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    administrative_rule = by_scenario["administrative_rule_search_candidate_detail_guardrail"]

    assert administrative_rule.status == "needs_more_source_loading"
    assert administrative_rule.public_interfaces == ["search_administrative_rules"]
    assert administrative_rule.must_have["administrative_rule_candidate_preserved"] is True
    assert administrative_rule.must_have["identity_metadata_preserved"] is True
    assert administrative_rule.must_have["no_administrative_rule_detail_loaded"] is True
    assert administrative_rule.must_have["no_citable_operational_criteria_loaded"] is True
    assert administrative_rule.citations == []
    assert administrative_rule.evidence["citations_loaded"] == 0
    assert administrative_rule.evidence["service_call_targets"] == []
    assert (
        "administrative_rule_search_hit_requires_get_administrative_rule_detail"
        in administrative_rule.risk_flags
    )


def test_legislative_expert_e2e_audit_keeps_administrative_rule_issued_on_out_of_as_of_claims():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    issued_on = by_scenario["administrative_rule_issued_on_not_effective_as_of_guardrail"]

    assert issued_on.status == "needs_more_source_loading"
    assert issued_on.public_interfaces == ["search_administrative_rules"]
    assert issued_on.must_have["issued_on_filter_preserved"] is True
    assert issued_on.must_have["issued_on_not_effective_date"] is True
    assert issued_on.must_have["no_administrative_rule_detail_loaded"] is True
    assert issued_on.must_have["current_operational_claim_blocked"] is True
    assert issued_on.citations == []
    assert issued_on.evidence["reference_date"] == "20250101"
    assert issued_on.evidence["candidate"] == {
        "name": "전기자동차 충전시설 운영 규정",
        "issuing_date": "20250101",
        "effective_date": "20250301",
        "current_status": "현행",
    }
    assert issued_on.evidence["search_call_params"][0]["date"] == "20250101"
    assert issued_on.evidence["service_call_targets"] == []
    assert (
        "administrative_rule_issued_on_filter_is_not_effective_as_of"
        in issued_on.risk_flags
    )


def test_legislative_expert_e2e_audit_preserves_administrative_rule_article_status():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    status = by_scenario["administrative_rule_article_status_guardrail"]

    assert status.status == "ready_for_reasoning"
    assert status.public_interfaces == ["load_administrative_rule_context"]
    assert status.must_have["administrative_rule_loaded"] is True
    assert status.must_have["deleted_article_status_preserved"] is True
    assert status.must_have["moved_article_status_preserved"] is True
    assert status.must_have["deleted_article_not_operational_text"] is True
    assert status.must_have["destination_article_loaded"] is True
    assert status.must_have["current_article_is_destination"] is True
    assert len(status.citations) == 3
    assert status.evidence["article_statuses"] == [
        {"article": "제3조", "revision_type": "삭제", "is_deleted": True, "moved_to": None},
        {"article": "제4조", "revision_type": "이동", "is_deleted": False, "moved_to": "제6조"},
    ]
    assert status.evidence["current_article"] == "제6조"
    assert status.evidence["loaded_articles"] == ["제3조", "제4조", "제6조"]
    assert (
        "administrative_rule_deleted_article_is_not_current_operational_criteria"
        in status.risk_flags
    )
    assert (
        "administrative_rule_moved_article_destination_loaded_before_current_criteria"
        in status.risk_flags
    )


def test_legislative_expert_e2e_audit_preserves_administrative_rule_supplementary_transition_context():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    transition = by_scenario["administrative_rule_supplementary_transition_guardrail"]

    assert transition.status == "ready_for_reasoning"
    assert transition.public_interfaces == ["get_administrative_rule"]
    assert transition.must_have["administrative_rule_article_loaded"] is True
    assert transition.must_have["supplementary_provisions_loaded"] is True
    assert transition.must_have["transition_text_loaded_from_supplementary_provision"] is True
    assert transition.must_have["transition_text_not_in_article"] is True
    assert transition.evidence["administrative_rule_effective_date"] == "20260701"
    assert transition.evidence["supplementary_provision_count"] == 2
    assert transition.evidence["supplementary_promulgation_numbers"] == ["2026-10", "2026-10"]
    assert {"administrative_rule", "supplementary_provision"} == {
        citation.source_type for citation in transition.citations
    }
    assert (
        "administrative_rule_supplementary_provision_required_for_transition_application"
        in transition.risk_flags
    )
    assert (
        "administrative_rule_effective_date_metadata_not_full_transition_analysis"
        in transition.risk_flags
    )


def test_legislative_expert_e2e_audit_treats_empty_administrative_rule_search_as_scoped_not_absence():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    empty_rule = by_scenario["empty_administrative_rule_search_absence_guardrail"]

    assert empty_rule.status == "needs_more_source_loading"
    assert empty_rule.public_interfaces == ["search_administrative_rules"]
    assert empty_rule.must_have["empty_search_result_preserved"] is True
    assert empty_rule.must_have["no_rule_detail_loaded"] is True
    assert empty_rule.must_have["delegation_absence_claim_blocked"] is True
    assert empty_rule.must_have["query_scope_preserved"] is True
    assert empty_rule.citations == []
    assert empty_rule.evidence["hit_count"] == 0
    assert empty_rule.evidence["search_call_targets"] == ["admrul"]
    assert empty_rule.evidence["service_call_targets"] == []
    assert (
        "empty_administrative_rule_search_is_not_absence_of_delegated_criteria"
        in empty_rule.risk_flags
    )


def test_legislative_expert_e2e_audit_keeps_comparable_mechanisms_as_candidates():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    comparable = by_scenario["comparable_mechanism_candidate_detail_guardrail"]

    assert comparable.status == "needs_more_source_loading"
    assert comparable.public_interfaces == ["find_comparable_mechanisms"]
    assert comparable.must_have["comparable_candidates_preserved"] is True
    assert comparable.must_have["article_anchor_metadata_preserved"] is True
    assert comparable.must_have["no_comparable_article_loaded"] is True
    assert comparable.must_have["no_citable_comparison_loaded"] is True
    assert comparable.citations == []
    assert comparable.evidence["citations_loaded"] == 0
    assert comparable.evidence["article_service_targets"] == []
    assert "comparable_mechanism_candidate_requires_selected_article_loading" in comparable.risk_flags


def test_legislative_expert_e2e_audit_keeps_annex_form_search_hits_as_candidates():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    annex = by_scenario["annex_form_search_candidate_detail_guardrail"]

    assert annex.status == "needs_more_source_loading"
    assert annex.public_interfaces == ["search_annex_forms"]
    assert annex.must_have["annex_candidate_preserved"] is True
    assert annex.must_have["annex_metadata_preserved"] is True
    assert annex.must_have["no_annex_body_loaded"] is True
    assert annex.must_have["no_citable_annex_criteria_loaded"] is True
    assert annex.citations == []
    assert annex.evidence["citations_loaded"] == 0
    assert annex.evidence["text_call_targets"] == []
    assert "annex_form_search_hit_requires_get_annex_form_body" in annex.risk_flags


def test_legislative_expert_e2e_audit_treats_empty_annex_form_search_as_scoped_not_absence():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    empty_annex = by_scenario["empty_annex_form_search_absence_guardrail"]

    assert empty_annex.status == "needs_more_source_loading"
    assert empty_annex.public_interfaces == ["search_annex_forms"]
    assert empty_annex.must_have["empty_search_result_preserved"] is True
    assert empty_annex.must_have["no_annex_body_loaded"] is True
    assert empty_annex.must_have["attached_material_absence_claim_blocked"] is True
    assert empty_annex.must_have["query_scope_preserved"] is True
    assert empty_annex.citations == []
    assert empty_annex.evidence["hit_count"] == 0
    assert empty_annex.evidence["search_call_targets"] == ["licbyl"]
    assert empty_annex.evidence["text_call_targets"] == []
    assert "empty_annex_form_search_is_not_absence_of_attached_material" in empty_annex.risk_flags


def test_legislative_expert_e2e_audit_marks_followup_loaded_delegated_criteria_ready():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    loaded = by_scenario["delegated_criteria_after_followups"]
    assert loaded.status == "ready_for_reasoning"
    assert loaded.public_interfaces == ["load_delegated_criteria"]
    assert loaded.must_have["candidate_stage_preserved_with_loaded_detail"] is True
    assert loaded.must_have["administrative_rule_body_loaded"] is True
    assert loaded.must_have["administrative_rule_annex_body_loaded"] is True
    assert loaded.must_have["structured_annex_rows_loaded"] is True
    assert loaded.evidence["call_targets"][-2:] == ["admrul", "admRulBylTextDownLoad.do"]
    assert loaded.evidence["loaded_detail_interfaces"] == [
        "get_administrative_rule",
        "get_annex_form_body",
    ]
    assert {"administrative_rule", "annex"}.issubset(
        {citation.source_type for citation in loaded.citations}
    )
    assert "delegated_criteria_loader_is_bounded_not_exhaustive_lower_rule_survey" in loaded.risk_flags


def test_legislative_expert_e2e_audit_marks_low_confidence_annex_rows_as_plain_text_fallback():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    annex = by_scenario["low_confidence_annex_body_guardrail"]

    assert annex.status == "ready_for_reasoning"
    assert annex.must_have["annex_body_loaded"] is True
    assert annex.must_have["plain_text_retained"] is True
    assert annex.must_have["low_confidence_preserved"] is True
    assert annex.evidence["parsing_confidence"] == "low"
    assert annex.evidence["structured_rows"] == 0
    assert annex.evidence["plain_text_contains_threshold"] is True
    assert "annex_structured_rows_low_confidence" in annex.risk_flags
    assert "empty_structured_rows_do_not_mean_no_annex_criteria" in annex.risk_flags


def test_legislative_expert_e2e_audit_marks_future_effective_promulgated_law():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    future = by_scenario["future_effective_promulgated_law_guardrail"]
    assert future.status == "ready_for_reasoning"
    assert future.must_have["promulgation_bridge_resolved"] is True
    assert future.must_have["reference_date_preserved"] is True
    assert future.must_have["future_effective_date_preserved"] is True
    assert future.must_have["not_effective_gap_preserved"] is True
    assert future.evidence["as_of"] == "20260617"
    assert future.evidence["effective_date"] == "20270101"
    assert "not_effective_as_of" in future.evidence["gap_kinds"]
    assert "promulgated_law_not_effective_as_of_reference_date" in future.risk_flags


def test_legislative_expert_e2e_audit_marks_historical_article_as_not_current_law():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    historical = by_scenario["historical_article_as_of_guardrail"]

    assert historical.status == "ready_for_reasoning"
    assert historical.must_have["historical_reference_date_used"] is True
    assert historical.must_have["historical_article_loaded"] is True
    assert historical.must_have["history_status_preserved"] is True
    assert historical.evidence["as_of"] == "20121230"
    assert historical.evidence["article_effective_date"] == "20120101"
    assert "폐지" in historical.evidence["history_statuses"]
    assert "historical_article_not_current_law" in historical.risk_flags
    assert "current_effective_no_result_does_not_prove_never_existed" in historical.risk_flags


def test_legislative_expert_e2e_audit_marks_future_effective_administrative_rule():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    future = by_scenario["future_effective_administrative_rule_guardrail"]
    assert future.status == "ready_for_reasoning"
    assert future.must_have["reference_date_preserved"] is True
    assert future.must_have["current_statute_loaded"] is True
    assert future.must_have["administrative_rule_body_loaded"] is True
    assert future.must_have["administrative_rule_future_effective_date_preserved"] is True
    assert future.must_have["administrative_rule_not_current_as_of"] is True
    assert future.must_have["statute_current_gap_not_confused_with_rule_effective_date"] is True
    assert future.evidence["as_of"] == "20260617"
    assert future.evidence["administrative_rule_effective_date"] == "20270101"
    assert "administrative_rule_not_effective_as_of_reference_date" in future.risk_flags


def test_legislative_expert_e2e_audit_limits_institutional_system_to_explicit_set():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    institutional = by_scenario["multi_law_concept_assembly"]
    assert institutional.status == "ready_for_reasoning"
    assert institutional.public_interfaces == ["load_institutional_system"]
    assert institutional.must_have["explicit_statute_set_preserved"] is True
    assert institutional.must_have["all_laws_loaded"] is True
    assert institutional.must_have["all_structures_loaded"] is True
    assert institutional.must_have["all_delegation_graphs_loaded"] is True
    assert institutional.evidence["request_statute_ids"] == [
        "전자금융거래법",
        "전자금융거래법 시행령",
    ]
    assert "institutional_system_does_not_discover_statute_set" in institutional.risk_flags


def test_legislative_expert_e2e_audit_marks_future_effective_institutional_system_law():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    future = by_scenario["institutional_system_future_effective_guardrail"]
    assert future.status == "ready_for_reasoning"
    assert future.must_have["explicit_statute_set_preserved"] is True
    assert future.must_have["reference_date_preserved"] is True
    assert future.must_have["future_effective_date_preserved"] is True
    assert future.must_have["not_effective_gap_preserved"] is True
    assert future.evidence["as_of"] == "20260617"
    assert future.evidence["effective_date"] == "20270101"
    assert "not_effective_as_of" in future.evidence["gap_kinds"]
    assert "institutional_system_contains_law_not_effective_as_of_reference_date" in future.risk_flags


def test_legislative_expert_e2e_audit_preserves_reasoning_citations_and_gaps():
    by_scenario = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    sanction = by_scenario["sanction_design"]
    assert sanction.status == "ready_for_reasoning"
    assert {citation.source_type for citation in sanction.citations} == {
        "law",
        "interpretation",
        "case",
        "constitutional",
        "annex",
    }
    assert sanction.must_have["websearch_gap_preserved"] is True
    assert sanction.evidence["loaded_authority_detail_types"] == [
        "interpretation_detail",
        "case_detail",
        "constitutional_detail",
    ]
    assert {"administrative_rule", "annex_form"}.issubset(sanction.evidence["candidate_types"])
    assert "context_bundle_is_bounded_first_pass_not_exhaustive_authority_survey" in sanction.risk_flags

    constitutional = by_scenario["constitutional_risk_scan"]
    assert constitutional.must_have["unloaded_decisions_deferred"] is True
    assert "detc_is_free_text_search_not_doctrine_index" in constitutional.risk_flags

    authority = by_scenario["interpretation_authority_distinction"]
    assert authority.status == "ready_for_reasoning"
    assert authority.evidence["labels"] == [
        ["moleg", "expc", None],
        ["ministry", "dapaCgmExpc", "방위사업청"],
    ]
    assert "ministry_interpretation_is_not_moleg_official_interpretation" in authority.risk_flags


def test_legislative_expert_e2e_audit_treats_missing_admin_rule_source_reference_as_unknown():
    report = {
        item.scenario: item
        for item in run_legislative_expert_e2e_audit()
    }["administrative_rule_missing_source_reference_guardrail"]

    assert report.status == "ready_for_reasoning"
    assert report.must_have["administrative_rule_detail_loaded"] is True
    assert report.must_have["source_law_reference_absent"] is True
    assert report.must_have["source_article_reference_absent"] is True
    assert report.must_have["absence_preserved_as_unknown_not_no_authorization"] is True
    assert report.evidence["source_law_name"] is None
    assert report.evidence["source_article"] is None
    assert report.evidence["service_call_targets"] == ["admrul"]
    assert (
        "missing_administrative_rule_source_reference_is_unknown_not_no_authorization"
        in report.risk_flags
    )


def test_legislative_expert_e2e_audit_treats_empty_interpretation_search_as_scoped_result():
    report = {
        item.scenario: item
        for item in run_legislative_expert_e2e_audit()
    }["empty_interpretation_search_absence_guardrail"]

    assert report.status == "needs_more_source_loading"
    assert report.must_have["empty_search_result_preserved"] is True
    assert report.must_have["no_interpretation_detail_loaded"] is True
    assert report.must_have["absence_claim_blocked"] is True
    assert report.evidence["hit_count"] == 0
    assert report.evidence["search_call_targets"] == ["expc"]
    assert report.evidence["service_call_targets"] == []
    assert report.citations == []
    assert "empty_interpretation_search_is_not_absence_of_authority" in report.risk_flags
