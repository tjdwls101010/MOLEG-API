# 변경 이력

이 문서는 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 형식을 따르며, 버전은 [유의적 버전](https://semver.org/lang/ko/)을 따릅니다.

`0.x` 단계이므로 마이너 버전 올림에 호환성 깨짐이 포함될 수 있습니다.

---

## [0.3.0] — 2026-07-19

에이전트 소비자를 위한 릴리스입니다. 응답이 자기 상태를 더 정확히 알리고, 컨텍스트를 덜 먹으며, 새 출처 계열이 하나 늘었습니다.

### 추가

**행정기관의 판단 — 위원회 의결과 행정심판 재결.** 12개 위원회(개인정보보호위 `ppc`, 공정위 `ftc`, 금융위 `fsc`, 증선위 `sfc`, 방통위 `kcc`, 인권위 `nhrck`, 권익위 `acr`, 노동위 `nlrc`, 고용보험심사위 `eiac`, 산재재심사위 `iaciac`, 중앙토지수용위 `oclt`, 중앙환경분쟁조정위 `ecc`)와 4개 특별 심판기관을 포함한 행정심판(`decc`, `acr`, `adap`, `tt`, `kmst`)에 닿습니다.

감독기관이 자기가 집행하는 법을 *적용한* 기록이며, **판례와 구분해서** 다룹니다 — 별도 타입(`AdjudicationHit`, `AdjudicationText`)과 별도 `kind`(`committee_decision_text`, `administrative_appeal_text`)를 가지고, 결과마다 이것이 판례가 아님을 밝히는 권위 문장이 붙습니다.

```python
api.search_committee_decisions("개인정보 유출", committee="ppc")
api.get_administrative_appeal("12345", tribunal="tt")
```

**개정이유** — `get_revision_reason()`. law.go.kr이 이미 싣고 있으나 정규화 과정에서 버려지던 「개정이유 및 주요내용」을 노출합니다. `mst`로 판본을 고정하거나 `as_of`로 시점을 지정합니다.

**컨텍스트 예산 3종.**

- `get_law_toc()` / `get-law --toc` — 본문 없이 조문 지도만. 개인정보 보호법 기준 276KB → 19KB
- `--brief` — 결정문 5종에서 요지만 남기고 전문을 뺍니다. 어떤 결정문에서는 페이로드의 82%가 줄었습니다
- `flags.large_payload` — 20,000자를 넘고 좁힐 옵션이 있었을 때 붙습니다. 명령별 조언이 `discipline`에 함께 옵니다

**모든 엔벨로프에 `version`.** 어느 버전이 답했는지 알 수 없으면, 빠진 필드가 "이 릴리스에서 미지원"인지 "호출이 잘못됨"인지 구분할 수 없습니다. 배포 메타데이터가 아니라 **실제로 실행된 코드**의 버전을 보고합니다 — 체크아웃이 `sys.path`에 있으면 site-packages를 가리기 때문입니다.

### 변경 — 호환성 주의

**없는 식별자의 종료코드가 3 → 4로 바뀌었습니다.**

law.go.kr은 모르는 식별자에 대해 오류가 아니라 빈 본문으로 답합니다. 이전에는 이걸 파싱 실패로 분류해 종료코드 3을 냈고, 그 규율은 "잠시 후 재시도"였습니다 — **영원히 성공할 수 없는 조회에 대한 조언**이었습니다.

이제 `no_result`(종료코드 4)로 가서 `search-*`로 유도합니다. 종료코드 3에 의존해 재시도 루프를 돌리던 코드가 있다면 확인이 필요합니다.

### 수정

`_normalization/unwrap.py`의 `ParseFailureError` NameError.

### 테스트

**전 명령 스모크 테스트.** 모든 서브커맨드를 디스패치까지 통과시키고 catalog·parser·dispatch의 합치를 검증합니다. argv를 파서에서 도출하므로 새 명령이 자동으로 커버됩니다.

0.2.3 파일 분할에서 명령 분기 안에서만 실행되는 임포트 3개가 빠졌는데 CI가 그대로 통과한 사고 뒤에 추가됐습니다.

---

## [0.2.4] — 2026-07-04

### 수정

`load_institutional_system`의 CLI 디스패치 복구. 0.2.3 분할에서 누락됐습니다.

---

## [0.2.3] — 2026-07-04

### 변경

**내부 모듈 분할.** 커진 파일들을 책임 단위로 쪼갰습니다 — `_models`, `_normalization`, `_laws`, `_cli`.

**공개 API는 그대로입니다.** 루트의 `models.py`·`laws.py`·`normalization.py`·`cli.py`가 얇은 호환 파사드로 남아 기존 임포트가 계속 동작합니다. 분할 전에 호환성을 잠그는 테스트를 먼저 넣었습니다.

이 릴리스부터 커밋 메시지에 Conventional Commits를 씁니다.

### 수정

`_normalization`의 헌재 처분(disposition) 임포트 복구.

---

## [0.2.2] — 2026-07-04

### 수정

페르소나 트랩 감사에서 나온 **Tier 1·2 결함 12건**. 회귀 잠금은 `tests/test_sdk_fixes_0_2_2.py`에 있으며, 각 결함의 사유가 테스트 docstring에 기록돼 있습니다.

---

## [0.2.1] — 2026-07-04

### 수정

실사용 왕복에서 발견된 결함 5건.

- 별표 도달 범위
- 위임 하위규범 재현율
- 별표 라벨 복구
- 헌재 행 키의 대문자 처리 — law.go.kr이 판례는 `prec`(소문자), 헌재는 `Detc`(대문자)로 키를 짓습니다
- CLI `--version`

---

## [0.2.0] — 2026-07-04

### 추가

**셸 CLI.** 모든 과업 메서드가 `moleg` 서브커맨드가 되고, 호출마다 JSON 엔벨로프 하나를 찍습니다.

**위키 문서.**

### 수정

과거 판본 로딩. `법령ID + 시행일`로는 판본이 고정되지 않고 오류 없이 현행이 돌아온다는 문제를 MST 해석 경로로 해결했습니다.

---

## [0.1.1] — 2026-06-23

### 추가

**공용 기본 OC 자격증명.** 등록 없이 바로 동작합니다. OC는 무료이며 비밀이 아닌 계정 식별자입니다.

GitHub Release 발행 시 PyPI로 자동 배포.

---

## [0.1.0] — 2026-06-18

첫 공개 릴리스.

### 추가

- 법령 검색과 본문·조문 로딩, 공포 기준 신원 해석
- 연혁 추적과 개정 전후 비교
- 위임 하위규범과 법령 체계도
- 행정규칙 검색·로딩과 맥락 해소
- 별표·서식 검색과 본문 추출
- 법제처·부처 법령해석, 판례, 헌재 결정
- 질의 확장과 유사 제도 발견
- 단계적 컨텍스트 번들과 **실행 가능한 후속 조회** — 응답이 준 `deferred` 객체를 그대로 다시 넣으면 다음 조회가 실행됩니다
- 타입이 붙은 예외 계층
- PyPI OIDC 신뢰 배포

---

[0.3.0]: https://github.com/tjdwls101010/MOLEG-API/releases/tag/v0.3.0
[0.2.4]: https://github.com/tjdwls101010/MOLEG-API/releases/tag/v0.2.4
[0.2.3]: https://github.com/tjdwls101010/MOLEG-API/releases/tag/v0.2.3
[0.2.2]: https://github.com/tjdwls101010/MOLEG-API/releases/tag/v0.2.2
[0.2.1]: https://github.com/tjdwls101010/MOLEG-API/releases/tag/v0.2.1
[0.2.0]: https://github.com/tjdwls101010/MOLEG-API/releases/tag/v0.2.0
[0.1.1]: https://github.com/tjdwls101010/MOLEG-API/releases/tag/v0.1.1
[0.1.0]: https://github.com/tjdwls101010/MOLEG-API/releases/tag/v0.1.0
