# 메인테이너 노트

내부 구조 자체는 [Architecture](Architecture.md)에, 개발 환경과 PR 절차는 [CONTRIBUTING.md](../../CONTRIBUTING.md)에 있다. 이 페이지는 **유지보수 규칙**이다.

## 깨뜨리면 안 되는 공개 표면

```python
from moleg_api import MolegApi
from moleg_api import LawGoKrClient
import moleg_api.models
import moleg_api.laws
import moleg_api.normalization
import moleg_api.cli
```

루트의 `models.py`·`laws.py`·`normalization.py`·`cli.py`는 **의도적으로 얇은 호환 계층**이다. 0.2.3에서 큰 파일들을 쪼갤 때 기존 임포트가 깨지지 않도록 남겼다. `tests/test_refactor_compat.py`가 이걸 잠그고 있다.

`moleg_api/__init__.py`의 `__all__`이 큐레이션된 공개 목록(71개)이다. `moleg_api.models.__all__`은 동적으로 계산되며 `Any`·`Literal`·`dataclass` 같은 비모델 이름이 새어 나오므로, **공개 계약의 기준은 `moleg_api/__init__.py`다.**

## 과업 하나를 추가·제거할 때

과업 메서드를 하나 건드리면 **네 곳을 함께 고쳐야 한다.**

1. `_laws/api_*.py` — 메서드 자체
2. `_cli/parser.py` — 서브커맨드와 옵션
3. `_cli/dispatch.py` — 라우팅
4. `_cli/catalog.py` — 명령 목록·라우팅 규칙·`kind`

그리고 문서 두 곳: [API Reference](API-Reference.md)와 [CLI Reference](CLI-Reference.md).

`tests/test_command_smoke_0_3_0.py`가 catalog·parser·dispatch의 합치를 검사한다. argv를 파서에서 도출하므로 **새 명령이 자동으로 커버된다.** 이 테스트는 0.2.3 파일 분할에서 명령 분기 안에서만 실행되는 임포트 3개가 빠졌는데 CI가 그대로 통과한 사고 뒤에 생겼다.

> **현재 알려진 불일치.** `catalog`의 `kinds` 목록에 코드가 실제로 배출하는 `catalog`와 `version_request_unfulfilled`가 빠져 있다. `catalog`를 단일 진실 공급원이라고 문서화하는 이상 이건 실제 계약 위반이다. 고칠 때 `_cli/catalog.py`의 `kinds`에 두 값을 추가하고 [Agent Integration](Agent-Integration.md)의 경고 문단을 지운다.

## 버전

`moleg_api/_version.py`의 리터럴이 **단일 진실 공급원**이다.

`importlib.metadata`를 쓰지 않는 것은 의도적이다. 메타데이터는 *설치된 배포판*을 설명하지만 실제로 도는 코드는 다른 데서 올 수 있다 — 체크아웃이 `sys.path`에 있으면 site-packages를 가리므로, `python -m moleg_api`가 체크아웃 코드를 실행하면서 메타데이터는 설치된 릴리스를 보고한다. 그러면 "어느 버전이 답했나"에 답할 수 없다.

리터럴은 코드와 함께 이동하므로 엔벨로프가 보고하는 버전은 언제나 그 응답을 만든 버전이다. `pyproject.toml`이 `[tool.setuptools.dynamic]`으로 이 속성을 읽으므로 빌드와 런타임이 어긋날 수 없다.

## 파일 크기 가드레일

목표는 **작고 의미 있는 파일**이지 파일 개수 최대화가 아니다.

- 루트 파사드는 얇고 호환 목적만
- 공개 `api_*.py` 믹스인은 검증·고수준 오케스트레이션·최종 반환 모양을 보여야 한다
- 비공개 헬퍼는 **실행 코드 250줄 안팎** 아래로. 공백·임포트·공개 API docstring 때문에 총 줄 수는 더 길어도 된다
- 서로 다른 책임이 섞이면 쪼갠다 (예: 후보 탐색과 상세 로드)
- **줄 수를 맞추려고 응집된 알고리즘을 쪼개지 마라.** 범용 `utils.py`보다 도메인 이름이 낫다

헬퍼는 그것을 소유한 도메인 옆에 둔다(`bundle_*`, `authority_context_*`, `delegated_criteria_*`, `institutional_*`). **공개 메서드 이름에서 출발해 헬퍼를 찾을 수 있어야 한다.**

현재 큰 로더의 분할:

| 공개 메서드 | 분할된 모듈 |
|---|---|
| `load_legal_context_bundle` | `bundle_modes`, `bundle_primary`, `bundle_candidates`, `bundle_eager`, `bundle_finalize` |
| `load_authority_context` | `authority_context_pipeline`, `authority_context_details` |
| `load_institutional_system` | `institutional_resolution`, `institutional_pipeline`, `institutional_candidates` |
| `load_delegated_criteria` | `delegated_criteria_pipeline`, `delegated_criteria_details` |
| `load_followup` | `followup_routing`, `followup_routing_authority`, `followup_routing_bundle` |

## 후행 별표 임포트는 건드리지 마라

`_laws/`의 일부 support 모듈은 **파일 맨 아래에서** 형제 모듈을 별표 임포트한다. 남은 찌꺼기처럼 보이지만 **의도된 장치**다 — 임포트 순환이 있어도 네임스페이스를 평평하게 유지한다.

모듈을 추가하면 `support.py`에 의존 순서대로 등록하고, 그 모듈이 필요한 후행 블록에도 넣어야 한다.

## 릴리스 전 점검

```bash
python -m compileall moleg_api tests -q
python -m pytest -q -m "not live"
MOLEG_OC=chunghun1 python -m pytest -q -m live
moleg catalog
```

패키징:

```bash
python -m build
python -m twine check dist/*
```

전체 릴리스 절차(버전 올리기, 태그, GitHub Release, PyPI 배포)는 [CONTRIBUTING.md](../../CONTRIBUTING.md)의 릴리스 절에 있다.

## 알려진 중복 — 손대기 전에 읽을 것

동작에는 영향이 없지만 코드를 고칠 때 헷갈리는 두 지점이다. 상세는 [Architecture](Architecture.md).

**`_models`의 follow-up 원시 타입** — `Ambiguity`·`ContextGap`·`DeferredLookup`이 `followups.py`와 `bundles.py`에, `FollowUpSearch`가 `followups.py`와 `query.py`에 중복 정의돼 있다. 임포트 순서상 `followups` 쪽이 공개 네임스페이스를 이기고, 그림자 사본은 직렬화 메서드를 못 받는다.

**`_normalization`의 헬퍼 4종** — `compact_whitespace`·`yes_no_or_none`·`is_deleted_article`·`article_text_marks_deleted`가 `primitives.py`와 `article_units.py`에 바이트 단위로 동일하게 정의돼 있다. `primitives` 쪽이 이긴다.

## 기본 OC

`chunghun1`. 무료 law.go.kr 계정 식별자이며 비밀이 아니다. 사용자는 `LawGoKrClient(oc=…)`나 `MOLEG_OC`로 덮어쓸 수 있다.

비밀이 아니지만 모든 오류 메시지·응답 스니펫에서 마스킹되고, `HistoryEvent.article_link`의 링크에서도 제거된다. 이 동작은 `tests/test_source.py`가 잠그고 있다.

## 관련 문서

- [Architecture](Architecture.md) — 4계층 구조와 정규화 계층
- [CONTRIBUTING.md](../../CONTRIBUTING.md) — 개발 환경, 테스트, 브랜치, 커밋, 릴리스
- [CHANGELOG.md](../../CHANGELOG.md) — 릴리스 이력
