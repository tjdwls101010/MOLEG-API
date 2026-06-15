# congress-db Live Schema Introspection

Generated at: `2026-06-15T01:18:32Z`

## Connection

- Current user: `congress_ro`
- Session user: `congress_ro`
- Transaction read-only: `on`
- Server in recovery: `False`

## Summary

- Schemas: 1
- Tables/views/materialized views: 17
- Columns: 77
- Foreign keys: 16
- Indexes: 45

## Tables By Schema

| Schema | Relation Count |
|---|---:|
| `public` | 17 |

## Promulgation Bridge Columns

| Table | Column | Type | Nullable | Comment |
|---|---|---|---|---|
| `public.bill_final_outcomes` | `promulgation_dt` | `date` | True | 공포일(법이 시행 근거를 갖춘 날). bills.law_proc_dt와 혼동 금지. **거부권 추론:** 가결인데 promulgation_dt NULL은 계류 또는 거부권 폐기다(가결 1,593 중 228건 미공포). plenary_dt가 bills.proc_dt와 다르면(27건) 거부권 후 재의결 후보(예: 노란봉투법·방송법·양곡관리법 — 상세는 plenary_dt COMMENT). 공포 없음 하나만으로 폐기 단정 금지. |
| `public.bill_final_outcomes` | `prom_no` | `text` | True | 공포번호(PROM_NO). 법제처 현행법 조회로 이어질 때 prom_law_nm과 함께 bridge key 후보. |
| `public.bill_final_outcomes` | `prom_law_nm` | `text` | True | 공포 법률명. ALLBILL은 숫자 법령ID를 주지 않음(현행법 본문은 법제처 단계로 이어지는 bridge). 공포일(promulgation_dt)은 있으나 이 값이 NULL인 66건은 전부 법률안의 실제 [1] 품질 갭(원천 미제공) — 이름에서 유도해 backfill하지 말 것(source가 줄 때만 채움). |

## Relations

| Type | Name | Columns / Detail |
|---|---|---|
| table | `public.bill_coproposers` | 공동발의 N:M(bill_id×mona_cd, 206k). co와 lead는 같은 법안에서 겹치지 않음 → 총 발의자 = 두 테이블 합집합(중복 없음). 1건당 보통 8~190명(중앙값 ~10), 모든 공동법안은 대표법안 부분집합(orphan 없음). |
| table | `public.bill_final_outcomes` | 본회의 의결 이후 정부이송·공포 이력(ALLBILL, bill_no 기준). 공포일은 여기 promulgation_dt. bills.law_proc_dt(법사위 처리일)를 공포일로 쓰지 말 것. |
| table | `public.bill_lead_proposers` | 대표발의 N:M(bill_id×mona_cd). 단일·다중 대표발의(191건, 최대 3인) 모두의 authoritative 소스. **발의주체 커버리지 함정:** 가결 법안 1,593건 중 1,026건(64%)은 여기에 lead가 없다 — 위원장 대안(768건; 원안은 bill_lineage 뷰로 역추적)·정부제출(196건; bill_name에 '(정부)')·기타 위원회/특위안(62건)은 개별 의원 대표발의가 아니기 때문. 따라서 발의자/정당 기반 '성공률·통과수' 분석은 이 셋을 별도 처리해야 하며, 이 테이블만 join하면 가결의 64%를 조용히 누락한다. 주의: 대표발의자 ~20명은 22대 명부에 없어 members에 이름만(poly_nm·units NULL) — 정당/선수 필터 시 누락될 수 있음. |
| view | `public.bill_lineage` | 폐기 원안 → 흡수한 canonical 대안 계보(1행=1 폐기원안, 3,715행). alternative_bill_id/no는 직접 매칭 우선, 실패 시 bill_source_aliases 경유 해소를 내부 캡슐화(raw 두 테이블은 ops-internal·소비자 비노출). 미해소면 alternative_bill_id=NULL(전부 수정안반영폐기 39건 — 대안이 bills에 부재). relation_type은 absorbed_proc_result 파생: 대안반영=100% 해소, 수정안반영=100% gap. 원안→대안 traversal은 이 뷰만 쓰면 됨(구 Q9 alias-join 대체). |
| view | `public.bill_meeting_contexts` | 법안×회의 evidence 컨텍스트(파생 뷰, 새 적재 없음). linked_bill_count=그 회의에 연결된 법안 수(fanout; 평균 32, p90 75, max 756) — 클수록 이 회의 발언을 해당 법안의 직접 증거로 보기 어렵다. utterance_count·utterances_by_role는 회의 단위 집계(evidence_scope=meeting_level): 발언↔특정 법안 직접 귀속은 원천이 주지 않는다. 증거강도 버킷 라벨은 일부러 두지 않음 — raw count로 소비자가 판단(DECISIONS 2026-06-11). meeting_bills 커버리지가 부분적이라 결과가 비어도 미논의를 뜻하지 않음. |
| table | `public.bill_relations` | 대안반영/수정안반영으로 폐기된 원안(absorbed_bill_id)과 내용을 흡수한 대안·수정안(alternative_bill_id)의 연결. alternative_bill_id는 likms source key라 bills.bill_id로 직접 join이 안 될 수 있음 → bill_source_aliases 경유. |
| table | `public.bill_source_aliases` | source별 BILL_ID를 안정키 bill_no를 경유해 canonical bills row로 잇는 정규화. canonical_bill_id가 NULL이면 해소 불가 gap. |
| table | `public.bills` | 국회에 *발의된* 의안(법률안 등). 시행 중인 현행법 본문이 아님(현행법은 법제처 소관, 이 DB 경계 밖). PK bill_id는 source마다 갈릴 수 있어 cross-source 영구키로 쓰지 말 것 — 안정키는 bill_no. |
| table | `public.committees` | Bill-side committee/referral dimension. Preserves committee_id -> committee_name from bill source rows; not committee membership or history. |
| table | `public.dead_letters` | 운영용 실패 item 보존. 미적재 갭의 일부만 여기 있고 accepted-gap(원천이 안 주는 값)은 없음 → 결측 판단의 단일 근거로 쓰지 말 것. |
| table | `public.ingest_cursors` | 운영용 source별 증분 기준점. 스킬 조회 대상 아님. |
| table | `public.ingest_runs` | 운영용 수집 실행 기록. 스킬 조회 대상 아님. |
| table | `public.meeting_bills` | 회의↔법안 N:M. 커버리지가 부분적(법안 약 85%·회의 약 59%만 연결) — 결과가 비어도 논의되지 않음을 뜻하지 않음(미연결일 수 있음). 답에 이 한계를 밝힐 것. |
| table | `public.meetings` | 회의록 인스턴스(웹 HTML 목록 기준). PK mnts_id. comm_name은 본회의에서 NULL 가능. |
| table | `public.members` | 국회의원 인적사항(22대). PK mona_cd. 떠난 의원도 행 유지(is_incumbent=false, 삭제 안 함). 명부 동기화 전 떠난 의원은 poly_nm이 NULL일 수 있으니 시점 정당은 votes.poly_nm_at_vote를 쓸 것. |
| table | `public.utterances` | 회의록 발언 stream(meeting_id+sequence 순). speaker_mona_cd는 비-의원 화자(장관·차관·증인·참고인·전문위원 등)에서 NULL이며 전체 발언의 38.5% — members와는 반드시 LEFT JOIN(INNER는 38.5%를 조용히 누락). 역할 필터는 speaker_role. |
| table | `public.votes` | 본회의 표결, 의원 1명당 1행. 행이 있으면 본회의까지 간 의안; 없으면 미상정이거나 원천 미수집(votes만으론 구분 불가 — bills.proc_result로 교차확인). 위원회 단계 표결은 원천이 안 줘 데이터에 없음. 표결된 법안 수 = count(DISTINCT bill_id). |

