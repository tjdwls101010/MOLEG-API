# 핵심 개념

이 패키지의 공개 표면은 작고 깊다. 그 모양을 결정한 개념이 여섯 개 있고, 이것들이 신뢰할 수 있는 인용과 조용히 오도하는 인용을 가른다.

메서드 시그니처는 [API Reference](API-Reference.md), 셸에서 쓸 거라면 [CLI Reference](CLI-Reference.md)를 보라.

## 1. 검색 → 선택 → 로드

모든 출처 계열에서 *발견*과 *로딩*이 분리돼 있고, 둘은 대체 불가다.

**검색·계획 메서드** — `search_laws`, `search_administrative_rules`, `search_annex_forms`, `search_interpretations`, `search_cases`, `search_constitutional_decisions`, `search_committee_decisions`, `search_administrative_appeals`, `expand_legal_query`, `find_comparable_mechanisms`, `resolve_promulgated_law` — 는 **후보 식별 정보**를 준다. 출처를 특정하고 실을지 말지 판단하기에 충분한 정보이되, **본문은 아니다.**

**로드 메서드** — `get_law`, `get_article`, `get_law_toc`, `get_administrative_rule`, `get_annex_form_body`, `get_interpretation`, `get_case`, `get_constitutional_decision`, `get_committee_decision`, `get_administrative_appeal`, 그리고 `load_*_context` 계열 — 은 실제 본문을 실어 온다.

**검색 결과는 인용할 수 없다.** `search_laws()`만 부른 상태에서 당신이 가진 것은 법의 이름과 날짜와 식별자다. 그 법이 무엇을 의무로 지우고 어떤 제재를 두는지는 **모른다**. 다른 계열도 같다 — 해석·판례·헌재 검색 결과는 제목과 날짜 메타데이터일 뿐, 판시사항과 이유는 대응하는 로더에서 나온다.

`expand_legal_query()`와 `find_comparable_mechanisms()`는 그보다도 앞단이다. 이건 *계획* 도구이고, 그 결과는 다음에 무엇을 검색·로드할지의 메뉴이지 권위가 아니다.

**0건은 범위 한정 결과이지 부재의 증명이 아니다.** "이 검색어로, 이 출처 계열에서, 이 필터 조합으로 행이 없었다"는 뜻이다. 그런 법·규칙·판례·별표가 존재하지 않는다는 증명이 아니다. 없다고 말하기 전에 검색어를 넓히거나, 다른 출처 계열을 보거나, 상세 경로를 실어 봐야 한다.

## 2. 후보 vs 실린 본문 — 타입으로 강제된다

위 구분이 데이터 모델에 그대로 박혀 있어, 손에 든 것이 후보인지 본문인지 타입만 봐도 안다.

| 손에 든 것 | 타입 | 내용 | 인용 가능? |
|---|---|---|---|
| 검색 결과 | `LawHit`, `AdministrativeRuleHit`, `AnnexFormHit`, `InterpretationHit`, `JudicialDecisionHit`, `AdjudicationHit` | 정규화된 `*Identity` + 원본 행 + `follow_up` | **아니오** |
| 실린 본문 | `LawText`, `ArticleText`, `LawToc`, `AdministrativeRuleText`, `AnnexFormText`, `InterpretationText`, `JudicialDecisionText`, `AdjudicationText` | 정규화된 본문·조문·구조화 필드 | 예 |

CLI에서는 `kind` 접미사가 같은 일을 한다 — `_hit_list`·`_candidate`·`_planning`이면 후보, `_text`·`_context`·`_identity`면 본문.

경계는 실행 시점에도 강제된다. 로더에 법령 **이름**을 넘기면 호출되지 않고 "먼저 `search_laws('…')`를 부르라"는 오류가 난다. 이름은 법을 유일하게 가리키지 못하고, 그 자리에서 아무거나 고르는 것이 이 패키지가 막으려는 실패이기 때문이다.

**한 가지 주의**: 실린 조문에서도 정의·예외·적용 대상·요건은 조문 제목이나 최상위 `조문내용`이 아니라 **중첩된 항·호·목** 안에 사는 경우가 많다. `ArticleText.text`는 그 중첩을 펼쳐 담고 있으니, 제목만 보고 요약하지 마라.

