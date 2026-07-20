# 빠른 시작

이 페이지는 첫 왕복을 Python과 CLI로 나란히 보여준다. 개념적 배경은 [Core Concepts](Core-Concepts.md), 설치는 [Installation](Installation.md)에 있다.

```bash
pip install moleg-api
```

등록 없이 바로 동작한다. 이유는 [Installation](Installation.md)의 OC 절을 보라.

## 1. 검색하고, 고르고, 싣는다

이 세 박자가 패키지 전체의 리듬이다. 검색은 **후보**를 주고, 로더는 **본문**을 준다. 후보는 인용할 수 없다.

### Python

```python
from moleg_api import MolegApi

api = MolegApi()

# 검색 — 후보 목록
hits = api.search_laws("주택임대차보호법", display=5)
if not hits:
    raise RuntimeError("후보 없음")   # 0건은 예외가 아니라 빈 리스트다

# 고른다 — 첫 후보를 무조건 집는 것은 위험하다. 아래 "모호성" 절 참고
identity = hits[0].identity

# 싣는다 — 이제 인용할 수 있는 본문
article = api.get_article(identity, "제7조")

print(article.article)   # 제7조
print(article.title)     # 차임 등의 증감청구권
print(article.text)      # 항·호·목까지 펼쳐진 본문
```

`LawHit`이든 그 안의 `LawIdentity`든 로더에 그대로 넘기면 된다. 여섯 자리 `JO` 코드로 조문 번호를 바꾸는 일은 없다 — `"제7조"`, `"제15조의2"`, 또는 정수 `7`을 그대로 쓴다.

### CLI

모든 메서드가 서브커맨드이고, 언제나 JSON 엔벨로프 하나를 stdout에 찍는다.

```bash
moleg search-laws "주택임대차보호법" --display 5
moleg get-article --law 001248 "제7조"
```

## 2. 엔벨로프 읽기

검색 응답은 이런 모양이다.

```json
{
  "ok": true,
  "command": "search-laws",
  "version": "0.3.0",
  "kind": "law_hit_list",
  "source": "법제처 / 법령검색",
  "count": 2,
  "data": [
    {
      "identity": {
        "law_id": "001248",
        "name": "주택임대차보호법",
        "basis": "effective",
        "mst": "276291",
        "effective_date": "20260102",
        "law_type": "법률"
      }
    }
  ],
  "flags": { "ambiguous_versions": true },
  "discipline": ["…"],
  "next": [
    { "why": "현행 판본 로드",
      "cmd": "moleg get-law --law 001248" }
  ]
}
```

핵심 키 넷.

- **`kind`** — 결과의 의미 유형. `_hit_list`·`_candidate`·`_planning`으로 끝나면 후보라서 인용할 수 없고, `_text`·`_context`·`_identity`로 끝나면 실린 본문이다. 접미사만 봐도 인용 가능 여부가 갈린다.
- **`version`** — 이 응답을 만든 코드의 버전. 항상 실린다.
- **`flags`** — 기계가 읽을 상태값. 위 예의 `ambiguous_versions`는 같은 이름의 법이 여러 판본으로 잡혔다는 뜻이다.
- **`next`** — 바로 실행 가능한 다음 명령. 최대 3개.

`discipline`은 이 결과를 해석할 때 지켜야 할 규율이 한국어 문장으로 실려 온다. 에이전트에 물릴 거라면 [Agent Integration](Agent-Integration.md)에서 세 신호를 전부 다룬다.

## 3. 로더에 법령 이름을 넘기면 거부된다

```bash
moleg get-article --law "주택임대차보호법" "제7조"
```

```json
{ "ok": false, "kind": "needs_search_first",
  "next": [{ "why": "먼저 신원 검색", "cmd": "moleg search-laws \"주택임대차보호법\"" }] }
```

종료코드 5. 의도된 동작이다 — 이름은 법을 유일하게 가리키지 못한다. 반드시 `search-laws`로 `law_id`를 먼저 얻어야 한다.

## 4. 모호성은 첫 후보를 고를 허가가 아니다

같은 이름에 여러 판본이나 여러 법이 걸리면 `AmbiguousLawError`가 나거나(Python) `kind: "ambiguous"`, 종료코드 2가 나온다(CLI).

