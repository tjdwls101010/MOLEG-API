# 내부 구조

코드를 고치려는 사람을 위한 페이지다. 쓰기만 할 거라면 [Core Concepts](Core-Concepts.md)로 충분하다.

## 전체 지도

```
moleg_api/
├── __init__.py         공개 표면 — 71개 이름 (MolegApi, LawGoKrClient, 예외 9종, 모델 59종)
├── _version.py         버전 리터럴 (단일 진실 공급원)
├── laws.py             파사드 → _laws
├── models.py           파사드 → _models + 직렬화 메서드 설치
├── normalization.py    파사드 → _normalization
├── cli.py              파사드 → _cli
├── errors.py           예외 계층
├── source.py           HTTP 전송 + MolegSource 프로토콜
│
├── _laws/          9,297줄 · 66파일   과업 로직
├── _normalization/ 2,240줄 · 16파일   law.go.kr 응답 정규화
├── _cli/           1,491줄 · 13파일   파서·디스패처·신호·엔벨로프
└── _models/          998줄 · 11파일   공개 데이터클래스 + 직렬화
```

루트의 `laws.py`·`models.py`·`normalization.py`·`cli.py`는 **의도적으로 얇은 호환 계층**이다. 0.2.3에서 큰 파일들을 쪼갤 때 기존 임포트가 깨지지 않도록 남겼다.

## `_laws/` — 4계층

과업 로직이 사는 곳이고 가장 큰 패키지다. 네 층으로 나뉜다.

| 층 | 파일 | 역할 |
|---|---|---|
| **1. foundation** | `foundation.py` | 순수 재수출 허브. `..errors`·`..models`·`..normalization`·`..source`를 한 네임스페이스로 모아, 다른 모든 모듈이 `from .foundation import *` 한 줄로 전체 어휘를 본다. 로직 없음 |
| **2. config** | `config.py` | 상수와 정책 테이블. `foundation`만 임포트한다 |
| **3. support** | 약 40개 모듈 | 자유 함수와 상태 데이터클래스. `support.py`가 이들을 의존 순서대로 모으는 단일 집결점 |
| **4. api_\*** | 22개 믹스인 | 공개 메서드. `from .support import *` + 믹스인 클래스 하나 |

`api.py`는 50줄이고 본문이 `pass`다 — **22개 믹스인을 합성하기만 한다.**

```python
class MolegApi(FollowupMixin, LawSearchMixin, LawLoadersMixin, ...):
    pass
```

생성자는 MRO 첫 믹스인인 `FollowupMixin`에 있다.

```python
def __init__(self, source: MolegSource | None = None) -> None:
    self.source = source or LawGoKrClient()
```

모든 믹스인은 `self.source.search / search_html / service / post_text`로 전선에 닿는다.

> **주의 — 후행 별표 임포트.** 일부 support 모듈은 파일 **맨 아래에서** 형제 모듈을 별표 임포트한다. 남은 찌꺼기가 아니라 **의도된 장치**다 — 임포트 순환이 있어도 네임스페이스를 평평하게 유지한다. 모듈을 추가하면 `support.py`에 등록하고, 그 모듈을 필요로 하는 후행 블록에도 넣어야 한다.

### support 모듈 군집

| 군집 | 모듈 | 책임 |
|---|---|---|
| 기반·검증 | `foundation`, `config`, `support`, `validation` | 네임스페이스, 엔드포인트·예산 테이블, 열거값 검증 |
| 신원·파라미터 | `identity_params`, `history_identity`, `authority_sources` | 문자열/히트/신원 → `LawIdentity`, 신원 → DRF 파라미터 |
| gap (연성 실패) | `article_gaps`, `requested_load_gaps`, `context_load_gaps`, `temporal_gaps`, `authority_article_gaps`, `authority_temporal_gaps`, `authority_temporal_filters` | 복구 가능한 실패를 예외 대신 `ContextGap` + `DeferredLookup`으로 |
| 스코프 매칭 | `delegated_scope`, `admin_scope`, `source_matching` | 하위규범·별표가 실제로 대상 조문을 인용하는지 판정 |
| 별표 파싱 | `annex_tables` | 헤더 재도출, 파이프 표·공백 정렬 표 파서 → `StructuredTableData` |
| 후보·랭킹 | `candidates`, `ranking`, `limits_intents` | 행 → 후보 모델, 중복 제거·점수·정렬, 예산→한도, 질의 의도 탐지 |
| 번들 파이프라인 | `bundle_state`, `bundle_modes`, `bundle_primary`, `bundle_candidates`, `bundle_eager`, `bundle_finalize` | 5단계 + 가변 `BundleState` |
| 권위 파이프라인 | `authority_context_pipeline`, `authority_context_details` | 대상 조문 로드 → 후보 검색 → 상세 로드 → 현행 권위 필터 |
| 제도 파이프라인 | `institutional_pipeline`, `institutional_candidates`, `institutional_resolution` | 명시된 법령 집합 순회 |
| 위임기준 파이프라인 | `delegated_criteria_pipeline`, `delegated_criteria_details` | 번들에서 후보 갱신 후 본문 로드 |
| 후속 조회 | `followup_basic`, `followup_identities`, `followup_hits`, `followup_searches`, `followup_routing`, `followup_routing_authority`, `followup_routing_bundle` | 후속 조회 생성·강제 변환·라우팅 |
| 연성 호출 | `bridge` | `safe_list(...)` — "부르고, 실패하면 gap과 deferred를 붙인다"의 범용 래퍼 |
| 레지스트리 | `adjudication_registry` | 위원회·심판기관 코드 표와 권위 문장 |

