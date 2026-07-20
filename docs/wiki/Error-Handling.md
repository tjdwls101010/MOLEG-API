# 오류 처리

이 패키지의 예외 체계는 하나를 무엇보다 우선해서 구분한다.

> **출처에 닿지 못한 것과 법적 출처가 없는 것은 다르다.**

호출 제한, 타임아웃, 파싱 실패는 "지금 답을 얻지 못했다"는 뜻이지 "그런 법은 없다"가 아니다. 이 둘을 섞으면 거짓 진술이 만들어진다.

```python
from moleg_api import (
    MolegApiError, NoResultError, AmbiguousLawError,
    UnsupportedFormatError, ParseFailureError, AsOfBeforeCoverageError,
    SourceApiError, RateLimitError, RetryExhaustedError,
)
```

## 계층

```
Exception
└── MolegApiError                 공개 인터페이스의 모든 실패
    ├── NoResultError             쓸 만한 결과 없음
    ├── AmbiguousLawError         복수 신원이 걸림
    ├── UnsupportedFormatError    지원하지 않는 형식·경로
    ├── ParseFailureError         응답을 모델로 정규화하지 못함
    ├── AsOfBeforeCoverageError   as_of가 통합본 커버리지 이전
    └── SourceApiError            law.go.kr 호출 자체가 실패
        ├── RateLimitError        HTTP 429
        └── RetryExhaustedError   재시도 가능한 실패가 전부 소진
```

`MolegApiError`를 잡으면 전부, 하위 클래스를 잡으면 특정 조건만 다룬다. `SourceApiError`를 잡으면 `RateLimitError`와 `RetryExhaustedError`도 함께 잡힌다.

---

## 각 예외

### `NoResultError`

형식이 올바른 요청에 대해 출처가 쓸 만한 결과를 돌려주지 않았다. **범위 한정 부재**다 — 이 식별자·이 조문·이 질의로 못 찾았다는 뜻이지, 그런 자료가 어디에도 없다는 뜻이 아니다.

세 가지 경우를 구분해 알아둘 만하다.

**로더에 법령 이름을 넘겼을 때.** 로더는 `LawIdentity`, `LawHit`, 또는 숫자 식별자를 받는다. 자유 텍스트 법령명을 주면 "먼저 검색하라"는 메시지와 함께 이 예외가 난다. CLI에서는 `needs_search_first`(종료코드 5)로 따로 표시된다.

**없는 식별자도 여기다.** law.go.kr은 모르는 식별자에 대해 「일치하는 …」 문장이 아니라 **빈 본문**(`{}`)으로 답한다. 0.3.0 이전에는 이걸 파싱 실패로 분류해 종료코드 3을 냈고, 그 규율은 "잠시 후 재시도"였다 — 영원히 성공할 수 없는 조회에 대한 조언이었다. 지금은 `no_result`(종료코드 4)로 가서 `search-*`로 유도한다.

**0건 검색은 오류가 아니다.** CLI에서 검색이 아무것도 못 찾으면 정상 성공이다 (`ok:true`, `count:0`, 종료코드 0). 예외로 올라오는 것은 *로드*뿐이다.

### `AmbiguousLawError`

복수의 그럴듯한 신원이 걸렸고, 패키지가 대신 고르기를 **거부한** 것이다.

| 속성 | 내용 |
|---|---|
| `.candidates` | 걸린 `LawIdentity` 목록 |
| `.kind` | 모호성의 종류를 나타내는 짧은 라벨 (예: `"promulgation_bridge"`) |
| `.message` | 사람이 읽는 요약 |

```python
try:
    identity = api.resolve_promulgated_law(prom_law_nm="…", prom_no="…")
except AmbiguousLawError as exc:
    for cand in exc.candidates:
        print(cand.name, cand.law_id, cand.promulgation_date)
    # 의도적으로 하나를 고른 뒤 다시 로드한다
```

**모호성은 첫 후보를 고를 허가가 아니다.** `.candidates[0]`을 집으면 이 예외가 존재하는 이유를 무효로 만드는 것이다. 후보를 드러내고, 호출자나 사용자가 고르게 하라.

### `UnsupportedFormatError`

출처가 지원 가능한 형식으로 답하지 못했거나, 요청한 경로가 이 인터페이스 밖이다. 실제로 나오는 경우들:

