# CLI 레퍼런스

모든 공개 메서드가 `moleg` 서브커맨드로 노출된다. 모든 호출은 stdout에 **JSON 엔벨로프 하나**를 찍고, 셸은 그 JSON을 파싱하지 않고도 **종료코드**로 분기할 수 있다.

엔벨로프 신호를 에이전트가 어떻게 읽어야 하는지는 [Agent Integration](Agent-Integration.md)에 있다. 이 페이지는 명령과 옵션의 전수 목록이다.

## 실행

```bash
moleg <command> [flags]              # 콘솔 스크립트
python -m moleg_api <command> …      # 모듈 형태 (체크아웃에서 편리)
```

**전역 플래그** — 서브커맨드 *앞*에 온다.

| 플래그 | 효과 |
|---|---|
| `--raw` | law.go.kr 원본 페이로드를 `data`에 포함. 디버깅용 |
| `--version` | `moleg-api 0.3.0`을 찍고 종료. 엔벨로프의 `version`과 같은 값 |
| `-h`, `--help` | 도움말 |

명령별 옵션은 `moleg <command> --help`로 볼 수 있다.

---

## 명령 목록

32개 과업 명령 + `catalog`. 버킷 구분은 `catalog`의 분류와 같다.

### 메타

| 명령 | 설명 |
|---|---|
| `catalog` | 명령 목록·규약·라우팅 규칙·`kind` 명세. **네트워크도 자격증명도 쓰지 않는다** |

### 검색·계획 — 후보를 준다 (인용 불가)

| 명령 | 인자 | 주요 옵션 | `kind` |
|---|---|---|---|
| `search-laws` | `query` | `--as-of` `--basis {effective,promulgated}` `--law-type` `--ministry` `--display`(20) | `law_hit_list` |
| `resolve-promulgated-law` | — | `--prom-law-nm` `--prom-no` `--promulgation-dt` | `law_identity` |
| `search-administrative-rules` | `query` | `--ministry` `--rule-type` `--issued-on` `--include-history` `--display`(20) | `admin_rule_hit_list` |
| `search-annex-forms` | `query` | `--source {law,administrative_rule}` `--search-scope {title,source,body}` `--annex-type` `--ministry` `--display`(20) | `annex_form_hit_list` |
| `search-interpretations` | `query` | `--source {moleg,ministry,all,all_ministries}` `--ministry` `--search-body` `--interpreted-on` `--display`(20) | `interpretation_hit_list` |
| `search-cases` | `query` | `--court {all,supreme,lower}` `--court-name` `--search-body` `--decided-on` `--case-number` `--display`(20) | `case_hit_list` |
| `search-constitutional-decisions` | `query` | `--search-body` `--decided-on` `--case-number` `--display`(20) | `constitutional_hit_list` |
| `search-committee-decisions` | `query`(선택) | `--committee` **(필수)** `--display`(20) | `committee_decision_hit_list` |
| `search-administrative-appeals` | `query`(선택) | `--tribunal`(기본 `decc`) `--display`(20) | `administrative_appeal_hit_list` |
| `expand-legal-query` | `query` | `--display`(5) `--no-websearch-hint` | `query_expansion_planning` |
| `find-comparable-mechanisms` | `concept` | `--display`(5) | `comparable_planning_list` |

**`--committee` 코드 12종**
`ppc` 개인정보보호위 · `ftc` 공정위 · `fsc` 금융위 · `sfc` 증선위 · `kcc` 방통위 · `nhrck` 인권위 · `acr` 권익위 · `nlrc` 노동위 · `eiac` 고용보험심사위 · `iaciac` 산재재심사위 · `oclt` 중앙토지수용위 · `ecc` 중앙환경분쟁조정위

**`--tribunal` 코드 5종**
`decc` 일반 행정심판위(기본) · `acr` 권익위 특별 · `adap` 소청심사위 · `tt` 조세심판원 · `kmst` 해양안전심판원

> 소청·조세·해양안전 사안을 `decc`에서만 찾으면 조용히 0건이 나온다. 별도 심판기관 소관이기 때문이다. 0건일 때 `discipline`이 다른 `--tribunal`을 확인하라고 알려 준다.

### 본문 로드 — 인용 가능

