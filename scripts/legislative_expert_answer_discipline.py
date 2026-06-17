"""Answer-discipline gate for the future legislative-expert skill.

This harness does not draft legal advice. It checks the final pre-answer rule:
given the prompt plan and answer-readiness reports, which claims are allowed,
which claims must be withheld, and which follow-up sources must be loaded first.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.legislative_expert_e2e_audit import (
    LegislativeExpertScenarioReport,
    SourceCitation,
    run_legislative_expert_e2e_audit,
)
from scripts.legislative_expert_prompt_dry_run import (
    PromptDryRunReport,
    run_legislative_expert_prompt_dry_run,
)


AnswerDisciplineStatus = Literal[
    "can_answer_with_loaded_sources",
    "must_load_more_sources",
    "must_not_answer_as_current_law",
]


@dataclass(frozen=True)
class AnswerDisciplineReport:
    """One deterministic answer-discipline report."""

    scenario: str
    status: AnswerDisciplineStatus
    allowed_claims: list[str]
    forbidden_claims: list[str]
    required_disclosures: list[str] = field(default_factory=list)
    required_followups: list[str] = field(default_factory=list)
    citations: list[SourceCitation] = field(default_factory=list)
    evidence: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def run_legislative_expert_answer_discipline() -> list[AnswerDisciplineReport]:
    """Return answer-discipline reports for high-risk prompt/source pairs."""

    prompt_reports = {
        report.scenario: report
        for report in run_legislative_expert_prompt_dry_run()
    }
    readiness_reports = {
        report.scenario: report
        for report in run_legislative_expert_e2e_audit()
    }

    reports = [
        _proposed_bill_discipline(
            prompt_reports["proposed_bill_current_law_check"],
            readiness_reports["proposed_bill_without_promulgation_bridge_guardrail"],
        ),
        _enacted_bill_change_trace_discipline(
            prompt_reports["enacted_bill_change_trace"],
            readiness_reports["congress_bill_to_current_law"],
        ),
        _loaded_before_after_amendment_delta_discipline(
            prompt_reports["enacted_bill_change_trace"],
            readiness_reports["loaded_before_after_amendment_delta_guardrail"],
        ),
        _historical_repealed_law_discipline(
            prompt_reports["historical_repealed_law_review"],
            readiness_reports["historical_article_as_of_guardrail"],
        ),
        _nested_article_unit_discipline(
            prompt_reports["nested_article_unit_review"],
            readiness_reports["nested_article_unit_text_guardrail"],
        ),
        _deleted_article_discipline(
            prompt_reports["deleted_article_current_force_review"],
            readiness_reports["deleted_article_status_guardrail"],
        ),
        _moved_article_discipline(
            prompt_reports["moved_article_current_force_review"],
            readiness_reports["moved_article_status_guardrail"],
        ),
        _query_expansion_candidate_discipline(
            prompt_reports["query_expansion_candidate_authority_review"],
            readiness_reports["query_expansion_candidate_authority_guardrail"],
        ),
        _law_search_candidate_discipline(
            prompt_reports["law_search_candidate_detail_review"],
            readiness_reports["law_search_candidate_detail_guardrail"],
        ),
        _empty_law_search_absence_discipline(
            prompt_reports["empty_law_search_absence_review"],
            readiness_reports["empty_law_search_absence_guardrail"],
        ),
        _interpretation_authority_discipline(
            prompt_reports["mixed_interpretation_authority_review"],
            readiness_reports["interpretation_authority_distinction"],
        ),
        _interpretation_search_candidate_discipline(
            prompt_reports["interpretation_search_candidate_detail_review"],
            readiness_reports["interpretation_search_candidate_detail_guardrail"],
        ),
        _empty_interpretation_search_absence_discipline(
            prompt_reports["empty_interpretation_search_absence_review"],
            readiness_reports["empty_interpretation_search_absence_guardrail"],
        ),
        _source_access_failure_discipline(
            prompt_reports["source_access_failure_absence_review"],
            readiness_reports["source_access_failure_not_no_result_guardrail"],
        ),
        _case_search_candidate_discipline(
            prompt_reports["case_search_candidate_detail_review"],
            readiness_reports["case_search_candidate_detail_guardrail"],
        ),
        _empty_case_search_absence_discipline(
            prompt_reports["empty_case_search_absence_review"],
            readiness_reports["empty_case_search_absence_guardrail"],
        ),
        _constitutional_search_candidate_discipline(
            prompt_reports["constitutional_search_candidate_detail_review"],
            readiness_reports["constitutional_search_candidate_detail_guardrail"],
        ),
        _empty_constitutional_search_absence_discipline(
            prompt_reports["empty_constitutional_search_absence_review"],
            readiness_reports["empty_constitutional_search_absence_guardrail"],
        ),
        _authority_article_reference_mismatch_discipline(
            prompt_reports["authority_article_reference_match_review"],
            readiness_reports["loaded_authority_article_mismatch_guardrail"],
        ),
        _context_bundle_authority_article_mismatch_discipline(
            prompt_reports["context_bundle_authority_article_mismatch_review"],
            readiness_reports["context_bundle_authority_article_mismatch_guardrail"],
        ),
        _context_bundle_authority_article_unverified_discipline(
            prompt_reports["context_bundle_authority_article_unverified_review"],
            readiness_reports["context_bundle_authority_article_unverified_guardrail"],
        ),
        _context_bundle_authority_article_partial_match_discipline(
            prompt_reports["context_bundle_authority_article_partial_match_review"],
            readiness_reports["context_bundle_authority_article_partial_match_guardrail"],
        ),
        _context_bundle_authority_temporal_mismatch_discipline(
            prompt_reports["context_bundle_authority_temporal_mismatch_review"],
            readiness_reports["context_bundle_authority_temporal_mismatch_guardrail"],
        ),
        _law_structure_hierarchy_candidate_discipline(
            prompt_reports["law_structure_hierarchy_candidate_review"],
            readiness_reports["law_structure_hierarchy_candidate_guardrail"],
        ),
        _empty_delegation_graph_absence_discipline(
            prompt_reports["empty_delegation_graph_absence_review"],
            readiness_reports["empty_delegation_graph_absence_guardrail"],
        ),
        _administrative_rule_search_candidate_discipline(
            prompt_reports["administrative_rule_search_candidate_detail_review"],
            readiness_reports["administrative_rule_search_candidate_detail_guardrail"],
        ),
        _administrative_rule_issued_on_not_effective_as_of_discipline(
            prompt_reports["administrative_rule_issued_on_current_criteria_review"],
            readiness_reports["administrative_rule_issued_on_not_effective_as_of_guardrail"],
        ),
        _administrative_rule_article_status_discipline(
            prompt_reports["administrative_rule_article_status_review"],
            readiness_reports["administrative_rule_article_status_guardrail"],
        ),
        _administrative_rule_supplementary_transition_discipline(
            prompt_reports["administrative_rule_supplementary_transition_review"],
            readiness_reports["administrative_rule_supplementary_transition_guardrail"],
        ),
        _empty_administrative_rule_search_absence_discipline(
            prompt_reports["empty_administrative_rule_search_absence_review"],
            readiness_reports["empty_administrative_rule_search_absence_guardrail"],
        ),
        _administrative_rule_missing_source_reference_discipline(
            prompt_reports["administrative_rule_missing_source_reference_review"],
            readiness_reports["administrative_rule_missing_source_reference_guardrail"],
        ),
        _comparable_mechanism_candidate_discipline(
            prompt_reports["comparable_mechanism_candidate_detail_review"],
            readiness_reports["comparable_mechanism_candidate_detail_guardrail"],
        ),
        _annex_form_search_candidate_discipline(
            prompt_reports["annex_search_candidate_detail_review"],
            readiness_reports["annex_form_search_candidate_detail_guardrail"],
        ),
        _empty_annex_form_search_absence_discipline(
            prompt_reports["empty_annex_form_search_absence_review"],
            readiness_reports["empty_annex_form_search_absence_guardrail"],
        ),
        _delegated_criteria_discipline(
            prompt_reports["delegated_operational_criteria"],
            readiness_reports["delegated_criteria_tracing"],
        ),
        _delegated_criteria_after_followups_discipline(
            prompt_reports["delegated_operational_criteria"],
            readiness_reports["delegated_criteria_after_followups"],
        ),
        _delegated_criteria_source_mismatch_discipline(
            prompt_reports["delegated_operational_criteria"],
            readiness_reports["delegated_criteria_source_mismatch_guardrail"],
        ),
        _low_confidence_annex_body_discipline(
            prompt_reports["annex_table_extraction_confidence"],
            readiness_reports["low_confidence_annex_body_guardrail"],
        ),
        _future_effective_administrative_rule_discipline(
            prompt_reports["delegated_operational_criteria"],
            readiness_reports["future_effective_administrative_rule_guardrail"],
        ),
        _future_effective_promulgated_law_discipline(
            prompt_reports["proposed_bill_current_law_check"],
            readiness_reports["future_effective_promulgated_law_guardrail"],
        ),
        _constitutional_risk_discipline(
            prompt_reports["constitutional_risk_review"],
            readiness_reports["constitutional_risk_scan"],
        ),
        _comparative_design_discipline(
            prompt_reports["comparative_sanction_design"],
            readiness_reports["comparative_design"],
        ),
        _context_bundle_authority_discipline(
            prompt_reports["context_bundle_bounded_authority_review"],
            readiness_reports["sanction_design"],
        ),
        _institutional_system_discipline(
            prompt_reports["institutional_system_explicit_statute_set_review"],
            readiness_reports["multi_law_concept_assembly"],
        ),
        _latest_social_context_discipline(
            prompt_reports["latest_social_context_plus_current_law"],
            readiness_reports["latest_social_context_websearch_handoff"],
        ),
        _supplementary_transition_discipline(
            prompt_reports["supplementary_transition_review"],
            readiness_reports["supplementary_provision_transition_guardrail"],
        ),
    ]
    _validate_answer_discipline(reports)
    return reports


def _proposed_bill_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="proposed_bill_current_law_answer_discipline",
        status="must_not_answer_as_current_law",
        allowed_claims=[
            "The prompt starts from a bill title, not a proven current-law identity.",
            "The skill must return to congress-db for bill status and promulgation bridge fields.",
        ],
        forbidden_claims=[
            "The proposed bill is current law.",
            "MOLEG current-law text was loaded for this bill title.",
        ],
        required_disclosures=[
            "A National Assembly bill is not current law unless promulgation is proven.",
        ],
        required_followups=["congress-db.bill_final_outcomes"],
        citations=[],
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "moleg_source_calls": readiness.evidence["source_calls"],
        },
    )


def _enacted_bill_change_trace_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    required_followups = [
        step.interface
        for step in prompt.planned_steps
        if step.interface in {"trace_law_history", "compare_law_versions"}
    ]
    return AnswerDisciplineReport(
        scenario="enacted_bill_change_trace_answer_discipline",
        status="must_load_more_sources",
        allowed_claims=[
            "The promulgation bridge resolved to a current-law identity.",
            "Loaded current-law text may be cited as current wording, not as proof of the amendment delta.",
            "History and diff follow-ups remain required before explaining what the bill changed.",
        ],
        forbidden_claims=[
            "The bill changed specific articles before trace_law_history() or compare_law_versions() has loaded them.",
            "Current text alone proves the amendment delta.",
            "Promulgation bridge resolution proves which provisions changed.",
            "Law-level chronology alone proves full before/after wording.",
        ],
        required_disclosures=[
            "Separate current-law identity/current wording from amendment-delta tracing.",
            "Disclose that history/diff has not been loaded when only the bridge/current-law packet is available.",
        ],
        required_followups=required_followups,
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "resolved_law": readiness.evidence["resolved_law"],
            "basis": readiness.evidence["basis"],
            "has_history_followup": readiness.evidence["has_history_followup"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _loaded_before_after_amendment_delta_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="loaded_before_after_amendment_delta_answer_discipline",
        status="can_answer_with_loaded_sources",
        allowed_claims=[
            "The loaded before/after wording comparison can support the selected article's wording delta.",
            "The source before and after identities may be disclosed with their MST and effective-date metadata.",
            "The answer may describe only the loaded article changes, not an exhaustive law or bill summary.",
        ],
        forbidden_claims=[
            "The oldAndNew comparison proves legislative intent or policy purpose.",
            "The selected article diff proves every article changed by the bill.",
            "The before/after wording alone proves amendment reason or National Assembly deliberation history.",
            "The diff source replaces trace_law_history() when chronology, reason, or bill linkage matters.",
        ],
        required_disclosures=[
            "Disclose that the amendment-delta claim is limited to the selected article loaded from oldAndNew.",
            "Disclose when legislative intent, amendment reason, or full bill purpose still needs history or congress-db materials.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.interface == "trace_law_history"
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "law": readiness.evidence["law"],
            "before_mst": readiness.evidence["before_mst"],
            "after_mst": readiness.evidence["after_mst"],
            "changes": readiness.evidence["changes"],
            "reason_loaded": readiness.evidence["reason_loaded"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _historical_repealed_law_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="historical_repealed_law_answer_discipline",
        status="can_answer_with_loaded_sources",
        allowed_claims=[
            "The historical article text was loaded for the explicit reference date.",
            "The law-history packet preserved repeal/history status from the source row.",
            "The source can be discussed as historical legal context, not current-law authority.",
        ],
        forbidden_claims=[
            "The historical article is currently in force.",
            "Current effective search no-result proves the law never existed.",
            "Historical text can be cited without an as-of date.",
            "A repealed/historical source is current-law authority for today's answer.",
        ],
        required_disclosures=[
            "Disclose the historical as-of date before quoting or summarizing the article.",
            "Disclose the preserved repeal/history status separately from current-law analysis.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and not step.required_before_answer
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "as_of": readiness.evidence["as_of"],
            "article_effective_date": readiness.evidence["article_effective_date"],
            "history_statuses": readiness.evidence["history_statuses"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _nested_article_unit_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="nested_article_unit_answer_discipline",
        status="can_answer_with_loaded_sources",
        allowed_claims=[
            "The selected current article text was loaded with nested paragraph, subparagraph, and item units.",
            "Definitions and application-target analysis may use the loaded full ArticleText.text.",
            "Nested unit labels may be cited when they materially affect the legal requirement.",
        ],
        forbidden_claims=[
            "The article was reviewed from 조문제목 or top-level 조문내용 alone.",
            "Nested 호 or 목 can be omitted when the prompt asks for definitions or application targets.",
            "Missing nested units in a summary prove the source article has no exceptions, definitions, or requirements below the article heading.",
        ],
        required_disclosures=[
            "Cite the article and preserve nested 항, 호, or 목 labels when they carry the relevant definition or requirement.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and not step.required_before_answer
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "line_count": readiness.evidence["line_count"],
            "contains_terms": readiness.evidence["contains_terms"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _deleted_article_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="deleted_article_answer_discipline",
        status="can_answer_with_loaded_sources",
        allowed_claims=[
            "The selected current article was loaded and is marked deleted by the source.",
            "The deletion marker may be cited to explain that this article is not current operative text.",
            "Movement and change metadata may be disclosed as source metadata, not as prior wording.",
        ],
        forbidden_claims=[
            "The deleted article imposes a current duty, permission, sanction, or procedure.",
            "The deletion marker is substantive article content.",
            "The reason for deletion or prior wording is known before history or version comparison is loaded.",
        ],
        required_disclosures=[
            "Disclose that the article is marked deleted before discussing legal effect.",
            "Disclose the article effective date and movement metadata when using them.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and not step.required_before_answer
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "is_deleted": readiness.evidence["is_deleted"],
            "revision_type": readiness.evidence["revision_type"],
            "effective_date": readiness.evidence["effective_date"],
            "moved_from": readiness.evidence["moved_from"],
            "moved_to": readiness.evidence["moved_to"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _moved_article_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="moved_article_answer_discipline",
        status="can_answer_with_loaded_sources",
        allowed_claims=[
            f"The searched article is source-marked as moved to {readiness.evidence['moved_to']}.",
            f"The loaded destination article is {readiness.evidence['current_article']}.",
            "Current substance may be discussed only from the loaded destination article text.",
        ],
        forbidden_claims=[
            "The moved article marker imposes a current duty, permission, sanction, or procedure.",
            "The prior wording or movement reason is known before history or version comparison is loaded.",
        ],
        required_disclosures=[
            "Disclose that the searched article is a moved article marker.",
            "Disclose that current-substance claims are based on the loaded destination article.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and not step.required_before_answer
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "is_deleted": readiness.evidence["is_deleted"],
            "revision_type": readiness.evidence["revision_type"],
            "effective_date": readiness.evidence["effective_date"],
            "moved_from": readiness.evidence["moved_from"],
            "moved_to": readiness.evidence["moved_to"],
            "current_article": readiness.evidence["current_article"],
            "loaded_articles": readiness.evidence["loaded_articles"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _query_expansion_candidate_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="query_expansion_candidate_answer_discipline",
        status="must_load_more_sources",
        allowed_claims=[
            "Query expansion found planning candidate legal terms, related articles, and related laws for follow-up loading.",
            "The candidate law names and article anchors may be used to plan source loading.",
            "No final legal basis has been loaded yet.",
        ],
        forbidden_claims=[
            "Legal-term, related-law, or AI-search candidates are inspected legal authority.",
            "The current legal basis is established from expand_legal_query() output alone.",
            "A related article candidate proves the operative article text before get_article() loads it.",
        ],
        required_disclosures=[
            "Disclose that query expansion is planning context until selected source text is loaded.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and step.interface != "expand_legal_query"
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "citations_loaded": readiness.evidence["citations_loaded"],
            "follow_up_interfaces": readiness.evidence["follow_up_interfaces"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _law_search_candidate_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="law_search_candidate_answer_discipline",
        status="must_load_more_sources",
        allowed_claims=[
            "Law search found identity candidates with law ID, MST, and basis metadata.",
            "The identity candidate may be used to choose which law or article source text to load next.",
        ],
        forbidden_claims=[
            "The search result identity metadata is inspected law text.",
            "The current duty, sanction, procedure, or article wording is established from search_laws() output alone.",
            "A single law search hit can be cited as legal substance before selected source text is loaded.",
        ],
        required_disclosures=[
            "Disclose that search_laws() candidates require get_law() or get_article() source loading before substance claims.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and step.interface != "search_laws"
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "citations_loaded": readiness.evidence["citations_loaded"],
            "service_call_targets": readiness.evidence["service_call_targets"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _empty_law_search_absence_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="empty_law_search_absence_answer_discipline",
        status="must_load_more_sources",
        allowed_claims=[
            "The exact current-law search returned zero hits for the recorded query and basis.",
            "The zero hits may be disclosed only with the searched terms and scope.",
        ],
        forbidden_claims=[
            "No current legal basis exists.",
            "No related statute or legal source exists.",
            "The absence of search_laws() hits proves absence of current law.",
            "The legal issue has no statutory basis before alternate names, related terms, or bridge paths are checked.",
        ],
        required_disclosures=[
            "Disclose that zero hits came from one scoped law search, not an exhaustive statute search.",
            "Disclose unsearched alternate law names, related terms, historical/current-basis variants, or congress-db bridge paths.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and not (
                step.interface == "search_laws"
                and step.purpose.startswith("Run the initial")
            )
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "query": readiness.evidence["query"],
            "hit_count": readiness.evidence["hit_count"],
            "search_call_targets": readiness.evidence["search_call_targets"],
            "citations_loaded": readiness.evidence["citations_loaded"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _delegated_criteria_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="delegated_criteria_answer_discipline",
        status="must_load_more_sources",
        allowed_claims=[
            "The current statute article and delegation graph were loaded.",
            "Administrative-rule or annex/form hits remain candidates until selected bodies are loaded.",
        ],
        forbidden_claims=[
            "Administrative-rule operational criteria were inspected.",
            "Annex/form thresholds or criteria were inspected.",
        ],
        required_disclosures=[
            "The answer may cite loaded statute/delegation context only; operational criteria require follow-up loading.",
        ],
        required_followups=["get_administrative_rule", "get_annex_form_body"],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "risk_flags": readiness.risk_flags,
        },
    )


def _interpretation_authority_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="interpretation_authority_answer_discipline",
        status="can_answer_with_loaded_sources",
        allowed_claims=[
            "MOLEG official interpretations and ministry first-instance interpretations were found with distinct authority labels.",
            "source='all' means MOLEG plus the specified ministry, not a registry-wide ministry search.",
        ],
        forbidden_claims=[
            "The ministry first-instance interpretation is a MOLEG official interpretation.",
            "source='all' searched all ministry interpretation registries.",
            "Interpretation search metadata proves the substantive legal reasoning of the interpretation.",
            "MOLEG or ministry interpretations are court cases or Constitutional Court decisions.",
        ],
        required_disclosures=[
            "Disclose source_type/source_target/ministry labels when citing interpretation hits.",
            "Load selected interpretation detail before discussing the interpretation's legal substance.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and not step.required_before_answer
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "labels": readiness.evidence["labels"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _interpretation_search_candidate_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="interpretation_search_candidate_answer_discipline",
        status="must_load_more_sources",
        allowed_claims=[
            "Interpretation search found candidate interpretations with source authority metadata.",
            "The candidate interpretation identities may be used to choose which interpretation detail to load next.",
        ],
        forbidden_claims=[
            "The search metadata proves the interpretation's question, answer, or reason.",
            "The selected interpretation question, answer, reason, or related-law text was inspected.",
            "search_interpretations() output alone is enough to cite the interpretation's legal substance.",
        ],
        required_disclosures=[
            "Disclose that interpretation hits are candidate metadata until get_interpretation() loads selected detail.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and step.interface != "search_interpretations"
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "citations_loaded": readiness.evidence["citations_loaded"],
            "service_call_targets": readiness.evidence["service_call_targets"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _case_search_candidate_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="case_search_candidate_answer_discipline",
        status="must_load_more_sources",
        allowed_claims=[
            "Court-case search found candidate decisions with case number, court, and decision date metadata.",
            "The candidate case identities may be used to choose which case detail to load next.",
        ],
        forbidden_claims=[
            "The search metadata proves the judicial holding or case reasoning.",
            "The selected case full text, holdings, summary, or referenced statutes were inspected.",
            "search_cases() output alone is enough to cite the court's legal rule.",
        ],
        required_disclosures=[
            "Disclose that case hits are candidate metadata until get_case() loads selected detail.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and step.interface != "search_cases"
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "citations_loaded": readiness.evidence["citations_loaded"],
            "service_call_targets": readiness.evidence["service_call_targets"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _empty_case_search_absence_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="empty_case_search_absence_answer_discipline",
        status="must_load_more_sources",
        allowed_claims=[
            "The exact scoped court-case search returned zero hits.",
            "The zero hits may be disclosed only with the searched terms, court scope, and body/title scope.",
        ],
        forbidden_claims=[
            "No relevant precedent exists.",
            "No court case or judicial authority can matter.",
            "The absence of search_cases() hits proves absence of judicial reasoning.",
            "No legal risk exists because the case search returned zero hits.",
        ],
        required_disclosures=[
            "Disclose that zero hits came from one scoped case search, not an exhaustive precedent survey.",
            "Disclose unsearched alternate terms, court scopes, Constitutional Court decisions, and interpretation sources.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and not (
                step.interface == "search_cases"
                and step.purpose.startswith("Run the initial")
            )
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "query": readiness.evidence["query"],
            "court": readiness.evidence["court"],
            "search_body": readiness.evidence["search_body"],
            "hit_count": readiness.evidence["hit_count"],
            "search_call_targets": readiness.evidence["search_call_targets"],
            "citations_loaded": readiness.evidence["citations_loaded"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _empty_interpretation_search_absence_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="empty_interpretation_search_absence_answer_discipline",
        status="must_load_more_sources",
        allowed_claims=[
            "The exact scoped MOLEG official interpretation search returned zero hits.",
            "The zero-hit result may be disclosed only with the query terms and source scope.",
        ],
        forbidden_claims=[
            "No relevant interpretation exists.",
            "MOLEG or ministry interpretations cannot matter.",
            "The absence of search hits proves absence of authority.",
        ],
        required_disclosures=[
            "Disclose that zero hits came from one scoped search, not an exhaustive interpretation survey.",
            "Disclose any unsearched alternate terms, ministry interpretation sources, or neighboring authority families.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and not (
                step.interface == "search_interpretations"
                and step.purpose.startswith("Run the initial scoped")
            )
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "query": readiness.evidence["query"],
            "hit_count": readiness.evidence["hit_count"],
            "search_call_targets": readiness.evidence["search_call_targets"],
            "citations_loaded": readiness.evidence["citations_loaded"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _source_access_failure_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="source_access_failure_answer_discipline",
        status="must_load_more_sources",
        allowed_claims=[
            "The attempted MOLEG source access failed before legal candidates could be inspected.",
            "The source access failed state may be disclosed as a temporary access problem.",
        ],
        forbidden_claims=[
            "No current legal basis exists.",
            "law.go.kr has no result for the query.",
            "A rate limit, timeout, or retry exhaustion proves that the legal source is absent.",
            "Current law is absent because search_laws() did not return hits after a source-access failure.",
        ],
        required_disclosures=[
            "Disclose the source-access failure as distinct from a legal no-result state.",
            "Disclose that no citable MOLEG legal source was loaded.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and step.required_before_answer
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "error_type": readiness.evidence["error_type"],
            "hit_count": readiness.evidence["hit_count"],
            "source_calls": readiness.evidence["source_calls"],
            "citations_loaded": readiness.evidence["citations_loaded"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _constitutional_search_candidate_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="constitutional_search_candidate_answer_discipline",
        status="must_load_more_sources",
        allowed_claims=[
            "Constitutional Court search found candidate decisions with case number and final decision date metadata.",
            "The candidate decision identities may be used to choose which decision detail to load next.",
        ],
        forbidden_claims=[
            "The search metadata proves the constitutional holding or decision reasoning.",
            "The selected decision holdings, summary, reviewed statutes, referenced statutes, or full text were inspected.",
            "search_constitutional_decisions() output alone is enough to cite the Constitutional Court's legal rule.",
        ],
        required_disclosures=[
            "Disclose that Constitutional Court hits are candidate metadata until get_constitutional_decision() loads selected detail.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and step.interface != "search_constitutional_decisions"
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "citations_loaded": readiness.evidence["citations_loaded"],
            "service_call_targets": readiness.evidence["service_call_targets"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _empty_constitutional_search_absence_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="empty_constitutional_search_absence_answer_discipline",
        status="must_load_more_sources",
        allowed_claims=[
            "The exact scoped Constitutional Court free-text search returned zero hits.",
            "The zero hits may be disclosed only with the searched doctrine/statute terms and body/title scope.",
        ],
        forbidden_claims=[
            "No constitutional decision exists.",
            "No constitutional authority can matter.",
            "The absence of search_constitutional_decisions() hits proves absence of constitutional risk.",
            "There is no constitutional risk because the detc free-text search returned zero hits.",
        ],
        required_disclosures=[
            "Disclose that zero hits came from one scoped Constitutional Court search, not an exhaustive doctrine survey.",
            "Disclose unsearched alternate doctrine terms, reviewed-statute terms, ordinary court cases, and interpretation sources.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and not (
                step.interface == "search_constitutional_decisions"
                and step.purpose.startswith("Run the initial")
            )
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "query": readiness.evidence["query"],
            "search_body": readiness.evidence["search_body"],
            "hit_count": readiness.evidence["hit_count"],
            "search_call_targets": readiness.evidence["search_call_targets"],
            "citations_loaded": readiness.evidence["citations_loaded"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _authority_article_reference_mismatch_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="authority_article_reference_mismatch_answer_discipline",
        status="must_load_more_sources",
        allowed_claims=[
            "Loaded authority details were inspected and their structured article references do not match the target article.",
            "The mismatched referenced_articles and reviewed_articles may be used as follow-up search context.",
        ],
        forbidden_claims=[
            "A loaded interpretation, court case, or Constitutional Court decision is authority for the target article when its structured article references point to a different article.",
            "The loaded interpretation or court case can be cited for the target article without a referenced_articles match.",
            "The loaded Constitutional Court decision can be cited for the target article without a reviewed_articles match.",
            "No relevant authority exists for the target article because the loaded authority details point to different articles.",
        ],
        required_disclosures=[
            "Disclose that the loaded authority details' structured article references do not match the target article.",
            "Disclose that target-article authority requires matching referenced_articles or reviewed_articles, or additional source loading.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api"
            and (step.interface == "load_authority_context" or step.interface.startswith("search_"))
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "target_article": readiness.evidence["target_article"],
            "interpretation_referenced_articles": readiness.evidence[
                "interpretation_referenced_articles"
            ],
            "case_referenced_articles": readiness.evidence["case_referenced_articles"],
            "constitutional_reviewed_articles": readiness.evidence[
                "constitutional_reviewed_articles"
            ],
            "authority_article_matches": readiness.evidence["authority_article_matches"],
            "service_call_targets": readiness.evidence["service_call_targets"],
            "citations_loaded": readiness.evidence["citations_loaded"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _context_bundle_authority_article_mismatch_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="context_bundle_authority_article_mismatch_answer_discipline",
        status="must_load_more_sources",
        allowed_claims=[
            "The context bundle loaded the target article as current source text.",
            "The context bundle surfaced authority_article_mismatch gaps for eager-loaded authority details.",
            "Mismatched eager-loaded authority details may guide follow-up searches, not target-article citations.",
        ],
        forbidden_claims=[
            "The context bundle's eager-loaded interpretation, court case, or Constitutional Court detail is authority for the target article despite authority_article_mismatch gaps.",
            "A context bundle loaded detail can be cited as target article authority without referenced_articles or reviewed_articles matching the target article.",
            "The context bundle proved no target-article authority exists before follow-up searches.",
        ],
        required_disclosures=[
            "Disclose the authority_article_mismatch gap before discussing loaded authority detail.",
            "Disclose that only the target article text, not mismatched eager-loaded authority detail, is citable for the target article.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and step.interface != "load_legal_context_bundle"
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "target_article": readiness.evidence["target_article"],
            "authority_gap_interfaces": readiness.evidence["authority_gap_interfaces"],
            "authority_article_matches": readiness.evidence["authority_article_matches"],
            "gap_kinds": readiness.evidence["gap_kinds"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _context_bundle_authority_article_unverified_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="context_bundle_authority_article_unverified_answer_discipline",
        status="must_load_more_sources",
        allowed_claims=[
            "The context bundle loaded the target article as current source text.",
            "The context bundle surfaced authority_article_unverified gaps for eager-loaded authority details.",
            "Authority details with missing structured article references may guide follow-up searches, not target-article citations.",
        ],
        forbidden_claims=[
            "The context bundle's eager-loaded interpretation, court case, or Constitutional Court detail is authority for the target article despite authority_article_unverified gaps.",
            "Missing referenced_articles or reviewed_articles can be treated as an implicit match to the target article.",
            "The context bundle proved no target-article authority exists before follow-up searches.",
        ],
        required_disclosures=[
            "Disclose the authority_article_unverified gap before discussing loaded authority detail.",
            "Disclose that only the target article text, not unverified eager-loaded authority detail, is citable for the target article.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and step.interface != "load_legal_context_bundle"
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "target_article": readiness.evidence["target_article"],
            "authority_gap_interfaces": readiness.evidence["authority_gap_interfaces"],
            "authority_reference_counts": readiness.evidence["authority_reference_counts"],
            "gap_kinds": readiness.evidence["gap_kinds"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _context_bundle_authority_article_partial_match_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="context_bundle_authority_article_partial_match_answer_discipline",
        status="must_load_more_sources",
        allowed_claims=[
            "The context bundle loaded the requested articles as current source text.",
            "The context bundle surfaced authority_article_partial_match gaps for requested articles not matched by eager-loaded authority detail.",
            "Eager-loaded authority detail may support only the structured requested article it references and may guide follow-up searches for missing requested articles.",
        ],
        forbidden_claims=[
            "The context bundle's eager-loaded interpretation, court case, or Constitutional Court detail is authority for every requested article despite authority_article_partial_match gaps.",
            "Authority detail that references 개인정보 보호법 제17조 can be cited as authority for 개인정보 보호법 제15조 without follow-up loading.",
            "The context bundle proved no target-article authority exists for the missing requested article before follow-up searches.",
        ],
        required_disclosures=[
            "Disclose the authority_article_partial_match gap before discussing loaded authority detail.",
            "Disclose which requested article matched loaded authority detail and which requested article still needs follow-up authority search.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and step.interface != "load_legal_context_bundle"
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "target_articles": readiness.evidence["target_articles"],
            "authority_gap_interfaces": readiness.evidence["authority_gap_interfaces"],
            "authority_matched_articles": readiness.evidence["authority_matched_articles"],
            "missing_authority_article": readiness.evidence["missing_authority_article"],
            "gap_kinds": readiness.evidence["gap_kinds"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _context_bundle_authority_temporal_mismatch_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="context_bundle_authority_temporal_mismatch_answer_discipline",
        status="must_load_more_sources",
        allowed_claims=[
            "The context bundle loaded the target article as current source text.",
            "The eager-loaded authority details reference or review the target article.",
            "Older, date-unverified, or after-reference-date authority details may be described as follow-up context until the temporal gap is resolved.",
        ],
        forbidden_claims=[
            "Older, date-unverified, or after-reference-date eager-loaded interpretation, court case, or Constitutional Court detail is current target-article authority or as-of target-article authority merely because referenced_articles or reviewed_articles match.",
            "A matching referenced article proves the authority reflects the currently effective wording or reference-date wording.",
            "The context bundle resolved current legal meaning before trace_law_history or authority-date article text is checked.",
        ],
        required_disclosures=[
            "Disclose the authority_temporal_mismatch gap before discussing older, date-unverified, or after-reference-date authority detail.",
            "Disclose the target article's effective date, reference date when supplied, and authority dates before any current/as-of authority claim.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and step.interface != "load_legal_context_bundle"
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "target_article": readiness.evidence["target_article"],
            "authority_dates": readiness.evidence["authority_dates"],
            "authority_article_matches": readiness.evidence["authority_article_matches"],
            "authority_gap_interfaces": readiness.evidence["authority_gap_interfaces"],
            "authority_gap_queries": readiness.evidence["authority_gap_queries"],
            "gap_kinds": readiness.evidence["gap_kinds"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _annex_form_search_candidate_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="annex_form_search_candidate_answer_discipline",
        status="must_load_more_sources",
        allowed_claims=[
            "Annex/form search found candidate attachments with title, related source, and attachment-type metadata.",
            "The candidate attachment identities may be used to choose which annex/form body to load next.",
        ],
        forbidden_claims=[
            "The search metadata proves attached criteria, thresholds, amounts, or form contents.",
            "The selected annex/form body text or extracted rows were inspected.",
            "search_annex_forms() output alone is enough to cite attached criteria.",
        ],
        required_disclosures=[
            "Disclose that annex/form hits are candidate metadata until get_annex_form_body() loads selected body text.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and step.interface != "search_annex_forms"
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "citations_loaded": readiness.evidence["citations_loaded"],
            "text_call_targets": readiness.evidence["text_call_targets"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _empty_annex_form_search_absence_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="empty_annex_form_search_absence_answer_discipline",
        status="must_load_more_sources",
        allowed_claims=[
            "The exact annex/form search returned zero hits for the recorded query, source, type, and scope.",
            "The zero hits may be disclosed only with the searched terms and annex/form source scope.",
        ],
        forbidden_claims=[
            "No attached criteria exist.",
            "No annex, form, threshold table, amount criterion, or attached material exists.",
            "The absence of search_annex_forms() hits proves absence of attached criteria.",
            "The legal source has no attached operational criteria before source text, alternate annex/form terms, administrative-rule sources, or detail paths are checked.",
        ],
        required_disclosures=[
            "Disclose that zero hits came from one scoped annex/form search, not an exhaustive attached-material survey.",
            "Disclose unsearched source-law text, enforcement instruments, administrative-rule annexes, alternate titles, and form/annex type variants.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and not (
                step.interface == "search_annex_forms"
                and step.purpose.startswith("Run the initial")
            )
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "query": readiness.evidence["query"],
            "source": readiness.evidence["source"],
            "annex_type": readiness.evidence["annex_type"],
            "search_scope": readiness.evidence["search_scope"],
            "hit_count": readiness.evidence["hit_count"],
            "search_call_targets": readiness.evidence["search_call_targets"],
            "citations_loaded": readiness.evidence["citations_loaded"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _law_structure_hierarchy_candidate_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="law_structure_hierarchy_candidate_answer_discipline",
        status="must_load_more_sources",
        allowed_claims=[
            "The loaded law structure shows lower instruments in the statute hierarchy.",
            "The hierarchy node identities may be used to choose which delegation graph or lower-rule detail to load next.",
        ],
        forbidden_claims=[
            "The law structure proves article-level delegation from the selected statute article.",
            "The lower-rule body text or operational criteria were inspected.",
            "A hierarchy node alone proves which lower-rule article applies to the user's facts.",
        ],
        required_disclosures=[
            "Disclose that get_law_structure() is hierarchy context, not article-level delegation or lower-rule body text.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and step.interface != "get_law_structure"
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "instrument_names": readiness.evidence["instrument_names"],
            "service_call_targets": readiness.evidence["service_call_targets"],
            "article_level_delegation_targets": readiness.evidence[
                "article_level_delegation_targets"
            ],
            "risk_flags": readiness.risk_flags,
        },
    )


def _empty_delegation_graph_absence_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="empty_delegation_graph_absence_answer_discipline",
        status="must_load_more_sources",
        allowed_claims=[
            "The exact article-level delegation lookup returned zero rules for the recorded law and article.",
            "The zero rules may be disclosed only with the searched law/article scope and source family.",
        ],
        forbidden_claims=[
            "No delegated rule exists.",
            "No subordinate rule, notice, annex, or delegated criteria exists.",
            "The absence of find_delegated_rules() rules proves absence of delegated criteria.",
            "The statute contains no lower-rule path before law structure, alternate article scopes, administrative-rule sources, or annex/forms are checked.",
        ],
        required_disclosures=[
            "Disclose that zero rules came from one scoped delegation graph, not an exhaustive lower-source survey.",
            "Disclose unsearched law hierarchy, alternate article scopes, administrative-rule candidates, statute annexes, and administrative-rule annexes.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and not (
                step.interface == "find_delegated_rules"
                and step.purpose.startswith("Run the initial")
            )
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "law": readiness.evidence["law"],
            "article": readiness.evidence["article"],
            "rule_count": readiness.evidence["rule_count"],
            "service_call_targets": readiness.evidence["service_call_targets"],
            "lower_rule_detail_targets": readiness.evidence["lower_rule_detail_targets"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _administrative_rule_search_candidate_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="administrative_rule_search_candidate_answer_discipline",
        status="must_load_more_sources",
        allowed_claims=[
            "Administrative-rule search found candidate rules with identity and date metadata.",
            "The candidate administrative-rule identities may be used to choose which rule detail to load next.",
        ],
        forbidden_claims=[
            "The search metadata proves operational criteria, article text, or supplementary provisions.",
            "The selected administrative-rule body text or articles were inspected.",
            "search_administrative_rules() output alone is enough to cite current operational criteria.",
        ],
        required_disclosures=[
            "Disclose that administrative-rule hits are candidate metadata until get_administrative_rule() loads selected detail.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and step.interface != "search_administrative_rules"
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "citations_loaded": readiness.evidence["citations_loaded"],
            "service_call_targets": readiness.evidence["service_call_targets"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _administrative_rule_issued_on_not_effective_as_of_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="administrative_rule_issued_on_not_effective_as_of_answer_discipline",
        status="must_load_more_sources",
        allowed_claims=[
            "The administrative-rule search used an issued_on 발령일자 filter and found candidate metadata.",
            "The candidate metadata may disclose distinct issuing_date and effective_date fields.",
            "Current operational status remains unresolved until selected detail is loaded and effective_date is compared to the reference date.",
        ],
        forbidden_claims=[
            "issued_on proves the rule was effective as of the reference date.",
            "The administrative-rule search hit states current operational criteria.",
            "A current_status field in search metadata is enough to answer current operational effect on the reference date.",
        ],
        required_disclosures=[
            "Disclose that issued_on is a 발령일자 filter, not an effective-date as-of lookup.",
            "Disclose the candidate issuing_date and effective_date before making current-operational claims.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and not (
                step.interface == "search_administrative_rules"
                and step.purpose.startswith("Use administrative-rule search")
            )
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "reference_date": readiness.evidence["reference_date"],
            "candidate": readiness.evidence["candidate"],
            "search_call_params": readiness.evidence["search_call_params"],
            "service_call_targets": readiness.evidence["service_call_targets"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _administrative_rule_article_status_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="administrative_rule_article_status_answer_discipline",
        status="can_answer_with_loaded_sources",
        allowed_claims=[
            "The selected administrative-rule detail was loaded and one article is a deleted administrative-rule article.",
            f"The selected administrative-rule detail marks one article as moved to {readiness.evidence['moved_to']}.",
            f"The loaded destination administrative-rule article is {readiness.evidence['current_article']}.",
            "Current operational criteria may be discussed only from the loaded destination administrative-rule article text.",
        ],
        forbidden_claims=[
            "The deleted administrative-rule article states current operational criteria.",
            "The moved administrative-rule article marker states current operational criteria.",
            "The prior wording or movement reason is known before history or comparison context is loaded.",
        ],
        required_disclosures=[
            "Disclose administrative-rule article status before discussing current operational criteria.",
            "Disclose that current operational criteria are based on the loaded destination administrative-rule article.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and not step.required_before_answer
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "administrative_rule": readiness.evidence["administrative_rule"],
            "effective_date": readiness.evidence["effective_date"],
            "article_statuses": readiness.evidence["article_statuses"],
            "deleted_article": readiness.evidence["deleted_article"],
            "moved_article": readiness.evidence["moved_article"],
            "moved_to": readiness.evidence["moved_to"],
            "current_article": readiness.evidence["current_article"],
            "loaded_articles": readiness.evidence["loaded_articles"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _administrative_rule_supplementary_transition_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="administrative_rule_supplementary_transition_answer_discipline",
        status="can_answer_with_loaded_sources",
        allowed_claims=[
            "The selected administrative-rule article and administrative-rule supplementary provisions were both loaded.",
            "Enforcement-date or transitional-application claims may be made only from the loaded administrative-rule supplementary provisions.",
            "The loaded administrative-rule effective_date can be disclosed as metadata, not as a substitute for 부칙 analysis.",
        ],
        forbidden_claims=[
            "The administrative-rule article alone proves whether pending procedures are covered.",
            "The administrative-rule effective_date metadata fully answers 시행일, 적용례, or 경과조치.",
            "No administrative-rule 경과조치 exists without inspecting loaded supplementary provisions.",
            "Administrative-rule supplementary provisions can be merged into the article citation without separate labeling.",
        ],
        required_disclosures=[
            "Cite administrative-rule supplementary provisions separately when discussing 시행일, 적용례, or 경과조치.",
            "Disclose when a transition question may still require source-law or rule history/diff for the specific amendment event.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and not step.required_before_answer
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "administrative_rule_effective_date": readiness.evidence[
                "administrative_rule_effective_date"
            ],
            "supplementary_provision_count": readiness.evidence[
                "supplementary_provision_count"
            ],
            "supplementary_text_contains_transition": readiness.evidence[
                "supplementary_text_contains_transition"
            ],
            "risk_flags": readiness.risk_flags,
        },
    )


def _empty_administrative_rule_search_absence_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="empty_administrative_rule_search_absence_answer_discipline",
        status="must_load_more_sources",
        allowed_claims=[
            "The exact administrative-rule search returned zero hits for the recorded query and filters.",
            "The zero hits may be disclosed only with the searched terms, source family, and filters.",
        ],
        forbidden_claims=[
            "No delegated operational criteria exist.",
            "No subordinate rule, notice, annex, or administrative rule exists.",
            "The absence of search_administrative_rules() hits proves absence of delegated criteria.",
            "The statute contains no practical execution criteria before delegation, structure, alternate rule names, or annex/forms are checked.",
        ],
        required_disclosures=[
            "Disclose that zero hits came from one scoped administrative-rule search, not an exhaustive subordinate-source survey.",
            "Disclose unsearched delegation paths, enforcement instruments, ministry scopes, alternate rule names, administrative-rule annexes, or statute annex/forms.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and not (
                step.interface == "search_administrative_rules"
                and step.purpose.startswith("Run the initial")
            )
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "query": readiness.evidence["query"],
            "hit_count": readiness.evidence["hit_count"],
            "search_call_targets": readiness.evidence["search_call_targets"],
            "citations_loaded": readiness.evidence["citations_loaded"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _administrative_rule_missing_source_reference_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="administrative_rule_missing_source_reference_answer_discipline",
        status="must_load_more_sources",
        allowed_claims=[
            "The administrative-rule detail was loaded and may be cited as administrative-rule text.",
            "MOLEG did not expose source-law/source-article back-reference metadata in this payload.",
            "The absence of back-reference metadata is an unknown source state, not proof that no authorizing basis exists.",
        ],
        forbidden_claims=[
            "The administrative rule has no legal basis because source_law_name is None.",
            "The administrative rule is invalid because source_article is None.",
            "Missing source-law/source-article metadata proves there is no delegation.",
        ],
        required_disclosures=[
            "Disclose that source-law/source-article metadata was not exposed by this MOLEG payload.",
            "Separate loaded administrative-rule text from any claim about authorization, delegation absence, or invalidity.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and step.interface != "get_administrative_rule"
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "source_law_name": readiness.evidence["source_law_name"],
            "source_article": readiness.evidence["source_article"],
            "service_call_targets": readiness.evidence["service_call_targets"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _comparable_mechanism_candidate_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="comparable_mechanism_candidate_answer_discipline",
        status="must_load_more_sources",
        allowed_claims=[
            "Comparable-mechanism discovery found planning candidates with law and article-anchor metadata.",
            "The candidate identities may be used to choose which comparable articles to load next.",
        ],
        forbidden_claims=[
            "The candidate metadata proves the mechanisms are legally equivalent.",
            "The selected comparable article text or legal structure was inspected.",
            "find_comparable_mechanisms() output alone proves a design is suitable for a new bill.",
        ],
        required_disclosures=[
            "Disclose that comparable-mechanism candidates require get_article() source loading before comparison claims.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and step.interface != "find_comparable_mechanisms"
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "citations_loaded": readiness.evidence["citations_loaded"],
            "article_service_targets": readiness.evidence["article_service_targets"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _delegated_criteria_after_followups_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="delegated_criteria_after_followups_answer_discipline",
        status="can_answer_with_loaded_sources",
        allowed_claims=[
            "The current statute article, delegation graph, selected administrative-rule body, and selected annex/form body were loaded.",
            "Operational criteria may be discussed only from the loaded administrative-rule and annex/form text.",
        ],
        forbidden_claims=[
            "All lower-level enforcement criteria for the statute were exhaustively inspected.",
            "Latest enforcement practice, statistics, or policy context were inspected through MOLEG.",
        ],
        required_disclosures=[
            "The answer is limited to the selected loaded administrative-rule and annex/form sources.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "websearch" or not step.required_before_answer
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "structured_annex_rows": readiness.evidence["structured_annex_rows"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _delegated_criteria_source_mismatch_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="delegated_criteria_source_mismatch_answer_discipline",
        status="must_load_more_sources",
        allowed_claims=[
            "The current statute article and delegation graph were loaded.",
            "The mismatched administrative-rule detail may be used only as follow-up context.",
        ],
        forbidden_claims=[
            "The loaded administrative-rule body is operational criteria for the target article despite delegated_criteria_source_mismatch.",
            "The loaded annex/form body proves target-article criteria when its related administrative rule has a source mismatch.",
            "A loaded administrative-rule detail can be cited as target delegated criteria without matching source_law_name/source_article.",
        ],
        required_disclosures=[
            "Disclose the delegated_criteria_source_mismatch gap before discussing the loaded administrative-rule detail.",
            "Disclose the target article and the loaded administrative rule's source article before any operational-criteria claim.",
        ],
        required_followups=[
            "find_delegated_rules",
            "search_administrative_rules",
            "get_administrative_rule",
            "get_annex_form_body",
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "target_articles": readiness.evidence["target_articles"],
            "loaded_source_articles": readiness.evidence["loaded_source_articles"],
            "gap_kinds": readiness.evidence["gap_kinds"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _low_confidence_annex_body_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="low_confidence_annex_body_answer_discipline",
        status="can_answer_with_loaded_sources",
        allowed_claims=[
            "The selected annex body text was loaded and may be cited as plain text.",
            "The structured table extraction is low-confidence and has no reliable rows.",
            "Manual table inspection or cautious plain-text reading is required before exact threshold extraction.",
        ],
        forbidden_claims=[
            "The empty structured rows prove there are no annex criteria.",
            "The extracted structured table reliably contains all monetary thresholds.",
            "Numeric criteria were safely extracted from structured rows despite low parsing confidence.",
            "Annex metadata alone proves the attached criteria.",
        ],
        required_disclosures=[
            "Disclose the low parsing confidence before presenting any table-like extraction.",
            "Separate loaded plain text from machine-structured rows.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and not step.required_before_answer
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "extraction_confidence": readiness.evidence["extraction_confidence"],
            "parsing_confidence": readiness.evidence["parsing_confidence"],
            "structured_rows": readiness.evidence["structured_rows"],
            "structured_notes": readiness.evidence["structured_notes"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _future_effective_promulgated_law_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="future_effective_promulgated_law_answer_discipline",
        status="can_answer_with_loaded_sources",
        allowed_claims=[
            "The bill has a promulgation bridge to a MOLEG law identity.",
            "The loaded law is not effective as of the reference date.",
        ],
        forbidden_claims=[
            "The promulgated law is currently in force as of the reference date.",
            "Promulgation date alone proves current-force status.",
        ],
        required_disclosures=[
            "Disclose both the reference date and the future effective date before discussing current force.",
        ],
        required_followups=[],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "as_of": readiness.evidence["as_of"],
            "effective_date": readiness.evidence["effective_date"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _future_effective_administrative_rule_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="future_effective_administrative_rule_answer_discipline",
        status="can_answer_with_loaded_sources",
        allowed_claims=[
            "The current statute article and delegation graph were loaded.",
            "The selected administrative-rule body was loaded but is not effective as of the reference date.",
        ],
        forbidden_claims=[
            "The selected administrative rule states current operational criteria as of the reference date.",
            "Loaded administrative-rule text can be treated as current solely because it was returned by MOLEG.",
        ],
        required_disclosures=[
            "Disclose both the reference date and the administrative-rule future effective date before discussing current operational criteria.",
        ],
        required_followups=["search_administrative_rules", "get_administrative_rule"],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "as_of": readiness.evidence["as_of"],
            "administrative_rule_effective_date": readiness.evidence["administrative_rule_effective_date"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _comparative_design_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="comparative_design_answer_discipline",
        status="can_answer_with_loaded_sources",
        allowed_claims=[
            "A selected comparable article was loaded and can be cited as source context.",
            "Comparable-mechanism discovery can guide further legislative-design review.",
        ],
        forbidden_claims=[
            "The candidate mechanisms are legally equivalent.",
            "The loaded article alone proves the design is appropriate for a new bill.",
        ],
        required_disclosures=[
            "Comparable-mechanism candidates are planning context, not legal equivalence findings.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and not step.required_before_answer
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "risk_flags": readiness.risk_flags,
        },
    )


def _context_bundle_authority_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="context_bundle_authority_answer_discipline",
        status="must_load_more_sources",
        allowed_claims=[
            "Loaded authority details from the context bundle can be cited as bounded source context.",
            "The bundle preserves candidates, gaps, and risk flags that guide further authority loading.",
        ],
        forbidden_claims=[
            "The context bundle completed an exhaustive authority survey.",
            "No further interpretation, case, Constitutional Court, administrative-rule, or annex/form source can matter.",
            "Eager-loaded authority details prove the absence of contrary authority.",
        ],
        required_disclosures=[
            "Disclose that load_legal_context_bundle() is a bounded first pass, not an exhaustive authority survey.",
            "Disclose that additional detail loading is required before making coverage or absence-of-authority claims.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and step.interface != "load_legal_context_bundle"
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "loaded_authority_detail_types": readiness.evidence["loaded_authority_detail_types"],
            "candidate_types": readiness.evidence["candidate_types"],
            "deferred_interfaces": readiness.evidence["deferred_interfaces"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _institutional_system_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="institutional_system_answer_discipline",
        status="can_answer_with_loaded_sources",
        allowed_claims=[
            "The explicitly selected statute set was loaded as one institutional-system bundle.",
            "Loaded law text, law structures, and delegation graphs can be cited for the selected statutes.",
        ],
        forbidden_claims=[
            "The loaded statute set is an exhaustive list of every law in the institution.",
            "MOLEG-API decided which statute is primary for the institution.",
            "Omitted statutes are irrelevant without a separate discovery step.",
        ],
        required_disclosures=[
            "Disclose that load_institutional_system() composes an explicit statute set selected before the call.",
            "Disclose any additional statute-discovery step separately before claiming coverage of the wider institution.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and not step.required_before_answer
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "request_statute_ids": readiness.evidence["request_statute_ids"],
            "loaded_laws": readiness.evidence["loaded_laws"],
            "law_structures": readiness.evidence["law_structures"],
            "delegation_graphs": readiness.evidence["delegation_graphs"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _constitutional_risk_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="constitutional_risk_answer_discipline",
        status="can_answer_with_loaded_sources",
        allowed_claims=[
            "Loaded Constitutional Court decisions can be cited with their reviewed article references.",
            "Deferred Constitutional Court decision candidates remain unreviewed until detail is loaded.",
        ],
        forbidden_claims=[
            "The Constitutional Court doctrine search was exhaustive.",
            "No constitutional risk exists solely because the loaded detc decisions do not find one.",
            "The detc source provides a structured doctrine index for proportionality or equality review.",
        ],
        required_disclosures=[
            "Disclose that doctrine terms were used as free-text search terms, not source-backed filters.",
            "Disclose deferred Constitutional Court candidates before claiming coverage limits.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and not step.required_before_answer
        ]
        + ["get_constitutional_decision"],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "loaded_constitutional_decisions": readiness.evidence["loaded_constitutional_decisions"],
            "deferred_constitutional_decisions": readiness.evidence["deferred_constitutional_decisions"],
            "reviewed_articles": readiness.evidence["reviewed_articles"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _latest_social_context_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    required_followups = [
        f"{step.source}.{step.interface}"
        for step in prompt.planned_steps
        if step.source == "websearch"
    ]
    return AnswerDisciplineReport(
        scenario="latest_social_context_answer_discipline",
        status="must_load_more_sources",
        allowed_claims=[
            "The current statute article was loaded and may be cited as legal text.",
            "MOLEG-API can answer only the enacted-law part of the prompt before WebSearch runs.",
            "The latest statistics, news, announcements, or social context remain unanswered until WebSearch sources are loaded.",
        ],
        forbidden_claims=[
            "MOLEG-API loaded the latest 피해 통계 or current social facts.",
            "The MOLEG legal citation proves the latest statistics or news context.",
            "The final answer can combine legal text and latest social facts without separate WebSearch citations.",
            "A law.go.kr source gap means there are no recent statistics or announcements.",
        ],
        required_disclosures=[
            "Separate MOLEG legal-source citations from WebSearch social-fact citations.",
            "Disclose that latest social facts have not been loaded when only the MOLEG packet is available.",
        ],
        required_followups=required_followups,
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "follow_up_interfaces": readiness.evidence["follow_up_interfaces"],
            "social_fact_sources_loaded": readiness.evidence["social_fact_sources_loaded"],
            "risk_flags": readiness.risk_flags,
        },
    )


def _supplementary_transition_discipline(
    prompt: PromptDryRunReport,
    readiness: LegislativeExpertScenarioReport,
) -> AnswerDisciplineReport:
    return AnswerDisciplineReport(
        scenario="supplementary_transition_answer_discipline",
        status="can_answer_with_loaded_sources",
        allowed_claims=[
            "The main statute article and supplementary provisions were both loaded.",
            "Enforcement-date or transitional-application claims may be made only from the loaded supplementary-provision text.",
            "The loaded law effective date can be disclosed as metadata, not as a substitute for 부칙 analysis.",
        ],
        forbidden_claims=[
            "The main article alone proves whether existing contracts are covered.",
            "The law effective_date metadata fully answers 시행일, 적용례, or 경과조치.",
            "No 경과조치 exists without inspecting loaded supplementary provisions.",
            "Supplementary provisions can be merged into the main article citation without separate labeling.",
        ],
        required_disclosures=[
            "Cite supplementary provisions separately from main articles when discussing 시행일, 적용례, or 경과조치.",
            "Disclose when a transition question may still require history/diff for the specific amendment event.",
        ],
        required_followups=[
            step.interface
            for step in prompt.planned_steps
            if step.source == "moleg-api" and not step.required_before_answer
        ],
        citations=readiness.citations,
        evidence={
            "prompt_status": prompt.status,
            "readiness_status": readiness.status,
            "law_effective_date": readiness.evidence["law_effective_date"],
            "supplementary_provision_count": readiness.evidence["supplementary_provision_count"],
            "supplementary_text_contains_transition": readiness.evidence[
                "supplementary_text_contains_transition"
            ],
            "risk_flags": readiness.risk_flags,
        },
    )


def _validate_answer_discipline(reports: list[AnswerDisciplineReport]) -> None:
    for report in reports:
        if not report.allowed_claims:
            raise AssertionError(f"{report.scenario} has no allowed claims")
        if not report.forbidden_claims:
            raise AssertionError(f"{report.scenario} has no forbidden claims")
        if report.status != "can_answer_with_loaded_sources" and not report.required_followups:
            raise AssertionError(f"{report.scenario} needs follow-up sources")


def main() -> None:
    print(
        json.dumps(
            [report.to_dict() for report in run_legislative_expert_answer_discipline()],
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