- 잘못된 열거값 (`basis`, `court`, `source`, 위원회·심판기관 코드 등)
- `compare_law_versions`에 임의의 두 날짜 구간을 준 경우
- 헌재 신원을 `get_case`에 넘긴 경우(또는 그 반대)
- 본문 조회를 지원하지 않는 두 부처(국세청·재정경제부)의 해석 본문을 요구한 경우
- `load_followup`에 `websearch`나 `congress-db` 인터페이스를 넘긴 경우 — **의도된 경계 표시다**

**법적 부재가 아니다.** 다른 명령이나 다른 출처로는 닿을 수 있다.

### `ParseFailureError`

응답은 받았는데 공개 모델로 정규화하지 못했다. 신원 페이로드에 법령명이 없거나, 체계도 페이로드의 모양이 예상과 다르거나, HTML 표의 열 개수가 다를 때.

**재시도해도 소용없다.** 종료코드 3을 일시적 오류들과 공유하지만, 그건 "출처 쪽에서 뭔가 잘못됐다"는 점만 같기 때문이다. 알아보지 못한 응답 모양은 다음 호출에서도 똑같이 알아보지 못한다. **식별자 착오를 먼저 배제하고**(`search-*`로 재확인), 그 다음 다른 명령이나 경로를 시도하라.

### `AsOfBeforeCoverageError`

`as_of`가 통합본 커버리지 시작 이전이다.

| 속성 | 내용 |
|---|---|
| `.law_id` | 대상 법령 |
| `.earliest_available` | 조회 가능한 가장 이른 시점 |

**영구 조건이지 일시적 실패가 아니다.** 재시도가 아니라 개정 연혁(`trace_law_history`)으로 가야 한다. CLI는 `kind: "version_request_unfulfilled"`로 내고 그 명령을 `next`에 담아 준다.

### `SourceApiError`

law.go.kr 호출 자체가 실패했거나 유효하지 않은 응답을 줬다 — 재시도 불가 HTTP 오류, 또는 JSON이 아닌 본문. 아래 두 일시적 오류의 부모다. **출처 접근 실패이지 법령의 부재가 아니다.**

### `RateLimitError`

HTTP **429**를 받고 재시도가 소진됐다. 패키지가 공용 기본 OC를 싣고 있으므로, 무거운 사용이나 동시 호출에서 걸릴 수 있다.

**일시적 접근 실패이며 법령이 없다는 증거가 절대 아니다.** 물러났다 재시도하라. 자주 걸린다면 자기 OC를 발급받아라 → [Installation](Installation.md)

### `RetryExhaustedError`

재시도 가능한 실패(타임아웃, 연결 오류, HTTP 408·500·502·503·504)가 허용된 모든 시도에서 계속됐다. 역시 **일시적이지 부재가 아니다.**

`max_retries=0`으로 재시도를 끈 경우, 타임아웃과 연결 오류는 이 예외 대신 평범한 `SourceApiError`로 나온다 — 재시도를 안 한 클라이언트가 "재시도 소진"을 보고하는 것은 말이 안 되기 때문이다.

---

## 일시적 실패 vs 부재 — 대응표

| 의미 | 예외 | 대응 |
|---|---|---|
| **일시적 접근 실패** | `RateLimitError`, `RetryExhaustedError`, `SourceApiError` | 나중에 재시도. **"그런 법 없음"으로 다루지 마라.** 시급한 사실은 미확인 표지를 달아 대체 출처로만 채우고, 위헌성·판례 주장은 "1차 확인 필요"로 남겨라 |
| **정규화 실패** | `ParseFailureError` | 부재도 아니고 **일시적도 아니다.** 식별자 착오를 먼저 배제하고 다른 경로를 시도 |
| **범위 한정 부재** | `NoResultError` (`no_result`) | 질의·범위를 넓히거나 식별자를 재확인. **정확히 무엇을 어떤 범위·필터로 검색했는지 밝히지 않고 부재를 주장하지 마라** |
| **입력·순서 오류** | `NoResultError` (`needs_search_first`), 인자 오류 | 먼저 검색해 신원을 얻거나 인자를 고쳐라 |
| **커버리지 하한** | `AsOfBeforeCoverageError` | 영구. 연혁으로 이동 |
| **복수 일치** | `AmbiguousLawError` | 후보를 제시하고 의도적으로 선택 |