| 명령 | 인자 | 주요 옵션 | `kind` |
|---|---|---|---|
| `get-law` | — | `--law`**(필수)** `--as-of` `--basis` `--article`(반복) `--no-metadata` `--toc` | `law_text` / `--toc`면 `law_toc_map` |
| `get-article` | `article` | `--law`**(필수)** `--as-of` `--basis` | `article_text` |
| `load-article-context` | `article` | `--law`**(필수)** `--as-of` `--basis` `--no-follow-moved` | `article_context` |
| `get-administrative-rule` | — | `--id`**(필수)** `--article`(반복) `--no-metadata` | `admin_rule_text` |
| `load-administrative-rule-context` | — | `--id`**(필수)** `--article` `--no-metadata` `--no-follow-moved` | `admin_rule_context` |
| `get-annex-form-body` | — | `--id`/`--annex-id`**(필수)** `--source` `--title` `--no-metadata` `--no-structuring` | `annex_form_text` |
| `get-interpretation` | — | `--id`**(필수)** `--source` `--ministry` `--no-metadata` `--brief` | `interpretation_text` |
| `get-case` | — | `--id`**(필수)** `--no-metadata` `--brief` | `case_text` |
| `get-constitutional-decision` | — | `--id`**(필수)** `--no-metadata` `--brief` | `constitutional_text` |
| `get-committee-decision` | — | `--id`**(필수)** `--committee`**(필수)** `--brief` | `committee_decision_text` |
| `get-administrative-appeal` | — | `--id`**(필수)** `--tribunal` `--brief` | `administrative_appeal_text` |

> `get-interpretation`의 `--source` 기본값은 **`None`**이다(검색 쪽 기본값 `moleg`와 다르다). 부처 해석 본문을 실으려면 `--source ministry --ministry <기관>`이 필요하다 — `--id`만으로는 안 실린다.

### 연혁·체계·위임

| 명령 | 주요 옵션 | `kind` |
|---|---|---|
| `trace-law-history` | `--law`**(필수)** `--article` `--date-from` `--date-to` | `law_history` |
| `get-revision-reason` | `--law`**(필수)** `--mst` `--as-of` | `revision_reason_text` |
| `compare-law-versions` | `--law`**(필수)** `--article` | `law_diff` |
| `find-delegated-rules` | `--law`**(필수)** `--article` | `delegation_graph` |
| `get-law-structure` | `--law`**(필수)** `--depth`(0) | `law_structure_hierarchy_only` |

**개정 관련 3분기** — 자주 헷갈리는 지점이다.

- **왜** 고쳤나 → `get-revision-reason` (「개정이유 및 주요내용」)
- **무엇이** 바뀌었나 → `compare-law-versions` (조문 전후 대비)
- **어떤 개정들이** 있었나 → `trace-law-history` (연혁 목록)

연혁 이벤트의 `identity.mst`를 `get-revision-reason --mst`에 넣으면 그 개정으로 정확히 내려간다.

`--date-from`과 `--date-to`는 **둘 다** 줘야 범위 필터가 적용된다.

### 권위·묶음

| 명령 | 주요 옵션 | `kind` |
|---|---|---|
| `load-authority-context` | `--law`**(필수)** `--article`**(필수, 반복)** `--query` `--budget` `--as-of` | `authority_context` |
| `load-legal-context-bundle` | `--query` `--law` `--article` `--mode {question,promulgated_bill,statute_review}` `--budget` `--as-of` `--prom-law-nm` `--prom-no` `--promulgation-dt` | `legal_context_bundle` |
| `load-institutional-system` | `--statute`**(반복, 최소 1개)** `--article` `--budget` `--as-of` | `legal_context_bundle` |
| `load-delegated-criteria` | `--law`**(필수)** `--article` `--query` `--budget` `--as-of` | `legal_context_bundle` |
| `load-followup` | `--json`**(필수)** — deferred 객체 또는 `-`(stdin) | 결과 타입에서 파생 |

`--budget`은 `minimal | standard | broad`, 기본 `standard`.

`load-institutional-system`은 법령을 반복 지정한다: `--statute 001248 --statute 001250`

---

## 엔벨로프

```json
{
  "ok": true,
  "command": "get-article",
  "version": "0.3.0",
  "kind": "article_text",
  "source": "법제처 / 법령 조문",
  "count": 3,
  "data": { },
  "flags": { },
  "discipline": [ ],
  "next": [ ]
}
```

