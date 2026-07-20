# API 레퍼런스

`MolegApi`가 `moleg_api`의 단일 공개 클래스다. **33개 과업 메서드**를 노출한다.

```python
from moleg_api import MolegApi

api = MolegApi()                  # 내장 기본 자격증명, 등록 불필요
hits = api.search_laws("주택임대차보호법", display=5)
article = api.get_article(hits[0].identity, "제7조")
print(article.text)
```

**생성자** — `MolegApi(source=None)`. 기본값은 라이브 `LawGoKrClient`를 만든다. `source=`는 테스트용 주입이나 자격증명 세부 제어에만 쓴다.

모든 메서드는 같은 이름의 kebab-case CLI 서브커맨드를 갖는다(`get_law_toc`만 예외로 `get-law --toc`에 접힌다). → [CLI Reference](CLI-Reference.md)

## 전체에 적용되는 규약

**식별자.** 로더는 `LawIdentity`, 검색에서 받은 `*Hit`, 또는 원시 ID 문자열을 받는다. 검색에서 받은 객체를 그대로 넘기는 것이 가장 안전하다 — 판본을 가리키는 `mst`가 함께 따라가기 때문이다. **법령 이름 문자열은 거부된다.**

**`basis`와 `as_of`.** `basis="effective"`(기본)는 시행 중인 텍스트, `"promulgated"`는 공포본. `as_of="YYYYMMDD"`(또는 `"YYYY-MM-DD"`)는 그 시점에 시행 중이던 판본.

**조문 표기.** `"제10조의2"` 같은 사람 표기나 정수를 그대로 넘긴다. 여섯 자리 `JO` 값을 만들 일이 없다.

**키워드 전용.** `*` 뒤의 인자는 전부 키워드 전용이다.

**직렬화.** 모든 반환 타입이 아래 두 헬퍼를 갖는다.

```python
result.to_dict()                    # 중첩 dict. 원본 페이로드 제외
result.to_dict(include_raw=True)    # law.go.kr 원본 포함
result.to_json_string()             # JSON 문자열. include_raw도 받는다
```

리스트를 받았으면 원소별로: `[hit.to_dict() for hit in hits]`

---

## 1. 검색·계획 — 후보를 준다

**결과는 후보 메타데이터다. 로더가 본문을 실어 오기 전에는 법적 실질을 인용할 수 없다.** 대부분의 검색 결과는 알맞은 상세 로더를 가리키는 `follow_up`을 함께 단다.

```python
search_laws(query, *, as_of=None, basis="effective",
            law_type=None, ministry=None, display=20) -> list[LawHit]
```
법령 신원 후보 검색. `basis="promulgated"`면 시행예정 행이 가려지지 않도록 내부에서 `nw=1`을 붙인다.

```python
resolve_promulgated_law(*, prom_law_nm=None, prom_no=None,
                        promulgation_dt=None) -> LawIdentity
```
공포 사실(법령명·공포번호·공포일)에서 **정확히 하나의** 신원으로 잇는 엄격한 해석기. `search_laws`보다 엄격하다 — 여럿 남으면 `AmbiguousLawError`, 없으면 `NoResultError`.

```python
search_administrative_rules(query, *, ministry=None, rule_type=None,
                            issued_on=None, include_history=False,
                            display=20) -> list[AdministrativeRuleHit]
```
고시·훈령·예규 검색. **`issued_on`은 발령일자이지 시행일이 아니다.**

```python
search_annex_forms(query, *, source="law", search_scope="title",
                   annex_type=None, ministry=None, display=20) -> list[AnnexFormHit]
```
별표·서식 검색. 과태료 기준·수수료표·부과기준이 실제로 사는 곳이다.
`source ∈ {law, administrative_rule}`, `search_scope ∈ {title, source, body}`.
`annex_type`은 한글/영문 별칭을 받는다 — 별표, 서식, 별지, 별도, 부록 (별도·부록은 `source="law"`에서만).

```python
search_interpretations(query, *, source="moleg", ministry=None,
                       search_body=False, interpreted_on=None,
                       display=20) -> list[InterpretationHit]
```
법령해석 검색. `source ∈ {moleg, ministry, all, all_ministries}`.
`"all"`은 법제처 **+ 지정한 부처 하나**이고, `"all_ministries"`가 40개 부처 전체 팬아웃이다(비용이 크므로 깊은 분석에만).

