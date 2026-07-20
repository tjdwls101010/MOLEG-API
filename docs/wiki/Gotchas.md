# 함정

이 패키지는 law.go.kr 출처를 정규화하지만, 그 출처가 무엇을 *의미하는지* 결정하지는 않는다. 아래는 뭉개기 쉽고, 뭉개면 조용히 틀린 법적 주장이 만들어지는 지점들이다.

모든 항목을 관통하는 두 문장:

> **검색 결과는 신원 후보이지 본문이 아니다.**
> **결과가 없는 것은 부재의 증명이 아니다.**

함정이 특정 결과에서 *실제로 살아 있을 때* CLI는 `discipline` 문장과 대개 `flags` 항목을 함께 낸다. 조건이 실제로 있을 때만 울리므로 평범한 경로는 조용하다. Python API에서는 같은 조건이 모델 필드로 드러난다.

---

## 1. 검색 결과에서 인용하지 마라

`search_*`는 `identity`를 감싼 `*Hit`을 준다. *어느* 출처인지를 확정할 뿐, 인용 가능한 문언·의무·제재·절차·판시·기준을 담고 있지 않다.

```python
hits = api.search_laws("주택임대차보호법", display=5)
selected = hits[0].identity          # 후보 — 인용 불가
article = api.get_article(selected, "제3조")
print(article.text)                  # 실린 본문 — 인용 가능
```

CLI는 순서를 구조적으로 강제한다 — 로더에 법령 **이름**을 넘기면 `kind: needs_search_first`(종료코드 5)로 거부한다.

`expand_legal_query()`와 `find_comparable_mechanisms()`도 마찬가지다. 그 용어 후보·관련 법령·관련 조문·비교 대상은 *계획* 맥락이지 권위가 아니다.

## 2. 공포일과 시행일은 다르다

법은 공포되고도 시행 전일 수 있다. `LawIdentity`가 둘을 별도 필드로 들고 있다 — `promulgation_date`, `effective_date`, 그리고 어느 기준으로 조회했는지의 `basis`.

실제 사례: `search_laws("주택임대차보호법")`에서 `promulgation_date="20251001"`, `effective_date="20260102"`인 후보가 나온다. 2025년에 공포됐지만 2026년까지 시행되지 않는다.

CLI는 실린 판본의 시행일이 오늘보다 뒤면 `flags.not_effective_as_of`를 붙이고, `source` 표기 자체를 「공포본(장래 시행 — 아직 미시행)」으로 바꾼다. 이 플래그는 `--as-of`를 줬는지와 **무관하게** 뜬다 — 미래 판본은 어느 경로로든 도착할 수 있기 때문이다.

`resolve_promulgated_law()`로 공포 사실에서 신원을 확정한 것은 *신원*의 확정이지 *현재 효력*의 확인이 아니다.

## 3. 첫 후보를 집는 것이 가장 위험한 자리

검색 결과의 `[0]`이 **현행 판본이라는 보장이 없다.** 미시행 판본이 위에 올 수 있고, 그때 `flags.top_candidate_not_yet_effective`가 붙는다.

`AmbiguousLawError`도 같다. `.candidates`는 사람에게 제시하라는 뜻이지 첫 항목을 쓰라는 뜻이 아니다. CLI는 `kind: ambiguous`(종료코드 2)로 내고, 규율 문장은 「모호성이지 첫 후보를 고를 허가가 아님 — 후보를 사용자에게 제시.」다.

동명 법령이 시행일만 다른 경우가 가장 흔하다. 현행은 `get_law(law_id)`로, 특정 과거 판본은 `as_of=<시행일>`로 싣되 — **누가 고를지 정한 뒤에** 해야 한다.

## 4. `as_of`는 필터가 아니라 판본 해석이다

`as_of`는 걸러내는 것이 아니라 그 시점에 시행 중이던 판본을 찾아온다. 그 시점에 시행 중인 판본이 없으면 **이후 판본**이 대신 온다.

돌아온 `effective_date`를 요청일과 반드시 비교하라. CLI는 이걸 계산해 `flags.version_mismatch`를 `{requested, loaded}`로 붙인다.

`법령ID + 시행일`로 원시 조회하면 오류 없이 현행이 돌아온다는 것이 근본 원인이다 → [Historical Versions](Historical-Versions.md)

## 5. 현행 텍스트는 개정 델타가 아니다

공포 사실로 신원을 잇고 현행 텍스트를 실은 것은 *신원과 현재 문언*을 증명한다. **어떤 법률안이 무엇을 바꿨는지는 증명하지 않는다.**

- `compare_law_versions()` → 선택된 행의 전후 문언만. 개정 이유·입법 취지·법안 전체 목적·변경 조문 망라를 담지 않는다.
- `trace_law_history()` → 개정 연혁. 전체 법 연혁에서는 `HistoryEvent.article_text`가 `None`이고, 조문 스코프 연혁(`article=…`)에서만 채워질 수 있다.
- `get_revision_reason()` → 「개정이유 및 주요내용」. **제안자의 자기 진술**이며 중립 요약이 아니다.