## 3. 시행(effective) vs 공포(promulgated)

대부분의 메서드가 `basis` 인자를 받는다. `Literal["effective", "promulgated"]`, 기본값 `"effective"`.

- **`basis="effective"` (시행일 기준)** — 지금 또는 그때 **효력이 있던** 텍스트. "현행법이 뭐라고 하나"에 답하는 기준이며 기본값이다.
- **`basis="promulgated"` (공포일 기준)** — 공포일·공포번호로 키를 잡는다. 국회 의안의 공포 사실에서 법령 신원을 잇거나, 과거 공포 맥락을 재구성할 때 쓴다.

**공포된 법이 시행 중인 법은 아니다.** 공포는 됐는데 시행일이 미래인 상태가 흔하다. 공포 기준으로 텍스트를 실었다는 것은 *신원과 문언*을 확인한 것이지 *현재 효력*을 확인한 것이 아니다.

이건 워낙 자주 틀리는 지점이라 신호로도 나온다 — 실린 판본의 시행일이 오늘보다 미래면 `flags.not_effective_as_of`가 붙고 `source` 표기 자체가 「공포본(장래 시행 — 아직 미시행)」으로 바뀐다. 이 플래그는 `--as-of`를 줬는지와 무관하게 뜬다. 미래 판본은 어느 경로로든 도착할 수 있기 때문이다.

## 4. 식별자 — `ID`, `MST`, `LID`, `JO`

법령 하나는 시행일마다 하나씩, **판본의 계열**로 존재한다. 모든 판본이 같은 `law_id`를 공유하고, 각 판본은 자기만의 `mst`를 갖는다.

| 필드 | 원래 이름 | 가리키는 것 |
|---|---|---|
| `law_id` | `ID` (법령ID) | **법 자체**. "이 법의 현행판" |
| `mst` | 법령일련번호 | **그 법의 특정 판본**. 시간 축의 손잡이 |
| `lid` | `LID` | 함께 보존되지만 파라미터 선택에는 쓰지 않는다 |

`법령ID + 시행일`로 상세를 조회하면 law.go.kr은 **오류 없이 현행 텍스트를 준다.** 판본을 고정하는 유일한 키가 `mst`다. 이게 `as_of`가 왜 존재하는지의 이유이며, [Historical Versions](Historical-Versions.md)에서 따로 다룬다. 다만 `mst`를 손으로 관리할 일은 없다 — 후보를 로더에 그대로 넘기면 판본이 함께 따라간다.

**`JO`**는 법제처의 여섯 자리 조문 코드다(`제15조의2` → `001502`, `제3조` → `000300`). **호출자는 이걸 볼 일이 없다.** 공개 메서드는 `"제15조의2"`, `"15조의2"`, 정수 `15`를 받아 내부에서 변환한다.

원본 키들은 감사 목적으로 `identity.raw_keys`에 보존되지만, 코드가 딛고 설 것은 정규화된 필드다.

## 5. 권위 유형은 평탄화되지 않는다

법제처는 여섯 종류의 서로 다른 권위를 노출한다. 이들은 무게가 다르고 서로를 대체하지 못한다.

| 권위 | 출처 계열 | 메서드 | 성격 |
|---|---|---|---|
| 법제처 법령해석 (법령해석례) | `expc` | `search_interpretations(source="moleg")` / `get_interpretation` | 법제처의 공식 해석 |
| 부처 1차 해석 | `*CgmExpc` (40개 부처) | `search_interpretations(source="ministry", ministry=…)` | 개별 부처의 자체 판단. 법제처 해석과 **다른 층위** |
| 대법원 판례 | `prec` | `search_cases` / `get_case` | 일반 법원의 선례 |
| 헌재 결정 (헌재결정례) | `detc` | `search_constitutional_decisions` / `get_constitutional_decision` | 위헌심사. 일반 판례가 **아니다** |
| 위원회 의결 | 12개 위원회 | `search_committee_decisions` / `get_committee_decision` | 행정기관의 처분·의결. 판례가 **아니다** |
| 행정심판 재결 | 5개 심판기관 | `search_administrative_appeals` / `get_administrative_appeal` | 행정심판의 재결. 법원 판결이 **아니다** |

각 결과는 `source_type` / `source_authority`를 끝까지 달고 다닌다. 답을 쓸 때 이걸 "법에 따르면"으로 뭉개면 그 보존이 무의미해진다.