```python
search_cases(query, *, court="all", court_name=None, search_body=False,
             decided_on=None, case_number=None, display=20) -> list[JudicialDecisionHit]

search_constitutional_decisions(query, *, search_body=False, decided_on=None,
                                case_number=None, display=20) -> list[JudicialDecisionHit]
```
판례 / 헌재 결정 검색. `court ∈ {all, supreme, lower}`. **기본은 제목 검색**이므로 본문까지 훑으려면 `search_body=True`.

```python
search_committee_decisions(query=None, *, committee, display=20) -> list[AdjudicationHit]
search_administrative_appeals(query=None, *, tribunal="decc", display=20) -> list[AdjudicationHit]
```
위원회 의결 / 행정심판 재결 검색. 코드 목록은 [CLI Reference](CLI-Reference.md) 또는 [Sources & Coverage](Sources-and-Coverage.md)에 있다. 모르는 코드는 `UnsupportedFormatError`를 낸다 — "기록 없음"으로 오해되지 않게 하기 위해서다.

```python
expand_legal_query(query, *, display=5,
                   include_websearch_hint=True) -> LegalQueryExpansion
```
검색 *계획* 도구. 법률 용어·일상 용어·관련 법령·관련 조문 후보와 실행 가능한 `follow_up_searches`를 준다. **권위가 아니다.** 빈 질의에만 `NoResultError`를 내고, 선택적 출처의 실패는 예외가 아니라 `gaps`로 기록된다.

```python
find_comparable_mechanisms(concept, *, display=5) -> list[LawIdentity]
```
유사 제도 발견 — 과징금·인허가·신고제 같은 개념을 쓰는 다른 법령들. 입법 설계 비교용이며 **법적 동등성의 판단이 아니다.** 조문 앵커가 각 후보의 `raw_keys`에 보존된다.

> `search_*`는 결과가 없으면 **빈 리스트**를 준다(예외 아님). `expand_legal_query`와 `find_comparable_mechanisms`는 빈 질의에 `NoResultError`를 낸다.

---

## 2. 본문 로드 — 인용 가능

```python
get_law(identifier, *, as_of=None, basis="effective",
        articles=None, include_metadata=True) -> LawText
```
법령 본문. 조문 목록과 부칙을 함께 준다. `articles=["제3조", "제7조"]`로 좁힐 수 있다.

```python
get_law_toc(law_identifier, *, as_of=None, basis="effective",
            include_metadata=False) -> LawToc
```
장 제목과 조문 스텁(번호·제목·삭제/이동 상태)만 문서 순서대로. **본문 없음.** 컨텍스트 예산 장치이며 CLI에서는 `get-law --toc`다.

```python
get_article(law_identifier, article, *, as_of=None,
            basis="effective") -> ArticleText
```
조문 하나. 사람 표기로 부른다.

```python
load_article_context(law_identifier, article, *, as_of=None,
                     basis="effective", follow_moved=True) -> ArticleContext
```
조문을 싣되 **이동·삭제 표시를 해소한다.** 「삭제」나 「제12조로 이동」 스텁을 운용 조문으로 착각하지 않게 한다. 목적지 로드가 실패하면 예외가 아니라 `ContextGap`으로 떨어진다.

```python
get_administrative_rule(identifier, *, articles=None,
                        include_metadata=True) -> AdministrativeRuleText

load_administrative_rule_context(identifier, *, articles=None,
                                 include_metadata=True,
                                 follow_moved=True) -> AdministrativeRuleContext
```
행정규칙 본문 / 이동 해소판. `identifier`는 신원 객체, 히트, 일련번호, 또는 정확한 이름을 받는다.

```python
get_annex_form_body(identifier, *, source="law", title=None,
                    include_metadata=True,
                    attempt_structuring=True) -> AnnexFormText
```
별표·서식 본문. `attempt_structuring=True`면 표를 `StructuredTableData`로 재구성해 붙인다 — **다만 `parsing_confidence`를 확인하라.** `low`거나 행이 비었으면 평문 `text`로 돌아가야 하며, 그걸 "기준 없음"으로 읽으면 안 된다.

```python
get_interpretation(identifier, *, source=None, ministry=None,
                   include_metadata=True) -> InterpretationText
```
해석 본문(질의요지·회답·이유·관련법령). 부처 해석은 `source="ministry", ministry="…"`가 필요하다. 두 부처(국세청·재정경제부)는 검색은 되지만 본문 조회가 안 되며 `UnsupportedFormatError`를 낸다.

```python
get_case(identifier, *, include_metadata=True) -> JudicialDecisionText
get_constitutional_decision(identifier, *, include_metadata=True) -> JudicialDecisionText
```
판례 / 헌재 결정 본문. **로더가 태그를 교차 검증한다** — 헌재 신원을 `get_case`에 넘기면(또는 그 반대) `UnsupportedFormatError`가 난다. 권위 유형이 섞이는 것을 타입 수준에서 막는다.

