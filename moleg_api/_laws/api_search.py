from __future__ import annotations

from .support import *

class LawSearchMixin:
    def search_laws(
        self,
        query: str,
        *,
        as_of: str | None = None,
        basis: Basis = "effective",
        law_type: str | None = None,
        ministry: str | None = None,
        display: int = 20,
    ) -> list[LawHit]:
        """Search law.go.kr for statute identity candidates.

        Use when: the skill has a law name, keyword, or expanded search term
        and needs candidate current or promulgated statute identities.
        Returns: a list of `LawHit` values carrying normalized `LawIdentity`
        objects plus the source row; an empty list means no source rows.
        Raises: source adapter errors or parse errors if a returned row cannot
        be normalized; no-result is represented as an empty list.
        Related: use `resolve_promulgated_law` for congress-db bridge fields
        and `expand_legal_query` when the query itself needs planning.
        """
        query = require_query(query)
        target = target_for(basis, "list")
        params: dict[str, Any] = {"query": query, "display": display}
        if basis == "promulgated":
            # The `law` search endpoint hides 시행예정(future-effective) rows by
            # default; a promulgated-basis search (and the promulgation bridge)
            # must see just-promulgated future amendments, so include them.
            params["nw"] = 1
        if as_of:
            params["efYd" if basis == "effective" else "date"] = compact_date(as_of)
        if law_type:
            params["knd"] = law_type
        if ministry:
            params["org"] = ministry

        payload = self.source.search(target, params)
        hits: list[LawHit] = []
        for row in unwrap_search_laws(payload):
            identity = normalize_law_identity(row, basis=basis)
            hits.append(
                LawHit(
                    identity=identity,
                    raw=row,
                    follow_up=law_hit_follow_up(identity),
                )
            )
        return hits

    def resolve_promulgated_law(
        self,
        *,
        prom_law_nm: str | None = None,
        prom_no: str | None = None,
        promulgation_dt: str | None = None,
    ) -> LawIdentity:
        """Resolve a congress-db promulgation bridge to one law identity.

        Use when: a National Assembly bill row has reached the promulgation
        side and provides bridge fields such as law name, promulgation number,
        or promulgation date.
        Returns: one normalized `LawIdentity` on the promulgated basis.
        Raises: `NoResultError` when required bridge fields are missing or no
        source row matches; `AmbiguousLawError` when several identities remain.
        Related: `search_laws(basis="promulgated")` is free-text discovery;
        this method is the stricter bridge resolver for enacted bill facts.
        """
        law_name = string_value(prom_law_nm)
        law_name = law_name.strip() if law_name else None
        if not law_name:
            raise NoResultError(
                "prom_law_nm is required to resolve a promulgated law without unbounded source search"
            )

        hits = self.search_laws(law_name, basis="promulgated")
        filtered = [
            hit
            for hit in hits
            if matches_bridge(hit.identity, prom_no=prom_no, promulgation_dt=promulgation_dt)
        ]
        if not filtered:
            raise NoResultError("No law identity matched the promulgation bridge")
        identities = dedupe_identities([hit.identity for hit in filtered])
        if len(identities) > 1:
            names = ", ".join(identity.name for identity in identities[:5])
            raise AmbiguousLawError(
                f"Promulgation bridge matched multiple laws: {names}",
                kind="promulgation_bridge",
                candidates=identities,
            )
        return identities[0]

__all__ = [name for name in globals() if not name.startswith("__")]
