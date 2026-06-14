# MOLEG-API Context

MOLEG-API is the legal-source layer for a future legislative-expert skill. It turns the law.go.kr OpenAPI catalog into deep task-level interfaces for current law research and legislative review.

## Language

**MOLEG-API**:
This repository's interface over law.go.kr sources for current statutes, articles, delegated rules, administrative rules, official interpretations, cases, constitutional decisions, and legal terminology.
_Avoid_: legislative copilot, congress-db client, generic OpenAPI SDK

**Legislative-Expert Skill**:
The future agent-facing skill that will combine `congress-db` SQL, MOLEG-API, and WebSearch to answer legislative design and review questions.
_Avoid_: treating this repository itself as the whole skill

**congress-db**:
The National Assembly fact database for bills, votes, minutes, meeting-bill links, and promulgation bridge fields.
_Avoid_: using MOLEG-API for National Assembly bill status or vote facts

**Promulgation Bridge**:
The `congress-db` fields (`prom_law_nm`, `prom_no`, `promulgation_dt`) that connect a passed/promulgated bill to a law.go.kr law identity.
_Avoid_: assuming every bill has become current law

**Current Statute**:
A statute available through law.go.kr as currently relevant legal text. It may be queried by promulgation-date basis or effective-date basis.
_Avoid_: proposed bill, pending bill

**Promulgation-Date Basis**:
MOLEG lookup based on promulgation date and promulgation number. Useful for historical linkage and promulgation bridge resolution.
_Avoid_: using it as the default answer to "what is in force now?"

**Effective-Date Basis**:
MOLEG lookup based on the date a legal text is or was effective. This is the preferred basis for current-force questions.
_Avoid_: 공포일 기준

**Law Identity**:
The normalized identity MOLEG-API exposes for a law: law ID, sequence/master keys where available, law name, promulgation date, effective date, promulgation number, and source basis.
_Avoid_: treating `ID`, `MST`, `LID`, and `lsi_seq` as interchangeable without proof

**Article**:
A law provision addressed by human notation such as "제2조" or "제10조의2". MOLEG may require this as a six-digit `JO` value internally.
_Avoid_: forcing callers to pass raw `JO`

**Delegated Rules**:
The enforcement decrees, enforcement rules, notices, and administrative rules that a statute delegates to or depends on.
_Avoid_: stopping at statute text when implementation criteria are delegated

**Administrative Rule**:
MOLEG administrative-rule sources such as notices, directives, and established rules that often carry practical execution criteria.
_Avoid_: treating as lower-value by default

**Official Interpretation**:
MOLEG 법령해석례. It is an official interpretation source but has a different authority from court cases or Constitutional Court decisions.
_Avoid_: generic "interpretation" that erases source authority

**Ministry First-Instance Interpretation**:
Central ministry legal interpretations exposed as the `cgmExpc...` endpoint family. They should be registry-backed, not one public function per ministry.
_Avoid_: dozens of shallow ministry functions

**Case**:
Supreme Court precedent from law.go.kr `prec` endpoints.
_Avoid_: mixing with Constitutional Court decisions without a source label

**Constitutional Decision**:
Constitutional Court decision from law.go.kr `detc` endpoints.
_Avoid_: treating as ordinary precedent

**Legal Query Expansion**:
Use of law terms, everyday terms, related terms, related articles, intelligent search, and law abbreviations to plan searches.
_Avoid_: treating query expansion output as final legal authority

**WebSearch Context**:
Current social context, news, statistics, and government announcements outside MOLEG's legal corpus.
_Avoid_: trying to answer latest social facts from MOLEG-API

## Relationships

- The **Legislative-Expert Skill** uses **congress-db**, **MOLEG-API**, and **WebSearch Context** together.
- A **Promulgation Bridge** may resolve to a **Law Identity**.
- A **Law Identity** has one or more **Articles**.
- A **Current Statute** can be inspected by **Promulgation-Date Basis** or **Effective-Date Basis**.
- A **Current Statute** may delegate implementation detail to **Delegated Rules** and **Administrative Rules**.
- **Official Interpretations**, **Ministry First-Instance Interpretations**, **Cases**, and **Constitutional Decisions** are distinct authority types.

## Flagged Ambiguities

- "현행법령" can mean promulgation-date or effective-date lookup in the source API. Resolved for callers: MOLEG-API must make the basis explicit and default current-force questions to effective-date reasoning.
- "법령 ID" can refer to multiple source keys. Resolved for callers: expose a normalized **Law Identity** and keep raw key handling inside implementation/docs.
