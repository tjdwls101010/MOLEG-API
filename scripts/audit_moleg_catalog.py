#!/usr/bin/env python3
"""Generate the MOLEG OpenAPI catalog audit document from the local SQLite DB."""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


DEFAULT_DB_PATH = Path(".Seongjin/DataBases/법제처 api.db")


CORE_GUIDES = {
    # Current statutes: promulgation-date and effective-date basis.
    "lsNwListGuide",
    "lsNwInfoGuide",
    "lsEfYdListGuide",
    "lsEfYdInfoGuide",
    # Article-level lookup.
    "lsNwJoListGuide",
    "lsEfYdJoListGuide",
    # History and before/after comparison.
    "lsHstListGuide",
    "lsHstInfoGuide",
    "lsChgListGuide",
    "lsDayJoRvsListGuide",
    "lsJoChgListGuide",
    "oldAndNewListGuide",
    "oldAndNewInfoGuide",
    # Delegation and hierarchy.
    "lsStmdListGuide",
    "lsStmdInfoGuide",
    "lsDelegated",
    "lsRltGuide",
    "thdCmpListGuide",
    "thdCmpInfoGuide",
    # Administrative rules.
    "admrulListGuide",
    "admrulInfoGuide",
    "admrulOldAndNewListGuide",
    "admrulOldAndNewInfoGuide",
    # Official MOLEG interpretations.
    "expcListGuide",
    "expcInfoGuide",
    # Judicial and constitutional authorities.
    "precListGuide",
    "precInfoGuide",
    "detcListGuide",
    "detcInfoGuide",
    # Legal terms and query expansion.
    "lsTrmListGuide",
    "lsTrmInfoGuide",
    "lstrmAIGuide",
    "dlytrmGuide",
    "lstrmRltGuide",
    "dlytrmRltGuide",
    "lstrmRltJoGuide",
    "joRltLstrmGuide",
    "aiSearchGuide",
    "aiRltLsGuide",
    "lsAbrvListGuide",
}

OPTIONAL_GUIDES = {
    # Annex/form endpoints are demand-gated, but these are likely early samples.
    "lsBylListGuide",
    "admrulBylListGuide",
    "ordinBylListGuide",
    # Useful but not needed for the first deep statute slice.
    "datDelHstGuide",
    "oneViewListGuide",
    "oneViewInfoGuide",
    "lsEngListGuide",
    "lsEngInfoGuide",
    "lsOrdinConGuide",
    "lsOrdinConListGuide",
    "ordinLsConListGuide",
}

REJECTED_GUIDE_PREFIXES = (
    "cust",
    "mob",
)

OPTIONAL_GUIDE_PREFIXES = (
    "cgmExpc",
    "specialDecc",
)

OPTIONAL_CATEGORIES = {
    "자치법규": "Local ordinance work is demand-gated until repeated skill scenarios require it.",
    "조약": "Treaty work is demand-gated until international-agreement scenarios are proven.",
    "행정심판례": "Administrative appeals can matter by domain, but are outside the initial core.",
    "특별행정심판": "Special administrative appeals are domain-specific and demand-gated.",
    "위원회 결정문": "Committee decisions are valuable by field, but should be added as dedicated modules after demand is proven.",
    "사전컨설팅 의견서": "Audit-office pre-consulting opinions are specialized guidance, not initial legislative core.",
    "학칙ㆍ공단 ㆍ공공기관": "School/public-institution rules are outside the national-law core.",
}


@dataclass(frozen=True)
class Guide:
    guide_id: str
    title: str
    category: str
    subcategory: str
    operation_kind: str
    target: str
    supports_json: bool
    supports_xml: bool
    supports_html: bool
    request_url: str
    parameters: list[dict]
    outputs: list[dict]
    samples: list[dict]


@dataclass(frozen=True)
class Classification:
    tier: str
    module: str
    reason: str


def load_guides(db_path: Path) -> list[Guide]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        """
        SELECT
          guide_id,
          title,
          category,
          subcategory,
          operation_kind,
          target,
          supports_json,
          supports_xml,
          supports_html,
          request_url,
          parameters,
          outputs,
          samples
        FROM api_catalog_flat
        ORDER BY category, subcategory, guide_id
        """
    ).fetchall()
    con.close()

    return [
        Guide(
            guide_id=row["guide_id"],
            title=row["title"],
            category=row["category"] or "",
            subcategory=row["subcategory"] or "",
            operation_kind=row["operation_kind"] or "",
            target=row["target"] or "",
            supports_json=bool(row["supports_json"]),
            supports_xml=bool(row["supports_xml"]),
            supports_html=bool(row["supports_html"]),
            request_url=row["request_url"] or "",
            parameters=json.loads(row["parameters"] or "[]"),
            outputs=json.loads(row["outputs"] or "[]"),
            samples=json.loads(row["samples"] or "[]"),
        )
        for row in rows
    ]


