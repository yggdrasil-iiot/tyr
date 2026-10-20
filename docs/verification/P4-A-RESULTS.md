# P4-A 검증 결과 · 2026-10-17

신규 50/50, 기존 P1/P2/P3-A~F 회귀 480/480 통과. 기존 Schema 46개 hash 보존. 새 common/import-batch/mapping-proposal 2.6 세 가지를 추가했다.

| 검증 | 통과 / 전체 |
|---|---|
| p4a-validation | 50 / 50 |
| p3f-p4a-regression | 38 / 38 |
| p3e-p4a-regression | 55 / 55 |
| p3d-p4a-regression | 62 / 62 |
| p3c-p4a-regression | 41 / 41 |
| p3b-p4a-regression | 66 / 66 |
| p3a-workspace-p4a-regression | 37 / 37 |
| p3a-contract-p4a-regression | 52 / 52 |
| p2-p4a-regression | 24 / 24 |
| p1-p4a-regression | 105 / 105 |

10개 독립 주소 oracle, 네 PLC profile, template base/stride/override, alias chain/cycle/missing/duplicate, unknown/formula 보존, original byte/hash/locator/변조, 가정 미확인, SQLite/CAS·HTTP 보호·순수 preview를 검증했다. 가져온 source를 실제 속도 의미에 연결하여 가상 1500 rpm의 최종 Double 결과를 확인했다.

UI에서 한국어 헤더 XLSX를 columnMap으로 해석하여 4개 draft/6개 관측을 저장했고, 설정 JSON에서 9개 draft/14개 관측을 저장했다. 페이지 재개방 후 원본 hash·셀 locator와 alias A4→A3를 확인했다. 기존 02 편집기에서 source note를 수정하여 저장한 뒤 importRef·원본/수동 evidence가 유지됨을 대조했다. UI 검증 DB 최종 revision 34이며 원본 P3-F DB revision 30과 기존 시나리오 4개를 보존했다. 미해석 총 7개와 신규 정의 13개 모두 초안 상태로 남겼다.

제안 2.6에 원본 파일·batch·관측·정의를 내보내어 원본 bytes와 SHA-256이 일치함을 확인했다. 이 검증과 미리보기는 SQLite를 변경하지 않았다. 미해석은 import.unresolved finding으로 남는다. 원본/정의 검토와 승인·운영 적용은 별도다.

패턴 기준선 current 14/14·gap 8/8·planned 34는 별도이며 planned를 통과로 계산하지 않는다. MP03/12/18은 bounded subset 부분 지원이다.

[기계 판독 증거](p4a-ui-observation.json) · [최종 코드/fixture hash](p4a-validation.json) · [설계·제한](../P4-A-FILE-IMPORT.md)

실제 솔루션 exporter는 미선정이다. XLSX와 tyr-config-v1 범위를 검증했으며 PDF/.xls, vendor UDT/설정 자동 해석, 임의 주소식·수식 실행 및 실제 장치 통신은 제외했다.

![가져오기 원본·초안·미해석 보존](p4a-import.png)
