# 출처와 커버리지

법제처 OpenAPI의 모든 엔드포인트를 1:1 메서드로 노출하지 않는다. **반복적으로 필요한 법적 출처 계열**을 골라 깊게 감쌌다. 이 페이지는 무엇이 덮여 있고, 무엇이 범위 밖이며, 인용할 때 무엇을 염두에 둬야 하는지를 다룬다.

여기 나오는 모든 메서드에 대응하는 `moleg` 서브커맨드가 있다. 전체 목록과 라우팅 규칙은 `moleg catalog`.

## 대응표

| 출처 계열 | Python | CLI |
|---|---|---|
| 법령 (현행·공포) | `search_laws`, `resolve_promulgated_law`, `get_law`, `get_law_toc`, `get_article`, `load_article_context` | `search-laws`, `resolve-promulgated-law`, `get-law`(`--toc`), `get-article`, `load-article-context` |
| 부칙 | `get_law` 결과에 포함 | `get-law` 안에 |
| 연혁·개정이유·비교 | `trace_law_history`, `get_revision_reason`, `compare_law_versions` | `trace-law-history`, `get-revision-reason`, `compare-law-versions` |
| 위임·체계 | `find_delegated_rules`, `get_law_structure` | `find-delegated-rules`, `get-law-structure` |
| 행정규칙 (고시·훈령·예규) | `search_administrative_rules`, `get_administrative_rule`, `load_administrative_rule_context` | 동명 |
| 별표·서식 | `search_annex_forms`, `get_annex_form_body` | 동명 |
| 법령해석 (법제처·부처) | `search_interpretations`, `get_interpretation` | 동명 |
| 판례 | `search_cases`, `get_case` | 동명 |
| 헌재 결정 | `search_constitutional_decisions`, `get_constitutional_decision` | 동명 |
| 위원회 의결 | `search_committee_decisions`, `get_committee_decision` | 동명 |
| 행정심판 재결 | `search_administrative_appeals`, `get_administrative_appeal` | 동명 |
| 계획·번들 | `expand_legal_query`, `find_comparable_mechanisms`, `load_legal_context_bundle`, `load_institutional_system`, `load_delegated_criteria`, `load_authority_context`, `load_followup` | 동명 |

---

## 계열별 상세

### 법령 본문

`search_laws`가 이름·키워드로 신원 후보를 찾고, `get_law`·`get_article`이 고른 신원 뒤의 텍스트를 싣는다. 둘 다 `basis`(`"effective"` / `"promulgated"`)를 받는다.

`get_law_toc`(CLI: `get-law --toc`)는 본문 없이 조문 지도만 준다. 컨텍스트 예산 장치다.

`resolve_promulgated_law`는 더 엄격한 해석기다. 공포 메타데이터(법령명·공포번호·공포일)에서 자유 탐색 없이 **정확히 하나의** 공포 기준 신원으로 잇는다.

### 조문 — 이동·삭제 상태 포함

`get_article`은 `제10조의2` 같은 사람 표기로 조문 하나를 싣는다. `ArticleText`가 `moved_from`/`moved_to` 쌍과 `is_deleted` 플래그를 들고 있어, 이동·삭제 표시가 운용 조문으로 오인되지 않는다.

`load_article_context`는 여기에 얹혀서, 조문이 이동했으면 **현재 목적지를 해소한다.** 요청 조문, 목적지(안전하게 실린 경우), 실린 행 전체, 그리고 실질 주장 전에 해소해야 할 gap과 후속 조회를 함께 준다.

### 부칙

`get_law`가 본 조문과 함께 추출해 `LawText.supplementary_provisions`에 담는다. 별도 로더는 없다.

### 연혁·개정이유·비교

세 명령이 서로 다른 질문에 답한다.

| 질문 | 명령 |
|---|---|
| 어떤 개정들이 있었나 | `trace_law_history` |
| 그 개정은 **왜** 했나 | `get_revision_reason` |
| **무엇이** 바뀌었나 | `compare_law_versions` |

`trace_law_history`는 전체 법령, 날짜 범위, 또는 조문 하나(`article="제7조"`)에 대해 개정 이력을 싣는다. 전체 법령 연혁은 law.go.kr이 **HTML로만** 주는 경로를 파싱해 온다.

`get_revision_reason`은 특정 **판본**의 「개정이유 및 주요내용」을 준다. `trace_law_history` 이벤트의 `identity.mst`를 `mst=`에 넣으면 그 개정으로 정확히 내려간다. 오래된 판본에는 없는 경우가 흔하다.

`compare_law_versions`는 law.go.kr이 자체적으로 노출하는 전후 비교 표면을 쓴다. **임의의 두 날짜 구간은 지원하지 않으며** `before=`/`after=`에 날짜를 주면 `UnsupportedFormatError`가 난다.