def classify(guide: Guide) -> Classification:
    guide_id = guide.guide_id

    if guide_id in CORE_GUIDES:
        return Classification("core", core_module(guide), core_reason(guide))

    if guide_id.startswith("cgmExpc"):
        return Classification(
            "core",
            "official-interpretations",
            "Ministry first-instance interpretations are core as a registry-backed family; do not expose one public function per ministry endpoint.",
        )

    if guide_id in OPTIONAL_GUIDES:
        return Classification("optional", optional_module(guide), optional_reason(guide))

    if guide_id.startswith(REJECTED_GUIDE_PREFIXES):
        return Classification("rejected", "excluded-surface", rejected_prefix_reason(guide))

    if guide_id.startswith(OPTIONAL_GUIDE_PREFIXES):
        return Classification("optional", optional_module(guide), optional_reason(guide))

    if guide.category in OPTIONAL_CATEGORIES:
        return Classification("optional", optional_module(guide), OPTIONAL_CATEGORIES[guide.category])

    if guide.category == "모바일":
        return Classification(
            "rejected",
            "mobile-fallback",
            "Mobile endpoints duplicate desktop/detail surfaces in most cases; keep only as a documented fallback when desktop JSON loses source information.",
        )

    if guide.category == "맞춤형":
        return Classification(
            "rejected",
            "customized-course",
            "Customized couse* endpoints are user-specific surfaces and do not belong in the default legislative-expert path.",
        )

    if guide.category == "별표ㆍ서식":
        return Classification(
            "optional",
            "annex-forms",
            "Annex/forms are demand-gated; sample them early for thresholds, tables, amounts, and requirements but do not block the first statute slice.",
        )

    return Classification(
        "optional",
        optional_module(guide),
        "Not rejected, but no recurring legislative-expert task has justified a first-class public interface yet.",
    )


def core_module(guide: Guide) -> str:
    if guide.guide_id in {
        "lsNwListGuide",
        "lsNwInfoGuide",
        "lsEfYdListGuide",
        "lsEfYdInfoGuide",
        "lsNwJoListGuide",
        "lsEfYdJoListGuide",
    }:
        return "current-statutes"
    if guide.guide_id in {
        "lsHstListGuide",
        "lsHstInfoGuide",
        "lsChgListGuide",
        "lsDayJoRvsListGuide",
        "lsJoChgListGuide",
        "oldAndNewListGuide",
        "oldAndNewInfoGuide",
    }:
        return "history-comparison"
    if guide.guide_id in {
        "lsStmdListGuide",
        "lsStmdInfoGuide",
        "lsDelegated",
        "lsRltGuide",
        "thdCmpListGuide",
        "thdCmpInfoGuide",
    }:
        return "delegation-hierarchy"
    if guide.guide_id.startswith("admrul"):
        return "administrative-rules"
    if guide.guide_id.startswith("expc") or guide.guide_id.startswith("cgmExpc"):
        return "official-interpretations"
    if guide.guide_id.startswith("prec") or guide.guide_id.startswith("detc"):
        return "judicial-constitutional"
    if guide.guide_id in {
        "lsTrmListGuide",
        "lsTrmInfoGuide",
        "lstrmAIGuide",
        "dlytrmGuide",
        "lstrmRltGuide",
        "dlytrmRltGuide",
        "lstrmRltJoGuide",
        "joRltLstrmGuide",
        "aiSearchGuide",
        "aiRltLsGuide",
        "lsAbrvListGuide",
    }:
        return "legal-terms-query-expansion"
    return "core"


