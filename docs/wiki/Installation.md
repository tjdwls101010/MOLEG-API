# 설치와 설정

## 요구 사항

- **Python 3.10 이상** (3.10 / 3.11 / 3.12에서 CI 검증)
- **런타임 의존성 0개** — 표준 라이브러리만 쓴다. `urllib`, `json`, `ssl`, `dataclasses`가 전부다.

의존성이 없는 것은 설계 결정이다. 이 패키지는 다른 도구의 의존성 트리 안에 얹히는 것을 전제로 만들어졌고, 거기서 버전 충돌을 일으키지 않는 편이 낫다고 봤다.

## 설치

```bash
pip install moleg-api
```

배포명은 하이픈(`moleg-api`), 임포트는 밑줄(`moleg_api`)이다.

타입 힌트가 함께 배포된다(PEP 561, `py.typed` 포함). mypy·pyright가 별도 스텁 없이 바로 읽는다.

설치하면 `moleg` 콘솔 명령이 등록된다. 체크아웃에서 바로 쓰려면 `python -m moleg_api`도 같게 동작한다.

### 소스에서

```bash
git clone https://github.com/tjdwls101010/MOLEG-API.git
cd MOLEG-API
pip install -e ".[test]"
```

개발 환경 상세는 [CONTRIBUTING.md](../../CONTRIBUTING.md)를 보라.

## 동작 확인

```bash
moleg --version          # moleg-api 0.3.0
moleg catalog            # 네트워크 없이 명령 명세를 찍는다
```

`catalog`는 자격증명도 네트워크도 쓰지 않는다. 이건 되는데 다른 명령이 안 되면, 문제는 설치가 아니라 네트워크나 자격증명 쪽이다.

라이브 호출까지 확인하려면:

```bash
moleg search-laws "주택임대차보호법" --display 3
```

## OC 자격증명

law.go.kr OpenAPI는 “OC”라는 계정 식별자를 쿼리 파라미터로 요구한다. **무료이고 비밀이 아니다** — 모든 요청 URL에 평문으로 실려 나간다.

패키지에는 공용 기본값(`chunghun1`)이 들어 있어 **등록 없이 바로 동작한다.** 실험하거나 가볍게 쓸 때는 그대로 두면 된다.

다만 OC는 계정 단위로 호출량이 관리된다. 공용 기본값은 모든 사용자의 트래픽을 한 자격증명으로 몰아넣으므로 law.go.kr의 호출 제한에 걸릴 수 있다. 실사용에서는 [law.go.kr 오픈API](https://open.law.go.kr/)에서 자기 것을 발급받아 쓰는 편이 낫다.

### 설정 방법 — 우선순위 순

```python
# 1. 생성자 인자 (가장 강함)
from moleg_api import MolegApi, LawGoKrClient
api = MolegApi(source=LawGoKrClient(oc="내계정"))
```

```bash
# 2. 환경변수
export MOLEG_OC=내계정

# 3. 현재 작업 디렉터리의 .env.local
echo 'MOLEG_OC=내계정' > .env.local

# 4. 현재 작업 디렉터리의 .env
echo 'MOLEG_OC=내계정' > .env
```

넷 다 없으면 내장 기본값을 쓴다. CLI에는 `--oc` 플래그가 없다 — 2~4번 경로를 쓴다.

**주의할 점 두 가지.**

`.env` 파일은 **패키지 위치나 저장소 루트가 아니라 현재 작업 디렉터리(`Path.cwd()`) 기준**으로 찾는다. 어디서 실행하느냐에 따라 결과가 달라진다.

읽은 값은 `os.environ`에 심어지지 않는다. 조회할 때마다 파일에서 다시 읽으며, 같은 프로세스의 다른 라이브러리는 이 값을 보지 못한다.

`python-dotenv` 의존성은 없다. 파싱은 직접 구현돼 있고 — 빈 줄과 `#` 주석을 건너뛰고, 첫 `=`에서 나누고, 값을 감싼 따옴표 한 쌍을 벗긴다.

### 마스킹

OC는 비밀이 아니지만 그래도 새어 나가면 지저분하다. 모든 오류 메시지와 응답 스니펫에서 `***`로 치환되고, `HistoryEvent.article_link`에 실리는 law.go.kr 링크에서도 `OC=` 파라미터가 정규식으로 제거된다.

## 클라이언트 조정

기본값을 바꿔야 하면 `LawGoKrClient`를 직접 만들어 넘긴다. 인자는 전부 키워드 전용이다.

```python
from moleg_api import MolegApi, LawGoKrClient

api = MolegApi(source=LawGoKrClient(
    oc="내계정",
    timeout_seconds=30,        # 기본 30
    max_retries=2,             # 기본 2 → 총 3회 시도
    retry_delay_seconds=0.5,   # 기본 0.5. 고정 대기이며 지수 백오프가 아니다
    ca_file=None,              # 아래 참고
))
```

재시도 대상은 HTTP `408 429 500 502 503 504`와 타임아웃·네트워크 오류다. 그 밖의 상태 코드는 재시도하지 않고 즉시 올린다. 자세한 것은 [Error Handling](Error-Handling.md).

## macOS에서 SSL 인증서 오류가 날 때

Homebrew로 설치한 Python은 CA 번들을 못 찾는 경우가 있다. 이 패키지는 다음 순서로 알아서 찾는다.

1. `ca_file=`로 명시한 경로
2. 시스템 기본 검증 경로 (`ssl.get_default_verify_paths()`)
3. `/etc/ssl/cert.pem` → `/opt/homebrew/etc/openssl@3/cert.pem` → `/usr/local/etc/openssl@3/cert.pem` 중 실제로 존재하는 첫 번째
4. 기본 컨텍스트

그래도 `CERTIFICATE_VERIFY_FAILED`가 나면 경로를 직접 준다.

```python
LawGoKrClient(ca_file="/opt/homebrew/etc/openssl@3/cert.pem")
```

**인증서 검증을 끄는 경로는 제공하지 않는다.** 필요해 보인다면 그건 CA 번들 경로 문제이지 검증 문제가 아니다.

## 다음

- [Quickstart](Quickstart.md) — 첫 왕복
- [Core Concepts](Core-Concepts.md) — 왜 검색과 로드가 나뉘어 있는지
- [Agent Integration](Agent-Integration.md) — 에이전트에 물릴 때
