# P3-F 검증 결과 · 2026-10-17

P3-F 38/38 통과. 기존 P1/P2/P3-A~E 회귀 442/442 통과. 패턴 기준선의 current 14·gap 8·planned 34는 별도이며 planned를 통과로 계산하지 않는다.

| 검증 | 통과 / 전체 |
|---|---|
| p3f-validation | 38 / 38 |
| p3e-p3f-regression | 55 / 55 |
| p3d-p3f-regression | 62 / 62 |
| p3c-p3f-regression | 41 / 41 |
| p3b-p3f-regression | 66 / 66 |
| p3a-workspace-p3f-regression | 37 / 37 |
| p3a-contract-p3f-regression | 52 / 52 |
| p2-p3f-regression | 24 / 24 |
| p1-p3f-regression | 105 / 105 |

기존 Schema 44개 hash 보존. 신규 graph/common 2.5 계약만 추가했다. 7개 독립 값 oracle와 경계·기본 정책·출처 변경·시간/품질·SQLite/CAS·HTTP 검증을 수행했다.

UI에서 기본 후보 1을 저장하고 재개방했다. 가상 index 2, previousIndex 0, 미선택 pressure-up 결측, 선택 pressure-down 200 입력 → 기본 후보 사용과 출처 변경 경고, uncertain/200 Double kPa를 확인했다. 선택 후보 bad는 최종 결과 null로 차단됨을 확인했다. selector-default-change 시나리오를 SQLite에 저장한 뒤 페이지 재개방·조회·재평가했다.

원본 build/p3e-ui/editor.sqlite3 revision 27의 workspace hash가 이전 P3-E 증거와 일치한다. P3-F 복제 DB revision 30에서 검증했으며 미리보기 전후 작성본/시나리오가 동일했다. 이전 3개 시나리오는 삭제하지 않고 stale로 보존한다.

[기계 판독 증거](p3f-ui-observation.json) · [최종 코드/fixture hash와 테스트](p3f-validation.json) · [설계/제한](../P3-F-BOUNDED-SELECTOR.md)

후보는 최대 32개 직접 scalar 소스, 인덱스는 직접 정수 소스다. 후보 그래프·임의 주소식·실제 통신·운영 적용·자동 failover는 제외한다.

![P3-F 미리보기](p3f-preview.png)
