from __future__ import annotations

from .foundation import *
from .constants import CliError, EXIT_USAGE, FOLLOWUP_HANDOFFS, FOLLOWUP_INTERFACES
from .data import _statute_args
from .brief_mode import brief_dropped, to_brief
from .signals_meta import parse_as_of

def _call(api: MolegApi, args: argparse.Namespace) -> Any:
    result = _dispatch(api, args)
    if getattr(args, "brief", False):
        # Record what was actually withheld *before* blanking it. Signals only
        # sees the trimmed result, and "empty because brief" must stay
        # distinguishable from "empty because the source had none" — otherwise a
        # caller goes hunting for a section that never existed.
        args.brief_dropped = brief_dropped(result)
        return to_brief(result)
    return result


def _dispatch(api: MolegApi, args: argparse.Namespace) -> Any:
    c = args.command
    # Strictly validate --as-of once, for every command that carries it, so a
    # malformed date is a usage error rather than a silent wrong-version load.
    if getattr(args, "as_of", None):
        args.as_of = parse_as_of(args.as_of)
    if c == "search-laws":
        return api.search_laws(args.query, as_of=args.as_of, basis=args.basis,
                               law_type=args.law_type, ministry=args.ministry, display=args.display)
    if c == "resolve-promulgated-law":
        return api.resolve_promulgated_law(prom_law_nm=args.prom_law_nm, prom_no=args.prom_no, promulgation_dt=args.promulgation_dt)
    if c == "search-administrative-rules":
        return api.search_administrative_rules(args.query, ministry=args.ministry, rule_type=args.rule_type,
                                               issued_on=args.issued_on, include_history=args.include_history, display=args.display)
    if c == "search-annex-forms":
        return api.search_annex_forms(args.query, source=args.source, search_scope=args.search_scope,
                                      annex_type=args.annex_type, ministry=args.ministry, display=args.display)
    if c == "search-interpretations":
        return api.search_interpretations(args.query, source=args.source, ministry=args.ministry,
                                          search_body=args.search_body, interpreted_on=args.interpreted_on, display=args.display)
    if c == "search-cases":
        return api.search_cases(args.query, court=args.court, court_name=args.court_name, search_body=args.search_body,
                                decided_on=args.decided_on, case_number=args.case_number, display=args.display)
    if c == "search-constitutional-decisions":
        return api.search_constitutional_decisions(args.query, search_body=args.search_body,
                                                    decided_on=args.decided_on, case_number=args.case_number, display=args.display)
    if c == "search-committee-decisions":
        return api.search_committee_decisions(args.query, committee=args.committee, display=args.display)
    if c == "get-committee-decision":
        return api.get_committee_decision(args.identifier, committee=args.committee)
    if c == "search-administrative-appeals":
        return api.search_administrative_appeals(args.query, tribunal=args.tribunal, display=args.display)
    if c == "get-administrative-appeal":
        return api.get_administrative_appeal(args.identifier, tribunal=args.tribunal)
    if c == "expand-legal-query":
        return api.expand_legal_query(args.query, display=args.display, include_websearch_hint=not args.no_websearch_hint)
    if c == "find-comparable-mechanisms":
        return api.find_comparable_mechanisms(args.concept, display=args.display)
    if c == "get-law":
        if args.toc:
            return api.get_law_toc(args.law, as_of=args.as_of, basis=args.basis)
        return api.get_law(args.law, as_of=args.as_of, basis=args.basis,
                           articles=args.article or None, include_metadata=not args.no_metadata)
    if c == "get-article":
        return api.get_article(args.law, args.article, as_of=args.as_of, basis=args.basis)
    if c == "load-article-context":
        return api.load_article_context(args.law, args.article,
                                        as_of=args.as_of, basis=args.basis, follow_moved=not args.no_follow_moved)
    if c == "get-administrative-rule":
        return api.get_administrative_rule(args.identifier, articles=args.article or None, include_metadata=not args.no_metadata)
    if c == "load-administrative-rule-context":
        return api.load_administrative_rule_context(args.identifier, articles=args.article or None,
                                                    include_metadata=not args.no_metadata, follow_moved=not args.no_follow_moved)
    if c == "get-annex-form-body":
        return api.get_annex_form_body(args.identifier, source=args.source, title=args.title,
                                       include_metadata=not args.no_metadata, attempt_structuring=not args.no_structuring)
    if c == "get-interpretation":
        return api.get_interpretation(args.identifier, source=args.source, ministry=args.ministry, include_metadata=not args.no_metadata)
    if c == "get-case":
        return api.get_case(args.identifier, include_metadata=not args.no_metadata)
    if c == "get-constitutional-decision":
        return api.get_constitutional_decision(args.identifier, include_metadata=not args.no_metadata)
    if c == "trace-law-history":
        date_range = (args.date_from, args.date_to) if (args.date_from and args.date_to) else None
        return api.trace_law_history(args.law, date_range=date_range, article=args.article)
    if c == "get-revision-reason":
        return api.get_revision_reason(args.law, mst=args.mst, as_of=args.as_of)
    if c == "compare-law-versions":
        return api.compare_law_versions(args.law, article=args.article)
    if c == "find-delegated-rules":
        return api.find_delegated_rules(args.law, article=args.article)
    if c == "get-law-structure":
        return api.get_law_structure(args.law, depth=args.depth)
    if c == "load-authority-context":
        return api.load_authority_context(args.law, articles=args.article,
                                          query=args.query, budget=args.budget, as_of=args.as_of)
    if c == "load-legal-context-bundle":
        bridge = _bridge(args)
        law = args.law or None
        return api.load_legal_context_bundle(args.query, promulgation_bridge=bridge, law_identifier=law,
                                             articles=args.article or None, mode=args.mode, budget=args.budget, as_of=args.as_of)
    if c == "load-institutional-system":
        return api.load_institutional_system(_statute_args(args.statute), articles=args.article or None, budget=args.budget, as_of=args.as_of)
    if c == "load-delegated-criteria":
        return api.load_delegated_criteria(args.law, articles=args.article or None,
                                           query=args.query, budget=args.budget, as_of=args.as_of)
    if c == "load-followup":
        return api.load_followup(_read_followup(args.json_arg))
    raise CliError(f"unknown command: {c}", kind="usage", exit_code=EXIT_USAGE)


