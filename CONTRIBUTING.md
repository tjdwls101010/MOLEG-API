# 기여 안내

`moleg-api`에 기여해 주셔서 감사합니다. 이 문서는 개발 환경, 테스트, 브랜치·커밋 규칙, 릴리스 절차를 다룹니다.

내부 구조를 먼저 파악하려면 [Architecture](docs/wiki/Architecture.md)와 [Maintainer Notes](docs/wiki/Maintainer-Notes.md)를 보세요.

## 개발 환경

```bash
git clone https://github.com/tjdwls101010/MOLEG-API.git
cd MOLEG-API
python -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"
```

Python **3.10 이상**. CI는 3.10 / 3.11 / 3.12에서 돕니다.

`test` 추가 의존성은 `pytest`뿐입니다. 런타임 의존성은 **0개**이며, 이건 유지해야 할 성질입니다 — 이 패키지는 다른 도구의 의존성 트리 안에 얹히는 것을 전제로 만들어졌습니다. 새 의존성을 추가하는 PR은 그것이 왜 불가피한지 설명이 필요합니다.

`pyproject.toml`에 `dev` 추가 의존성도 있지만 `psycopg`만 더 넣으며, 지금은 **쓰이지 않습니다**(사라진 congress-db 연동의 잔재). `requirements-dev.txt`도 같은 이유로 아무 데서도 참조되지 않습니다. 개발에는 `test`를 쓰세요.

### 환경변수

```bash
cp .env.example .env.local
```

| 변수 | 용도 |
|---|---|
| `MOLEG_OC` | law.go.kr 자격증명. **라이브 테스트에만 필요** |
| `CONGRESS_DB_READONLY_URL` | `.env.example`에 있지만 **패키지 어디서도 읽지 않습니다**. 잔재입니다 |

`.env`와 `.env.*`는 gitignore돼 있고 `.env.example`만 커밋됩니다. `tests/test_source.py`가 `.env.example`의 두 키가 **값 없이** 선언돼 있는지 검사합니다 — 비밀이 커밋되는 것을 막는 장치입니다.

## 테스트

**529개 테스트** — 오프라인 511개, 라이브 18개.

```bash
# 오프라인만 — CI가 도는 것
python -m pytest -q -m "not live"

# 라이브만
MOLEG_OC=<your-oc> python -m pytest -q -m live

# 전부
python -m pytest -q
```

> ⚠️ **`pytest`를 맨몸으로 돌리면 라이브 테스트도 함께 돕니다.** `pyproject.toml`에 `addopts`로 `live`를 빼는 설정이 없어서, `MOLEG_OC`가 환경변수나 `.env`/`.env.local` 어디에든 잡히면 실행됩니다. 오프라인만 돌리려면 `-m "not live"`를 명시하세요.

라이브 테스트는 `tests/test_live_smoke.py` 한 파일이고, 모듈 수준 `pytestmark`로 `MOLEG_OC`가 없으면 스킵됩니다. law.go.kr이 아무것도 안 돌려주면 실패가 아니라 스킵으로 떨어집니다 — 상류 불안정이 CI를 빨갛게 만들면 안 되기 때문입니다.

### 테스트 작성법

**`conftest.py`가 없습니다.** 녹화된 카세트도, VCR도, `responses`도 없습니다. 이음매는 `MolegSource` 프로토콜이고, 테스트는 직접 만든 가짜를 주입합니다.

```python
class FakeSource:
    def __init__(self, *, search_payloads=None, service_payloads=None, ...):
        self.calls = []

    def search(self, target, params):
        self.calls.append(("search", target, params))
        return self.search_payloads.pop(0)   # FIFO 큐

api = MolegApi(source=FakeSource(search_payloads=[{...}]))
```

각 큐는 **FIFO `pop(0)`**입니다. 그래서 테스트가 호출 *순서*를 검증할 수 있고, `self.calls`로 어떤 target과 파라미터가 나갔는지 확인할 수 있습니다 — 예를 들어 검증 가드가 **출처 호출 전에** 입력을 거부했는지, MST가 ID보다 우선됐는지.