```python
get_committee_decision(decision_id, *, committee) -> AdjudicationText
get_administrative_appeal(decision_id, *, tribunal="decc") -> AdjudicationText
```
위원회 의결 / 행정심판 재결 본문. 결과는 이것이 판례가 **아님**을 밝히는 권위 문장을 항상 달고 나온다.

---

## 3. 연혁·개정·비교·체계

```python
trace_law_history(law_identifier, *, date_range=None, article=None,
                  promulgation_bridge=None) -> LawHistory
```
개정 연혁. `HistoryEvent`에 공포번호·시행일·개정 유형·사유가 담긴다. `date_range`는 `(from, to)` 튜플이다. 전체 법 연혁은 law.go.kr이 **HTML로만** 주는 경로를 파싱한다.

```python
get_revision_reason(law_identifier, *, mst=None, as_of=None,
                    include_metadata=True) -> RevisionReason
```
특정 **판본**의 「개정이유 및 주요내용」. 판본 선택 규칙:

- `mst`를 주면 그 판본으로 정확히 고정 (연혁 이벤트의 `identity.mst`를 쓴다)
- `as_of`를 주면 그날 시행 중이던 판본
- **둘 다 없으면** 파일상 가장 최신 시행일 판본 — 이것이 **미래 시행 판본일 수 있다**

오래된 판본은 이유도 공포문도 없는 경우가 흔하고, 그러면 `NoResultError`다.

> 개정이유는 **제안자의 자기 진술**이며 그 판본 하나에만 적용된다. 중립적 요약이 아니다.

```python
compare_law_versions(law_identifier, *, before=None, after=None,
                     article=None) -> LawDiff
```
개정 전후 대비. **임의의 두 날짜 구간은 지원하지 않는다** — 출처가 못 한다. `UnsupportedFormatError`가 난다. 임의 두 시점을 비교하려면 `get_article`을 `as_of` 달리해 두 번 부르라.

```python
find_delegated_rules(law_identifier, *, article=None) -> DelegationGraph
get_law_structure(law_identifier, *, depth=0) -> LawStructure
```
조문 단위 위임 관계 / 법령 체계도(법률 → 시행령 → 시행규칙 → 행정규칙). 둘은 다른 질문에 답한다 — 체계도는 계층 맥락일 뿐 조문 단위 위임의 증거가 아니다.

**`find_delegated_rules`의 결과에 별표는 없다.** 과태료 기준표 같은 것은 `search_annex_forms`로 따로 찾아야 한다.

---

## 4. 권위·번들

```python
load_authority_context(law_identifier, *, articles, query=None,
                       budget="standard", as_of=None) -> AuthorityContext
```
정밀 도구. **지정한 조문들에 스코프를 건** 해석·판례·헌재 결정을 모으고, 조문과 어긋나거나 날짜가 없거나 개정 이전인 것을 걸러낸다. `articles`는 **필수 키워드**다.

인용은 결과의 **`current_authorities`**에서 하라. `loaded`에는 실린 것 전부가, `current_authorities`에는 실제로 대상 조문을 참조하고 시점이 맞는 것만 남는다.

```python
load_legal_context_bundle(query=None, *, promulgation_bridge=None,
                          law_identifier=None, articles=None,
                          mode="question", budget="standard",
                          as_of=None) -> LegalContextBundle
```
넓은 질문에 대한 한 번의 제한된 1차 통과.

| `mode` | 필요한 것 | 동작 |
|---|---|---|
| `"question"` | `query` | 질의 확장 후 후보 탐색. 법령 후보가 **여럿이면 자동 선택하지 않고** `Ambiguity`와 `gap`을 남긴다 |
| `"promulgated_bill"` | `promulgation_bridge` | 공포 사실에서 신원을 잇는다. law.go.kr 미반영 지연도 gap으로 기록 |
| `"statute_review"` | `law_identifier` | 탐색 없이 바로 그 법령으로 |

```python
load_institutional_system(statute_identifiers, *, articles=None,
                          budget="standard", as_of=None) -> LegalContextBundle
```
**이미 고른** 법령 집합을 하나의 제도로 훑는다. 집합을 발견하거나 무엇이 주된 법인지 결정하지 않는다. 개별 법령의 실패는 예외가 아니라 기록된다.

```python
load_delegated_criteria(law_identifier, *, articles=None, query=None,
                        budget="standard", as_of=None) -> LegalContextBundle
```
법령 하나에 닻을 내리고 행정규칙과 별표·서식의 **본문까지** 제한적으로 싣는다. 이름이 아니라 구체적 집행 기준이 필요할 때.