def core_reason(guide: Guide) -> str:
    module = core_module(guide)
    reasons = {
        "current-statutes": "Needed for the first vertical slice: law search, normalized identity, effective/promulgation basis, and law text/article retrieval.",
        "history-comparison": "Legislative expertise requires tracing what changed, when it changed, and how before/after text differs.",
        "delegation-hierarchy": "Law-only review misses enforcement decrees, enforcement rules, notices, and related-law structure.",
        "administrative-rules": "Notices, directives, and established rules often carry the practical execution criteria behind statutes.",
        "official-interpretations": "Official interpretation sources constrain how statutes are applied, but MOLEG and ministry interpretations must retain separate authority labels.",
        "judicial-constitutional": "Cases and Constitutional Court decisions identify judicial meaning and constitutional risk.",
        "legal-terms-query-expansion": "Useful for query planning, legal-term expansion, related articles, and law-name candidate discovery rather than final authority.",
    }
    return reasons.get(module, "Core endpoint for a recurring legislative-expert task.")


def optional_module(guide: Guide) -> str:
    if guide.category == "별표ㆍ서식" or "Byl" in guide.guide_id:
        return "annex-forms"
    if guide.category == "자치법규":
        return "local-ordinances"
    if guide.category == "조약":
        return "treaties"
    if "Decc" in guide.guide_id or guide.category in {"행정심판례", "특별행정심판"}:
        return "administrative-appeals"
    if guide.category == "위원회 결정문":
        return "committee-decisions"
    if guide.guide_id.startswith("cgmExpc"):
        return "official-interpretations"
    if guide.category == "법령":
        return "statute-adjacent"
    return "demand-gated"


def optional_reason(guide: Guide) -> str:
    if guide.guide_id in {"lsBylListGuide", "admrulBylListGuide", "ordinBylListGuide"}:
        return "Annex/form lookup can prevent missing tables, thresholds, amounts, and forms, but should be added after live samples show the first failures."
    if guide.guide_id.startswith("specialDecc"):
        return "Special administrative appeals are useful in narrow fields, but should be introduced by a domain-specific scenario."
    if guide.guide_id in {"oneViewListGuide", "oneViewInfoGuide"}:
        return "One-view output is a presentation helper, not the first source of legal identity or text."
    if guide.guide_id in {"lsEngListGuide", "lsEngInfoGuide"}:
        return "English statutes are useful for translation workflows but not for the Korean legislative core."
    if guide.guide_id in {"datDelHstGuide"}:
        return "Deleted-data tracking is operational maintenance, not a first public interface."
    if "Ordin" in guide.guide_id or guide.category == "자치법규":
        return "Local ordinance work is demand-gated until repeated skill scenarios require it."
    return "Demand-gated: keep catalog knowledge, but wait for repeated legislative-expert scenarios before exposing a public interface."


def rejected_prefix_reason(guide: Guide) -> str:
    if guide.guide_id.startswith("cust"):
        return "Customized couse* endpoints are user-specific and would make the default interface depend on hidden user state."
    if guide.guide_id.startswith("mob"):
        return "Mobile endpoints are duplicate view surfaces unless desktop/detail JSON cannot preserve the needed source information."
    return "Rejected from the default surface."


def required_param_names(guide: Guide) -> str:
    names = unique_names([
        param.get("name", "")
        for param in guide.parameters
        if param.get("required") in {1, True}
    ])
    return ", ".join(names) if names else "-"


def optional_param_names(guide: Guide) -> str:
    names = unique_names([
        param.get("name", "")
        for param in guide.parameters
        if param.get("required") not in {1, True}
    ])
    return ", ".join(names[:8]) + ("..." if len(names) > 8 else "") if names else "-"