## Foreign Keys

| Constraint | From | To |
|---|---|---|
| `bill_coproposers_bill_id_fkey` | `public.bill_coproposers(bill_id)` | `public.bills(bill_id)` |
| `bill_coproposers_mona_cd_fkey` | `public.bill_coproposers(mona_cd)` | `public.members(mona_cd)` |
| `bill_final_outcomes_bill_no_fkey` | `public.bill_final_outcomes(bill_no)` | `public.bills(bill_no)` |
| `bill_lead_proposers_bill_id_fkey` | `public.bill_lead_proposers(bill_id)` | `public.bills(bill_id)` |
| `bill_lead_proposers_mona_cd_fkey` | `public.bill_lead_proposers(mona_cd)` | `public.members(mona_cd)` |
| `bill_relations_absorbed_bill_id_fkey` | `public.bill_relations(absorbed_bill_id)` | `public.bills(bill_id)` |
| `bill_source_aliases_canonical_bill_id_fkey` | `public.bill_source_aliases(canonical_bill_id)` | `public.bills(bill_id)` |
| `bills_committee_id_fkey` | `public.bills(committee_id)` | `public.committees(committee_id)` |
| `dead_letters_run_id_fkey` | `public.dead_letters(run_id)` | `public.ingest_runs(id)` |
| `ingest_cursors_updated_run_id_fkey` | `public.ingest_cursors(updated_run_id)` | `public.ingest_runs(id)` |
| `meeting_bills_bill_id_fkey` | `public.meeting_bills(bill_id)` | `public.bills(bill_id)` |
| `meeting_bills_meeting_id_fkey` | `public.meeting_bills(meeting_id)` | `public.meetings(mnts_id)` |
| `utterances_meeting_id_fkey` | `public.utterances(meeting_id)` | `public.meetings(mnts_id)` |
| `utterances_speaker_mona_cd_fkey` | `public.utterances(speaker_mona_cd)` | `public.members(mona_cd)` |
| `votes_bill_id_fkey` | `public.votes(bill_id)` | `public.bills(bill_id)` |
| `votes_mona_cd_fkey` | `public.votes(mona_cd)` | `public.members(mona_cd)` |