### 설계 패턴 하나 — 연성 실패

`bridge.safe_list(...)`가 이 패키지의 성격을 가장 잘 보여준다. 번들 로더에서 개별 출처 호출이 실패해도 **예외를 올리지 않는다.** `gaps`에 무엇이 안 메워졌는지, `deferred`에 다시 시도할 방법을 남기고 계속 간다.

이유: 열 개 출처를 훑는 1차 통과에서 하나가 실패했다고 아홉 개를 버리는 것은 손해이고, 무엇이 빠졌는지 호출자가 알 수만 있으면 나머지는 여전히 쓸모 있기 때문이다.

## `_normalization/` — 무엇을 푸는가

law.go.kr OpenAPI는 서로 거의 아무것도 합의하지 않은 엔드포인트 가족이다. 정규화 계층은 그 전부를 frozen 데이터클래스로 평탄화하는 **단일 지점**이다.

실제로 처리하는 난맥상들:

**같은 개념, 다른 이름.** `first_value(row, *keys)`가 존재하는 키 중 첫 번째를 고른다. 별칭 집합이 크다 — 행정규칙의 위임 법령 ID 하나에 **20가지 철자**(위임법령ID / 근거법령ID / 수권법령ID / 상위법령ID / 모법령ID / 법적근거법령ID × 내부 공백 변형)가 있고, 위임 조문 가지 키는 24가지다.

**봉투 대소문자.** law.go.kr은 행 요소 키를 **요청한 target이 아니라 자기 대소문자**로 짓는다 — 판례는 `prec`(소문자)인데 헌재는 `Detc`(대문자)다. 대소문자 무시로 매칭한다.

**모양으로 매칭해야 하는 경우.** 4개 특별 심판기관은 `acrSpecialDecc`를 요청해도 `decc`로 키를 지은 행을 준다. 요청 target으로 키를 잡으면 **아무것도 안 나오고 "이 기관은 기록이 없다"로 읽힌다.** 그래서 이름이 아니라 모양으로 찾는다.

**스칼라 vs 리스트.** 같은 필드가 어떤 때는 문자열, 어떤 때는 배열, 어떤 때는 단일 키 객체다. 장과 절 제목을 동시에 가진 행은 중첩 배열로 오는데, 여기 `str()`을 걸면 파이썬 repr(`[['제3장 …', '제1절 …']]`)이 나오고 그게 법령의 문언인 것처럼 실려 나간다.

**조문 표기 4종.** 이미 포맷된 `제15조의2`, 6자리 `001502`, `15조의2`, 맨 정수 `15`를 전부 받는다.

**날짜.** `compact_date`가 점 표기와 8자리를 처리하지만, 위원회는 `2020.6.8.`처럼 끝점이 붙고 0 패딩이 없는 형태를 내보내 공통 함수를 그냥 통과한다. 정규화 안 된 날짜는 정렬과 비교가 틀리고, **감독 질문에서는 날짜가 곧 발견**이다. 그래서 위원회 전용 날짜 처리가 따로 있다.

**문자열 `"null"`.** 몇몇 출처가 네 글자 문자열 `"null"`을 보낸다. 그대로 두면 진짜 사건번호나 제목처럼 답에 실린다.

**HTML만 주는 엔드포인트.** 연혁(`lsHistory`)은 HTML만 준다. 표준 `HTMLParser`로 파싱하며 **정확히 9열**을 요구한다. 1열 행은 "결과 없음" 안내 페이지로 취급하고, 그 외 폭은 `ParseFailureError`다.

**순번을 조문번호로 착각하는 함정.** 구조문목록/신조문목록에서 `no`는 **순차 행 인덱스(1,2,3…)**다. 병렬 조인 키로는 유효하지만 조문 번호가 아니다. 이걸 `제N조`로 내보내면 **인용을 날조하게 된다.** 그래서 표시 라벨은 본문의 `제N조` 헤더에서 뽑고, 헤더가 없는 연속 행(항·호 조각)에는 앞의 것을 이어 붙인다.

