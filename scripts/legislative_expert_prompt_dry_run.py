"""Prompt-level dry-run plans for the future legislative-expert skill.

This harness does not reason about law. It checks the step before reasoning:
given a realistic user prompt, the skill should choose public MOLEG-API
interfaces, preserve source responsibilities, and block dangerous shortcuts.
"""

from __future__ import annotations

import inspect
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from moleg_api import MolegApi


DryRunStatus = Literal[
    "moleg_ready",
    "needs_congress_db_first",
    "needs_more_source_loading",
    "requires_websearch_handoff",
]

StepSource = Literal["moleg-api", "congress-db", "websearch"]

RAW_MOLEG_TARGETS = {
    "law",
    "eflaw",
    "lawjosub",
    "eflawjosub",
    "lsDelegated",
    "lsStmd",
    "admrul",
    "licbyl",
    "admbyl",
    "expc",
    "prec",
    "detc",
    "lstrmAI",
    "dlytrm",
    "aiSearch",
    "aiRltLs",
}


@dataclass(frozen=True)
class PromptWorkflowStep:
    """One planned tool call or non-MOLEG handoff before legal reasoning."""

    source: StepSource
    interface: str
    purpose: str
    required_before_answer: bool = True


@dataclass(frozen=True)
class PromptDryRunReport:
    """A deterministic prompt-to-workflow dry-run report."""

    scenario: str
    prompt: str
    status: DryRunStatus
    planned_steps: list[PromptWorkflowStep]
    guardrails: list[str] = field(default_factory=list)
    forbidden_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def run_legislative_expert_prompt_dry_run() -> list[PromptDryRunReport]:
    """Return prompt-level dry-run plans for representative skill prompts."""

    reports = [
        PromptDryRunReport(
            scenario="current_article_review",
            prompt="개인정보 보호법 제15조의 현재 수집 동의 요건과 관련 해석례를 검토해줘.",
            status="moleg_ready",
            planned_steps=[
                PromptWorkflowStep("moleg-api", "search_laws", "Resolve the current effective statute identity."),
                PromptWorkflowStep("moleg-api", "get_article", "Load the selected current article text before citing it."),
                PromptWorkflowStep("moleg-api", "find_delegated_rules", "Check whether operative criteria are delegated."),
                PromptWorkflowStep("moleg-api", "search_interpretations", "Find official/ministry interpretation candidates."),
                PromptWorkflowStep("moleg-api", "search_cases", "Find judicial application context."),
                PromptWorkflowStep("moleg-api", "search_constitutional_decisions", "Find constitutional-risk candidates when rights limits may matter.", False),
            ],
            guardrails=[
                "Default to effective-date law text for current-law prompts.",
                "Preserve MOLEG interpretation, ministry interpretation, court case, and Constitutional Court labels separately.",
            ],
            forbidden_actions=[
                "Do not cite query-expansion candidates as final authority.",
                "Do not use source endpoint names in the skill-facing plan.",
            ],
        ),
        PromptDryRunReport(
            scenario="nested_article_unit_review",
            prompt="자동차관리법 제2조 정의에서 각 호와 목까지 포함해 적용대상을 검토해줘.",
            status="moleg_ready",
            planned_steps=[
                PromptWorkflowStep("moleg-api", "search_laws", "Resolve the current effective statute identity."),
                PromptWorkflowStep("moleg-api", "get_article", "Load the selected article with nested paragraph/subparagraph/item text."),
                PromptWorkflowStep("moleg-api", "search_interpretations", "Check interpretation constraints for the defined terms.", False),
            ],
            guardrails=[
                "Article text must preserve 항, 호, and 목 units when the source provides them separately.",
                "Definitions, exceptions, and legal requirements often live below the article heading or first sentence.",
            ],
            forbidden_actions=[
                "Do not summarize the article from 조문제목 or top-level 조문내용 alone.",
                "Do not omit nested 호 or 목 when the prompt asks for 적용대상 or definitions.",
            ],
        ),
        PromptDryRunReport(
            scenario="deleted_article_current_force_review",
            prompt="현행 자동차관리법 제8조가 삭제된 조문인지, 아직 의무가 남아 있는지 확인해줘.",
            status="moleg_ready",
            planned_steps=[
                PromptWorkflowStep("moleg-api", "search_laws", "Resolve the current effective statute identity."),
                PromptWorkflowStep("moleg-api", "get_article", "Load the selected current article and inspect article status fields."),
                PromptWorkflowStep("moleg-api", "trace_law_history", "Trace why or when the article was deleted if the user asks for amendment context.", False),
            ],
            guardrails=[
                "A source article marked deleted is current source context, not an operative legal requirement.",
                "Article status fields must be checked before treating a loaded article as current substantive text.",
            ],
            forbidden_actions=[
                "Do not cite a deleted article as a current duty or permission.",
                "Do not treat a deletion marker such as '제8조 삭제' as substantive article content.",
            ],
        ),
        PromptDryRunReport(
            scenario="moved_article_current_force_review",
            prompt="현행 자동차관리법 제8조가 제12조로 이동했다면 지금 의무 내용도 제8조 기준으로 설명해줘.",
            status="needs_more_source_loading",
            planned_steps=[
                PromptWorkflowStep("moleg-api", "search_laws", "Resolve the current effective statute identity."),
                PromptWorkflowStep("moleg-api", "load_article_context", "Load the searched article and follow moved_to to the destination article before citing current substantive text."),
                PromptWorkflowStep("moleg-api", "trace_law_history", "Trace the movement event or prior wording if the user asks why the article moved.", False),
            ],
            guardrails=[
                "A source article moved to another article is movement source state; current duties require the loaded current_article from load_article_context.",
                "Movement metadata can identify the destination article, but the movement marker itself is not operative text.",
            ],
            forbidden_actions=[
                "Do not cite the moved article marker as current duty, permission, sanction, or procedure.",
                "Do not describe destination article substance unless load_article_context.current_article is loaded.",
                "Do not infer prior wording or movement reason before history or comparison is loaded.",
            ],
        ),
        PromptDryRunReport(
            scenario="query_expansion_candidate_authority_review",
            prompt="자동차 방치 문제 관련 법령용어와 연관법령 검색 결과만 보고 현행 근거를 정리해줘.",
            status="needs_more_source_loading",
            planned_steps=[
                PromptWorkflowStep("moleg-api", "expand_legal_query", "Discover legal terms, related laws, related articles, and follow-up searches."),
                PromptWorkflowStep("moleg-api", "search_laws", "Resolve a selected candidate into a current effective law identity."),
                PromptWorkflowStep("moleg-api", "get_article", "Load selected current article text before citing a legal basis."),
            ],
            guardrails=[
                "Query expansion is planning context, not final legal authority.",
                "Legal terms, AI search rows, and related-law candidates need source loading before legal claims.",
            ],
            forbidden_actions=[
                "Do not cite legal-term, related-law, or AI-search candidates as inspected source text.",
                "Do not answer the current legal basis from expand_legal_query() output alone.",
            ],
        ),
        PromptDryRunReport(
            scenario="law_search_candidate_detail_review",
            prompt="자동차관리법 검색 결과만 보고 현행 제재 조항과 의무 내용을 설명해줘.",
            status="needs_more_source_loading",
            planned_steps=[
                PromptWorkflowStep("moleg-api", "search_laws", "Find current effective law identity candidates."),
                PromptWorkflowStep("moleg-api", "get_article", "Load selected current article text before citing duties, sanctions, or procedures."),
                PromptWorkflowStep("moleg-api", "find_delegated_rules", "Check whether detailed criteria are delegated after the article is loaded.", False),
            ],
            guardrails=[
                "Law search results are identity candidates, not inspected source text.",
                "A law name, law ID, MST, or effective-basis hit does not prove article content or current duty language.",
            ],
            forbidden_actions=[
                "Do not state current duty, sanction, procedure, or article text from search_laws() output alone.",
                "Do not treat a single search hit as citable legal substance before get_law() or get_article() loads source text.",
            ],
        ),
        PromptDryRunReport(
            scenario="empty_law_search_absence_review",
            prompt="법령 검색 결과가 0건이면 현행 법적 근거가 없다고 답해줘.",
            status="needs_more_source_loading",
            planned_steps=[
                PromptWorkflowStep(
                    "moleg-api",
                    "search_laws",
                    "Run the initial current-law search and preserve the exact query and effective-date basis.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "expand_legal_query",
                    "Find alternate law names, legal terms, related-law candidates, and follow-up searches before absence claims.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "search_laws",
                    "Retry with alternate law names, legal terms, or bridge-derived names before any no-current-law claim.",
                ),
            ],
            guardrails=[
                "An empty result from one scoped law search is not proof that no current law or legal basis exists.",
                "Any no-current-law claim must disclose searched terms, basis, and unsearched alternate names or bridge paths.",
            ],
            forbidden_actions=[
                "Do not say No current legal basis exists from one empty search_laws() result.",
                "Do not treat zero hits as proof that no current statute, related law, or promulgated bridge source exists.",
            ],
        ),
        PromptDryRunReport(
            scenario="mixed_interpretation_authority_review",
            prompt="법제처 해석과 방위사업청 1차 해석이 함께 검색될 때 둘을 같은 권위로 봐도 되는지 구분해줘.",
            status="moleg_ready",
            planned_steps=[
                PromptWorkflowStep("moleg-api", "search_interpretations", "Search MOLEG official interpretations plus one specified ministry source."),
                PromptWorkflowStep("moleg-api", "get_interpretation", "Load selected interpretation detail before discussing legal substance.", False),
            ],
            guardrails=[
                "MOLEG official interpretations and ministry first-instance interpretations must keep distinct authority labels.",
                "source='all' means MOLEG plus one specified ministry, not every ministry.",
                "Interpretation search metadata is enough to label authority but not enough to discuss the substance of an interpretation.",
            ],
            forbidden_actions=[
                "Do not describe a ministry first-instance interpretation as a MOLEG official interpretation.",
                "Do not describe source='all' as all ministries.",
                "Do not treat interpretations as court cases or Constitutional Court decisions.",
            ],
        ),
        PromptDryRunReport(
            scenario="interpretation_search_candidate_detail_review",
            prompt="법령해석례 검색 결과만 보고 질의요지, 회답, 이유를 정리해줘.",
            status="needs_more_source_loading",
            planned_steps=[
                PromptWorkflowStep("moleg-api", "search_interpretations", "Find interpretation candidates and preserve authority metadata."),
                PromptWorkflowStep("moleg-api", "get_interpretation", "Load selected interpretation detail before citing question, answer, reason, or related laws."),
                PromptWorkflowStep("moleg-api", "get_article", "Load referenced statute article text when the interpretation turns on a specific provision.", False),
            ],
            guardrails=[
                "Interpretation search hits are candidate metadata until selected interpretation detail is loaded.",
                "Interpretation substance claims require get_interpretation() detail, not search result identity fields.",
            ],
            forbidden_actions=[
                "Do not state the interpretation's question, answer, or reason from search_interpretations() output alone.",
                "Do not cite question, answer, reason, or related-law analysis before get_interpretation() loads the selected interpretation.",
            ],
        ),
        PromptDryRunReport(
            scenario="empty_interpretation_search_absence_review",
            prompt="법제처 해석례 검색 결과가 없으면 관련 해석례가 없다고 답해줘.",
            status="needs_more_source_loading",
            planned_steps=[
                PromptWorkflowStep(
                    "moleg-api",
                    "search_interpretations",
                    "Run the initial scoped interpretation search and preserve the exact query/source scope.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "expand_legal_query",
                    "Find alternate legal terms and related law/article context before making an absence claim.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "search_interpretations",
                    "Retry interpretation search with alternate terms, source scope, or ministry coverage before any no-interpretation claim.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "search_cases",
                    "Check judicial authorities separately if the legal issue may be answered by cases rather than interpretations.",
                    False,
                ),
            ],
            guardrails=[
                "An empty scoped interpretation search is a query/source result, not proof that no relevant interpretation exists.",
                "Any no-authority claim must disclose search terms, source scope, and unsearched authority families.",
            ],
            forbidden_actions=[
                "Do not say no relevant interpretation exists from one empty search_interpretations() result.",
                "Do not treat zero hits as proof that MOLEG or ministry interpretations cannot matter.",
            ],
        ),
        PromptDryRunReport(
            scenario="source_access_failure_absence_review",
            prompt="law.go.kr가 rate limit이면 자료가 없는 걸로 보고 현행 근거가 없다고 답해줘.",
            status="needs_more_source_loading",
            planned_steps=[
                PromptWorkflowStep(
                    "moleg-api",
                    "search_laws",
                    "Attempt to load current effective law candidates and preserve any source-access error separately from no-result state.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "search_laws",
                    "Retry after source-access recovery or backoff before any no-current-law or no-source claim.",
                ),
            ],
            guardrails=[
                "A source-access problem is not a legal no-result state.",
                "RateLimitError and RetryExhaustedError require retry, deferral, or disclosure before legal absence claims.",
            ],
            forbidden_actions=[
                "Do not say no current legal basis exists because a rate limit, timeout, or retry exhaustion occurred.",
                "Do not convert a source-access failure into a zero-hit law search result.",
            ],
        ),
        PromptDryRunReport(
            scenario="case_search_candidate_detail_review",
            prompt="과징금 부과처분 판례 검색 결과만 보고 법원이 어떤 기준을 세웠는지 정리해줘.",
            status="needs_more_source_loading",
            planned_steps=[
                PromptWorkflowStep("moleg-api", "search_cases", "Find court-case candidates and preserve decision metadata."),
                PromptWorkflowStep("moleg-api", "get_case", "Load selected case detail before citing holdings, summary, referenced statutes, or full text."),
                PromptWorkflowStep("moleg-api", "get_article", "Load referenced statute article text when the case rule turns on a specific provision.", False),
            ],
            guardrails=[
                "Court-case search hits are candidate metadata until selected case detail is loaded.",
                "Judicial reasoning claims require get_case() detail, not search result identity fields.",
            ],
            forbidden_actions=[
                "Do not state the judicial holding from search_cases() output alone.",
                "Do not cite case full text, holdings, or referenced-statute reasoning before get_case() loads the selected case.",
            ],
        ),
        PromptDryRunReport(
            scenario="empty_case_search_absence_review",
            prompt="대법원 판례 검색 결과가 0건이면 관련 판례는 없다고 답해줘.",
            status="needs_more_source_loading",
            planned_steps=[
                PromptWorkflowStep(
                    "moleg-api",
                    "search_cases",
                    "Run the initial scoped court-case search and preserve query/court/body scope.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "search_cases",
                    "Retry with alternate legal terms, statute names, article numbers, and broader court/body scope.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "search_constitutional_decisions",
                    "Check neighboring Constitutional Court authority before any no-authority claim.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "search_interpretations",
                    "Check MOLEG/ministry interpretations when administrative or interpretive authority may matter.",
                ),
            ],
            guardrails=[
                "An empty result from one scoped case search is not proof that no relevant precedent or judicial authority exists.",
                "Case coverage depends on search terms, court scope, source body coverage, and neighboring authority families.",
            ],
            forbidden_actions=[
                "Do not say No relevant precedent exists from one empty search_cases() result.",
                "Do not treat zero hits as proof that no court case, judicial authority, or related legal reasoning exists.",
            ],
        ),
        PromptDryRunReport(
            scenario="constitutional_search_candidate_detail_review",
            prompt="헌재결정례 검색 결과만 보고 과잉금지원칙 관련 결정요지와 위헌 여부를 정리해줘.",
            status="needs_more_source_loading",
            planned_steps=[
                PromptWorkflowStep(
                    "moleg-api",
                    "search_constitutional_decisions",
                    "Find Constitutional Court decision candidates and preserve decision metadata.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "get_constitutional_decision",
                    "Load selected Constitutional Court decision detail before citing holdings, summary, reviewed statutes, or full text.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "get_article",
                    "Load reviewed statute article text when the constitutional decision turns on a specific provision.",
                    False,
                ),
            ],
            guardrails=[
                "Constitutional Court search hits are candidate metadata until selected decision detail is loaded.",
                "Constitutional reasoning claims require get_constitutional_decision() detail, not search result identity fields.",
            ],
            forbidden_actions=[
                "Do not state the constitutional holding from search_constitutional_decisions() output alone.",
                "Do not cite decision summary, holdings, reviewed-statute reasoning, or full text before get_constitutional_decision() loads the selected decision.",
            ],
        ),
        PromptDryRunReport(
            scenario="empty_constitutional_search_absence_review",
            prompt="헌재결정례 검색 결과가 0건이면 관련 결정도 없고 위헌 위험도 낮다고 답해줘.",
            status="needs_more_source_loading",
            planned_steps=[
                PromptWorkflowStep(
                    "moleg-api",
                    "search_constitutional_decisions",
                    "Run the initial scoped Constitutional Court free-text search and preserve query/body scope.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "search_constitutional_decisions",
                    "Retry with alternate doctrine terms, statute/article names, reviewed-statute terms, and body/title scopes.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "search_cases",
                    "Check ordinary court cases when constitutional risk may be reflected through judicial reasoning.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "search_interpretations",
                    "Check interpretations when constitutional or application-risk reasoning may be discussed outside detc.",
                ),
            ],
            guardrails=[
                "An empty result from one scoped Constitutional Court search is not proof that no constitutional authority exists.",
                "A free-text detc no-result is not a no-constitutional-risk finding.",
            ],
            forbidden_actions=[
                "Do not say No constitutional decision exists from one empty search_constitutional_decisions() result.",
                "Do not say there is no constitutional risk from a zero-hit Constitutional Court free-text search.",
            ],
        ),
        PromptDryRunReport(
            scenario="authority_article_reference_match_review",
            prompt="개인정보 보호법 제15조에 대해 로드된 해석례, 판례, 헌재결정이 있으니 바로 근거로 인용해줘.",
            status="needs_more_source_loading",
            planned_steps=[
                PromptWorkflowStep(
                    "moleg-api",
                    "load_authority_context",
                    "Load target-article interpretation, case, and Constitutional Court context and cite only current_authorities.",
                ),
            ],
            guardrails=[
                "load_authority_context.current_authorities is the citable target-article authority set.",
                "Loaded interpretations and court cases are target-article authority only when referenced_articles match the requested law/article.",
                "Loaded Constitutional Court decisions are target-article authority only when reviewed_articles match the requested law/article.",
                "Mismatched loaded authority details may guide follow-up search terms, but they are not citations for the target article.",
            ],
            forbidden_actions=[
                "Do not cite loaded authority that references a different article as authority for the target article.",
                "Do not cite a Constitutional Court decision that reviewed a different article as constitutional authority for the target article.",
                "Do not say no relevant authority exists merely because the loaded authority details point to different articles.",
            ],
        ),
        PromptDryRunReport(
            scenario="context_bundle_authority_article_mismatch_review",
            prompt="context bundle에 개인정보 보호법 제15조와 관련된 권위자료가 로드되어 있으면 바로 인용해줘.",
            status="needs_more_source_loading",
            planned_steps=[
                PromptWorkflowStep(
                    "moleg-api",
                    "load_legal_context_bundle",
                    "Load a staged bundle for the target article and inspect authority_article_mismatch gaps.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "search_interpretations",
                    "Run target-article interpretation search when bundle eager-loaded interpretation detail references another article.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "search_cases",
                    "Run target-article case search when bundle eager-loaded court-case detail references another article.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "search_constitutional_decisions",
                    "Run target-article Constitutional Court search when bundle eager-loaded reviewed_articles point elsewhere.",
                ),
            ],
            guardrails=[
                "A context bundle authority_article_mismatch gap means eager-loaded authority detail is not target-article authority.",
                "Bundle-loaded authority still requires referenced_articles or reviewed_articles to match the requested article before citation.",
                "The target article itself may be cited separately from mismatched eager-loaded authority details.",
            ],
            forbidden_actions=[
                "Do not cite eager-loaded context bundle authority as target-article authority when authority_article_mismatch gaps exist.",
                "Do not ignore context bundle authority_article_mismatch gaps because the detail text was loaded.",
                "Do not say the context bundle proved no target-article authority exists before follow-up searches.",
            ],
        ),
        PromptDryRunReport(
            scenario="context_bundle_authority_article_unverified_review",
            prompt="context bundle에 권위자료 상세가 로드됐는데 관련 조문 정보가 비어 있어도 개인정보 보호법 제15조 근거로 인용해도 돼?",
            status="needs_more_source_loading",
            planned_steps=[
                PromptWorkflowStep(
                    "moleg-api",
                    "load_legal_context_bundle",
                    "Load a staged bundle for the target article and inspect authority_article_unverified gaps.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "search_interpretations",
                    "Run target-article interpretation search when bundle eager-loaded interpretation detail has no structured referenced_articles.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "search_cases",
                    "Run target-article case search when bundle eager-loaded court-case detail has no structured referenced_articles.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "search_constitutional_decisions",
                    "Run target-article Constitutional Court search when bundle eager-loaded detail has no structured reviewed_articles.",
                ),
            ],
            guardrails=[
                "A context bundle authority_article_unverified gap means eager-loaded authority detail is not verified target-article authority.",
                "Bundle-loaded authority requires structured referenced_articles or reviewed_articles to match the requested article before citation.",
                "Empty structured article references are an unknown source state, not a target-article match.",
            ],
            forbidden_actions=[
                "Do not cite eager-loaded context bundle authority as target-article authority when authority_article_unverified gaps exist.",
                "Do not treat missing referenced_articles or reviewed_articles as an implicit match to the requested article.",
                "Do not say the context bundle proved no target-article authority exists before follow-up searches.",
            ],
        ),
        PromptDryRunReport(
            scenario="context_bundle_authority_article_partial_match_review",
            prompt="context bundle이 개인정보 보호법 제15조와 제17조 권위자료를 로드했는데 제17조만 참조하면 둘 다 근거로 써도 돼?",
            status="needs_more_source_loading",
            planned_steps=[
                PromptWorkflowStep(
                    "moleg-api",
                    "load_legal_context_bundle",
                    "Load a staged bundle for the requested articles and inspect authority_article_partial_match gaps.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "search_interpretations",
                    "Run scoped interpretation search for requested articles missing from bundle-loaded referenced_articles.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "search_cases",
                    "Run scoped case search for requested articles missing from bundle-loaded referenced_articles.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "search_constitutional_decisions",
                    "Run scoped Constitutional Court search for requested articles missing from bundle-loaded reviewed_articles.",
                ),
            ],
            guardrails=[
                "A context bundle authority_article_partial_match gap means eager-loaded authority detail matches only some requested articles.",
                "Bundle-loaded authority supports only requested articles that appear in structured referenced_articles or reviewed_articles.",
                "Missing requested articles require follow-up authority searches before target-article authority claims.",
            ],
            forbidden_actions=[
                "Do not broadcast eager-loaded context bundle authority to all requested articles when authority_article_partial_match gaps exist.",
                "Do not treat a partial referenced_articles or reviewed_articles match as authority for every requested article.",
                "Do not say no authority exists for the missing requested article before follow-up searches.",
            ],
        ),
        PromptDryRunReport(
            scenario="context_bundle_authority_temporal_mismatch_review",
            prompt="context bundle 권위자료가 개인정보 보호법 제15조를 참조하긴 하는데 판단일이 현재 조문 시행 전이면 그래도 현재 해석 근거로 써도 돼?",
            status="needs_more_source_loading",
            planned_steps=[
                PromptWorkflowStep(
                    "moleg-api",
                    "load_legal_context_bundle",
                    "Load a staged bundle for the target article and inspect authority_temporal_mismatch gaps.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "trace_law_history",
                    "Check whether target article wording changed between the authority date and the current article effective date.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "get_article",
                    "Load target article text as of the authority date if a historical comparison is needed.",
                ),
            ],
            guardrails=[
                "A matching referenced_articles or reviewed_articles value is not enough when authority_temporal_mismatch gaps exist.",
                "Authority dated before the loaded target article's effective date, or missing a parseable authority date, may support historical or follow-up context, not current target-article authority.",
                "Current-authority claims require history or as-of article loading across the authority date and current effective date.",
            ],
            forbidden_actions=[
                "Do not cite older or date-unverified eager-loaded authority as current target-article authority merely because it references the same article.",
                "Do not ignore authority_temporal_mismatch gaps because referenced_articles or reviewed_articles match.",
                "Do not say the authority reflects current wording before checking article history or as-of article text.",
            ],
        ),
        PromptDryRunReport(
            scenario="law_structure_hierarchy_candidate_review",
            prompt="법령체계도에 자동차관리법 시행령이 보이면 제26조의 위임 조문과 하위 처리기준까지 설명해줘.",
            status="needs_more_source_loading",
            planned_steps=[
                PromptWorkflowStep(
                    "moleg-api",
                    "get_law_structure",
                    "Load the statute/enforcement-instrument hierarchy around the selected law.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "find_delegated_rules",
                    "Load article-level delegation before saying which provision delegates to which lower rule.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "get_article",
                    "Load the source statute article before citing the delegation text.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "get_administrative_rule",
                    "Load selected lower-rule detail before citing operational criteria.",
                ),
            ],
            guardrails=[
                "Law structure is hierarchy context, not article-level delegation detail.",
                "A lower instrument appearing in the hierarchy is not proof that its body or operational criteria were inspected.",
            ],
            forbidden_actions=[
                "Do not cite article-level delegation from get_law_structure() output alone.",
                "Do not state lower-rule body text or operational criteria from hierarchy nodes alone.",
            ],
        ),
        PromptDryRunReport(
            scenario="empty_delegation_graph_absence_review",
            prompt="위임조문 조회 결과가 0건이면 이 조문에는 위임규정이나 하위규정이 없다고 답해줘.",
            status="needs_more_source_loading",
            planned_steps=[
                PromptWorkflowStep(
                    "moleg-api",
                    "find_delegated_rules",
                    "Run the initial article-level delegation lookup and preserve law/article scope.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "get_law_structure",
                    "Load hierarchy context before claiming no lower instrument exists.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "find_delegated_rules",
                    "Retry with alternate article scope, law identity, or broader statute-level delegation lookup.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "search_administrative_rules",
                    "Check whether practical criteria are exposed through administrative-rule candidates.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "search_annex_forms",
                    "Check whether operational criteria live in attached tables/forms rather than delegation graph hits.",
                ),
            ],
            guardrails=[
                "An empty result from one scoped delegation graph is not proof that no delegated rule or lower instrument exists.",
                "Delegated criteria may be discoverable through law structure, alternate article scopes, administrative rules, or annex/form paths.",
            ],
            forbidden_actions=[
                "Do not say No delegated rule exists from one empty find_delegated_rules() result.",
                "Do not treat zero rules as proof that no subordinate rule, notice, annex, or delegated criteria exists.",
            ],
        ),
        PromptDryRunReport(
            scenario="administrative_rule_search_candidate_detail_review",
            prompt="행정규칙 검색 결과만 보고 무단방치 자동차 처리 기준과 현재 적용 여부를 정리해줘.",
            status="needs_more_source_loading",
            planned_steps=[
                PromptWorkflowStep(
                    "moleg-api",
                    "search_administrative_rules",
                    "Find administrative-rule candidates and preserve identity metadata.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "get_administrative_rule",
                    "Load selected administrative-rule detail before citing article text, criteria, supplementary provisions, or current operational criteria.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "get_article",
                    "Load the authorizing statute article when the administrative rule references a source provision.",
                    False,
                ),
            ],
            guardrails=[
                "Administrative-rule search hits are candidate metadata until selected rule detail is loaded.",
                "List issued_on filters are issuing-date filters, not source-loaded current-force proof.",
            ],
            forbidden_actions=[
                "Do not state operational criteria, article text, supplementary provisions, or current operational criteria from search_administrative_rules() output alone.",
                "Do not cite administrative-rule body text before get_administrative_rule() loads the selected rule.",
            ],
        ),
        PromptDryRunReport(
            scenario="administrative_rule_issued_on_current_criteria_review",
            prompt="2025년 1월 1일 기준으로 전기자동차 충전시설 운영 고시가 현행 처리기준인지 확인해줘.",
            status="needs_more_source_loading",
            planned_steps=[
                PromptWorkflowStep(
                    "moleg-api",
                    "search_administrative_rules",
                    "Use administrative-rule search only as candidate discovery; issued_on filters 발령일자, not 시행일자/as-of.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "get_administrative_rule",
                    "Load selected administrative-rule detail before citing criteria or deciding current operational status.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "search_administrative_rules",
                    "If the selected detail is not effective as of the reference date, search for the currently effective rule text or disclose the gap.",
                ),
            ],
            guardrails=[
                "search_administrative_rules(issued_on=...) filters 발령일자, not effective-date as-of state.",
                "Administrative-rule search hits are candidate metadata even when they include current_status or effective_date fields.",
                "Current operational criteria require selected detail loading and effective_date comparison against the reference date.",
            ],
            forbidden_actions=[
                "Do not treat issued_on as an as-of filter for current administrative-rule effect.",
                "Do not cite current operational criteria from administrative-rule search metadata alone.",
                "Do not say the rule was effective on the issued_on date before loading selected detail and comparing effective_date.",
            ],
        ),
        PromptDryRunReport(
            scenario="administrative_rule_article_status_review",
            prompt="무단방치 자동차 처리 규정 제3조가 삭제되고 제4조가 제6조로 이동했다면 현재 운영기준을 바로 설명해줘.",
            status="needs_more_source_loading",
            planned_steps=[
                PromptWorkflowStep(
                    "moleg-api",
                    "load_administrative_rule_context",
                    "Load selected administrative-rule articles and follow moved_to to current destination articles before citing operational criteria.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "trace_law_history",
                    "Trace source-law or rule-change context if the user asks why the criteria moved or disappeared.",
                    False,
                ),
            ],
            guardrails=[
                "A deleted administrative-rule article is source state, not current operational criteria.",
                "A moved administrative-rule article marker is source state; current criteria require load_administrative_rule_context.current_articles.",
            ],
            forbidden_actions=[
                "Do not cite a deleted administrative-rule article as current operational criteria.",
                "Do not cite a moved administrative-rule article marker as current operational criteria.",
                "Do not infer prior wording or movement reason before history or comparison context is loaded.",
            ],
        ),
        PromptDryRunReport(
            scenario="administrative_rule_supplementary_transition_review",
            prompt="무단방치 자동차 처리 규정 부칙상 시행일과 경과조치가 진행 중인 처리절차에 어떤 영향을 주는지 확인해줘.",
            status="moleg_ready",
            planned_steps=[
                PromptWorkflowStep(
                    "moleg-api",
                    "search_administrative_rules",
                    "Resolve the selected administrative-rule identity if the prompt did not provide an exact serial ID.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "get_administrative_rule",
                    "Load selected administrative-rule detail so supplementary provisions are available.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "trace_law_history",
                    "Check source-law or rule-change history if the transition question depends on a specific amendment event.",
                    False,
                ),
            ],
            guardrails=[
                "Administrative-rule supplementary provisions must be cited separately for 시행일, 적용례, or 경과조치.",
                "Administrative-rule effective_date metadata and article text do not by themselves answer transitional application.",
                "Use get_administrative_rule(), not search_administrative_rules() or one article alone, when the prompt asks for administrative-rule 부칙 or 경과조치.",
            ],
            forbidden_actions=[
                "Do not answer transitional scope from the administrative-rule article alone.",
                "Do not say no administrative-rule 경과조치 exists unless supplementary provisions were loaded and inspected.",
                "Do not treat administrative-rule effective_date metadata as the full 시행일/적용례 analysis.",
            ],
        ),
        PromptDryRunReport(
            scenario="empty_administrative_rule_search_absence_review",
            prompt="행정규칙 검색 결과가 0건이면 위임된 세부기준이나 하위규정이 없다고 답해줘.",
            status="needs_more_source_loading",
            planned_steps=[
                PromptWorkflowStep(
                    "moleg-api",
                    "search_administrative_rules",
                    "Run the initial scoped administrative-rule search and preserve query/filter scope.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "find_delegated_rules",
                    "Load statute-level delegation context before any no-delegated-criteria claim.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "search_administrative_rules",
                    "Retry with alternate rule names, statute names, ministry scope, or related legal terms.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "search_annex_forms",
                    "Check whether operational criteria live in attached tables/forms rather than administrative-rule search hits.",
                    False,
                ),
            ],
            guardrails=[
                "An empty result from one scoped administrative-rule search is not proof that no delegated operational criteria exist.",
                "Detailed criteria may live in enforcement decrees, enforcement rules, notices, administrative-rule annexes, or statute annex/forms.",
            ],
            forbidden_actions=[
                "Do not say No delegated operational criteria exist from one empty search_administrative_rules() result.",
                "Do not treat zero hits as proof that no subordinate rule, notice, annex, or delegated criteria exists.",
            ],
        ),
        PromptDryRunReport(
            scenario="administrative_rule_missing_source_reference_review",
            prompt="행정규칙 상세에 위임법령이나 근거조문이 안 나오면 근거 법령이 없어서 무효라고 보면 되지?",
            status="needs_more_source_loading",
            planned_steps=[
                PromptWorkflowStep(
                    "moleg-api",
                    "get_administrative_rule",
                    "Load selected administrative-rule detail and preserve whether source-law/source-article metadata is exposed.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "find_delegated_rules",
                    "Load statute-level delegation context before claiming that no authorizing basis exists.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "get_law_structure",
                    "Load broader statute/enforcement/administrative-rule hierarchy if the delegation path is the question.",
                    False,
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "get_article",
                    "Load candidate authorizing statute articles before making legality or delegation-absence claims.",
                    False,
                ),
            ],
            guardrails=[
                "Missing administrative-rule source-law/source-article metadata means unknown in this MOLEG payload, not no authorizing statute.",
                "A legality or invalidity claim requires separate source loading and legal reasoning beyond the administrative-rule detail payload.",
            ],
            forbidden_actions=[
                "Do not infer absence of authorization from source_law_name=None or source_article=None.",
                "Do not say the administrative rule is invalid or lacks legal basis from missing back-reference metadata alone.",
            ],
        ),
        PromptDryRunReport(
            scenario="comparable_mechanism_candidate_detail_review",
            prompt="유사 입법례 후보만 보고 새 법안에 어떤 과징금 제도가 적합한지 결론 내줘.",
            status="needs_more_source_loading",
            planned_steps=[
                PromptWorkflowStep(
                    "moleg-api",
                    "find_comparable_mechanisms",
                    "Find source-backed comparable-mechanism planning candidates.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "get_article",
                    "Load selected comparable article text before citing structure, equivalence, or design suitability.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "search_cases",
                    "Check judicial limits for selected comparable mechanisms.",
                    False,
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "search_constitutional_decisions",
                    "Check constitutional-risk candidates for selected comparable mechanisms.",
                    False,
                ),
            ],
            guardrails=[
                "Comparable-mechanism results are planning candidates until selected source text is loaded.",
                "Article anchors from discovery surfaces are not proof of legal equivalence or design suitability.",
            ],
            forbidden_actions=[
                "Do not say mechanisms are legally equivalent from find_comparable_mechanisms() output alone.",
                "Do not recommend a design as suitable before selected comparable articles are loaded and inspected.",
            ],
        ),
        PromptDryRunReport(
            scenario="proposed_bill_current_law_check",
            prompt="플랫폼 노동자 보호법안이 지금 시행 중인 법인지 확인하고 현행 조문을 설명해줘.",
            status="needs_congress_db_first",
            planned_steps=[
                PromptWorkflowStep("congress-db", "bill_final_outcomes", "Check bill status and promulgation bridge fields."),
                PromptWorkflowStep("moleg-api", "resolve_promulgated_law", "Resolve bridge fields only if congress-db proves promulgation."),
                PromptWorkflowStep("moleg-api", "get_law", "Load effective law text with an explicit as-of reference date after bridge resolution."),
            ],
            guardrails=[
                "A proposed bill title is not a current-law identity.",
                "No MOLEG current-law loader should run before a promulgation bridge exists.",
                "Promulgation date alone does not prove current-force status; compare the loaded effective date to the reference date.",
            ],
            forbidden_actions=[
                "Do not describe a proposed bill as current law from its title alone.",
                "Do not run current-law text loaders before congress-db status is checked.",
                "Do not describe a promulgated law as currently in force when its effective date is after the reference date.",
            ],
        ),
        PromptDryRunReport(
            scenario="enacted_bill_change_trace",
            prompt="공포까지 확인된 데이터기본법 개정안이 현행법에서 무엇을 바꿨는지 조문별로 설명해줘.",
            status="needs_more_source_loading",
            planned_steps=[
                PromptWorkflowStep("congress-db", "bill_final_outcomes", "Load enacted-bill status and promulgation bridge fields."),
                PromptWorkflowStep("moleg-api", "resolve_promulgated_law", "Resolve the promulgation bridge into a MOLEG law identity."),
                PromptWorkflowStep("moleg-api", "get_law", "Load current effective text as current wording, not as amendment-delta proof."),
                PromptWorkflowStep("moleg-api", "trace_law_history", "Trace law/article history for the affected promulgation event."),
                PromptWorkflowStep("moleg-api", "compare_law_versions", "Load before/after text for selected affected provisions."),
            ],
            guardrails=[
                "Resolving a promulgation bridge or loading current law text proves identity/current wording, not the amendment delta.",
                "Do not explain what changed until trace_law_history() or compare_law_versions() has loaded the relevant date/article.",
                "Law-level history can identify chronology; article-level wording changes need article/date-scoped history or compare output.",
            ],
            forbidden_actions=[
                "Do not infer changed provisions from current text alone.",
                "Do not claim bridge resolution proves which articles changed.",
                "Do not cite law-level chronology as full before/after wording.",
            ],
        ),
        PromptDryRunReport(
            scenario="historical_repealed_law_review",
            prompt="폐지된 온라인개인정보보호법 제2조가 2012년 말에는 어떤 내용이었는지, 지금도 현행 근거인지 구분해줘.",
            status="moleg_ready",
            planned_steps=[
                PromptWorkflowStep("moleg-api", "search_laws", "Discover historical/promulgated law identity candidates rather than relying only on current effective search."),
                PromptWorkflowStep("moleg-api", "trace_law_history", "Confirm repeal/history status and choose the relevant historical event."),
                PromptWorkflowStep("moleg-api", "get_article", "Load the historical article with an explicit as-of date before citing text."),
                PromptWorkflowStep("moleg-api", "search_laws", "Run a current effective lookup separately if the prompt asks whether it is still current.", False),
            ],
            guardrails=[
                "A historical or repealed-law prompt is not a current-law prompt.",
                "No-result from current effective search does not prove the law never existed.",
                "Historical article text must carry an explicit as-of date and must not be cited as current law.",
            ],
            forbidden_actions=[
                "Do not answer a historical-law question from current effective search alone.",
                "Do not describe a repealed/historical article as currently in force.",
                "Do not treat a current no-result as proof that the historical source never existed.",
            ],
        ),
        PromptDryRunReport(
            scenario="supplementary_transition_review",
            prompt="현행 전세사기피해자 지원법이 기존 임대차계약에도 적용되는지 부칙 시행일과 경과조치를 같이 확인해줘.",
            status="moleg_ready",
            planned_steps=[
                PromptWorkflowStep("moleg-api", "search_laws", "Resolve the current effective statute identity."),
                PromptWorkflowStep("moleg-api", "get_law", "Load the full law text so supplementary provisions are available."),
                PromptWorkflowStep("moleg-api", "trace_law_history", "Check whether the transition question depends on a specific amendment event.", False),
            ],
            guardrails=[
                "Effective-date metadata and main-article text do not by themselves answer transitional application.",
                "Supplementary provisions must be cited separately when discussing enforcement dates or 경과조치.",
                "Use get_law(), not only get_article(), when the prompt asks for 부칙 or 경과조치.",
            ],
            forbidden_actions=[
                "Do not answer transitional scope from the main article alone.",
                "Do not say no 경과조치 exists unless supplementary provisions were loaded and inspected.",
                "Do not treat law effective_date metadata as the full 시행일/적용례 analysis.",
            ],
        ),
        PromptDryRunReport(
            scenario="delegated_operational_criteria",
            prompt="자동차관리법 제26조의 무단방치 차량 처리 기준이 시행령, 고시, 별표까지 어떻게 이어지는지 봐줘.",
            status="needs_more_source_loading",
            planned_steps=[
                PromptWorkflowStep(
                    "moleg-api",
                    "load_delegated_criteria",
                    "Load the statute anchor, delegation graph, selected administrative-rule body, and selected annex/form body.",
                ),
            ],
            guardrails=[
                "load_delegated_criteria is bounded source loading, not an exhaustive survey of every lower instrument.",
                "Statute text alone is insufficient when delegated criteria may control practice.",
                "After loading selected administrative-rule detail, compare its effective date to the reference date before calling it current operational criteria.",
            ],
            forbidden_actions=[
                "Do not claim every administrative rule or annex/form was exhaustively inspected from the bounded delegated-criteria bundle.",
                "Do not describe future-effective administrative-rule text as current operational criteria.",
            ],
        ),
        PromptDryRunReport(
            scenario="annex_search_candidate_detail_review",
            prompt="별표 검색 결과만 보고 과태료 금액 기준과 적용 요건을 정리해줘.",
            status="needs_more_source_loading",
            planned_steps=[
                PromptWorkflowStep(
                    "moleg-api",
                    "search_annex_forms",
                    "Find annex/form candidates and preserve attachment metadata.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "get_annex_form_body",
                    "Load selected annex/form body before citing thresholds, amounts, criteria, form content, or extracted rows.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "get_article",
                    "Load the authorizing statute or enforcement article when the attached body references a provision.",
                    False,
                ),
            ],
            guardrails=[
                "Annex/form search hits are candidate metadata until selected body text is loaded.",
                "Attached thresholds, amounts, criteria, and form content require get_annex_form_body() detail.",
            ],
            forbidden_actions=[
                "Do not state thresholds, amounts, criteria, or form contents from search_annex_forms() output alone.",
                "Do not cite attached body text or extracted rows before get_annex_form_body() loads the selected annex/form.",
            ],
        ),
        PromptDryRunReport(
            scenario="empty_annex_form_search_absence_review",
            prompt="별표 검색 결과가 0건이면 과태료 세부기준이나 첨부서식은 없다고 답해줘.",
            status="needs_more_source_loading",
            planned_steps=[
                PromptWorkflowStep(
                    "moleg-api",
                    "search_annex_forms",
                    "Run the initial scoped annex/form search and preserve query/source/type/scope.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "get_law",
                    "Load source law or enforcement text before claiming attached criteria are absent.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "search_annex_forms",
                    "Retry with alternate annex/form terms, source law names, administrative-rule source, and form/annex types.",
                ),
                PromptWorkflowStep(
                    "moleg-api",
                    "search_administrative_rules",
                    "Check whether practical criteria live in notices, directives, or administrative-rule annexes.",
                ),
            ],
            guardrails=[
                "An empty result from one scoped annex/form search is not proof that no attached criteria or forms exist.",
                "Attached criteria may live under enforcement instruments, administrative rules, alternate annex/form titles, or text-export paths.",
            ],
            forbidden_actions=[
                "Do not say No attached criteria exist from one empty search_annex_forms() result.",
                "Do not treat zero hits as proof that no annex, form, threshold table, amount criterion, or attached material exists.",
            ],
        ),
        PromptDryRunReport(
            scenario="annex_table_extraction_confidence",
            prompt="식품위생법 시행령 별표의 과태료 금액 기준을 표로 뽑아서 바로 비교해줘.",
            status="moleg_ready",
            planned_steps=[
                PromptWorkflowStep("moleg-api", "search_annex_forms", "Discover candidate annex tables that may carry monetary criteria."),
                PromptWorkflowStep("moleg-api", "get_annex_form_body", "Load the selected annex body before extracting thresholds."),
                PromptWorkflowStep("moleg-api", "get_article", "Load the authorizing statute/enforcement article when the annex references a provision.", False),
            ],
            guardrails=[
                "Structured annex rows are usable only when parsing_confidence is high.",
                "Low-confidence structured_data means the retained plain text, not empty rows, is the source fallback.",
                "No structured rows does not prove that no annex criteria or thresholds exist.",
            ],
            forbidden_actions=[
                "Do not extract numeric criteria from empty low-confidence structured rows.",
                "Do not say the annex has no thresholds because structured_data.rows is empty.",
                "Do not cite annex metadata without loading the selected annex body.",
            ],
        ),
        PromptDryRunReport(
            scenario="comparative_sanction_design",
            prompt="새 법안에 과징금 제도를 넣으려는데 유사 입법례와 조문 구조를 찾아줘.",
            status="moleg_ready",
            planned_steps=[
                PromptWorkflowStep("moleg-api", "find_comparable_mechanisms", "Find source-backed comparable mechanism candidates."),
                PromptWorkflowStep("moleg-api", "get_article", "Load selected comparable article text before comparing."),
                PromptWorkflowStep("moleg-api", "search_interpretations", "Check interpretation constraints for selected mechanisms.", False),
                PromptWorkflowStep("moleg-api", "search_cases", "Check judicial limits for selected mechanisms.", False),
                PromptWorkflowStep("moleg-api", "search_constitutional_decisions", "Check constitutional-risk candidates for sanction design.", False),
            ],
            guardrails=[
                "Comparable-mechanism candidates are planning context, not proof of legal equivalence.",
                "The skill designs and compares only after selected source text is loaded.",
            ],
            forbidden_actions=[
                "Do not claim mechanisms are equivalent from candidate metadata alone.",
            ],
        ),
        PromptDryRunReport(
            scenario="context_bundle_bounded_authority_review",
            prompt="식품위생법 과징금 bundle 한 번으로 관련 법제처 해석례, 판례, 헌재 결정, 행정규칙, 별표까지 전부 검토했다고 결론내줘.",
            status="needs_more_source_loading",
            planned_steps=[
                PromptWorkflowStep("moleg-api", "load_legal_context_bundle", "Load a staged first-pass legal context bundle."),
                PromptWorkflowStep("moleg-api", "get_interpretation", "Load additional interpretation details before claiming interpretation coverage."),
                PromptWorkflowStep("moleg-api", "get_case", "Load additional case details before claiming judicial coverage."),
                PromptWorkflowStep("moleg-api", "get_constitutional_decision", "Load additional Constitutional Court decision details before claiming constitutional coverage."),
                PromptWorkflowStep("moleg-api", "get_administrative_rule", "Load selected administrative-rule detail before claiming operational-rule coverage."),
                PromptWorkflowStep("moleg-api", "get_annex_form_body", "Load selected annex/form bodies before claiming attached-criteria coverage."),
                PromptWorkflowStep("moleg-api", "search_interpretations", "Search alternate terms if the authority survey itself is the task.", False),
                PromptWorkflowStep("moleg-api", "search_cases", "Search alternate case terms if judicial coverage is the task.", False),
                PromptWorkflowStep("moleg-api", "search_constitutional_decisions", "Search alternate constitutional terms if doctrine coverage is the task.", False),
                PromptWorkflowStep("moleg-api", "search_administrative_rules", "Search alternate operational-rule terms if administrative-rule coverage is the task.", False),
                PromptWorkflowStep("moleg-api", "search_annex_forms", "Search alternate attached-material terms if annex/form coverage is the task.", False),
            ],
            guardrails=[
                "A context bundle is a bounded first pass, not an exhaustive authority survey.",
                "Eager-loaded interpretation, case, Constitutional Court, administrative-rule, or annex/form context is citable only for loaded sources.",
            ],
            forbidden_actions=[
                "Do not claim exhaustive authority survey completion from load_legal_context_bundle() output alone.",
                "Do not say no further interpretation, case, Constitutional Court, administrative-rule, or annex/form source can matter unless the deferred searches/details were reviewed.",
            ],
        ),
        PromptDryRunReport(
            scenario="institutional_system_explicit_statute_set_review",
            prompt="전자금융거래법과 전자금융거래법 시행령을 기준으로 전자금융 제도를 묶어 검토해줘.",
            status="moleg_ready",
            planned_steps=[
                PromptWorkflowStep("moleg-api", "load_institutional_system", "Load the explicit statute set as one staged institutional-system bundle."),
                PromptWorkflowStep("moleg-api", "expand_legal_query", "Search for additional statutes first if the statute set is uncertain.", False),
                PromptWorkflowStep("moleg-api", "search_laws", "Resolve additional statute candidates before expanding the set.", False),
            ],
            guardrails=[
                "load_institutional_system() composes the statutes the skill already selected.",
                "Loaded statutes, structures, and delegations do not prove that every statute in the institution was discovered.",
            ],
            forbidden_actions=[
                "Do not claim the institutional-system statute set is exhaustive from load_institutional_system() output alone.",
                "Do not treat omitted statutes as irrelevant unless the discovery step was separately run and disclosed.",
            ],
        ),
        PromptDryRunReport(
            scenario="constitutional_risk_review",
            prompt="집회 제한 조항이 과잉금지원칙 관점에서 헌법상 위험이 있는지 관련 헌재 결정을 검토해줘.",
            status="moleg_ready",
            planned_steps=[
                PromptWorkflowStep("moleg-api", "search_laws", "Resolve the statute identity for the challenged article."),
                PromptWorkflowStep("moleg-api", "get_article", "Load the article text before constitutional-risk analysis."),
                PromptWorkflowStep("moleg-api", "search_constitutional_decisions", "Search Constitutional Court decisions by free-text doctrine terms."),
                PromptWorkflowStep("moleg-api", "get_constitutional_decision", "Load selected Constitutional Court decision detail before citing it."),
                PromptWorkflowStep("moleg-api", "search_cases", "Check ordinary judicial application context separately when it may matter.", False),
            ],
            guardrails=[
                "Constitutional doctrine terms are free-text search terms, not structured source-backed filters.",
                "Loaded Constitutional Court decisions do not prove exhaustive doctrine coverage when candidates remain deferred.",
                "Use reviewed_articles to connect loaded decisions to the challenged article before spending reasoning budget.",
            ],
            forbidden_actions=[
                "Do not claim doctrine-indexed exhaustive Constitutional Court coverage from detc search results.",
                "Do not say there is no constitutional risk solely because a free-text search returned few or no hits.",
            ],
        ),
        PromptDryRunReport(
            scenario="latest_social_context_plus_current_law",
            prompt="최근 전세사기 피해 통계와 현행 지원법 조문을 함께 검토해줘.",
            status="requires_websearch_handoff",
            planned_steps=[
                PromptWorkflowStep("moleg-api", "expand_legal_query", "Plan legal source discovery for the statutory part."),
                PromptWorkflowStep("moleg-api", "search_laws", "Resolve candidate current-law identities."),
                PromptWorkflowStep("moleg-api", "get_article", "Load selected current legal text."),
                PromptWorkflowStep("websearch", "latest_social_facts", "Fetch latest statistics, announcements, and non-MOLEG context."),
            ],
            guardrails=[
                "MOLEG-API owns enacted legal sources, not latest statistics or news.",
                "Use WebSearch for current social facts and cite it separately from legal sources.",
            ],
            forbidden_actions=[
                "Do not force MOLEG-API to answer current statistics or news.",
            ],
        ),
    ]
    _validate_prompt_reports(reports)
    return reports


def _validate_prompt_reports(reports: list[PromptDryRunReport]) -> None:
    public_methods = {
        name
        for name, value in inspect.getmembers(MolegApi, inspect.isfunction)
        if not name.startswith("_")
    }
    for report in reports:
        for step in report.planned_steps:
            if step.source == "moleg-api" and step.interface not in public_methods:
                raise AssertionError(f"{report.scenario} uses unknown MolegApi interface: {step.interface}")
            if step.interface in RAW_MOLEG_TARGETS:
                raise AssertionError(f"{report.scenario} leaked raw MOLEG target: {step.interface}")


def main() -> None:
    print(
        json.dumps(
            [report.to_dict() for report in run_legislative_expert_prompt_dry_run()],
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