| 키 | 의미 |
|---|---|
| `ok` | 완료면 `true`(**0건 검색 포함**), 오류면 `false` |
| `command` | 실행된 서브커맨드. 인자 파싱 실패 시 `null` |
| `version` | 이 응답을 만든 **코드**의 버전. 모든 엔벨로프에 실린다 |
| `kind` | 결과의 의미 유형. 접미사가 인용 가능 여부를 가른다 |
| `source` | 사람이 읽는 출처 표기. 예: `법제처 / 헌재결정 본문` |
| `count` | 목록 결과에만. 0건이면 `0` |
| `data` | 직렬화된 결과. `--raw` 없으면 원본 페이로드 제외 |
| `flags` | 기계가 읽는 상태값. **비어 있으면 키 자체가 없다** |
| `discipline` | 해석 규율 문장 목록. 해당 함정이 이 결과에서 실제로 살아 있을 때만 나온다 |
| `next` | 실행 가능한 다음 명령. **최대 3개**. 넘치면 `flags.more_followups`에 개수 |

오류 엔벨로프는 `ok: false`, 오류 `kind`, `error` 메시지를 싣고 `data`는 없다. **오류도 stdout으로 나간다** — stderr가 아니다.

`version`이 항상 실리는 이유: 설치된 배포판이 아니라 **실제로 돈 코드**의 버전이어야 하기 때문이다. 체크아웃이 `sys.path`에 있으면 site-packages를 가리므로, 배포 메타데이터를 읽으면 "누가 답했나"에 답할 수 없다.

### `kind` 접미사 규약

- `*_hit` / `*_candidate` / `*_planning` → **검색 후보.** 다음에 무엇을 실을지의 메뉴다. 문언·금액·판시·법적 동등성을 여기서 인용하면 안 된다.
- `*_text` / `*_context` / `*_identity` → **실린 본문.** 인용 가능.

`kind`는 서브커맨드가 아니라 **결과 데이터클래스 타입**에서 파생된다. 그래서 `load-followup`으로 도착한 결과도 실제 실행된 인터페이스에 맞는 `kind`를 단다.

---

## 종료코드

| 코드 | 이름 | 의미 |
|---|---|---|
| `0` | 성공 | **0건 검색 포함** (`ok:true`, `count:0`) |
| `2` | 모호 | 복수 신원이 걸림. 후보를 제시하라, 고르지 마라 |
| `3` | 출처 | 읽기 실패 또는 해석 실패. **`kind`로 갈린다** |
| `4` | 결과 없음 | 본문 없음. **없는 식별자 포함**. 재시도 무의미 |
| `5` | 사용 오류 | 인자 오류, 또는 로더에 법령 이름을 넘김 |

코드 1은 쓰지 않는다. argparse 기본 종료코드 2는 `EXIT_AMBIGUOUS`와 충돌하지 않도록 5로 재매핑돼 있다.

**종료코드 3의 두 얼굴** — `source_access_error`는 일시적이라 재시도가 옳고, `parse_error`는 응답 모양을 못 알아본 것이라 재시도해도 똑같이 실패한다. 후자면 식별자를 먼저 의심하라.

**없는 식별자는 4다.** law.go.kr은 없는 식별자에 빈 본문으로 답한다. 이걸 파싱 실패(3)로 분류하면 영원히 성공할 수 없는 조회를 재시도하게 되므로, `no_result`(4)로 보내 검색으로 유도한다.

`kind` → 종료코드 대응:

| 코드 | `kind` |
|---|---|
| `2` | `ambiguous` |
| `3` | `source_access_error`, `parse_error`, `error` |
| `4` | `no_result`, `version_request_unfulfilled` |
| `5` | `needs_search_first`, `usage_error`, `unsupported` |

---

## 실전 예시

### 로더에 법령 이름을 넘겼을 때

```bash
$ moleg get-article --law "주택임대차보호법" 제3조
```
```json
{
  "ok": false, "kind": "needs_search_first",
  "error": "Identifier '주택임대차보호법' looks like a law name, not a law ID. …",
  "discipline": ["로더에 법령명이 들어옴 — search-laws로 law_id를 먼저 얻어 --law에 넘겨라."],
  "next": [{ "why": "먼저 신원 검색", "cmd": "moleg search-laws \"주택임대차보호법\"" }]
}
```
종료코드 5.

### 0건 검색

```bash
$ moleg search-cases "존재하지않는판례검색어" --display 3
```
```json
{
  "ok": true, "kind": "case_hit_list", "count": 0, "data": [],
  "flags": { "count": 0, "searched": { "query": "존재하지않는판례검색어", "court": "all" } },
  "discipline": ["0건 — 이 검색어·범위로 못 찾음일 뿐, 부재의 증명 아님."]
}
```
종료코드 0. `flags.searched`가 **무엇을 어떤 범위로 검색했는지** 되돌려 준다 — "이 검색어로 못 찾음"과 "존재하지 않음"을 구분하기 위해서다.