**헌재 처분 복구.** 헌재 상세에는 판결유형 키가 없어 `decision_type`이 항상 비어 있다. 【주문】 구간을 잘라 헌법불합치·한정위헌·한정합헌·합헌·위헌·각하·기각·인용을 **구체적인 것부터** 매칭한다. 이유 부분은 반대의견이 같은 표현을 반복하므로 **주문 구간만** 훑는다.

**빈 페이로드의 분류.** 이 판단이 종료코드를 가른다. `is_empty_payload`는 의도적으로 보수적이다 — 공백류 스칼라와 빈 컨테이너만 빈 것으로 친다. 우리가 단지 *알아보지 못한* 페이로드는 "레코드 없음"으로 오분류되지 않고 `ParseFailureError`로 간다.

## `_cli/` — 파서에서 엔벨로프까지

의존 순서대로 별표 임포트한다: `foundation → constants → data → signals_meta → signal_helpers → signals → parser → dispatch → catalog → main`.

핵심은 **`signals_for(command, result, args)`**다. 결과를 보고 `kind`·`source`·`flags`·`discipline`·`next`를 도출한다.

`kind`는 **명령 이름이 아니라 결과 데이터클래스 타입**에서 나온다. 그래서 `load-followup`으로 도착한 결과도 올바른 `kind`를 단다. `AdjudicationHit`은 `source_type`에 `appeal`이 있느냐로, `JudicialDecisionHit`은 `detc`가 있느냐로 갈린다.

`catalog`는 `MolegApi()`를 만들기 **전에** 단락(short-circuit)한다. 그래서 자격증명도 네트워크도 필요 없다.

## `MolegSource` 프로토콜 — 테스트 주입 지점

```python
class MolegSource(Protocol):
    def search(self, target, params) -> dict: ...
    def search_html(self, target, params) -> str: ...
    def service(self, target, params) -> dict: ...
    def post_text(self, path, params) -> str: ...
```

`MolegApi(source=...)`가 이 프로토콜을 구현하는 무엇이든 받는다. 테스트는 `FakeSource`(FIFO 큐로 페이로드를 돌려주고 호출을 기록)를 넘긴다. **`_laws/` 전체가 네트워크 없이 테스트된다.**

`LawGoKrClient`는 표준 라이브러리 `urllib`만 쓴다. 세션도 커넥션 풀도 없이 시도마다 새 `urlopen`이다. 재시도 정책과 SSL 처리는 [Error Handling](Error-Handling.md)과 [Installation](Installation.md)에 있다.

## `_models/` — frozen 데이터클래스와 직렬화

모든 공개 모델이 `@dataclass(frozen=True)`다.

`models.py`가 `install_serialization_methods(globals(), public_module=__name__)`를 부른다. 이게 네임스페이스를 훑으며 모든 데이터클래스 **타입**에 대해 `__module__`을 `"moleg_api.models"`로 고쳐 쓰고 `to_dict`·`to_json_string`을 붙인다.

직렬화 규칙과 그 근거는 [API Reference](API-Reference.md)의 직렬화 계약 절에 있다. 여기서는 덜 뻔한 것 하나만 — **비문자열 딕셔너리 키 처리**. `{1: "a", "1": "b"}`는 `str()`을 거치면 충돌한다. 충돌한 키를 `type:repr` 형태로 승격하고, 승격된 키가 다시 기존 문자열 키와 충돌하면 또 승격하는 루프를 돈다. 손실 없이, 결정적으로 직렬화된다.

## 알려진 중복

문서화해 둘 가치가 있는 두 가지다. 둘 다 동작에는 영향이 없지만 코드를 고칠 때 헷갈린다.

**`_models`의 follow-up 원시 타입.** `bundles.py`가 `.followups`에서 `Ambiguity`·`ContextGap`·`DeferredLookup`을 임포트한 **뒤 셋을 다시 정의한다.** `query.py`도 `FollowUpSearch`를 임포트한 뒤 재정의한다. 런타임에 서로 다른 클래스다.

`_models/__init__.py`의 임포트 순서 덕에 **`followups` 쪽이 공개 네임스페이스를 이긴다.** 그림자 사본은 `to_dict`를 못 받으므로, 그걸 직접 만들면 구조는 맞는데 `isinstance`가 안 맞고 직렬화도 안 된다. 필드 목록이 같아서 부모의 `to_dict`는 여전히 동작한다(타입이 아니라 `is_dataclass`로 훑기 때문).

**`_normalization`의 헬퍼.** `compact_whitespace`·`yes_no_or_none`·`is_deleted_article`·`article_text_marks_deleted`가 `primitives.py`와 `article_units.py`에 **바이트 단위로 동일하게** 두 번 정의돼 있다. 별표 임포트 순서상 `primitives` 쪽이 이긴다.

## 관련 문서

- [Maintainer Notes](Maintainer-Notes.md) — 파일 크기 가드레일, 릴리스 전 점검
- [CONTRIBUTING.md](../../CONTRIBUTING.md) — 개발 환경, 테스트, PR 절차
- [API Reference](API-Reference.md) — 공개 표면
