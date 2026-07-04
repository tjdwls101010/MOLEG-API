from __future__ import annotations

from .institutional_candidates import discover_institutional_candidates
from .support import *


@dataclass
class InstitutionalState:
    source_notes: list[str]
    ambiguities: list[Ambiguity]
    gaps: list[ContextGap]
    deferred: list[DeferredLookup]
    loaded_laws: list[LawText]
    loaded_articles: list[ArticleText]
    loaded_delegations: list[DelegationGraph]
    law_structures: list[LawStructure]
    law_candidates: list[LawIdentity]
    administrative_candidates: list[AdministrativeRuleHit]
    annex_form_candidates: list[AnnexFormHit]
    interpretation_candidates: list[InterpretationHit]
    case_candidates: list[JudicialDecisionHit]
    constitutional_candidates: list[JudicialDecisionHit]


def new_institutional_state() -> InstitutionalState:
    return InstitutionalState(
        source_notes=["Institutional-system bundle is staged source context, not a legal conclusion."],
        ambiguities=[],
        gaps=[],
        deferred=[],
        loaded_laws=[],
        loaded_articles=[],
        loaded_delegations=[],
        law_structures=[],
        law_candidates=[],
        administrative_candidates=[],
        annex_form_candidates=[],
        interpretation_candidates=[],
        case_candidates=[],
        constitutional_candidates=[],
    )


def process_institutional_statute(
    api: Any,
    statute_identifier: str | LawIdentity | LawHit,
    articles: list[str | int] | None,
    limits: dict[str, int],
    reference_date: str | None,
    state: InstitutionalState,
) -> None:
    try:
        resolution = api._resolve_institutional_statute(
            statute_identifier,
            display=max(2, limits["law_candidates"]),
        )
    except MolegApiError as exc:
        label = statute_identifier_label(statute_identifier)
        state.source_notes.append(f"Statute resolution skipped for {label}: {exc}")
        append_institutional_statute_resolution_failure_gap(
            exc,
            label,
            state.gaps,
            state.deferred,
        )
        return

    state.law_candidates.extend(resolution.candidates)
    if resolution.identity is None:
        append_unresolved_institutional_statute(resolution, state)
        return

    identity = resolution.identity
    if articles:
        identity = load_institutional_articles(
            api,
            identity,
            articles,
            limits,
            reference_date,
            state,
        )
    else:
        identity = load_institutional_law(api, identity, reference_date, state)

    load_institutional_structure_and_delegation(api, identity, limits, state)
    discover_for_institutional_identity(api, identity, limits, state)
    state.gaps.append(
        ContextGap(
            kind="websearch_required",
            reason="Use WebSearch for latest social facts, statistics, policy announcements, news, or non-MOLEG background.",
            query=identity.name,
            recommended_interface="websearch",
        )
    )


def append_unresolved_institutional_statute(
    resolution: InstitutionalStatuteResolution,
    state: InstitutionalState,
) -> None:
    if resolution.error_kind == "ambiguous":
        state.ambiguities.append(
            Ambiguity(
                kind="statute_identity",
                message=resolution.message or f"Statute identifier is ambiguous: {resolution.identifier}",
                candidates=resolution.candidates,
            )
        )
    else:
        state.source_notes.append(
            resolution.message or f"Statute '{resolution.identifier}' was not found"
        )
    state.gaps.append(
        ContextGap(
            kind="manual_review_required",
            reason="A statute identifier could not be resolved to one MOLEG law identity.",
            query=resolution.identifier,
            recommended_interface="search_laws",
        )
    )
    state.deferred.append(
        DeferredLookup(
            interface="search_laws",
            query=resolution.identifier,
            reason="Resolve the statute identity before loading this part of the institutional system.",
            source_type="law",
            filters={"basis": "effective"},
        )
    )