페이로드는 각 테스트 안에 인라인으로, 검증 대상 필드만 남겨 씁니다.

다른 가짜들:

| 이름 | 용도 |
|---|---|
| `StubApi` | `__getattr__` 포괄 스텁. SDK를 건드리지 않고 CLI 디스패치만 구동 |
| `FakeResponse` | `urlopen` 대역. HTTP 계층 자체를 시험 |

CLI 테스트는 `capsys`로 엔벨로프 JSON을 파싱합니다.

**CLI 테스트는 결과 데이터클래스 타입을 키로 씁니다**(명령 이름이 아니라). 그래서 명령 이름이 바뀌어도 살아남습니다.

### 테스트 파일 지도

| 파일 | 다루는 것 |
|---|---|
| `test_laws.py` | 대부분. `FakeSource`로 모든 과업 메서드 |
| `test_cli.py` | 엔벨로프와 신호 도출, 오류→종료코드 매핑 |
| `test_source.py` | 전송 계층 — 재시도, 호출 제한, SSL/CA, OC 해석 순서, `.env` 파싱 |
| `test_models.py` | 데이터클래스 불변식, 재귀 직렬화, `include_raw` |
| `test_versions.py` | 판본 로딩, MST 해석, 연혁 파서 |
| `test_live_smoke.py` | 유일한 라이브 파일 |
| `test_refactor_compat.py` | 호환 파사드 잠금 |
| `test_sdk_fixes_0_2_1.py`, `test_sdk_fixes_0_2_2.py` | 회귀 잠금 |
| `test_*_0_3_0.py` (6개) | 0.3.0 작업 항목별 회귀 잠금 |

**결함별 사유가 테스트 파일 docstring에 기록돼 있습니다.** 회귀 테스트를 추가할 때 이 관행을 따라 주세요 — 무엇을 잠갔는지보다 **왜 잠갔는지**가 나중에 훨씬 유용합니다.

날짜에 의존하는 테스트는 `date.today()` 취약성을 피하려고 아주 먼 미래(2999년)나 과거를 씁니다.

## CI

두 워크플로가 있고, **라이브 테스트는 CI에서 절대 돌지 않습니다** — 둘 다 `-m "not live"`를 쓰고 `MOLEG_OC` 시크릿을 주입하지 않습니다.

### `ci.yml` — PR과 main 푸시

**`test` 잡** (ubuntu, Python 3.10/3.11/3.12 매트릭스)

1. `python -m pip install -e ".[test]"`
2. `python -m compileall moleg_api tests`
3. `git diff --check` — 공백 위생
4. `python -m pytest -q -m "not live"`

**`package` 잡** — 휠을 빌드해 임시 디렉터리에 설치한 뒤, **체크아웃 밖에서** 다음을 단언합니다.

- 임포트된 `moleg_api.__file__`이 설치 대상 안에 있는가 (체크아웃이 아니라)
- `py.typed`가 함께 배포되는가
- `__all__`의 모든 이름이 실제로 해석되는가
- `LawIdentity.to_dict()`가 `raw`를 빼는가
- `DeferredLookup.to_dict()`가 집합을 결정적으로 정렬하고 키 충돌을 명확히 구분하는가

> **린터도, 포매터도, 타입 체커도, 커버리지도 없습니다.** 정적 게이트는 `compileall`과 `git diff --check`가 전부입니다. 이건 의도된 최소주의라기보다 현재 상태에 가깝습니다 — 도입 PR은 환영하지만 별도 논의가 필요합니다.

### `workflow.yml` — PyPI 배포

`release: published`에 발동하거나 `workflow_dispatch`로 수동 실행합니다. OIDC 신뢰 배포를 쓰므로 API 토큰이 없습니다. `pypi`로의 수동 배포는 `main` 브랜치에서만 허용됩니다.

## 브랜치와 커밋

### 브랜치 이름

저장소 이력에는 **세 가지 체계가 공존**합니다 — `1-slug`(초기), `codex/50-slug`(에이전트 작업), `wi-p1-slug`(0.3.0 작업 항목). 새 작업은 다음 형태를 써 주세요.

