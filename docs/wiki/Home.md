# moleg-api 위키

`moleg-api`는 법제처 [law.go.kr](https://www.law.go.kr/) OpenAPI를 **법적 과업 단위**로 감싼 Python SDK이자 CLI다. PyPI 패키지명은 `moleg-api`, 임포트는 `moleg_api`.

핵심 원리 한 줄: **검색으로 후보를 고르고, 로더로 본문을 싣는다.**

이 위키는 그 원리에서 파생되는 모든 것을 다룬다 — 왜 검색 결과를 인용하면 안 되는지, 왜 응답에 `discipline` 문자열이 실려 오는지, 왜 조문 번호를 여섯 자리로 바꿀 일이 없는지.

## 어디서부터 읽을 것인가

**처음이라면** → [Installation](Installation.md) → [Quickstart](Quickstart.md) → [Core Concepts](Core-Concepts.md)

**LLM 에이전트에 물리려 한다면** → [Core Concepts](Core-Concepts.md) → **[Agent Integration](Agent-Integration.md)** → [Gotchas](Gotchas.md)
이 패키지의 1차 소비자가 에이전트다. 엔벨로프의 세 신호, `catalog` 자기기술 명세, 종료코드 5종, 컨텍스트 예산 장치는 전부 그쪽을 위해 만들어졌다.

**특정 자료를 찾는다면** → [Sources & Coverage](Sources-and-Coverage.md)에서 출처 계열을 확인하고 [API Reference](API-Reference.md) 또는 [CLI Reference](CLI-Reference.md)로.

**과거 시점의 법을 물어야 한다면** → [Historical Versions](Historical-Versions.md). 여기엔 조용히 틀리는 함정이 하나 있어 별도 페이지를 뒀다.

**코드를 고치려 한다면** → [Architecture](Architecture.md) → [Maintainer Notes](Maintainer-Notes.md) → [CONTRIBUTING.md](../../CONTRIBUTING.md)

## 전체 목차

| 페이지 | 내용 |
|---|---|
| [Installation](Installation.md) | 설치, OC 자격증명 설정, 자격증명 해석 순서, macOS SSL 사정 |
| [Quickstart](Quickstart.md) | 검색→로드 왕복, 엔벨로프 해부, 번들과 후속 조회 |
| [Core Concepts](Core-Concepts.md) | 여섯 개념 — 검색→선택→로드, 후보 vs 본문, 시행 vs 공포, 식별자 체계, 권위 유형, 단계적 번들 |
| [Agent Integration](Agent-Integration.md) | `flags`·`discipline`·`next` 세 신호, `catalog` 계약, 종료코드, 컨텍스트 예산, 의도 게이트 |
| [CLI Reference](CLI-Reference.md) | 32개 과업 서브커맨드 + `catalog` 전수, 옵션, 엔벨로프 키, 종료코드 |
| [API Reference](API-Reference.md) | 33개 공개 메서드 시그니처 전수, 공개 데이터클래스, 직렬화 계약 |
| [Historical Versions](Historical-Versions.md) | `as_of`, MST가 판본을 고정하는 이유, "조용한 현행" 함정, 커버리지 하한 |
| [Sources & Coverage](Sources-and-Coverage.md) | 출처 계열 → 메서드/명령 대응표, 위원회·심판기관 코드, 40개 부처, 범위 밖 |
| [Gotchas](Gotchas.md) | 조용히 틀리는 지점 모음 |
| [Error Handling](Error-Handling.md) | 예외 계층, 일시적 실패 vs 영구 부재, 재시도 정책 |
| [Architecture](Architecture.md) | 4계층 구조, 22개 믹스인 합성, 정규화 계층이 푸는 문제 |
| [Maintainer Notes](Maintainer-Notes.md) | 호환 파사드, 파일 크기 가드레일, 알려진 중복, 릴리스 절차 |

## 무엇을 다루고 무엇을 안 다루는가

커버리지 상세는 [Sources & Coverage](Sources-and-Coverage.md)에 있고, 여기서는 경계만 밝힌다.

**다룬다** — 법령 본문과 조문, 부칙, 연혁과 개정 전후 비교, 과거 판본, 개정이유, 위임 하위규범과 법령 체계도, 행정규칙, 별표·서식 본문, 법제처·부처 법령해석, 대법원 판례, 헌재 결정, 12개 위원회 의결과 행정심판 재결, 질의 확장과 단계적 컨텍스트 번들.

**안 다룬다**

- **법률 자문.** 이 패키지는 법적 출처를 싣는다. 그것을 해석해 결론을 내지 않는다.
- **국회 의안 데이터.** 의안 진행 상황·발의자·표결·회의록은 범위 밖이다. 별도 출처를 써라.
- **입법예고.** 국민참여입법센터는 별개 시스템이다.
- **최신 통계·뉴스·정책 발표.** 웹 검색이나 다른 현재 출처를 써라.

명시적으로 못박아 둘 두 가지가 더 있다.

**검색 0건은 부재의 증명이 아니다.** 그 검색어와 그 출처 계열, 그 필터 조합으로 못 찾았다는 뜻일 뿐이다.

**권위 유형은 평탄화되지 않는다.** 법제처 해석, 부처 1차 해석, 대법원 판례, 헌재 결정, 위원회 의결, 행정심판 재결은 출처 권위가 서로 다르고 서로 대체하지 못한다. 이 패키지는 그 구분을 타입과 `source_type`/`source_authority` 필드로 끝까지 보존한다. 답을 쓸 때 뭉개면 그 보존이 무의미해진다.

## 상태

알파 (`0.3.0`). 인터페이스는 쓸 만하지만 law.go.kr의 라이브 동작은 출처·자격증명·엔드포인트 가용성에 따라 달라진다. 검색 결과는 로더가 본문을 실어 오기 전까지 후보다.