def load_institutional_articles(
    api: Any,
    identity: LawIdentity,
    articles: list[str | int],
    limits: dict[str, int],
    reference_date: str | None,
    state: InstitutionalState,
) -> LawIdentity:
    current_identity = identity
    for article in articles[: limits["articles"]]:
        try:
            article_context = api.load_article_context(
                current_identity,
                article,
                as_of=reference_date,
                basis="effective",
            )
            state.loaded_articles.extend(article_context.loaded_articles)
            state.gaps.extend(article_context.gaps)
            state.deferred.extend(article_context.deferred)
            state.source_notes.extend(article_context.source_notes)
            for article_text in article_context.loaded_articles:
                current_identity = prefer_versioned_law_identity(current_identity, article_text.identity)
                append_not_effective_as_of_gap(
                    article_text.identity,
                    reference_date,
                    state.gaps,
                    state.source_notes,
                    query=current_identity.name,
                )
        except MolegApiError as exc:
            state.source_notes.append(f"Article load skipped for {current_identity.name} {article}: {exc}")
            append_requested_article_load_gap(
                exc,
                current_identity,
                article,
                state.gaps,
                state.deferred,
                as_of=reference_date,
            )
    return current_identity


def load_institutional_law(
    api: Any,
    identity: LawIdentity,
    reference_date: str | None,
    state: InstitutionalState,
) -> LawIdentity:
    try:
        law_text = api.get_law(identity, as_of=reference_date)
        state.loaded_laws.append(law_text)
        loaded_identity = law_text.identity
        state.law_candidates.append(loaded_identity)
        append_not_effective_as_of_gap(
            loaded_identity,
            reference_date,
            state.gaps,
            state.source_notes,
            query=loaded_identity.name,
        )
        append_whole_law_article_status_gaps(
            law_text,
            state.gaps,
            state.deferred,
            state.source_notes,
            as_of=reference_date,
            basis="effective",
        )
        return loaded_identity
    except MolegApiError as exc:
        state.source_notes.append(f"Law load skipped for {identity.name}: {exc}")
        append_requested_law_load_gap(
            exc,
            identity,
            state.gaps,
            state.deferred,
            as_of=reference_date,
        )
        return identity


def load_institutional_structure_and_delegation(
    api: Any,
    identity: LawIdentity,
    limits: dict[str, int],
    state: InstitutionalState,
) -> None:
    try:
        state.law_structures.append(api.get_law_structure(identity, depth=1))
    except MolegApiError as exc:
        state.source_notes.append(f"Law-structure lookup skipped for {identity.name}: {exc}")
        append_law_structure_load_gap(exc, identity, state.gaps, state.deferred)

    try:
        graph = api.find_delegated_rules(identity)
        state.loaded_delegations.append(limit_delegation_graph(graph, limits["delegations"]))
    except NoResultError:
        state.loaded_delegations.append(DelegationGraph(identity=identity, rules=[], raw={}))
        append_empty_delegation_lookup_gap(
            identity,
            state.gaps,
            state.deferred,
            recommended_interface="search_administrative_rules",
            deferred_interface=None,
        )
    except MolegApiError as exc:
        state.source_notes.append(f"Delegation lookup skipped for {identity.name}: {exc}")
        append_delegation_lookup_failure_gap(exc, identity, state.gaps, state.deferred)


def discover_for_institutional_identity(
    api: Any,
    identity: LawIdentity,
    limits: dict[str, int],
    state: InstitutionalState,
) -> None:
    administrative, annexes, interpretations, cases, constitutional = discover_institutional_candidates(
        api,
        identity,
        limits,
        state.source_notes,
        state.gaps,
        state.deferred,
    )
    state.administrative_candidates.extend(administrative)
    state.annex_form_candidates.extend(annexes)
    state.interpretation_candidates.extend(interpretations)
    state.case_candidates.extend(cases)
    state.constitutional_candidates.extend(constitutional)


__all__ = [name for name in globals() if not name.startswith("__")]
