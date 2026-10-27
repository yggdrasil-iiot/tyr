# P4-A B 오프라인 수용 결과

2026-10-18 최종 구현 수용 완료. [설계·경계](../P4-A-IMPORT-RECONCILIATION.md), [fixture 안내](../P4-A-B-FIXTURES.md), [기계 판독 결과](p4ab-validation.json).

## 완료 범위

- 2.14 import-batch: 원본 bytes/관측/미해석 오류를 고정하고 명시적 source 해결·비소스 분류·검토자/사유/시각·hash chain을 기록.
- 해결 결정과 draft 채택을 분리. 다른 신호를 자동으로 해석 정답처럼 채우지 않고 편집용 틀 복사는 사용자가 선택.
- 안정된 recordKey로 이전 imported 기준/현재 로컬 수정/새 파일의 필드 비교, 충돌별 ours/incoming, 현재 정의 전체 유지, 새 항목 채택/보존, 제거 보존/재등장.
- canonical 소스 ID·매핑 sourceRef·로컬 note를 유지하고 관련 target/graph/mapping/write-definition 근거 closure에 새 원본 근거를 추가.
- SQLite JSON/CAS 재사용. 새 2.14 원본 교체·검토/채택 이력 축소·완료한 reconciliation 변경을 일반 workspace PUT에서도 거부.
- 독립 Java가 검토 chain·source 형태/근거·이전 batch hash·3방향 비교/선택/결과/채택 기준을 검사하고 기존 Bifrost 두 키 승인·파일 발행으로 연결.

## 검증 수치

| 범위 | 통과 |
|---|---:|
| 신규 검토·XLSX 수동 해석·병합·유지/재등장·원본/이력 보호·SQLite/HTTP/CAS | 58/58 |
| 기존 P1~P6 | 701/701 |
| 기존 A07 | 39/39 |
| 기존 graph 후보 | 39/39 |
| 기존 논리 구조 | 30/30 |
| 기존 sqrt/clamp | 17/17 |
| Python/fixture 합계 | 884/884 |
| 독립 Java MappingPublicationTest / LogicalStructureTest / MappingGateTest | 95 + 3 + 2 = 100/100 |
| 격리 브라우저·HTTP·SQLite·Java CLI 수용 경로 | 24/24 |

수용 JSON의 총 30개 check는 경로 24개와 테스트 suite 종료 확인 6개다. suite marker나 반복 실행을 개별 테스트 수에 중복 합산하지 않는다. Java에는 신규 16개(기존 2.6 닫힌 importer 승인/발행과 canonical Unicode hash 포함)가 포함된다.

브라우저에서 명시적 편집 틀 복사→수동 해결 저장→별도 draft 채택→새 파일 비교→필드 충돌 선택/현재 정의 유지→병합→SQLite 재열기→정의 재확인→정준 값 1500 rpm preview→제출→독립 Java validate→서로 다른 두 Ed25519 키 승인→파일 publish→화면 published 상태를 검증했다. activation은 not-performed다.

## 호환성과 증거

기존 schema 69개(계약 파일 70개)·fixture 파일 483개 SHA를 유지했다. 기존 2.6 batch/제안·source/semantic/graph 계약과 SQLite schema/migration 경로를 보존한다. 새 workflow를 선택할 때만 해당 batch를 2.14로 승격한다. 기존 DB를 여는 것만으로 body/revision을 다시 쓰지 않는다.

최종 입력 파일 전체와 inventory 및 JAR hash가 수용 snapshot과 일치한다. Tyr (Týr)/Bifrost의 2.14 schema 사본은 byte hash가 같다. Java는 코드 공유 없이 wire만 검증한다. 원래 parser 관측 replay는 Tyr가 수행하며 Java가 vendor parser 정답을 인증한다는 의미가 아니다.

- [전체 수용](p4ab-full-acceptance.json), [P1~P6 회귀](p4ab-regression.json), [A07](p4ab-a07.json)
- [신규 58 검증 로그](p4ab-new-tests.log), [graph 후보 회귀](p4ab-graph-candidate-regression.log), [논리 구조](p4ab-logical-structure-regression.log), [수학 연산](p4ab-bounded-math-regression.log)
- [독립 Java 계약·승인·발행](p4ab-java-MappingPublicationTest.xml), [논리 구조](p4ab-java-LogicalStructureTest.xml), [CLI](p4ab-java-MappingGateTest.xml)
- [병합 검토 화면](p4ab-merge.png), [실행 이력](p4ab-run-history.json)
- 최종 raw evidence: ../../build/p4ab/20261018-034801

Docker network none, DNS 127.0.0.1, cap-drop ALL로 외부 네트워크를 차단하고 localhost만 사용했다. 원본 SQLite는 읽기 전용 backup하고 별도 격리 DB에서 검증했다. 운영 키를 사용하지 않았고 임시 개인 키는 evidence에 보관하지 않았다. 호스트 Windows 전체 방화벽 검증은 별도다.

첫 Java 검증에서 드러난 번들 내부 교차 버전 schema 참조와 supplementary Unicode hash 직렬화 차이를 수정했다. 초기 오류 보고는 build/p4ab-java-initial에 보존했다. 첫 전체 실행은 신규 53개와 기존 826개를 통과했고, 최종 실행은 원본/이력 보호·현재 정의 유지·제거 후 재등장과 명시적 편집 틀 선택을 반영해 다시 전체 검증했다.

## 별도 현장 PoV·한도

실제 vendor exporter·제품 버전·현장 XLSX layout/헤더/ID 안정성·수동 해석/비소스 분류의 독립 정답·canonical 의미 동등성·검토 시간/오매핑률은 현장 자료와 담당자 PoV가 필요하다. PDF/.xls·UDT 상속/cross-file alias·대량 history/GC·자동 fuzzy matching은 완료 범위가 아니다.

access/rawRepresentation 등은 top-level 원자 필드로 비교하며 부분 내부 필드 자동 병합을 하지 않는다. 새 파일에서 사라진 소스를 자동 삭제하지 않는다. 채택된 imported 해석 기준을 소급 변경하지 않고 현재 정의 편집과 새 batch로 검토한다. 타입·단위 일치만으로 실제 의미 동등성을 확정하지 않는다. 장치 통신·외부 SQL·쓰기 실행은 계속 제외한다.

새 로컬 화면: http://127.0.0.1:59778/ . 별도 build/p4ab-ui/editor.sqlite3 revision 2는 미해석 항목부터 시작한다. 상단 파일 선택에 사용할 실제 가상 업로드 파일은 [새 설정](../../build/p4ab-ui/new-settings.json), [기준 설정](../../build/p4ab-ui/base-settings.json), [엑셀](../../build/p4ab-ui/memory-map.xlsx)이다. 기존 사용자/검증 DB와 운영 registry는 변경하지 않았다.
