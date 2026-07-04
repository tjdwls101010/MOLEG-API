"""Literal type aliases for public MOLEG models."""

from __future__ import annotations

from typing import Literal

Basis = Literal["effective", "promulgated"]
AnnexFormSource = Literal["law", "administrative_rule"]
AnnexSearchScope = Literal["title", "source", "body"]
AnnexType = Literal[
    "annex",
    "별표",
    "form",
    "서식",
    "attached_form",
    "별지",
    "separate",
    "별도",
    "appendix",
    "부록",
]
InterpretationSearchSource = Literal["moleg", "ministry", "all", "all_ministries"]
CaseCourt = Literal["all", "supreme", "lower"]
BundleMode = Literal["question", "promulgated_bill", "statute_review"]
BundleRequestMode = Literal["question", "promulgated_bill", "statute_review", "institutional_system", "delegated_criteria"]
BundleBudget = Literal["minimal", "standard", "broad"]