def _bridge(args: argparse.Namespace) -> dict[str, Any] | None:
    keys = {"prom_law_nm": args.prom_law_nm, "prom_no": args.prom_no, "promulgation_dt": args.promulgation_dt}
    keys = {k: v for k, v in keys.items() if v}
    return keys or None


def _read_followup(json_arg: str) -> DeferredLookup:
    text = sys.stdin.read() if json_arg == "-" else json_arg
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CliError(f"--json is not valid JSON: {exc}", kind="usage", exit_code=EXIT_USAGE) from exc
    if isinstance(obj, list):
        raise CliError("--json expects one deferred object (data.deferred[i]), not a list", kind="usage", exit_code=EXIT_USAGE)
    interface = obj.get("interface")
    if interface not in FOLLOWUP_INTERFACES and interface not in FOLLOWUP_HANDOFFS and not any(str(interface).startswith(h) for h in FOLLOWUP_HANDOFFS):
        raise CliError(
            f"unknown follow-up interface {interface!r} — pass a deferred object from a prior bundle/expand response, not a hand-written one",
            kind="usage", exit_code=EXIT_USAGE,
        )
    return DeferredLookup(
        interface=str(interface),
        query=str(obj.get("query", "")),
        reason=str(obj.get("reason", "")),
        source_type=obj.get("source_type"),
        filters=obj.get("filters") or {},
    )

__all__ = [name for name in globals() if not name.startswith("__")]