0건일 때 나오는 `next` 제안들:
- 판례·헌재 검색은 기본이 제목 검색이므로 `--search-body` 재시도를 제안
- 별표 검색은 `--search-scope`를 `title` ↔ `source`로 뒤집어 볼 것을 제안
- `--ministry` `--law-type` `--court-name` `--rule-type` 같은 필터를 걸었다면, 그걸 뺀 재시도를 제안

### 동명 법령이 여러 판본일 때

```bash
$ moleg search-laws "주택임대차보호법" --display 3
```
```json
{
  "ok": true, "kind": "law_hit_list", "count": 3,
  "flags": { "count": 3, "ambiguous_versions": true },
  "next": [
    { "why": "후보 로드: 주택임대차보호법 (시행 20260102)", "cmd": "moleg get-law --law 001248" },
    { "why": "후보 로드: 주택임대차보호법 (시행 20230719)", "cmd": "moleg get-law --law 001248 --as-of 20230719" }
  ]
}
```

`next`가 후보를 **현행 / 미시행 / 과거**로 갈라 라벨을 붙여 준다. 현행 판본에는 날짜가 없고, 나머지에는 각자의 시행일이 `--as-of`로 붙는다.

---

## 컨텍스트 예산

기본 로드가 질문이 필요로 하는 것보다 훨씬 클 수 있다. 실측(2026-07-19):

| 호출 | 바이트 |
|---|---|
| `get-law --law 011357` (조문 139개) | 276,748 |
| `get-law --law 011357 --toc` | 18,831 |
| `get-case --id 193332` | 82,700 |
| `get-case --id 193332 --brief` | 14,046 |

- **`--toc`** — 조문 지도만. `kind`가 `law_toc_map`이지 `*_text`가 아니다. **목차는 법령이 아니고**, 조문 제목은 그 조문이 무엇을 요구하는지 말할 근거가 못 된다.
- **`--brief`** — 결정문 5종에서 요지만. 축자 인용에는 전체 로드가 필요하며, `flags.brief.withheld`가 무엇을 뺐는지 정확히 알려 준다.
- **`flags.large_payload`** — 20,000자를 넘고 좁힐 옵션이 있었을 때. 검색 계열은 면제다.

상세는 [Agent Integration](Agent-Integration.md)의 컨텍스트 예산 절.

---

## `--as-of`

`--as-of <날짜>`는 그 날짜에 **시행 중이던** 판본을 싣는다(시행일이 요청일 이하인 것 중 최신). `YYYY-MM-DD`와 `YYYYMMDD` 둘 다 받는다.

날짜 형식이 틀리면 **조용히 현행으로 떨어지지 않고** 사용 오류(종료코드 5)가 난다. 달력 검증까지 한다 — 13월, 2월 30일, 99일은 거부된다.

반드시 돌아온 `flags.effective_date`를 확인하라. 요청일에 시행 중이던 판본이 없으면 이후 판본이 실려 오고 `flags.version_mismatch`가 붙는다. 자세한 것은 [Historical Versions](Historical-Versions.md).

---

## `load-followup` 파이프

```bash
moleg load-legal-context-bundle --query "온라인 플랫폼 허위광고 규율" \
  | jq '.data.deferred[0]' \
  | moleg load-followup --json -
```

`--json '<객체>'`로 인라인 전달도 되고 `--json -`로 stdin에서 읽어도 된다. **손으로 타이핑하지 마라** — 한국어 텍스트와 중첩 따옴표 때문에 오류가 나기 쉽고, `interface` 값이 알려진 목록에 없으면 거부된다. 리스트를 통째로 넘기는 것도 거부된다.

대부분의 엔벨로프는 `next`에 객체가 이미 박힌 `moleg load-followup --json …` 명령을 직접 담아 주므로, 파이프 대신 그걸 복사해도 된다.

`interface`가 `websearch`나 `congress-db`인 항목은 의도된 경계 표시다 — 그 사실은 다른 시스템 소관이다.

---

## 관련 문서

- [Agent Integration](Agent-Integration.md) — 신호를 읽는 법, `catalog` 계약, 컨텍스트 예산
- [API Reference](API-Reference.md) — 각 서브커맨드 뒤의 Python 메서드
- [Error Handling](Error-Handling.md) — 예외 계층과 재시도 정책
- [Gotchas](Gotchas.md) — 조용히 틀리는 지점
