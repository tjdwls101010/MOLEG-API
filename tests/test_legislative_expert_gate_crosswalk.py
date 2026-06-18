from scripts.legislative_expert_e2e_audit import run_legislative_expert_e2e_audit
from scripts.legislative_expert_prompt_dry_run import run_legislative_expert_prompt_dry_run


def test_prompt_plans_have_matching_answer_readiness_guardrails():
    prompt_reports = {
        report.scenario: report
        for report in run_legislative_expert_prompt_dry_run()
    }
    readiness_reports = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    proposed_prompt = prompt_reports["proposed_bill_current_law_check"]
    proposed_readiness = readiness_reports["proposed_bill_without_promulgation_bridge_guardrail"]
    assert proposed_prompt.status == "needs_congress_db_first"
    assert proposed_readiness.status == "blocked_for_manual_review"
    assert any(step.source == "congress-db" for step in proposed_prompt.planned_steps)
    assert "proposed_bill_is_not_current_law_without_promulgation_bridge" in proposed_readiness.risk_flags
    future_effective = readiness_reports["future_effective_promulgated_law_guardrail"]
    assert future_effective.status == "ready_for_reasoning"
    assert any("effective date" in guardrail for guardrail in proposed_prompt.guardrails)
    assert "not_effective_as_of" in future_effective.evidence["gap_kinds"]
    assert "promulgated_law_not_effective_as_of_reference_date" in future_effective.risk_flags

    change_trace_prompt = prompt_reports["enacted_bill_change_trace"]
    bridge_readiness = readiness_reports["congress_bill_to_current_law"]
    assert change_trace_prompt.status == "needs_more_source_loading"
    assert bridge_readiness.status == "ready_for_reasoning"
    assert "history_not_loaded_until_article_or_date_known" in bridge_readiness.risk_flags
    assert any("amendment delta" in guardrail for guardrail in change_trace_prompt.guardrails)
    assert {"trace_law_history", "compare_law_versions"}.issubset({
        step.interface
        for step in change_trace_prompt.planned_steps
        if step.required_before_answer
    })
    loaded_delta_readiness = readiness_reports["loaded_before_after_amendment_delta_guardrail"]
    assert loaded_delta_readiness.status == "ready_for_reasoning"
    assert loaded_delta_readiness.public_interfaces == ["compare_law_versions"]
    assert loaded_delta_readiness.evidence["changes"][0]["article"] == "제1조"
    assert loaded_delta_readiness.evidence["before_mst"] == "270885"
    assert loaded_delta_readiness.evidence["after_mst"] == "276865"
    assert (
        "before_after_comparison_supports_wording_delta_only"
        in loaded_delta_readiness.risk_flags
    )

    historical_prompt = prompt_reports["historical_repealed_law_review"]
    historical_readiness = readiness_reports["historical_article_as_of_guardrail"]
    assert historical_prompt.status == "moleg_ready"
    assert historical_readiness.status == "ready_for_reasoning"
    assert historical_readiness.evidence["as_of"] == "20121230"
    assert "폐지" in historical_readiness.evidence["history_statuses"]
    assert "historical_article_not_current_law" in historical_readiness.risk_flags
    assert any("not a current-law prompt" in guardrail for guardrail in historical_prompt.guardrails)

    supplementary_prompt = prompt_reports["supplementary_transition_review"]
    supplementary_readiness = readiness_reports["supplementary_provision_transition_guardrail"]
    assert supplementary_prompt.status == "moleg_ready"
    assert supplementary_readiness.status == "ready_for_reasoning"
    assert any(step.interface == "get_law" for step in supplementary_prompt.planned_steps)
    assert supplementary_readiness.must_have["supplementary_provisions_loaded"] is True
    assert supplementary_readiness.must_have["transition_text_not_in_main_article"] is True
    assert "supplementary_provision_required_for_transition_application" in supplementary_readiness.risk_flags
    assert any("Supplementary provisions" in guardrail for guardrail in supplementary_prompt.guardrails)

    nested_prompt = prompt_reports["nested_article_unit_review"]
    nested_readiness = readiness_reports["nested_article_unit_text_guardrail"]
    assert nested_prompt.status == "moleg_ready"
    assert nested_readiness.status == "ready_for_reasoning"
    assert any(step.interface == "get_article" for step in nested_prompt.planned_steps)
    assert nested_readiness.must_have["subparagraph_text_preserved"] is True
    assert nested_readiness.must_have["item_text_preserved"] is True
    assert "nested_article_units_required_for_complete_article_text" in nested_readiness.risk_flags
    assert any("항, 호, and 목" in guardrail for guardrail in nested_prompt.guardrails)

    deleted_prompt = prompt_reports["deleted_article_current_force_review"]
    deleted_readiness = readiness_reports["deleted_article_status_guardrail"]
    assert deleted_prompt.status == "moleg_ready"
    assert deleted_readiness.status == "ready_for_reasoning"
    assert any(step.interface == "get_article" for step in deleted_prompt.planned_steps)
    assert deleted_readiness.evidence["is_deleted"] is True
    assert deleted_readiness.evidence["revision_type"] == "삭제"
    assert "deleted_article_is_not_current_operational_text" in deleted_readiness.risk_flags
    assert any("marked deleted" in guardrail for guardrail in deleted_prompt.guardrails)

    moved_prompt = prompt_reports["moved_article_current_force_review"]
    moved_readiness = readiness_reports["moved_article_status_guardrail"]
    assert moved_prompt.status == "needs_more_source_loading"
    assert moved_readiness.status == "ready_for_reasoning"
    moved_required_interfaces = [
        step.interface
        for step in moved_prompt.planned_steps
        if step.required_before_answer
    ]
    assert "load_article_context" in moved_required_interfaces
    assert moved_readiness.evidence["revision_type"] == "이동"
    assert moved_readiness.evidence["moved_to"] == "제12조"
    assert moved_readiness.evidence["current_article"] == "제12조"
    assert {citation.article for citation in moved_readiness.citations} == {"제8조", "제12조"}
    assert "moved_article_destination_loaded_before_current_substance" in moved_readiness.risk_flags
    assert any("current_article" in guardrail for guardrail in moved_prompt.guardrails)

    query_expansion_prompt = prompt_reports["query_expansion_candidate_authority_review"]
    query_expansion_readiness = readiness_reports["query_expansion_candidate_authority_guardrail"]
    assert query_expansion_prompt.status == "needs_more_source_loading"
    assert query_expansion_readiness.status == "needs_more_source_loading"
    assert any(step.interface == "expand_legal_query" for step in query_expansion_prompt.planned_steps)
    assert query_expansion_readiness.evidence["citations_loaded"] == 0
    assert all(
        filters.get("basis") == "effective"
        for filters in query_expansion_readiness.evidence["search_laws_followup_filters"]
    )
    assert all(
        filters.get("include_history") is False
        for filters in query_expansion_readiness.evidence["administrative_followup_filters"]
    )
    assert query_expansion_readiness.evidence["authority_followup_filters"] == [
        {
            "interface": "search_interpretations",
            "filters": {"source": "moleg", "search_body": False},
        },
        {
            "interface": "search_cases",
            "filters": {"court": "all", "search_body": False},
        },
        {
            "interface": "search_constitutional_decisions",
            "filters": {"search_body": False},
        },
    ]
    assert query_expansion_readiness.citations == []
    assert "query_expansion_is_not_final_authority" in query_expansion_readiness.risk_flags
    assert any("planning context" in guardrail for guardrail in query_expansion_prompt.guardrails)

    law_search_prompt = prompt_reports["law_search_candidate_detail_review"]
    law_search_readiness = readiness_reports["law_search_candidate_detail_guardrail"]
    assert law_search_prompt.status == "needs_more_source_loading"
    assert law_search_readiness.status == "needs_more_source_loading"
    assert any(step.interface == "search_laws" for step in law_search_prompt.planned_steps)
    assert "get_article" in {
        step.interface
        for step in law_search_prompt.planned_steps
        if step.required_before_answer
    }
    assert law_search_readiness.evidence["citations_loaded"] == 0
    assert law_search_readiness.evidence["service_call_targets"] == []
    assert (
        "law_search_hit_requires_selected_law_or_article_loading"
        in law_search_readiness.risk_flags
    )

    empty_law_prompt = prompt_reports["empty_law_search_absence_review"]
    empty_law_readiness = readiness_reports["empty_law_search_absence_guardrail"]
    assert empty_law_prompt.status == "needs_more_source_loading"
    assert empty_law_readiness.status == "needs_more_source_loading"
    empty_law_required_interfaces = [
        step.interface
        for step in empty_law_prompt.planned_steps
        if step.required_before_answer
    ]
    assert empty_law_required_interfaces.count("search_laws") == 2
    assert "expand_legal_query" in empty_law_required_interfaces
    assert empty_law_readiness.evidence["hit_count"] == 0
    assert empty_law_readiness.evidence["search_call_targets"] == ["eflaw"]
    assert (
        "empty_law_search_is_not_absence_of_current_law"
        in empty_law_readiness.risk_flags
    )
    assert any("one scoped law search" in guardrail for guardrail in empty_law_prompt.guardrails)
    assert any("No current legal basis exists" in action for action in empty_law_prompt.forbidden_actions)

    interpretation_prompt = prompt_reports["mixed_interpretation_authority_review"]
    interpretation_readiness = readiness_reports["interpretation_authority_distinction"]
    assert interpretation_prompt.status == "moleg_ready"
    assert interpretation_readiness.status == "ready_for_reasoning"
    assert any("distinct authority labels" in guardrail for guardrail in interpretation_prompt.guardrails)
    assert interpretation_readiness.evidence["labels"] == [
        ["moleg", "expc", None],
        ["ministry", "dapaCgmExpc", "방위사업청"],
    ]
    assert "ministry_interpretation_is_not_moleg_official_interpretation" in interpretation_readiness.risk_flags

    interpretation_detail_prompt = prompt_reports["interpretation_search_candidate_detail_review"]
    interpretation_detail_readiness = readiness_reports[
        "interpretation_search_candidate_detail_guardrail"
    ]
    assert interpretation_detail_prompt.status == "needs_more_source_loading"
    assert interpretation_detail_readiness.status == "needs_more_source_loading"
    assert any(
        step.interface == "search_interpretations"
        for step in interpretation_detail_prompt.planned_steps
    )
    assert "get_interpretation" in {
        step.interface
        for step in interpretation_detail_prompt.planned_steps
        if step.required_before_answer
    }
    assert interpretation_detail_readiness.evidence["citations_loaded"] == 0
    assert interpretation_detail_readiness.evidence["service_call_targets"] == []
    assert (
        "interpretation_search_hit_requires_get_interpretation_detail"
        in interpretation_detail_readiness.risk_flags
    )

    empty_interpretation_prompt = prompt_reports["empty_interpretation_search_absence_review"]
    empty_interpretation_readiness = readiness_reports[
        "empty_interpretation_search_absence_guardrail"
    ]
    assert empty_interpretation_prompt.status == "needs_more_source_loading"
    assert empty_interpretation_readiness.status == "needs_more_source_loading"
    empty_required_interfaces = [
        step.interface
        for step in empty_interpretation_prompt.planned_steps
        if step.required_before_answer
    ]
    assert empty_required_interfaces.count("search_interpretations") == 2
    assert "expand_legal_query" in empty_required_interfaces
    assert empty_interpretation_readiness.evidence["hit_count"] == 0
    assert empty_interpretation_readiness.evidence["search_call_targets"] == ["expc"]
    assert (
        "empty_interpretation_search_is_not_absence_of_authority"
        in empty_interpretation_readiness.risk_flags
    )
    assert any("zero hits" in action for action in empty_interpretation_prompt.forbidden_actions)

    source_access_prompt = prompt_reports["source_access_failure_absence_review"]
    source_access_readiness = readiness_reports[
        "source_access_failure_not_no_result_guardrail"
    ]
    assert source_access_prompt.status == "needs_more_source_loading"
    assert source_access_readiness.status == "needs_more_source_loading"
    source_access_required_interfaces = [
        step.interface
        for step in source_access_prompt.planned_steps
        if step.required_before_answer
    ]
    assert source_access_required_interfaces == ["search_laws", "search_laws"]
    assert source_access_readiness.evidence["error_type"] == "RateLimitError"
    assert source_access_readiness.evidence["hit_count"] is None
    assert source_access_readiness.evidence["citations_loaded"] == 0
    assert source_access_readiness.evidence["bundle_gap_interfaces"] == [
        "search_administrative_rules",
        "search_annex_forms",
        "search_annex_forms",
    ]
    assert (
        "source_access_failure_is_not_legal_no_result"
        in source_access_readiness.risk_flags
    )
    assert any("source-access problem" in guardrail for guardrail in source_access_prompt.guardrails)
    assert any("no current legal basis" in action for action in source_access_prompt.forbidden_actions)

    case_prompt = prompt_reports["case_search_candidate_detail_review"]
    case_readiness = readiness_reports["case_search_candidate_detail_guardrail"]
    assert case_prompt.status == "needs_more_source_loading"
    assert case_readiness.status == "needs_more_source_loading"
    assert any(step.interface == "search_cases" for step in case_prompt.planned_steps)
    assert "get_case" in {
        step.interface
        for step in case_prompt.planned_steps
        if step.required_before_answer
    }
    assert case_readiness.evidence["citations_loaded"] == 0
    assert case_readiness.evidence["service_call_targets"] == []
    assert "case_search_hit_requires_get_case_detail" in case_readiness.risk_flags

    empty_case_prompt = prompt_reports["empty_case_search_absence_review"]
    empty_case_readiness = readiness_reports["empty_case_search_absence_guardrail"]
    assert empty_case_prompt.status == "needs_more_source_loading"
    assert empty_case_readiness.status == "needs_more_source_loading"
    empty_case_required_interfaces = [
        step.interface
        for step in empty_case_prompt.planned_steps
        if step.required_before_answer
    ]
    assert empty_case_required_interfaces.count("search_cases") == 2
    assert "search_constitutional_decisions" in empty_case_required_interfaces
    assert "search_interpretations" in empty_case_required_interfaces
    assert empty_case_readiness.evidence["hit_count"] == 0
    assert empty_case_readiness.evidence["search_call_targets"] == ["prec"]
    assert (
        "empty_case_search_is_not_absence_of_judicial_authority"
        in empty_case_readiness.risk_flags
    )
    assert any("one scoped case search" in guardrail for guardrail in empty_case_prompt.guardrails)
    assert any("No relevant precedent exists" in action for action in empty_case_prompt.forbidden_actions)

    constitutional_detail_prompt = prompt_reports["constitutional_search_candidate_detail_review"]
    constitutional_detail_readiness = readiness_reports[
        "constitutional_search_candidate_detail_guardrail"
    ]
    assert constitutional_detail_prompt.status == "needs_more_source_loading"
    assert constitutional_detail_readiness.status == "needs_more_source_loading"
    assert any(
        step.interface == "search_constitutional_decisions"
        for step in constitutional_detail_prompt.planned_steps
    )
    assert "get_constitutional_decision" in {
        step.interface
        for step in constitutional_detail_prompt.planned_steps
        if step.required_before_answer
    }
    assert constitutional_detail_readiness.evidence["citations_loaded"] == 0
    assert constitutional_detail_readiness.evidence["service_call_targets"] == []
    assert (
        "constitutional_search_hit_requires_get_constitutional_decision_detail"
        in constitutional_detail_readiness.risk_flags
    )

    empty_constitutional_prompt = prompt_reports["empty_constitutional_search_absence_review"]
    empty_constitutional_readiness = readiness_reports[
        "empty_constitutional_search_absence_guardrail"
    ]
    assert empty_constitutional_prompt.status == "needs_more_source_loading"
    assert empty_constitutional_readiness.status == "needs_more_source_loading"
    empty_constitutional_required_interfaces = [
        step.interface
        for step in empty_constitutional_prompt.planned_steps
        if step.required_before_answer
    ]
    assert empty_constitutional_required_interfaces.count("search_constitutional_decisions") == 2
    assert "search_cases" in empty_constitutional_required_interfaces
    assert "search_interpretations" in empty_constitutional_required_interfaces
    assert empty_constitutional_readiness.evidence["hit_count"] == 0
    assert empty_constitutional_readiness.evidence["search_call_targets"] == ["detc"]
    assert (
        "empty_constitutional_search_is_not_absence_of_constitutional_authority"
        in empty_constitutional_readiness.risk_flags
    )
    assert any(
        "one scoped Constitutional Court search" in guardrail
        for guardrail in empty_constitutional_prompt.guardrails
    )
    assert any(
        "No constitutional decision exists" in action
        for action in empty_constitutional_prompt.forbidden_actions
    )

    authority_mismatch_prompt = prompt_reports["authority_article_reference_match_review"]
    authority_mismatch_readiness = readiness_reports[
        "loaded_authority_article_mismatch_guardrail"
    ]
    assert authority_mismatch_prompt.status == "needs_more_source_loading"
    assert authority_mismatch_readiness.status == "needs_more_source_loading"
    authority_mismatch_required_interfaces = {
        step.interface
        for step in authority_mismatch_prompt.planned_steps
        if step.required_before_answer
    }
    assert authority_mismatch_required_interfaces == {"load_authority_context"}
    assert authority_mismatch_readiness.evidence["authority_article_matches"] == {
        "interpretation": False,
        "case": False,
        "constitutional": False,
    }
    assert (
        "loaded_authority_reference_mismatch_not_target_article_authority"
        in authority_mismatch_readiness.risk_flags
    )
    assert any(
        "current_authorities" in guardrail
        for guardrail in authority_mismatch_prompt.guardrails
    )
    assert any(
        "referenced_articles" in guardrail
        for guardrail in authority_mismatch_prompt.guardrails
    )
    assert any(
        "different article" in action
        for action in authority_mismatch_prompt.forbidden_actions
    )

    bundle_authority_mismatch_prompt = prompt_reports[
        "context_bundle_authority_article_mismatch_review"
    ]
    bundle_authority_mismatch_readiness = readiness_reports[
        "context_bundle_authority_article_mismatch_guardrail"
    ]
    assert bundle_authority_mismatch_prompt.status == "needs_more_source_loading"
    assert bundle_authority_mismatch_readiness.status == "needs_more_source_loading"
    bundle_authority_mismatch_required_interfaces = {
        step.interface
        for step in bundle_authority_mismatch_prompt.planned_steps
        if step.required_before_answer
    }
    assert {
        "load_legal_context_bundle",
        "search_interpretations",
        "search_cases",
        "search_constitutional_decisions",
    }.issubset(bundle_authority_mismatch_required_interfaces)
    assert bundle_authority_mismatch_readiness.evidence["authority_gap_interfaces"] == [
        "search_interpretations",
        "search_cases",
        "search_constitutional_decisions",
    ]
    assert (
        "context_bundle_authority_article_mismatch_gap_requires_followup_search"
        in bundle_authority_mismatch_readiness.risk_flags
    )
    assert any(
        "authority_article_mismatch" in guardrail
        for guardrail in bundle_authority_mismatch_prompt.guardrails
    )
    assert any(
        "target-article authority" in action
        for action in bundle_authority_mismatch_prompt.forbidden_actions
    )

    bundle_authority_unverified_prompt = prompt_reports[
        "context_bundle_authority_article_unverified_review"
    ]
    bundle_authority_unverified_readiness = readiness_reports[
        "context_bundle_authority_article_unverified_guardrail"
    ]
    assert bundle_authority_unverified_prompt.status == "needs_more_source_loading"
    assert bundle_authority_unverified_readiness.status == "needs_more_source_loading"
    bundle_authority_unverified_required_interfaces = {
        step.interface
        for step in bundle_authority_unverified_prompt.planned_steps
        if step.required_before_answer
    }
    assert {
        "load_legal_context_bundle",
        "search_interpretations",
        "search_cases",
        "search_constitutional_decisions",
    }.issubset(bundle_authority_unverified_required_interfaces)
    assert bundle_authority_unverified_readiness.evidence["authority_gap_interfaces"] == [
        "search_interpretations",
        "search_cases",
        "search_constitutional_decisions",
    ]
    assert (
        "context_bundle_authority_article_unverified_gap_requires_followup_search"
        in bundle_authority_unverified_readiness.risk_flags
    )
    assert any(
        "authority_article_unverified" in guardrail
        for guardrail in bundle_authority_unverified_prompt.guardrails
    )
    assert any(
        "implicit match" in action
        for action in bundle_authority_unverified_prompt.forbidden_actions
    )

    bundle_authority_partial_prompt = prompt_reports[
        "context_bundle_authority_article_partial_match_review"
    ]
    bundle_authority_partial_readiness = readiness_reports[
        "context_bundle_authority_article_partial_match_guardrail"
    ]
    assert bundle_authority_partial_prompt.status == "needs_more_source_loading"
    assert bundle_authority_partial_readiness.status == "needs_more_source_loading"
    bundle_authority_partial_required_interfaces = {
        step.interface
        for step in bundle_authority_partial_prompt.planned_steps
        if step.required_before_answer
    }
    assert {
        "load_legal_context_bundle",
        "search_interpretations",
        "search_cases",
        "search_constitutional_decisions",
    }.issubset(bundle_authority_partial_required_interfaces)
    assert bundle_authority_partial_readiness.evidence["authority_gap_interfaces"] == [
        "search_interpretations",
        "search_cases",
        "search_constitutional_decisions",
    ]
    assert bundle_authority_partial_readiness.evidence["authority_matched_articles"] == {
        "interpretation": ["제17조"],
        "case": ["제17조"],
        "constitutional": ["제17조"],
    }
    assert (
        "context_bundle_authority_article_partial_match_gap_requires_followup_search"
        in bundle_authority_partial_readiness.risk_flags
    )
    assert any(
        "authority_article_partial_match" in guardrail
        for guardrail in bundle_authority_partial_prompt.guardrails
    )
    assert any(
        "all requested articles" in action
        for action in bundle_authority_partial_prompt.forbidden_actions
    )

    bundle_authority_temporal_prompt = prompt_reports[
        "context_bundle_authority_temporal_mismatch_review"
    ]
    bundle_authority_temporal_readiness = readiness_reports[
        "context_bundle_authority_temporal_mismatch_guardrail"
    ]
    assert bundle_authority_temporal_prompt.status == "needs_more_source_loading"
    assert bundle_authority_temporal_readiness.status == "needs_more_source_loading"
    bundle_authority_temporal_required_interfaces = {
        step.interface
        for step in bundle_authority_temporal_prompt.planned_steps
        if step.required_before_answer
    }
    assert {
        "load_legal_context_bundle",
        "trace_law_history",
        "get_article",
    }.issubset(bundle_authority_temporal_required_interfaces)
    assert bundle_authority_temporal_readiness.evidence["target_article"] == {
        "law_name": "개인정보 보호법",
        "article": "제15조",
        "effective_date": "20250101",
    }
    assert bundle_authority_temporal_readiness.evidence["authority_article_matches"] == {
        "interpretation": True,
        "case": True,
        "constitutional": True,
    }
    assert bundle_authority_temporal_readiness.evidence["authority_gap_interfaces"] == [
        "trace_law_history",
        "trace_law_history",
        "trace_law_history",
    ]
    assert bundle_authority_temporal_readiness.evidence["authority_deferred_interfaces"] == [
        "trace_law_history",
        "trace_law_history",
        "trace_law_history",
    ]
    assert (
        "context_bundle_authority_temporal_mismatch_gap_requires_history_check"
        in bundle_authority_temporal_readiness.risk_flags
    )
    assert any(
        "authority_temporal_mismatch" in guardrail
        for guardrail in bundle_authority_temporal_prompt.guardrails
    )
    assert any(
        "current wording" in action
        for action in bundle_authority_temporal_prompt.forbidden_actions
    )

    law_structure_prompt = prompt_reports["law_structure_hierarchy_candidate_review"]
    law_structure_readiness = readiness_reports["law_structure_hierarchy_candidate_guardrail"]
    assert law_structure_prompt.status == "needs_more_source_loading"
    assert law_structure_readiness.status == "needs_more_source_loading"
    law_structure_required_interfaces = {
        step.interface
        for step in law_structure_prompt.planned_steps
        if step.required_before_answer
    }
    assert {"get_law_structure", "find_delegated_rules", "get_article"}.issubset(
        law_structure_required_interfaces
    )
    assert law_structure_readiness.evidence["service_call_targets"] == ["lsStmd"]
    assert law_structure_readiness.evidence["article_level_delegation_targets"] == []
    assert (
        "law_structure_is_not_article_level_delegation"
        in law_structure_readiness.risk_flags
    )
    assert any(
        "article-level delegation" in action
        for action in law_structure_prompt.forbidden_actions
    )

    empty_delegation_prompt = prompt_reports["empty_delegation_graph_absence_review"]
    empty_delegation_readiness = readiness_reports[
        "empty_delegation_graph_absence_guardrail"
    ]
    assert empty_delegation_prompt.status == "needs_more_source_loading"
    assert empty_delegation_readiness.status == "needs_more_source_loading"
    empty_delegation_required_interfaces = [
        step.interface
        for step in empty_delegation_prompt.planned_steps
        if step.required_before_answer
    ]
    assert empty_delegation_required_interfaces.count("find_delegated_rules") == 2
    assert "get_law_structure" in empty_delegation_required_interfaces
    assert "search_administrative_rules" in empty_delegation_required_interfaces
    assert "search_annex_forms" in empty_delegation_required_interfaces
    assert empty_delegation_readiness.evidence["rule_count"] == 0
    assert empty_delegation_readiness.evidence["service_call_targets"] == ["lsDelegated"]
    assert (
        "empty_delegation_graph_is_not_absence_of_delegated_rules"
        in empty_delegation_readiness.risk_flags
    )
    assert any(
        "one scoped delegation graph" in guardrail
        for guardrail in empty_delegation_prompt.guardrails
    )
    assert any(
        "No delegated rule exists" in action
        for action in empty_delegation_prompt.forbidden_actions
    )

    administrative_rule_detail_prompt = prompt_reports[
        "administrative_rule_search_candidate_detail_review"
    ]
    administrative_rule_detail_readiness = readiness_reports[
        "administrative_rule_search_candidate_detail_guardrail"
    ]
    assert administrative_rule_detail_prompt.status == "needs_more_source_loading"
    assert administrative_rule_detail_readiness.status == "needs_more_source_loading"
    assert any(
        step.interface == "search_administrative_rules"
        for step in administrative_rule_detail_prompt.planned_steps
    )
    assert "get_administrative_rule" in {
        step.interface
        for step in administrative_rule_detail_prompt.planned_steps
        if step.required_before_answer
    }
    assert administrative_rule_detail_readiness.evidence["citations_loaded"] == 0
    assert administrative_rule_detail_readiness.evidence["service_call_targets"] == []
    assert (
        "administrative_rule_search_hit_requires_get_administrative_rule_detail"
        in administrative_rule_detail_readiness.risk_flags
    )

    administrative_rule_issued_on_prompt = prompt_reports[
        "administrative_rule_issued_on_current_criteria_review"
    ]
    administrative_rule_issued_on_readiness = readiness_reports[
        "administrative_rule_issued_on_not_effective_as_of_guardrail"
    ]
    assert administrative_rule_issued_on_prompt.status == "needs_more_source_loading"
    assert administrative_rule_issued_on_readiness.status == "needs_more_source_loading"
    administrative_rule_issued_on_required_interfaces = [
        step.interface
        for step in administrative_rule_issued_on_prompt.planned_steps
        if step.required_before_answer
    ]
    assert administrative_rule_issued_on_required_interfaces.count(
        "search_administrative_rules"
    ) == 2
    assert "get_administrative_rule" in administrative_rule_issued_on_required_interfaces
    assert administrative_rule_issued_on_readiness.evidence["candidate"]["issuing_date"] == (
        "20250101"
    )
    assert administrative_rule_issued_on_readiness.evidence["candidate"]["effective_date"] == (
        "20250301"
    )
    assert (
        "administrative_rule_issued_on_filter_is_not_effective_as_of"
        in administrative_rule_issued_on_readiness.risk_flags
    )
    assert any(
        "발령일자" in guardrail
        for guardrail in administrative_rule_issued_on_prompt.guardrails
    )
    assert any(
        "issued_on" in action
        for action in administrative_rule_issued_on_prompt.forbidden_actions
    )

    administrative_rule_status_prompt = prompt_reports[
        "administrative_rule_article_status_review"
    ]
    administrative_rule_status_readiness = readiness_reports[
        "administrative_rule_article_status_guardrail"
    ]
    assert administrative_rule_status_prompt.status == "needs_more_source_loading"
    assert administrative_rule_status_readiness.status == "ready_for_reasoning"
    administrative_rule_status_required_interfaces = [
        step.interface
        for step in administrative_rule_status_prompt.planned_steps
        if step.required_before_answer
    ]
    assert administrative_rule_status_required_interfaces == ["load_administrative_rule_context"]
    assert len(administrative_rule_status_readiness.citations) == 3
    assert administrative_rule_status_readiness.evidence["article_statuses"][0]["is_deleted"] is True
    assert administrative_rule_status_readiness.evidence["article_statuses"][1]["moved_to"] == "제6조"
    assert administrative_rule_status_readiness.evidence["current_article"] == "제6조"
    assert (
        "administrative_rule_moved_article_destination_loaded_before_current_criteria"
        in administrative_rule_status_readiness.risk_flags
    )
    assert any(
        "deleted administrative-rule article" in guardrail
        for guardrail in administrative_rule_status_prompt.guardrails
    )

    administrative_rule_transition_prompt = prompt_reports[
        "administrative_rule_supplementary_transition_review"
    ]
    administrative_rule_transition_readiness = readiness_reports[
        "administrative_rule_supplementary_transition_guardrail"
    ]
    assert administrative_rule_transition_prompt.status == "moleg_ready"
    assert administrative_rule_transition_readiness.status == "ready_for_reasoning"
    assert any(
        step.interface == "get_administrative_rule"
        for step in administrative_rule_transition_prompt.planned_steps
    )
    assert administrative_rule_transition_readiness.must_have["supplementary_provisions_loaded"] is True
    assert administrative_rule_transition_readiness.must_have["transition_text_not_in_article"] is True
    assert (
        "administrative_rule_supplementary_provision_required_for_transition_application"
        in administrative_rule_transition_readiness.risk_flags
    )
    assert any(
        "Administrative-rule supplementary provisions" in guardrail
        for guardrail in administrative_rule_transition_prompt.guardrails
    )

    empty_admin_rule_prompt = prompt_reports["empty_administrative_rule_search_absence_review"]
    empty_admin_rule_readiness = readiness_reports[
        "empty_administrative_rule_search_absence_guardrail"
    ]
    assert empty_admin_rule_prompt.status == "needs_more_source_loading"
    assert empty_admin_rule_readiness.status == "needs_more_source_loading"
    empty_admin_required_interfaces = [
        step.interface
        for step in empty_admin_rule_prompt.planned_steps
        if step.required_before_answer
    ]
    assert empty_admin_required_interfaces.count("search_administrative_rules") == 2
    assert "find_delegated_rules" in empty_admin_required_interfaces
    assert empty_admin_rule_readiness.evidence["hit_count"] == 0
    assert empty_admin_rule_readiness.evidence["search_call_targets"] == ["admrul"]
    assert (
        "empty_administrative_rule_search_is_not_absence_of_delegated_criteria"
        in empty_admin_rule_readiness.risk_flags
    )
    assert any(
        "one scoped administrative-rule search" in guardrail
        for guardrail in empty_admin_rule_prompt.guardrails
    )
    assert any(
        "No delegated operational criteria exist" in action
        for action in empty_admin_rule_prompt.forbidden_actions
    )

    comparable_candidate_prompt = prompt_reports["comparable_mechanism_candidate_detail_review"]
    comparable_candidate_readiness = readiness_reports[
        "comparable_mechanism_candidate_detail_guardrail"
    ]
    assert comparable_candidate_prompt.status == "needs_more_source_loading"
    assert comparable_candidate_readiness.status == "needs_more_source_loading"
    assert any(
        step.interface == "find_comparable_mechanisms"
        for step in comparable_candidate_prompt.planned_steps
    )
    assert "get_article" in {
        step.interface
        for step in comparable_candidate_prompt.planned_steps
        if step.required_before_answer
    }
    assert comparable_candidate_readiness.evidence["citations_loaded"] == 0
    assert comparable_candidate_readiness.evidence["article_service_targets"] == []
    assert (
        "comparable_mechanism_candidate_requires_selected_article_loading"
        in comparable_candidate_readiness.risk_flags
    )

    annex_detail_prompt = prompt_reports["annex_search_candidate_detail_review"]
    annex_detail_readiness = readiness_reports["annex_form_search_candidate_detail_guardrail"]
    assert annex_detail_prompt.status == "needs_more_source_loading"
    assert annex_detail_readiness.status == "needs_more_source_loading"
    assert any(step.interface == "search_annex_forms" for step in annex_detail_prompt.planned_steps)
    assert "get_annex_form_body" in {
        step.interface
        for step in annex_detail_prompt.planned_steps
        if step.required_before_answer
    }
    assert annex_detail_readiness.evidence["citations_loaded"] == 0
    assert annex_detail_readiness.evidence["text_call_targets"] == []
    assert "annex_form_search_hit_requires_get_annex_form_body" in annex_detail_readiness.risk_flags

    empty_annex_prompt = prompt_reports["empty_annex_form_search_absence_review"]
    empty_annex_readiness = readiness_reports["empty_annex_form_search_absence_guardrail"]
    assert empty_annex_prompt.status == "needs_more_source_loading"
    assert empty_annex_readiness.status == "needs_more_source_loading"
    empty_annex_required_interfaces = [
        step.interface
        for step in empty_annex_prompt.planned_steps
        if step.required_before_answer
    ]
    assert empty_annex_required_interfaces.count("search_annex_forms") == 2
    assert "get_law" in empty_annex_required_interfaces
    assert "search_administrative_rules" in empty_annex_required_interfaces
    assert empty_annex_readiness.evidence["hit_count"] == 0
    assert empty_annex_readiness.evidence["search_call_targets"] == ["licbyl"]
    assert (
        "empty_annex_form_search_is_not_absence_of_attached_material"
        in empty_annex_readiness.risk_flags
    )
    assert any(
        "one scoped annex/form search" in guardrail
        for guardrail in empty_annex_prompt.guardrails
    )
    assert any(
        "No attached criteria exist" in action
        for action in empty_annex_prompt.forbidden_actions
    )

    delegated_prompt = prompt_reports["delegated_operational_criteria"]
    delegated_readiness = readiness_reports["delegated_criteria_tracing"]
    delegated_loaded_readiness = readiness_reports["delegated_criteria_after_followups"]
    delegated_mismatch_readiness = readiness_reports[
        "delegated_criteria_source_mismatch_guardrail"
    ]
    delegated_future_admin_readiness = readiness_reports["future_effective_administrative_rule_guardrail"]
    assert delegated_prompt.status == "needs_more_source_loading"
    assert delegated_readiness.status == "needs_more_source_loading"
    assert any(step.interface == "load_delegated_criteria" for step in delegated_prompt.planned_steps)
    assert any("effective date" in guardrail for guardrail in delegated_prompt.guardrails)
    assert any("delegated_criteria_source_mismatch" in guardrail for guardrail in delegated_prompt.guardrails)
    assert delegated_readiness.must_have["deferred_followups_preserved"] is True
    assert delegated_loaded_readiness.status == "ready_for_reasoning"
    assert delegated_future_admin_readiness.status == "ready_for_reasoning"
    assert (
        "administrative_rule_not_effective_as_of_reference_date"
        in delegated_future_admin_readiness.risk_flags
    )
    assert {"load_delegated_criteria"}.issubset({
        step.interface
        for step in delegated_prompt.planned_steps
        if step.required_before_answer
    })
    assert delegated_loaded_readiness.public_interfaces == ["load_institutional_system", "load_followup"]
    assert delegated_loaded_readiness.must_have["administrative_rule_followup_executable"] is True
    assert delegated_loaded_readiness.must_have["annex_followup_executable"] is True
    assert delegated_mismatch_readiness.status == "needs_more_source_loading"
    assert delegated_mismatch_readiness.public_interfaces == ["load_delegated_criteria"]
    assert "delegated_criteria_source_mismatch" in delegated_mismatch_readiness.evidence["gap_kinds"]
    assert {citation.source_type for citation in delegated_mismatch_readiness.citations} == {
        "law",
        "delegation",
    }

    missing_admin_ref_prompt = prompt_reports["administrative_rule_missing_source_reference_review"]
    missing_admin_ref_readiness = readiness_reports[
        "administrative_rule_missing_source_reference_guardrail"
    ]
    assert missing_admin_ref_prompt.status == "needs_more_source_loading"
    assert missing_admin_ref_readiness.status == "ready_for_reasoning"
    assert missing_admin_ref_readiness.evidence["source_law_name"] is None
    assert missing_admin_ref_readiness.evidence["source_article"] is None
    assert (
        "missing_administrative_rule_source_reference_is_unknown_not_no_authorization"
        in missing_admin_ref_readiness.risk_flags
    )
    assert any(
        step.interface == "find_delegated_rules"
        for step in missing_admin_ref_prompt.planned_steps
        if step.required_before_answer
    )
    assert any("source_law_name=None" in action for action in missing_admin_ref_prompt.forbidden_actions)

    annex_prompt = prompt_reports["annex_table_extraction_confidence"]
    annex_readiness = readiness_reports["low_confidence_annex_body_guardrail"]
    assert annex_prompt.status == "moleg_ready"
    assert annex_readiness.status == "ready_for_reasoning"
    assert annex_readiness.evidence["parsing_confidence"] == "low"
    assert annex_readiness.evidence["structured_rows"] == 0
    assert "empty_structured_rows_do_not_mean_no_annex_criteria" in annex_readiness.risk_flags
    assert any("parsing_confidence is high" in guardrail for guardrail in annex_prompt.guardrails)

    comparative_prompt = prompt_reports["comparative_sanction_design"]
    comparative_readiness = readiness_reports["comparative_design"]
    assert comparative_prompt.status == "moleg_ready"
    assert comparative_readiness.status == "ready_for_reasoning"
    assert any(step.interface == "find_comparable_mechanisms" for step in comparative_prompt.planned_steps)
    assert comparative_readiness.must_have["selected_article_loaded_before_citation"] is True

    bundle_authority_prompt = prompt_reports["context_bundle_bounded_authority_review"]
    bundle_authority_readiness = readiness_reports["sanction_design"]
    assert bundle_authority_prompt.status == "needs_more_source_loading"
    assert bundle_authority_readiness.status == "ready_for_reasoning"
    assert any(
        step.interface == "load_legal_context_bundle"
        for step in bundle_authority_prompt.planned_steps
    )
    assert bundle_authority_readiness.evidence["loaded_authority_detail_types"] == [
        "interpretation_detail",
        "case_detail",
        "constitutional_detail",
    ]
    assert (
        "context_bundle_is_bounded_first_pass_not_exhaustive_authority_survey"
        in bundle_authority_readiness.risk_flags
    )
    bundle_required_interfaces = {
        step.interface
        for step in bundle_authority_prompt.planned_steps
        if step.required_before_answer
    }
    assert {
        "get_interpretation",
        "get_case",
        "get_constitutional_decision",
        "get_administrative_rule",
        "get_annex_form_body",
    }.issubset(bundle_required_interfaces)
    assert {"administrative_rule", "annex_form"}.issubset(
        bundle_authority_readiness.evidence["candidate_types"]
    )
    assert any("exhaustive authority survey" in action for action in bundle_authority_prompt.forbidden_actions)

    institutional_prompt = prompt_reports["institutional_system_explicit_statute_set_review"]
    institutional_readiness = readiness_reports["multi_law_concept_assembly"]
    assert institutional_prompt.status == "moleg_ready"
    assert institutional_readiness.status == "ready_for_reasoning"
    assert any(
        step.interface == "load_institutional_system"
        for step in institutional_prompt.planned_steps
        if step.required_before_answer
    )
    assert institutional_readiness.must_have["explicit_statute_set_preserved"] is True
    assert "institutional_system_does_not_discover_statute_set" in institutional_readiness.risk_flags
    assert any("exhaustive" in action for action in institutional_prompt.forbidden_actions)

    constitutional_prompt = prompt_reports["constitutional_risk_review"]
    constitutional_readiness = readiness_reports["constitutional_risk_scan"]
    assert constitutional_prompt.status == "moleg_ready"
    assert constitutional_readiness.status == "ready_for_reasoning"
    assert any("free-text" in guardrail for guardrail in constitutional_prompt.guardrails)
    assert constitutional_readiness.must_have["unloaded_decisions_deferred"] is True
    assert "detc_is_free_text_search_not_doctrine_index" in constitutional_readiness.risk_flags

    latest_prompt = prompt_reports["latest_social_context_plus_current_law"]
    latest_readiness = readiness_reports["latest_social_context_websearch_handoff"]
    assert latest_prompt.status == "requires_websearch_handoff"
    assert latest_readiness.status == "needs_more_source_loading"
    assert any(step.source == "websearch" for step in latest_prompt.planned_steps)
    assert latest_readiness.must_have["current_article_loaded"] is True
    assert latest_readiness.evidence["social_fact_sources_loaded"] == []
    assert "latest_social_facts_require_websearch" in latest_readiness.risk_flags
    assert any("cite it separately" in guardrail for guardrail in latest_prompt.guardrails)


def test_every_prompt_dry_run_terminal_state_has_a_skill_discipline_reason():
    for report in run_legislative_expert_prompt_dry_run():
        assert report.guardrails, report.scenario
        assert report.forbidden_actions, report.scenario
        if report.status != "moleg_ready":
            assert any(step.source != "moleg-api" for step in report.planned_steps) or any(
                step.required_before_answer for step in report.planned_steps
            )