```python
load_followup(lookup) -> Any
```
`DeferredLookup` 또는 `FollowUpSearch`를 실행한다. `interface` 문자열로 알맞은 공개 메서드에 라우팅한다. `websearch*`·`congress-db*`는 `UnsupportedFormatError` — 의도된 경계 표시다.

> **`budget`만으로 결정되지 않는다.** 번들의 상세 로드는 질의 내용이 함께 정한다. `"위헌"` 같은 키워드가 없으면 `--budget broad`여도 헌재 결정을 싣지 않는다. → [Agent Integration](Agent-Integration.md)의 의도 게이트

---

## 공개 데이터클래스

전부 `@dataclass(frozen=True)`이며 `moleg_api`에서 직접 임포트할 수 있다.

### 법령

| 타입 | 핵심 필드 |
|---|---|
| `LawIdentity` | `law_id` `name` `basis` `mst` `lid` `promulgation_date` `effective_date` `promulgation_number` `law_type` `ministry` `raw_keys` |
| `LawHit` | `identity` `raw` `follow_up` |
| `LawText` | `identity` `articles: list[ArticleText]` `supplementary_provisions` |
| `ArticleText` | `identity` `article` `text` `title` `effective_date` `article_kind` `revision_type` `moved_from` `moved_to` `has_changes` `is_deleted` |
| `ArticleContext` | `requested_article` `current_article` `loaded_articles` `deferred` `gaps` `source_notes` |
| `LawToc` / `LawTocEntry` | `identity` `entries` `article_count` / `article` `title` `heading` `entry_kind` `is_deleted` `moved_to` |
| `SupplementaryProvision` | `source_type` `text` `promulgation_date` `promulgation_number` `title` |
| `LawHistory` / `HistoryEvent` | `identity` `events` `source_failures` / `changed_date` `effective_date` `promulgation_number` `bill_id` `revision_type` `article` `reason` `article_link` |
| `RevisionReason` | `identity` `mst` `reason` `promulgation_text` |
| `LawDiff` / `LawDiffChange` | `identity` `before_identity` `after_identity` `changes` / `article` `before_text` `after_text` `title` |
| `DelegationGraph` / `DelegatedRule` | `identity` `rules` / `source_article` `delegated_type` `delegated_name` `delegated_law_id` `delegated_mst` `delegated_article` `text` |
| `LawStructure` / `LawStructureNode` | `identity` `instruments` / `name` `source_type` `instrument_type` `law_id` `mst` `children`(재귀) |

### 행정규칙 · 별표

| 타입 | 핵심 필드 |
|---|---|
| `AdministrativeRuleIdentity` | `serial_id` `name` `rule_id` `rule_type` `issuing_date` `effective_date` `ministry` `current_status` `source_law_id` `source_law_name` `source_article` |
| `AdministrativeRuleHit` / `Text` / `Context` / `ArticleText` | 법령 쪽과 같은 구조. `Text`는 평문 `text`와 `articles`를 **둘 다** 갖는다 |
| `AnnexFormIdentity` | `annex_id` `title` `source_type` `related_name` `annex_number` `annex_type` `file_link` `pdf_link` `detail_link` |
| `AnnexFormText` | `identity` `text` `file_type` `extraction_method` `extraction_confidence` `structured_data` |
| `StructuredTableData` | `title` `headers` `rows` `units` `parsing_confidence` `notes` |

### 권위

| 타입 | 핵심 필드 |
|---|---|
| `InterpretationIdentity` / `Hit` / `Text` | `interpretation_id` `title` `source_type` `case_number` `reply_agency` / `question` `answer` `reason` `related_laws` `referenced_articles` |
| `JudicialDecisionIdentity` / `Hit` / `Text` | `decision_id` `court` `case_number` `decision_date` / `holdings`(판시사항) `summary`(요지) `full_text`(전문) `referenced_statutes` `reviewed_statutes` `referenced_articles` `reviewed_articles` |
| `AdjudicationIdentity` / `Hit` / `Text` | `decision_id` `body` `body_name` `source_type` `source_authority` `respondent_agency` `review_agency` `decided_on` / `disposition`(주문) `summary`(요지) `reasoning`(이유) `claim` `applicant` `respondent` |
| `ArticleReference` | `law_name` `article` `law_id` — 자유 텍스트에서 파싱한 조문 인용 |

### 번들·후속

