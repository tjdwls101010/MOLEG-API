<p align="center">
  <img src="https://raw.githubusercontent.com/tjdwls101010/tjdwls101010/main/Images/moleg%20api.png" width="360" alt="MOLEG-API — Search. Choose. Load.">
</p>

<h1 align="center">moleg-api</h1>

<p align="center">
  법제처 <a href="https://www.law.go.kr/">law.go.kr</a> OpenAPI를 <b>법적 과업 단위</b>로 감싼 Python SDK · CLI<br>
  <b>검색으로 후보를 고르고, 로더로 본문을 싣는다.</b>
</p>

<p align="center">
  <a href="https://pypi.org/project/moleg-api/"><img src="https://img.shields.io/pypi/v/moleg-api" alt="PyPI"></a>
  <a href="https://pypi.org/project/moleg-api/"><img src="https://img.shields.io/pypi/pyversions/moleg-api" alt="Python versions"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="License: MIT"></a>
</p>

---

## 이게 무엇인가

법제처 OpenAPI는 195개 안내 문서에 흩어진 엔드포인트 묶음이다. 같은 개념이 엔드포인트마다 다른 한글 키 이름으로 오고, 조문 번호는 여섯 자리 `JO` 코드로 인코딩되며, 법령 하나를 가리키는 식별자만 `ID`·`MST`·`LID` 세 가지다. "지금 시행 중인 조문"과 "공포된 조문"은 아예 다른 엔드포인트 계열이고, 연혁만 HTML로 돌아온다.

`moleg-api`는 그 복잡성을 호출자에게 떠넘기지 않는다. 공개 표면은 **원시 엔드포인트가 아니라 법적 과업**으로 되어 있다 — 법령을 검색하고, 조문을 싣고, 개정 이력을 추적하고, 위임된 하위규범을 찾고, 헌재 결정을 읽는다.

```python
api.get_article(identity, "제3조")     # ← 이렇게 부른다
# target=eflawjosub, JO=000300, MST=…   ← 이런 건 몰라도 된다
```

## 왜 이런 모양인가

이 패키지의 1차 소비자는 **LLM 에이전트**다. 사람이 브라우저로 법령을 찾을 때와 달리, 에이전트는 (a) 무엇을 인용해도 되는지 스스로 판단해야 하고 (b) 컨텍스트 예산이 유한하며 (c) 빈 결과를 "그런 것은 없다"로 오독하면 그대로 답에 실린다.

그래서 세 가지가 라이브러리 설계에 박혀 있다.

**하나 — 검색 결과는 인용할 수 없다.** 검색은 *후보*(`*Hit`)를 주고, 로더는 *본문*(`*Text`)을 준다. 이 경계는 타입으로 강제된다. 로더에 법령 *이름*을 넘기면 실행되지 않고 "먼저 `search_laws`를 부르라"는 오류가 난다.

**둘 — 규율이 응답에 실려 나간다.** CLI 엔벨로프는 데이터만이 아니라 `discipline` 배열을 함께 싣는다. "0건은 이 검색어로 못 찾았다는 뜻일 뿐 부재의 증명이 아님", "법제처 해석 ≠ 부처 1차 해석 — 답에서 출처 유형 보존" 같은 문장이 기계가 읽을 수 있는 형태로 온다.

**셋 — 크기를 신호로 준다.** `get-law`로 개인정보 보호법 전문을 부르면 276KB다. `--toc`는 같은 법의 조문 지도만 19KB로 준다. 좁힐 수 있었는데 안 좁혔으면 `flags.large_payload`가 붙는다.

## 설치

```bash
pip install moleg-api
```

Python 3.10 이상. **런타임 의존성 0개** — 표준 라이브러리만 쓴다.

라이브 호출에는 law.go.kr OpenAPI 자격증명(“OC”)이 필요하지만, **패키지에 공용 기본값이 들어 있어 등록 없이 바로 동작한다.** 본격적으로 쓸 거라면 law.go.kr에 직접 등록해 `MOLEG_OC`를 설정하는 편이 좋다 → [Installation](docs/wiki/Installation.md)

## 첫 호출

Python — 검색해서 고르고, 고른 것을 싣는다.

