from __future__ import annotations

from .foundation import *

EXIT_OK = 0            # includes a zero-hit search (ok:true, count:0)
EXIT_AMBIGUOUS = 2     # multiple plausible identities — surface, don't pick
EXIT_SOURCE = 3        # source could not be read OR could not be parsed — kind splits it:
                       #   source_access_error = transient (rate limit / retry / 5xx), retry is right
                       #   parse_error         = unrecognized response shape, retry won't help
EXIT_NO_RESULT = 4     # a well-formed lookup found no source text — includes a bad identifier,
                       # which law.go.kr signals with an empty detail body (see unwrap_service_payload)
EXIT_USAGE = 5         # bad arguments, or a loader was handed a law name (search first)

# Public MolegApi methods reachable through load-followup rehydration. Guards the
# candidate->body discipline: an arbitrary interface string cannot smuggle a
# candidate in as if it were loaded text.
FOLLOWUP_INTERFACES = frozenset(
    {
        "expand_legal_query",
        "find_comparable_mechanisms",
        "resolve_promulgated_law",
        "search_laws",
        "get_law",
        "get_article",
        "load_article_context",
        "search_administrative_rules",
        "get_administrative_rule",
        "load_administrative_rule_context",
        "search_annex_forms",
        "get_annex_form_body",
        "search_interpretations",
        "get_interpretation",
        "search_cases",
        "get_case",
        "search_constitutional_decisions",
        "get_constitutional_decision",
        "load_authority_context",
        "find_delegated_rules",
        "get_law_structure",
        "trace_law_history",
        "compare_law_versions",
        "load_legal_context_bundle",
        "load_institutional_system",
        "load_delegated_criteria",
    }
)
# Handoffs that are valid follow-up interfaces but belong to other sources.
FOLLOWUP_HANDOFFS = frozenset({"websearch", "congress-db"})

# Searches return a list; a zero-hit search is a scoped ok:true result (count 0),
# never an error — even when the SDK signals "nothing found" by raising.
SEARCH_COMMANDS = frozenset(
    {
        "search-laws",
        "search-administrative-rules",
        "search-annex-forms",
        "search-interpretations",
        "search-cases",
        "search-constitutional-decisions",
    }
)


class CliError(Exception):
    """A CLI-level failure carrying the envelope kind and exit code to emit."""

    def __init__(self, message: str, *, kind: str, exit_code: int, extra: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.kind = kind
        self.exit_code = exit_code
        self.extra = extra or {}

__all__ = [name for name in globals() if not name.startswith("__")]