### 위임과 체계

`find_delegated_rules`는 법령(또는 조문)의 위임 하위규범 맥락을 준다 — 시행령·시행규칙·고시·행정규칙. 조문 단위 위임 링크를 보존한다.

`get_law_structure`는 법률 → 시행령 / 시행규칙 / 행정규칙의 계층도를 준다. **조문 단위 링크는 없다.** 계층 맥락일 뿐 조문 단위 위임의 증거가 아니다.

> **위임 목록에 별표는 없다.** 과태료 기준표·수수료표 같은 것은 `search_annex_forms`로 따로 찾아야 한다.

### 행정규칙

고시·훈령·예규 등 — 법령 본문 밖에 사는 실무 집행 기준. `search_administrative_rules`의 `issued_on`은 **발령일자**이지 시행일이 아니다.

### 별표·서식 — 텍스트 추출

운용적 내용이 첨부 자료에 사는 경우가 많다. 표, 임계값, 기준, 금액, 필수 서식.

`search_annex_forms`가 법령(`source="law"`)이나 행정규칙(`source="administrative_rule"`)에 붙은 후보를 찾는다. `annex_type`으로 별표·서식·별지·별도·부록(및 영문 별칭)을 거를 수 있다. `get_annex_form_body`가 고른 후보의 본문을 **평문**으로 싣는다.

**HWP나 PDF 파일을 직접 파싱하지 않는다** — law.go.kr의 텍스트 내보내기 엔드포인트를 쓴다. 표 구조화는 최선의 시도이며, 신뢰도가 낮아도 평문은 보존된다. 구조화 행이 비었다고 기준이 없는 것이 아니다.

### 법령해석

법원 판단과 구분되는 공식 해석. `source`가 권위 범위를 정한다.

| `source` | 범위 |
|---|---|
| `"moleg"` (기본) | 법제처 법령해석례 |
| `"ministry"` | 지정한 부처 하나의 1차 해석 (40개 부처 등록) |
| `"all"` | 법제처 **+ 지정한 부처 하나** |
| `"all_ministries"` | 40개 부처 전체 팬아웃. 비용이 크므로 깊은 분석에만 |

부처 해석 **본문**을 실으려면 `--source ministry --ministry <기관>`이 필요하다. `--id`만으로는 안 실린다.

두 부처(국세청·재정경제부)는 **검색은 되지만 본문 조회가 안 된다.** `get_interpretation`이 `UnsupportedFormatError`를 낸다.

### 판례와 헌재 결정

`search_cases` / `get_case`는 일반 법원(대법원·하급심), `search_constitutional_decisions` / `get_constitutional_decision`은 헌재를 다룬다. **서로 대체되지 않으며** 해석과도 대체되지 않는다.

로더가 태그를 교차 검증한다 — 헌재 신원을 `get_case`에 넘기면 `UnsupportedFormatError`다.

헌재 결정 상세에는 판결유형 키가 없어서 `decision_type`이 항상 비어 있다. 패키지는 **주문(【주 문】)에서 처분을 복구해** 각하·기각이 본안 판단으로 오인되지 않게 한다. 이유 부분은 반대의견 때문에 같은 표현을 반복하므로 주문만 훑는다.

헌법 도그마틱 탐색은 자유 텍스트 검색이다 → [Gotchas](Gotchas.md) 13번

### 위원회 의결 — 12개 기관

| 코드 | 기관 | 코드 | 기관 |
|---|---|---|---|
| `ppc` | 개인정보보호위원회 | `acr` | 국민권익위원회 |
| `ftc` | 공정거래위원회 | `nlrc` | 노동위원회 |
| `fsc` | 금융위원회 | `eiac` | 고용보험심사위원회 |
| `sfc` | 증권선물위원회 | `iaciac` | 산업재해보상보험재심사위원회 |
| `kcc` | 방송통신위원회 | `oclt` | 중앙토지수용위원회 |
| `nhrck` | 국가인권위원회 | `ecc` | 중앙환경분쟁조정위원회 |

**감독기관이 자기가 집행하는 법을 *적용한* 기록**이다 — 과징금, 시정명령, 침해 판단. 법령과 판례가 답하지 못하는 질문에 답한다: 그 감독기관이 실제로 움직였는가, 언제.

**판례가 아니다.** 한 기관의 집행 실무를 보여줄 뿐이며 행정소송에서 뒤집힐 수 있다.

### 행정심판 재결 — 일반 + 특별 4종