`HistoryEvent.bill_id`는 `promulgation_bridge`를 직접 넘겼을 때**만** 채워진다. 이 패키지는 의안 데이터베이스를 조회하지 않는다.

## 6. 삭제·이동 표시는 본문이 아니다

실린 `ArticleText`가 상태 필드를 들고 있다. 운용 규범으로 다루기 전에 확인하라.

- `is_deleted` 또는 `revision_type == "삭제"` — **「제N조 삭제」는 삭제 상태이지 현행 의무·허가·제재·절차가 아니다.**
- `moved_to` 또는 `revision_type == "이동"` — 실질은 다른 조문에 있다. 표시는 상태이고 본문은 목적지에 있다.

```python
art = api.get_article(selected, "제5조")
if art.moved_to:
    ctx = api.load_article_context(selected, "제5조")
    current = ctx.current_article      # 목적지 본문
```

`load_article_context()`는 기본적으로 이동을 따라간다. 이동·삭제 요청에서 `current_article`이 `None`이면 **실질이 실리지 않은 것**이다 — 현행 의무를 인용하지 마라.

law.go.kr은 실제로 이동하지 않은 행에 `제0조`·`0`·빈 문자열을 센티널로 내보낸다. 패키지는 이걸 걸러내므로 파싱 잡음이 실제 목적지처럼 보이지 않는다.

## 7. 실질은 제목이 아니라 중첩된 항·호·목에 있다

`ArticleText.text`는 중첩 항·호·목 구조를 펼쳐 담는다. 정의·예외·적용 대상·요건이 그 안에 사는 경우가 많다.

**조문 제목(`조문제목`)이나 최상위 `조문내용`만 보고 요약하지 마라.** 운용 조항을 놓친다.

## 8. 부칙은 별도 본문이다

시행일·적용례·경과조치는 부칙에 산다. `supplementary_provisions`라는 **별도 리스트**로 나오며 본 조문과 분리돼 있다.

경과 규정 질문을 본 조문이나 법령 수준의 `identity.effective_date` 메타데이터만으로 답하지 마라.

```python
law = api.get_law(selected)
for prov in law.supplementary_provisions:   # 시행일·적용례·경과조치
    print(prov.text)
```

행정규칙도 자기 부칙을 갖는다.

## 9. 행정규칙의 `issued_on`은 발령일자다

`search_administrative_rules(issued_on=…)`는 **발령일자**로 거른다. **시행일자가 아니다.** 파라미터 이름이 `as_of`가 아니라 `issued_on`인 것이 바로 이 혼동을 막기 위해서다.

규칙은 발령됐어도 아직 시행 전이거나 이미 대체됐을 수 있다. 현행 집행 기준이라고 부르기 전에 실린 `identity.effective_date`를 기준일과 비교하라.

CLI는 실린 행정규칙에 `flags.issued_on_note`를 상시 붙이고, 검색 결과에는 `flags.issued_on_is`를 붙인다.

## 10. 별표의 금액·기준은 본문을 실어야 나온다

`search_annex_forms()`는 메타데이터와 파일·상세 링크만 준다. 임계값·금액·기준·서식 내용은 첨부된 표에 있고, `get_annex_form_body()`로 실어야 한다.

본문을 실었어도 `structured_data`는 **최선의 시도**일 뿐이다. `rows`에 의존하기 전에 `parsing_confidence`를 확인하라. **비었거나 `"low"`인 것은 "기준 없음"이 아니다** — 평문 `text`로 돌아가야 한다.

빈 `search_annex_forms()` 결과 역시 "이 검색으로 못 찾음"의 증거지 첨부 기준이 없다는 증명이 아니다.

## 11. 권위 층위를 평탄화하지 마라

법제처 해석, 부처 1차 해석, 판례, 헌재 결정, 위원회 의결, 행정심판 재결은 서로 다른 권위 층위다. 신원이 구분 메타데이터를 들고 다닌다.

**두 종류의 행정 판단은 판례가 아니다.**

위원회 의결은 그 법을 집행하는 감독기관의 행정 처분이다. 그 기관이 법을 *어떻게 적용하는지*를 보여줄 뿐 법이 *무엇을 의미하는지*를 정하지 않으며, 행정소송에서 뒤집힐 수 있다.

행정심판 재결은 행정부 내부에서 *다른* 기관의 처분을 심사한 것이다. 패소한 쪽은 여전히 법원으로 갈 수 있다.

둘 중 하나라도 판례로 인용하면 그것이 확정한 바를 과장하는 것이다. 그래서 `kind` 값도 따로 있다(`committee_decision_text`, `administrative_appeal_text`).

권위를 특정 조문에 붙이기 전에 `referenced_articles`(해석·판례)와 `reviewed_articles`(결정)로 실제로 그 조문을 다루는지 확인하라. 번들에서는 `authority_article_mismatch` / `authority_article_unverified` / `authority_article_partial_match` gap이 어긋남을 알린다 — **`loaded` 전체가 아니라 `current_authorities`에 있는 것만 인용하라.**

