# 과거 판본

기본적으로 `get_law`와 `get_article`은 **현행** 통합본을 싣는다. 과거 시점에 시행 중이던 텍스트가 필요하면 `as_of`를 준다.

```python
current = api.get_article("001248", "제3조")
past    = api.get_article("001248", "제3조", as_of="2015-01-01")

print(current.effective_date)   # 예: 20260102
print(past.effective_date)      # 20140101 ← 요청일이 아니라 실제로 실린 판본의 시행일
```

```bash
moleg get-article --law 001248 제3조
moleg get-article --law 001248 --as-of 2015-01-01 제3조
```

로더는 **시행일이 요청일 이하인 것 중 가장 최신** 판본을 고른다. 위 예에서 2015-01-01을 물으면 시행일 20140101 판본이 오는데, 그게 그날 효력을 갖던 판본이기 때문이다.

## 왜 별도 페이지인가 — 조용한 현행 함정

이게 이 패키지에서 가장 조용히 틀리는 지점이다.

**law.go.kr에 `법령ID + 시행일`로 상세를 조회하면, 오류 없이 현행 텍스트가 돌아온다.** 과거 날짜를 줘도 그렇다. 예외도, 경고도, 아무 표시도 없다. 그대로 믿으면 "2015년 당시 법은 이랬습니다"라고 하면서 2026년 조문을 인용하게 된다.

판본을 고정하는 유일한 키는 **MST(법령일련번호)**다. `ID`는 법을 가리키고, `MST`는 그 법의 특정 판본을 가리킨다.

그래서 `as_of`는 날짜를 그냥 통과시키는 것이 아니라 세 단계를 밟는다.

1. 그 법령의 판본 목록을 조회한다 (각 행이 MST · 시행일 · 공포번호를 가진다)
2. 시행일이 `as_of` 이하인 것 중 최신 판본을 고른다
3. **그 MST로 다시 싣는다**

이 보정 경로는 필요할 때만 탄다. 평범한 현행 조회는 여전히 호출 한 번이다.

**실무적 결론: 원시 엔드포인트에 `efYd`를 직접 붙여 과거 판본을 기대하지 마라.** `as_of`를 쓰고, 돌아온 `effective_date`를 확인하라.

## 돌아온 `effective_date`를 반드시 확인하라

`as_of`는 *요청*이지 보장이 아니다. 실제로 무엇이 실렸는지는 반환된 신원의 `effective_date`가 말해 준다.

| 어디에 | 필드 |
|---|---|
| Python | `ArticleText.effective_date`, `LawText.identity.effective_date` |
| CLI | `flags.effective_date` (요청값은 `flags.as_of`에 그대로 반향) |

요청한 날짜와 실린 판본이 다르면 `flags.version_mismatch`가 `{requested, loaded}` 형태로 붙는다.

## 요청일에 시행 중인 판본이 없을 때

법이 제정되기 전 날짜를 물으면 그 시점에 시행 중이던 판본이 없다.

```bash
$ moleg get-article --law 001248 --as-of 1950-01-01 제1조
```
```json
{
  "flags": {
    "effective_date": "20260102",
    "as_of": "19500101",
    "version_mismatch": { "requested": "19500101", "loaded": "20260102" },
    "version_request_unfulfilled": true
  }
}
```

실린 `effective_date`(20260102)가 요청일보다 훨씬 뒤다 — **요청한 시점의 판본이 아니다.**

통합본 커버리지 자체가 시작되기 전이면 Python에서는 `AsOfBeforeCoverageError`가 난다. 이 예외는 `.earliest_available`을 들고 오므로 어디까지 거슬러 갈 수 있는지 바로 알 수 있다. 이건 **영구 조건이지 일시적 실패가 아니다** — 재시도해도 소용없고, 개정 연혁으로 가야 한다.

## 과거 텍스트 vs 개정이 바꾼 것

두 질문은 다르다.

**"그날 조문이 어떠했나"** → `as_of`. 그 시점의 전문을 준다.

**"이 개정이 무엇을 바꿨나"** → `compare_law_versions`. 전후 대비를 준다.

```python
diff = api.compare_law_versions("001248")
for change in diff.changes:
    print(change.article, change.before_text, change.after_text)
```

`compare_law_versions`는 law.go.kr이 자체적으로 노출하는 전후 비교 표면을 쓴다. **임의의 두 날짜 구간은 받지 않는다** — `before`/`after`에 날짜를 주면 `UnsupportedFormatError`다. 출처가 그걸 못 한다.

임의의 두 시점을 비교하려면 `as_of`를 달리해 두 번 싣고 직접 비교하라. 어떤 개정들이 있었는지 열거하려면 `trace_law_history`를 쓴다.

**"왜 바꿨나"** → `get_revision_reason`. 「개정이유 및 주요내용」을 준다. 다만 이건 제안자의 자기 진술이며 중립 요약이 아니고, 지정한 판본 하나에만 적용된다.

세 명령을 잇는 실용 경로:

```bash
moleg trace-law-history --law 001248             # 어떤 개정들이 있었나 → identity.mst 확보
moleg get-revision-reason --law 001248 --mst <mst>   # 그 개정은 왜
moleg compare-law-versions --law 001248          # 무엇이 바뀌었나
```

## 날짜 형식

`YYYY-MM-DD`와 `YYYYMMDD`를 받는다. 내부적으로 8자리로 정규화된다.

CLI는 **달력 검증까지 한다** — 13월, 2월 30일, 99일은 거부된다. 그리고 형식이 틀리면 **조용히 현행으로 떨어지지 않고** 사용 오류(종료코드 5)를 낸다. 잘못된 날짜가 아무 표시 없이 현행 조회가 되는 것이 이 페이지가 막으려는 바로 그 실패이기 때문이다.

## 주의할 점

- `as_of`는 `basis="effective"`에 적용된다. `basis="promulgated"`는 키가 다르므로 효과가 없다.
- 판본 해석은 출처가 판본 목록을 돌려주는 데 달려 있다. 목록도 못 받고 직접 조회도 실패하면 **조용히 현행을 주는 대신 예외를 낸다.**
- 판본 목록이 비었다고 과거 판본이 없다는 증명은 아니다. 그 조회로 그렇게 돌아왔을 뿐이다.
- **미래 판본에 주의하라.** 시행일이 오늘보다 뒤인 판본은 `flags.not_effective_as_of`가 붙고 `source` 표기가 「공포본(장래 시행 — 아직 미시행)」으로 바뀐다. 이건 `--as-of`를 줬는지와 무관하게 뜬다.
- `get_revision_reason`에서 `mst`도 `as_of`도 주지 않으면 **파일상 가장 최신 시행일 판본**을 쓰는데, 이게 미래 시행 판본일 수 있다. "최신"과 "현재 효력"은 다르다.

## 관련 문서

- [Core Concepts](Core-Concepts.md) — 식별자 체계와 시행 vs 공포
- [API Reference](API-Reference.md) — `get_law`, `get_article`, `compare_law_versions`, `trace_law_history`, `get_revision_reason` 시그니처
- [Gotchas](Gotchas.md) — 시점 관련 함정 모음
- [Error Handling](Error-Handling.md) — `AsOfBeforeCoverageError`