실무적으로 걸리는 세 지점.

**`source="all"`은 전부가 아니다.** `search_interpretations()`에서 `"all"`은 법제처 **+ 지정한 부처 하나**를 뜻한다. 부처 전체를 훑는 것은 `"all_ministries"`이며, 의도적으로 비용이 큰 경로다.

**헌법 원칙은 색인이 아니다.** 과잉금지원칙·평등원칙 같은 도그마틱은 `detc`에 필드로 존재하지 않는다. 자유 텍스트 검색일 뿐이라, 후보를 찾을 수는 있어도 "위헌 소지 없음"이나 도그마틱 망라성을 증명하지 못한다.

**행정기관 기록의 부재는 무사고의 증명이 아니다.** 위원회 의결과 행정심판 재결은 "그 기관이 실제로 판단했다"는 기록이다. 0건은 그 기관이 판단한 적이 없다는 뜻이지, 문제가 없었다는 뜻이 아니다. 그리고 소청·조세·해양안전 사안을 일반 행정심판위(`decc`)에서만 찾으면 조용히 0건이 나온다 — 그건 별도 심판기관 소관이다.

조문 단위로 권위를 붙여야 한다면 `load_authority_context()`를 쓰고, 그 결과의 **`current_authorities`**에서 인용하라. 여기엔 실제로 그 조문을 참조하고 날짜가 확인된 것만 남는다.

## 6. 단계적 번들과 후속 조회

넓은 질문에 대해 출처를 하나씩 손으로 싣는 것은 지루하다. 번들 로더는 한 번의 제한된 1차 통과를 돌고, 결과를 **세 층으로 분리해서** 돌려준다.

- **`loaded`** (`LoadedContext`) — 이미 실린 본문. 인용 가능.
- **`candidates`** (`CandidateContext`) — 발견됐지만 안 실린 것. 개념 2에 따라 여전히 후보다.
- **`deferred`** (`list[DeferredLookup]`) — 돌리지 않기로 한 다음 조회들. `ambiguities`, `gaps`, `source_notes`가 함께 온다.

**번들은 출처 로딩이지 결론이 아니다.** 번들 하나로 해석·판례·헌재·행정규칙·별표를 망라했다고 말할 수 없다.

`DeferredLookup`은 `interface`, `query`, `filters`, `reason`을 가진 실행 가능한 다음 수다. `load_followup()`에 넣으면 알맞은 로더로 라우팅된다 — 출처 target 이름도, `ID`/`MST` 규칙도, 조문 포맷도 만질 일이 없다.

```python
for lookup in bundle.deferred:
    if lookup.interface == "load_administrative_rule_context":
        rule = api.load_followup(lookup)
        break
```

`interface`가 `websearch`나 `congress-db`인 항목은 `UnsupportedFormatError`를 낸다. 버그가 아니라 **의도된 경계 표시**다 — 최신 사회적 사실은 웹 검색, 국회 의안·표결 사실은 별도 시스템 소관이고, 이 패키지는 그걸 아는 척하지 않는다.

같은 모양을 공유하는 번들 로더가 셋 더 있다.

- **`load_institutional_system()`** — 이미 고른 법령 **집합**을 하나의 제도로 훑는다. 집합을 구성해 줄 뿐, 어느 법이 주된 것인지 발견하거나 결정하지 않는다.
- **`load_delegated_criteria()`** — 법령 하나에 닻을 내리고, 행정규칙과 별표·서식의 **본문까지** 제한적으로 실어 온다. 이름만이 아니라 구체적 집행 기준이 필요할 때 쓴다.
- **`load_authority_context()`** — 지정한 조문들에 스코프를 건 정밀 도구. 조문과 어긋나거나 날짜가 없거나 개정 이전인 권위를 `current_authorities`에서 걸러낸다.

## 다음

- [Agent Integration](Agent-Integration.md) — 이 개념들이 엔벨로프 신호로 어떻게 표현되는지
- [Gotchas](Gotchas.md) — 조용히 틀리는 지점 모음
- [Historical Versions](Historical-Versions.md) — 판본과 `as_of`
- [Sources & Coverage](Sources-and-Coverage.md) — 출처 계열별 커버리지