def unique_names(names: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for name in names:
        if not name or name in seen:
            continue
        seen.add(name)
        unique.append(name)
    return unique


def supported_formats(guide: Guide) -> str:
    formats = []
    if guide.supports_json:
        formats.append("JSON")
    if guide.supports_xml:
        formats.append("XML")
    if guide.supports_html:
        formats.append("HTML")
    return ", ".join(formats) if formats else "-"


def md_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def render_markdown(db_path: Path, guides: list[Guide]) -> str:
    classifications = {guide.guide_id: classify(guide) for guide in guides}
    counts = Counter(classification.tier for classification in classifications.values())
    module_counts: dict[str, Counter] = defaultdict(Counter)
    for classification in classifications.values():
        module_counts[classification.tier][classification.module] += 1

    lines: list[str] = []
    lines.append("# MOLEG-API Catalog Audit")
    lines.append("")
    lines.append("Generated from the local MOLEG OpenAPI catalog SQLite database.")
    lines.append("")
    lines.append("## Source")
    lines.append("")
    lines.append(f"- DB: `{db_path}`")
    lines.append(f"- Audited guides: {len(guides)}")
    lines.append(f"- Classification counts: core {counts['core']}, optional {counts['optional']}, rejected {counts['rejected']}")
    lines.append("")
    lines.append("## Audit Stance")
    lines.append("")
    lines.append("This audit classifies source endpoints by whether they should sit behind a deep legislative-expert interface. `core` does not mean one public function per endpoint; ministry interpretation endpoints, for example, should be registry-backed behind `search_interpretations()` / `get_interpretation()` rather than exposed as dozens of shallow functions.")
    lines.append("")
    lines.append("The first implementation slice should use the current-statutes core: law-name search or a `congress-db` promulgation bridge candidate, normalized law identity, and effective-date text or article retrieval through the public interface.")
    lines.append("")
    lines.append("## Counts By Module")
    lines.append("")
    lines.append("| Tier | Module | Count |")
    lines.append("|---|---:|---:|")
    for tier in ("core", "optional", "rejected"):
        for module, count in sorted(module_counts[tier].items()):
            lines.append(f"| {tier} | {module} | {count} |")
    lines.append("")
    lines.append("## Key Findings")
    lines.append("")
    lines.append("- Effective-date statute endpoints (`eflaw`, `eflawjosub`) and promulgation-date endpoints (`law`, `lawjosub`) are separate; the public interface must make `basis` explicit and default to effective-date lookup for current-force questions.")
    lines.append("- `lsHstListGuide` / `lsHstInfoGuide` are HTML-only in the catalog, so history parsing must document and test HTML behavior instead of assuming JSON.")
    lines.append("- Article endpoints require MOLEG's six-digit `JO` format; callers should pass human article notation while the implementation formats `JO` internally.")
    lines.append("- The ministry interpretation family is large and regular; it should be a registry-backed source family, not dozens of public functions.")
    lines.append("- Mobile and customized endpoints should stay out of the default surface unless a documented fallback or user-specific scenario proves otherwise.")
    lines.append("")
    lines.append("## Full Endpoint Classification")
    lines.append("")
    lines.append("| Tier | Module | Guide | Title | Category | Operation | Target | Formats | Required Params | Reason |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for guide in guides:
        classification = classifications[guide.guide_id]
        category = f"{guide.category} / {guide.subcategory}".strip(" /")
        lines.append(
            "| "
            + " | ".join(
                [
                    classification.tier,
                    classification.module,
                    f"`{md_escape(guide.guide_id)}`",
                    md_escape(guide.title),
                    md_escape(category),
                    md_escape(guide.operation_kind),
                    f"`{md_escape(guide.target)}`",
                    md_escape(supported_formats(guide)),
                    md_escape(required_param_names(guide)),
                    md_escape(classification.reason),
                ]
            )
            + " |"
        )
    lines.append("")
    lines.append("## Parameter Notes For First Slice")
    lines.append("")
    first_slice_ids = [
        "lsEfYdListGuide",
        "lsEfYdInfoGuide",
        "lsEfYdJoListGuide",
        "lsNwListGuide",
        "lsNwInfoGuide",
        "lsNwJoListGuide",
    ]
    lines.append("| Guide | Required Params | Optional Params To Hide Behind Interface |")
    lines.append("|---|---|---|")
    guide_by_id = {guide.guide_id: guide for guide in guides}
    for guide_id in first_slice_ids:
        guide = guide_by_id[guide_id]
        lines.append(
            f"| `{guide.guide_id}` | {md_escape(required_param_names(guide))} | {md_escape(optional_param_names(guide))} |"
        )
    lines.append("")
    lines.append("## Next Implementation Step")
    lines.append("")
    lines.append("Implement the first vertical slice with deterministic tests around the public interface: `search_laws()`, `resolve_promulgated_law()`, `get_law()`, and `get_article()`. Use a fake or recorded MOLEG adapter for normal tests, and keep live smoke tests behind a separate marker/command using `MOLEG_OC`.")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--output", type=Path, default=Path("docs/design/MOLEG-API-AUDIT.md"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    guides = load_guides(args.db)
    if len(guides) != 195:
        raise SystemExit(f"Expected 195 guides, found {len(guides)}")

    classified_ids = {guide.guide_id for guide in guides if classify(guide).tier}
    missing = {guide.guide_id for guide in guides} - classified_ids
    if missing:
        raise SystemExit(f"Unclassified guides: {sorted(missing)}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_markdown(args.db, guides), encoding="utf-8")
    print(f"Wrote {args.output} ({len(guides)} guides)")


if __name__ == "__main__":
    main()
