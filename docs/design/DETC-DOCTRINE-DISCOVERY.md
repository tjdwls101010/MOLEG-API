# Constitutional Doctrine Discovery

Discovery for issue #68. The question was whether law.go.kr `detc` exposes a structured doctrine, principle, category, or issue field that MOLEG-API can surface as a source-backed `search_constitutional_decisions(doctrine=...)` filter.

## Finding

Not feasible with the current source surface. The law.go.kr `detc` list and detail catalog does not expose a structured doctrine/category/principle field. Do not add a `doctrine` parameter to `search_constitutional_decisions()` unless a future catalog or live response adds an explicit source field.

The legislative-expert skill may still search for doctrine terms such as `과잉금지원칙`, `평등원칙`, or `기본권 제한` as free-text queries, preferably with `search_body=True`, but those are keyword searches, not doctrine-indexed retrieval.

## Catalog Evidence

Authoritative local catalog: `.Seongjin/DataBases/법제처 api.db`.

`detcListGuide` parameters:

- `search` — search scope: `1` 사건명, `2` 본문검색
- `query` — free-text query
- `display`, `page`
- `gana`
- `sort`
- `date`, `edYd`
- `nb`
- `popYn`

No doctrine/category/principle parameter exists.

`detcListGuide` response fields:

- `target`
- `키워드`
- `section`
- `totalCnt`
- `page`
- `detc id`
- `헌재결정례일련번호`
- `종국일자`
- `사건번호`
- `사건명`
- `헌재결정례 상세링크`

`detcInfoGuide` response fields:

- `헌재결정례일련번호`
- `종국일자`
- `사건번호`
- `사건명`
- `사건종류명`
- `사건종류코드`
- `재판부구분코드`
- `판시사항`
- `결정요지`
- `전문`
- `참조조문`
- `참조판례`
- `심판대상조문`

Fields such as `판시사항`, `결정요지`, and `전문` can mention doctrines in prose, but they are not structured source labels.

## Live Check

With local `MOLEG_OC` available through `.env.local`, `LawGoKrClient().service("detc", {"ID": "58400"})` returned only these detail keys:

`결정요지`, `사건명`, `사건번호`, `사건종류명`, `사건종류코드`, `심판대상조문`, `재판부구분코드`, `전문`, `종국일자`, `참조조문`, `참조판례`, `판시사항`, `헌재결정례일련번호`.

No key containing `법리`, `원칙`, `분류`, `유형`, `쟁점`, `심사`, or `기본권` was present. Sample list searches for doctrine-like terms were query-sensitive and returned no rows in this run, so the catalog response-field evidence remains the stronger proof for the list surface.

## Decision For MOLEG-API

- Keep `search_constitutional_decisions(query, *, search_body=False, decided_on=None, case_number=None, display=20)` unchanged.
- Do not synthesize doctrine labels from `판시사항`, `결정요지`, or `전문`.
- Treat doctrine retrieval as a free-text search plus selective detail loading until law.go.kr exposes a structured doctrine field.