| 타입 | 핵심 필드 |
|---|---|
| `LegalContextBundle` | `request` `loaded` `candidates` `deferred` `ambiguities` `gaps` `source_notes` |
| `AuthorityContext` | `request` `target_articles` `loaded` **`current_authorities`** `candidates` `deferred` `gaps` |
| `LoadedContext` | `laws` `articles` `delegations` `law_structures` `administrative_rules` `annex_forms` `interpretations` `cases` `constitutional_decisions` |
| `CandidateContext` | `query_expansion` `laws` `administrative_rules` `annex_forms` `interpretations` `cases` `constitutional_decisions` |
| `BundleRequest` | `query` `mode` `budget` `articles` `statute_ids` `promulgation_bridge` `as_of` |
| `DeferredLookup` / `FollowUpSearch` | `interface` `query` `reason` `source_type` `filters` |
| `Ambiguity` | `kind` `message` `candidates` |
| `ContextGap` | `kind` `reason` `query` `recommended_interface` |
| `LegalQueryExpansion` | `original_query` `law_candidates` `term_candidates` `related_terms` `related_articles` `related_laws` `follow_up_searches` `empty_sources` `source_failures` |

### 리터럴 타입 별칭

| 별칭 | 값 |
|---|---|
| `Basis` | `effective`, `promulgated` |
| `AnnexFormSource` | `law`, `administrative_rule` |
| `AnnexSearchScope` | `title`, `source`, `body` |
| `AnnexType` | `annex`/`별표`, `form`/`서식`, `attached_form`/`별지`, `separate`/`별도`, `appendix`/`부록` |
| `InterpretationSearchSource` | `moleg`, `ministry`, `all`, `all_ministries` |
| `CaseCourt` | `all`, `supreme`, `lower` |
| `BundleMode` | `question`, `promulgated_bill`, `statute_review` |
| `BundleBudget` | `minimal`, `standard`, `broad` |

---

## 직렬화 계약

`to_dict(include_raw=False)` / `to_json_string(include_raw=False)`.

- **재귀적** — 중첩 데이터클래스, 리스트, 튜플, 집합, 딕셔너리를 모두 따라 내려간다.
- **`raw` 필드는 기본적으로 빠진다.** 컨텍스트 예산 때문이다. `raw_keys`는 감사용이라 항상 남는다.
- `to_json_string`은 `ensure_ascii=False`(한글 그대로)와 `sort_keys=True`(diff 안정)로 찍는다.
- 집합은 정렬해서 리스트로 나간다 — 출력이 결정적이어야 하기 때문이다.
- 비문자열 딕셔너리 키는 충돌 없이 처리된다. `{1: "a", "1": "b"}`가 손실 없이 직렬화된다.
- `LawToc`의 항목은 빈 필드를 생략한다. 보통은 "값 없음"도 정보지만 139줄짜리 목차에서는 자리표시자가 페이로드의 대부분이 된다.

---

## 예외

전부 `MolegApiError`의 하위 클래스다. 상세는 [Error Handling](Error-Handling.md).

| 예외 | 의미 | 재시도? |
|---|---|---|
| `NoResultError` | 쓸 만한 결과 없음 | 무의미 |
| `AmbiguousLawError` | 복수 신원. `.kind` `.candidates` 보유 | 해당 없음 |
| `UnsupportedFormatError` | 이 인터페이스 밖의 형식·경로·핸드오프 | 무의미 |
| `ParseFailureError` | 응답을 모델로 정규화하지 못함 | 무의미 |
| `AsOfBeforeCoverageError` | `as_of`가 통합본 커버리지 이전. `.law_id` `.earliest_available` 보유 | 무의미(영구) |
| `SourceApiError` | law.go.kr 실패 또는 잘못된 응답 | 경우에 따라 |
| `RateLimitError` | HTTP 429. `SourceApiError`의 하위 | **가능** |
| `RetryExhaustedError` | 재시도 가능한 실패가 전부 소진. `SourceApiError`의 하위 | **가능** |

**출처 접근 실패는 법적 부재가 아니다.** `SourceApiError` 계열을 잡았을 때 재시도하거나 출처 공백으로 드러내라. 그 법·권위·규칙이 존재하지 않는다고 결론짓지 마라.

---

## 관련 문서

- [Core Concepts](Core-Concepts.md) — 왜 이렇게 나뉘어 있는지
- [Agent Integration](Agent-Integration.md) — 엔벨로프 신호와 컨텍스트 예산
- [CLI Reference](CLI-Reference.md) — 같은 메서드의 셸 표면
- [Sources & Coverage](Sources-and-Coverage.md) — 출처 계열별 커버리지와 한계