```python
from moleg_api import MolegApi

api = MolegApi()
hits = api.search_laws("주택임대차보호법")            # 후보 (인용 불가)
article = api.get_article(hits[0].identity, "제3조")   # 본문 (인용 가능)
print(article.text)
```

셸 — 모든 메서드가 `moleg` 서브커맨드이고, 언제나 JSON 엔벨로프 하나를 찍는다.

```bash
moleg catalog                                       # 명령 목록·라우팅·kind 전체 명세
moleg search-laws "주택임대차보호법"                  # → law_id를 가진 후보들
moleg get-article --law 001248 제3조                 # 현행 조문
moleg get-article --law 001248 --as-of 2021-01-01 제3조   # 그날 시행 중이던 판본
```

`python -m moleg_api …`로도 같게 동작한다.

## 무엇을 다루는가

- **법령 본문** — 현행(`effective`)·공포(`promulgated`) 기준 법령과 조문, 삭제·이동 상태 포함
- **부칙·연혁·비교** — 부칙(시행일·적용례·경과조치), 개정 이력, 개정 전후 대비
- **과거 판본** — `as_of`로 특정 시점에 시행 중이던 조문을 싣는다
- **개정이유** — 특정 판본의 「개정이유 및 주요내용」
- **위임 구조** — 위임 하위규범, 법령 체계도, 행정규칙(고시·훈령·예규)
- **별표·서식** — 법령·행정규칙의 별표/별지 본문. 과태료 기준·수수료표가 실제로 사는 곳
- **해석과 판단** — 법제처 법령해석, 40개 부처 1차 해석, 대법원 판례, 헌재 결정
- **행정기관의 판단** — 12개 위원회 의결(개인정보보호위·공정위·금융위·인권위·노동위 등)과 4개 특별행정심판을 포함한 행정심판 재결. **판례와 구분해서** 다룬다
- **탐색 보조** — 질의 확장, 유사 제도 발견, 실행 가능한 후속 조회를 품은 단계적 컨텍스트 번들

**다루지 않는 것**: 법률 자문, 국회 의안 데이터(의안 진행·표결·회의록), 입법예고(국민참여입법센터는 별개 출처), 최신 통계·뉴스.

## 문서

| | |
|---|---|
| [Home](docs/wiki/Home.md) | 위키 진입점 |
| [Installation](docs/wiki/Installation.md) · [Quickstart](docs/wiki/Quickstart.md) | 설치와 첫 성공까지 |
| [Core Concepts](docs/wiki/Core-Concepts.md) | 검색→선택→로드, 후보 vs 본문, 식별자, 권위 구분 |
| **[Agent Integration](docs/wiki/Agent-Integration.md)** | **에이전트에 물릴 때 읽을 것** — 엔벨로프 신호, catalog 계약, 종료코드, 컨텍스트 예산 |
| [CLI Reference](docs/wiki/CLI-Reference.md) · [API Reference](docs/wiki/API-Reference.md) | 32개 서브커맨드 / 33개 메서드 전수 |
| [Historical Versions](docs/wiki/Historical-Versions.md) | `as_of`와 "조용한 현행" 함정 |
| [Sources & Coverage](docs/wiki/Sources-and-Coverage.md) | 출처 계열별 커버리지와 범위 밖 |
| [Gotchas](docs/wiki/Gotchas.md) | 조용히 틀리는 지점들 |
| [Error Handling](docs/wiki/Error-Handling.md) | 예외 계층, 재시도가 옳은 경우와 아닌 경우 |
| [Architecture](docs/wiki/Architecture.md) · [Maintainer Notes](docs/wiki/Maintainer-Notes.md) | 내부 구조 |

## 상태

알파 (`0.3.0`). 인터페이스는 쓸 만하지만 law.go.kr의 라이브 동작은 출처·자격증명·엔드포인트 가용성에 따라 달라진다. 검색 결과는 로더가 본문을 실어 오기 전까지 후보로 취급하라.

**이 패키지는 법적 출처 로더이지 법률 자문이 아니다.**

기여는 [CONTRIBUTING.md](CONTRIBUTING.md), 취약점 신고는 [SECURITY.md](SECURITY.md), 변경 이력은 [CHANGELOG.md](CHANGELOG.md)를 보라.

## 라이선스

MIT — [LICENSE](LICENSE)
