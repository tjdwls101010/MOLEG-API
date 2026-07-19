"""Public data models for the first MOLEG-API vertical slice."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, fields, is_dataclass
from typing import Any, Literal

from ._models import (
    AdministrativeRuleArticleText,
    AdministrativeRuleContext,
    AdministrativeRuleHit,
    AdministrativeRuleIdentity,
    AdministrativeRuleText,
    Ambiguity,
    AnnexFormHit,
    AnnexFormIdentity,
    AnnexFormSource,
    AnnexFormText,
    AnnexSearchScope,
    AnnexType,
    ArticleContext,
    ArticleReference,
    ArticleText,
    AuthorityContext,
    Basis,
    BundleBudget,
    BundleMode,
    BundleRequest,
    BundleRequestMode,
    CandidateContext,
    CaseCourt,
    ContextGap,
    DeferredLookup,
    DelegatedRule,
    DelegationGraph,
    FollowUpSearch,
    HistoryEvent,
    InterpretationHit,
    InterpretationIdentity,
    InterpretationSearchSource,
    InterpretationText,
    JudicialDecisionHit,
    JudicialDecisionIdentity,
    JudicialDecisionText,
    LawDiff,
    LawDiffChange,
    LawHit,
    LawHistory,
    LawIdentity,
    LawStructure,
    LawStructureNode,
    LawText,
    LegalArticleCandidate,
    LegalContextBundle,
    LegalLawCandidate,
    LegalQueryExpansion,
    LegalTermCandidate,
    LawToc,
    LawTocEntry,
    LoadedContext,
    RevisionReason,
    StructuredTableData,
    SupplementaryProvision,
    install_serialization_methods,
)
from ._models.serialization import (
    _dedupe_key,
    _json_sort_key,
    _model_to_dict,
    _model_to_json_string,
    _serialize_dataclass,
    _serialize_dict,
    _serialize_disambiguated_key,
    _serialize_key,
    _serialize_value,
    _serialized_entry_sort_key,
)

install_serialization_methods(globals(), public_module=__name__)

__all__ = [
    name
    for name, value in globals().items()
    if not name.startswith("_") and name not in {"annotations", "json"}
]