## 12. 기록이 없는 기관이 아무것도 안 한 기관은 아니다

`search-committee-decisions`와 `search-administrative-appeals`는 "감독기관이 실제로 움직였나"를 묻는 데 쓰인다. 그래서 **0건이 이 패키지에서 가장 위험한 결과**다 — 오독의 방향이 질문이 겨눈 방향과 정확히 일치하기 때문이다.

0건이 나오는 경우들: 기관이 신고를 받은 적이 없다 / 받았지만 사건을 열지 않았다 / 의결했지만 의결서를 공개하지 않았다 / 그 사안이 다른 기관 소관이다. **어느 것도 "아무 일 없었다"가 아니다.**

구체적 함정 둘:

**소관을 잘못 잡으면 부재로 읽힌다.** 소청·조세·해양안전 재결은 일반 `decc` 목록에 없다. 특별 심판기관(`--tribunal acr|adap|tt|kmst`)에 있다.

**기관을 잘못 잡아도 부재로 읽힌다.** 같은 행위가 어느 법의 렌즈를 대느냐에 따라 다른 규제기관 소관이 된다. 결론 내기 전에 다른 `--committee` 코드를 시도하라.

공개 기록이 소진되는 지점은 부정적 결론을 기록할 자리가 아니라, **공식 자료요구를 할 자리**다.

## 13. 헌법 원칙은 색인이 아니라 검색어다

`search_constitutional_decisions(search_body=True)`는 `detc`를 **자유 텍스트**로 검색한다. 과잉금지원칙·평등원칙 같은 도그마틱은 질의 문자열이지 구조화된 필터가 아니다 — law.go.kr에 도그마틱 필드가 없다.

키워드 검색으로 후보를 띄울 수는 있어도, **"위헌 소지 없음"이나 "도그마틱 망라"를 뒷받침하지 못한다.**

이 규율은 0건일 때도 뜬다. 가장 중요한 순간이 바로 그때이기 때문이다.

```bash
$ moleg search-constitutional-decisions "과잉금지원칙"
{ "ok": true, "count": 0,
  "discipline": [
    "doctrine(과잉금지원칙 등)는 색인 아닌 자유텍스트 검색어 — '위헌 소지 없음'·doctrine 망라 단정 금지…",
    "0건 — 이 검색어·범위로 못 찾음일 뿐, 부재의 증명 아님."
  ] }
```

## 14. 목차는 법령이 아니고, 요지는 판단이 아니다

`--toc`와 `--brief`는 로드 비용이 질문의 가치를 넘지 않게 하는 장치인데, 둘 다 **문서 하나 안에서** 후보-본문 간극을 다시 연다.

**`--toc`**는 `kind: law_toc_map`이지 `*_text`가 아니다. 조문 번호와 제목은 어디를 볼지 알려줄 뿐 무엇을 요구하는지 말하지 않는다 — 「제15조(개인정보의 수집·이용)」은 어떤 요건이 붙고 예외가 무엇인지 아무것도 알려주지 않는다.

**`--brief`**는 법원·기관 자신의 요약을 주고 전문을 뺀다. 결정요지는 부연이다. **판시 문구의 축자 인용은 전체 로드에서 나와야 한다.** `flags.brief.withheld`가 무엇을 뺐는지 정확히 알려 주며, 문서에 실제로 있던 것만 보고한다 — 원래 없던 항목이 있는 것처럼 보이지 않는다.

## 15. 0건과 접근 실패는 다르고, 둘 다 부재가 아니다

| 결과 | CLI `kind` | 종료 | 의미 |
|---|---|---|---|
| 0건 검색 | `*_hit_list`, `count: 0` | 0 | 이 질의·범위에 일치 없음 |
| 복수 신원 | `ambiguous` | 2 | 후보를 제시하라, 고르지 마라 |
| 접근 실패 | `source_access_error` | 3 | **일시적** — 재시도 |
| 정규화 실패 | `parse_error` | 3 | **영구** — 재시도 무의미, 식별자를 의심하라 |
| 본문 없음 | `no_result` | 4 | 이 식별자에 본문 없음 |
| 이름을 로더에 | `needs_search_first` | 5 | 먼저 `law_id`를 찾아라 |

**호출 제한이 "현행법 없음"으로 붕괴되면 안 된다.** 부재를 주장하기 전에 검색어와 출처 계열과 필터를 정확히 밝혀라.

빈 `find_delegated_rules()` 결과 역시 그 법령·조문에 한정된 것이지 위임이 없다는 증명이 아니다. 그리고 **위임 목록에 별표는 안 들어온다** — 과태료 기준표 같은 것은 `search_annex_forms`로 따로 찾아야 한다.

## 관련 문서

- [Core Concepts](Core-Concepts.md) — 이 함정들이 왜 생기는지
- [Agent Integration](Agent-Integration.md) — 답을 쓰기 전 점검표
- [Historical Versions](Historical-Versions.md) — 시점 관련 함정
- [Error Handling](Error-Handling.md) — 종료코드 계약
- [Sources & Coverage](Sources-and-Coverage.md) — 출처 계열별 한계