| 코드 | 기관 |
|---|---|
| `decc` (기본) | 일반 행정심판위원회 |
| `acr` | 국민권익위원회 특별행정심판 |
| `adap` | 소청심사위원회 |
| `tt` | 조세심판원 |
| `kmst` | 해양안전심판원 |

재결은 행정부 내부에서 다른 기관의 처분을 심사한 것이다.

**특별 심판기관의 재결은 일반 `decc` 목록에 없다.** 소청·조세·해양안전 사안을 `decc`에서만 찾으면 0건이 나오고, 그건 부재로 읽힌다. 재결은 법원 판결이 아니며 패소한 쪽은 여전히 행정소송을 낼 수 있다.

### 계획과 번들

위 계열들을 조합해 검색을 계획하거나 단계적 묶음을 만든다. **계획 보조이지 권위가 아니다.**

- `expand_legal_query` — 넓은 표현을 후보 법령·법률 용어·일상 용어·관련 조문·후속 조회 권고로 바꾼다
- `find_comparable_mechanisms` — 유사한 법적 장치(과징금·인허가·신고제 등)를 쓰는 법령 후보. 입법 설계 비교용
- `load_legal_context_bundle` — 넓은 질문에 대한 단계적 묶음
- `load_institutional_system` — **이미 고른** 법령 집합을 하나로
- `load_delegated_criteria` — 법령 하나에서 하위 행정규칙·별표 본문까지
- `load_authority_context` — 지정 조문에 스코프를 건 권위 수집
- `load_followup` — 위 결과가 준 후속 조회 실행

---

## 범위 밖

- **법률 자문.** 이 패키지는 법적 출처를 *싣는다*. 해석하거나 조언하지 않는다.
- **입법예고.** 입법예고는 국민참여입법센터라는 별개 시스템에 있고 law.go.kr OpenAPI가 노출하지 않는다.
- **국회 의안 데이터.** 의안 진행·발의자·표결·회의록은 별개 출처 소관이다. `resolve_promulgated_law`는 다른 출처가 제공한 공포 메타데이터를 *소비*할 뿐 직접 가져오지 않는다.
- **외국법·비교법.** 한국 law.go.kr 출처만 다룬다.
- **최신 통계·뉴스·정책 발표·사회적 맥락.** 법적 출처가 아니다.

`load_followup`에 `websearch`나 `congress-db` 인터페이스를 넘기면 `UnsupportedFormatError`가 난다 — 버그가 아니라 **경계 표시**다.

---

## 커버리지 한계

인용할 때 염두에 둘 것들. 상세는 [Gotchas](Gotchas.md).

**0건은 범위 한정이다.** 그 질의·출처 계열·필터로 행이 없었다는 뜻이다.

**검색 결과는 인용할 수 없다.** 제목·ID·날짜는 본문이 아니다.

**권위 층위는 분리된다.** 법제처 해석 ≠ 부처 해석 ≠ 판례 ≠ 헌재 결정 ≠ 위원회 의결 ≠ 행정심판 재결.

**빈 감독기관 기록은 무활동의 증명이 아니다.** 이 계열에서 오독의 손해가 가장 크다. 질문 자체가 대개 "그 기관이 안 움직였나"이기 때문이다. 다른 `--committee` 코드와 특별 심판기관을 확인하고, 공개 기록이 소진되면 그건 부정적 결론을 기록할 자리가 아니라 **공식 자료요구를 할 자리**다.

**공포 ≠ 시행.** 현행 효력 질문에는 `basis="effective"`를, 공포 사실 연결이나 과거 공포 맥락에는 `basis="promulgated"`를 쓴다.

**출처 실패는 법적 부재가 아니다.** `RateLimitError`·`RetryExhaustedError`·기타 `SourceApiError`는 접근 실패다.

**별표 추출은 평문을 보존한다.** 구조화 신뢰도가 낮아도 평문은 남는다.

---

## 원본 페이로드

공개 반환 모델은 정규화된 필드를 앞세우고 law.go.kr 원본 페이로드는 기본적으로 뺀다. 파서를 디버깅하거나 원본 모양을 확인할 때만 켠다.

```python
bundle.to_dict(include_raw=True)
```

CLI에서는 전역 `--raw` 플래그다. 평상시에는 기본값을 쓰라.

## 관련 문서

- [Core Concepts](Core-Concepts.md) — `basis` 선택과 권위 구분
- [Agent Integration](Agent-Integration.md) — 엔벨로프 신호와 컨텍스트 예산
- [Gotchas](Gotchas.md) — 각 한계가 실제로 어떻게 틀린 주장을 만드는지
- [Error Handling](Error-Handling.md) — 출처 실패 처리
- [CLI Reference](CLI-Reference.md) — 엔벨로프 계약과 서브커맨드