---

## 내장 재시도

`LawGoKrClient`가 예외를 올리기 전에 일시적 실패를 자동 재시도한다.

| 설정 | 기본값 | 의미 |
|---|---|---|
| 재시도 조건 | — | HTTP 408, 429, 500, 502, 503, 504 + 타임아웃 + 연결 오류 |
| `max_retries` | **2** | 첫 시도 이후 추가 시도 → 총 3회 |
| `retry_delay_seconds` | **0.5** | 시도 간 **고정** 대기. 지수 백오프도 지터도 없다 |
| `timeout_seconds` | **30** | 요청당 타임아웃 |

재시도가 소진되면 429는 `RateLimitError`, 나머지는 `RetryExhaustedError`. **재시도 불가 상태 코드와 JSON이 아닌 본문은 재시도 없이 즉시** `SourceApiError`다.

```python
api = MolegApi(source=LawGoKrClient(max_retries=4, retry_delay_seconds=1.0))
```

클라이언트 쪽 호출량 조절(토큰 버킷, 요청 간 지연)은 **없다.** 호출 제한 대응은 반응적이다 — 429를 받고 재시도한다. 동시 호출을 많이 낼 계획이라면 조절은 호출자 몫이다.

---

## CLI 종료코드

| 종료 | `kind` | 의미 | 대응 예외 |
|---|---|---|---|
| **0** | (다양) | 성공 — **0건 검색 포함** | — |
| **2** | `ambiguous` | 복수 신원. `flags.candidates`에 후보 | `AmbiguousLawError` |
| **3** | `source_access_error` | 일시적 접근 실패 — **재시도하라** | `RateLimitError`, `RetryExhaustedError` |
| **3** | `parse_error` | 알아보지 못한 응답 모양 — **재시도 무의미** | `ParseFailureError` |
| **3** | `error` | 그 밖의 출처 측 실패 | `SourceApiError`, 기타 `MolegApiError` |
| **4** | `no_result` | 본문 없음. **없는 식별자 포함** | `NoResultError` |
| **4** | `version_request_unfulfilled` | 요청 시점이 커버리지 이전 | `AsOfBeforeCoverageError` |
| **5** | `needs_search_first` | 로더에 법령 이름을 넘김 | `NoResultError` (이름 오입력) |
| **5** | `unsupported` | 지원하지 않는 형식·경로 | `UnsupportedFormatError` |
| **5** | `usage_error` | 인자 오류, 서브커맨드 누락, 알 수 없는 명령 | 인자 파싱 |

종료코드 1은 없다. 스크립트가 분기해야 하는 오류마다 전용 코드(2~5)를 줬고, 나머지 성공은 전부 0이다.

**종료코드 3만 보고 재시도 루프를 돌리면 안 된다.** 두 `kind` 중 하나만 재시도할 가치가 있다. `kind`로 분기하지 않으면 영구 조건에서 루프가 돈다.

`no_result`(4)와 `needs_search_first`(5)를 일부러 갈라 놓은 이유도 같다 — 전자는 진짜 범위 한정 부재고, 후자는 고칠 수 있는 입력 순서 실수다.

**오류도 stdout으로 나간다.** stderr가 아니다. 파싱 경로가 하나로 유지된다.

```json
{
  "ok": false,
  "command": "get-article",
  "version": "0.3.0",
  "kind": "needs_search_first",
  "error": "Identifier '주택임대차보호법' looks like a law name, not a law ID. …",
  "discipline": ["로더에 법령명이 들어옴 — search-laws로 law_id를 먼저 얻어라."],
  "next": [{ "why": "먼저 신원 검색", "cmd": "moleg search-laws \"주택임대차보호법\"" }]
}
```

## 관련 문서

- [Agent Integration](Agent-Integration.md) — 종료코드를 에이전트가 어떻게 다뤄야 하는지
- [CLI Reference](CLI-Reference.md) — 엔벨로프 계약 전체
- [Installation](Installation.md) — 자기 OC 설정으로 공용 호출 예산 벗어나기
- [Gotchas](Gotchas.md) — 조용히 틀리는 지점
