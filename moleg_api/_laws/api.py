from __future__ import annotations

from .api_admin_rules import AdministrativeRuleMixin
from .api_annex import AnnexMixin
from .api_article_context import ArticleContextMixin
from .api_authority_context import AuthorityContextMixin
from .api_bundle import LegalContextBundleMixin
from .api_compare import LawCompareMixin
from .api_comparable import ComparableMechanismsMixin
from .api_delegated_criteria import DelegatedCriteriaMixin
from .api_followups import FollowupMixin
from .api_history import LawHistoryMixin
from .api_institutional import InstitutionalSystemMixin
from .api_interpretations import InterpretationMixin
from .api_judicial import JudicialDecisionMixin
from .api_law_loaders import LawLoadersMixin
from .api_query_expansion import QueryExpansionMixin
from .api_search import LawSearchMixin
from .api_structure import LawStructureMixin
from .api_versions import LawVersionMixin

class MolegApi(
    FollowupMixin,
    LawSearchMixin,
    LawLoadersMixin,
    ArticleContextMixin,
    LawHistoryMixin,
    LawVersionMixin,
    LawCompareMixin,
    LawStructureMixin,
    AnnexMixin,
    AdministrativeRuleMixin,
    InterpretationMixin,
    JudicialDecisionMixin,
    AuthorityContextMixin,
    QueryExpansionMixin,
    ComparableMechanismsMixin,
    InstitutionalSystemMixin,
    DelegatedCriteriaMixin,
    LegalContextBundleMixin,
):
    pass

__all__ = ["MolegApi"]