```
<이슈번호>-<짧은-슬러그>       예: 42-annex-table-confidence
docs/<슬러그>                  문서만 바꿀 때
fix/<슬러그>                   이슈 없는 버그 수정
```

머지된 브랜치는 정리해 주세요. 현재 원격에 58개가 남아 있는데, 좋은 상태가 아닙니다.

### 커밋 메시지

**Conventional Commits**를 씁니다. 0.2.3부터 적용된 규칙이라 그 이전 이력은 따르지 않습니다.

```
feat(laws): reach agency adjudications — committee decisions and 행정심판 재결 (#101)
fix(cli): split permanent identifier failures out of exit 3 (#96)
refactor(models): split model internals behind public facade
test(refactor): lock sdk compatibility before splitting modules
chore(release): 0.3.0 (#102)
```

스코프: `laws`, `cli`, `models`, `normalization`, `source`, `docs`, `release`.

제목은 **무엇이 달라졌는지를 사용자 관점에서** 쓰세요. `feat(cli): add --toc flag`보다 `feat(cli): add a map, a précis, and a size signal`이 낫습니다 — 후자는 왜 그것들이 한 묶음인지를 말합니다.

## Pull Request

1. `main`에서 브랜치를 땁니다
2. 테스트를 함께 씁니다. 버그 수정이면 **먼저 실패하는 테스트**를 쓰고, docstring에 결함의 사유를 남깁니다
3. 과업 메서드를 건드렸으면 **네 곳을 함께** 고칩니다 — `_laws/api_*.py`, `_cli/parser.py`, `_cli/dispatch.py`, `_cli/catalog.py`
4. 문서를 함께 갱신합니다 — [API Reference](docs/wiki/API-Reference.md), [CLI Reference](docs/wiki/CLI-Reference.md)
5. 로컬에서 `python -m pytest -q -m "not live"`를 통과시킵니다
6. PR을 엽니다. CI가 매트릭스와 패키징 게이트를 돌립니다

라이브 동작에 영향이 있는 변경이라면 로컬에서 라이브 스모크도 돌려 보고, PR 본문에 결과를 적어 주세요. CI는 그걸 검증하지 못합니다.

## 릴리스 절차

메인테이너용입니다.

1. **버전을 올립니다** — `moleg_api/_version.py`의 리터럴 한 곳. `pyproject.toml`이 이 속성을 읽으므로 다른 데는 없습니다
2. **CHANGELOG.md**에 항목을 추가합니다
3. `chore(release): X.Y.Z` 커밋으로 PR을 열고 머지합니다
4. **점검**:
   ```bash
   python -m compileall moleg_api tests -q
   python -m pytest -q -m "not live"
   MOLEG_OC=<oc> python -m pytest -q -m live
   moleg catalog
   python -m build && python -m twine check dist/*
   ```
5. **주석 태그**를 답니다 (경량 태그가 아니라):
   ```bash
   git tag -a v0.3.1 -m "moleg-api 0.3.1"
   git push origin v0.3.1
   ```
6. **GitHub Release를 발행**합니다. 이게 `workflow.yml`을 발동시켜 PyPI로 배포합니다

`release: published`가 배포 트리거이므로, **태그만 밀고 Release를 안 만들면 PyPI에 올라가지 않습니다.**

## 문서

문서는 **한국어**로 씁니다(파일명은 영어 유지). 위키 페이지 하나를 고칠 때 지켜야 할 것:

- `docs/wiki/_Sidebar.md`에 새 페이지를 등록합니다
- README와 `Home.md`가 그 페이지를 가리키는지 확인합니다
- **README와 위키는 내용을 중복하지 않습니다.** README는 현관이고 위키는 깊이입니다. 한쪽에 속하는 내용은 다른 쪽에서 링크입니다

## 행동강령

이 프로젝트는 [행동강령](CODE_OF_CONDUCT.md)을 따릅니다.

## 보안

취약점은 이슈로 열지 마세요. [SECURITY.md](SECURITY.md)의 절차를 따라 주세요.