```python
from moleg_api import AmbiguousLawError

try:
    identity = api.resolve_promulgated_law(prom_law_nm="…", prom_no="…")
except AmbiguousLawError as exc:
    for candidate in exc.candidates:   # 후보를 사람에게 제시하라
        print(candidate)
```

`exc.candidates`를 그냥 `[0]`으로 집으면, 이 예외가 존재하는 이유를 무효로 만드는 것이다.

## 5. 과거 시점의 법 묻기

```python
past = api.get_article(identity, "제7조", as_of="2021-01-01")
print(past.identity.effective_date)   # 실제로 실린 판본의 시행일
```

```bash
moleg get-article --law 001248 --as-of 2021-01-01 "제7조"
```

**반드시 돌아온 `effective_date`를 확인하라.** 요청한 날짜에 시행 중이던 판본이 없으면 그 이후 판본이 실려 오고, `flags.version_mismatch`에 `{requested, loaded}`가 붙는다. 이 함정은 [Historical Versions](Historical-Versions.md)에서 따로 다룬다.

## 6. 질문이 넓을 때 — 단계적 번들

법령 이름을 아직 모르거나 질문이 넓으면 개별 검색 대신 번들로 시작한다. 한 번의 제한된 1차 통과로 여러 출처를 훑고, 실은 것과 후보만 잡은 것을 **분리해서** 돌려준다.

```python
bundle = api.load_legal_context_bundle(
    query="자동차 방치 처리 기준",
    mode="question",      # question | promulgated_bill | statute_review
    budget="standard",    # minimal | standard | broad
)

bundle.loaded.laws          # 실제로 실린 본문 — 인용 가능
bundle.candidates.laws      # 발견만 된 후보 — 인용 불가
bundle.gaps                 # 아직 안 메워진 것과 그걸 메울 출처
bundle.deferred             # 실행 가능한 다음 조회
```

`deferred` 항목은 손으로 풀어 쓸 필요 없이 그대로 다시 넣으면 된다.

```python
for lookup in bundle.deferred:
    if lookup.interface == "load_administrative_rule_context":
        rule = api.load_followup(lookup)
        break
```

CLI에서는 파이프로 흘려보낸다.

```bash
moleg load-legal-context-bundle --query "자동차 방치 처리 기준" \
  | jq '.data.deferred[0]' \
  | moleg load-followup --json -
```

**손으로 쓴 JSON은 거부된다.** 이전 응답이 준 객체만 받는다.

번들에 대해 알아둘 것 하나: `mode="question"`에서 법령 후보가 **여럿**이면 번들은 아무 것도 자동으로 고르지 않는다. `Ambiguity`와 `ContextGap`을 남기고 `search_laws` 후속 조회를 제안할 뿐이다. 고르는 것은 호출자의 몫이다.

`budget`이 로드량을 정하지만, 그게 전부가 아니다 — 질의 내용이 무엇을 실을지도 정한다. 자세한 것은 [Agent Integration](Agent-Integration.md)의 의도 게이트 절.

## 7. 직렬화

모든 공개 데이터클래스가 재귀적으로 직렬화된다. 번들 하나를 부르면 그 안의 법령·조문·후보·후속 조회가 전부 따라 나온다.

```python
data = article.to_dict()               # dict
text  = bundle.to_json_string()        # JSON 문자열 (ensure_ascii=False, sort_keys=True)

debug = bundle.to_dict(include_raw=True)   # law.go.kr 원본 페이로드까지
```

`raw`(원본 페이로드)는 **기본적으로 빠진다.** 컨텍스트 예산을 엔드포인트 모양 데이터로 낭비하지 않기 위해서다. 파서를 디버깅할 때만 켠다. CLI도 같은 규칙이고, 전역 `--raw` 플래그로 켠다.

## 다음

- [Core Concepts](Core-Concepts.md) — 여기서 본 규칙들의 근거
- [Agent Integration](Agent-Integration.md) — 엔벨로프 신호 전체, 컨텍스트 예산, `catalog` 계약
- [Gotchas](Gotchas.md) — 조용히 틀리는 지점들
- [API Reference](API-Reference.md) · [CLI Reference](CLI-Reference.md) — 전수 목록

이 패키지는 법적 출처 로더이지 법률 자문이 아니다.
