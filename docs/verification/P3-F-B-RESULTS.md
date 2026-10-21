# P3-F B 오프라인 수용 결과

2026-10-18 최종 구현본 수용 완료. [설계와 계약 경계](../P3-F-GRAPH-CANDIDATES.md), [fixture](../../fixtures/p3fb/README.md), [기계 판독 결과](p3fb-validation.json).

## 구현

- 2.13.0 graph의 최대 32개 직접 소스/같은 그래프 DAG 출력 후보. 스케일·단위 변환·다중 입력 차압·중첩 선택을 지원한다.
- 모든 후보의 scalar 타입·단위·참조·근거·순환·범위 정적 검증. 시간·품질·결측·변환 손실은 선택 경로만 평가한다.
- 후보 참조·정의 해시·실제 선택 source refs·명시적 이전 후보와의 출처 변경. 이전 후보 값은 실행하지 않으며 이전 lineage는 definition-only다.
- 후보 picker/순서/타입·단위 요약, 저장·재열기, 단계별 preview, 후보별 평가 상태와 선택 입력 DataValue 상세, SQLite 시나리오 저장.
- 기존 JSON/CAS·시나리오·P6 근거 closure를 재사용. 독립 Java schema/DAG 검증·서명 승인·파일 발행. 인덱스 inputStage가 후보 값의 변환 단계에 섞이지 않도록 Java 판정을 Python과 일치시켰다.

## 최종 검증

| 범위 | 통과 |
|---|---:|
| 신규 계약·선택 격리·출처·손실·시간 품질·SQLite/CAS | 39/39 |
| 기존 P1~P6 | 701/701 |
| 기존 A07 | 39/39 |
| 기존 논리 구조 | 30/30 |
| 기존 sqrt/clamp | 17/17 |
| Python/fixture 합계 | 826/826 |
| 독립 Java MappingPublicationTest / LogicalStructureTest / MappingGateTest | 79 + 3 + 2 = 84/84 |
| 격리 브라우저·HTTP·SQLite·Java CLI 경로 | 29/29 |

수용 JSON의 총 34개 check는 경로 29개와 위 테스트 suite의 종료 확인 5개다. suite marker를 개별 테스트와 중복 합산하지 않는다. 타입·단위 mismatch, 참조 누락·순환·근거 누락·기본 후보 범위, 선택/미선택 bad·stale·결측, skew, 같은 값/다른 경로, 같은 endpoint/다른 인덱스, 혼합 소스/노드, 중첩 선택, clipping 손실, 제어 입력 단계 분리를 확인했다.

최종 raw run: ../../build/p3fb/20261018-023431. 브라우저 작성→SQLite 재열기→preview→시나리오 저장→제출→Java validate→서로 다른 두 Ed25519 키의 승인→파일 publish→화면 published 상태를 검증했다. 결과 활성화는 not-performed다.

Docker network none + DNS 127.0.0.1 + cap-drop ALL로 외부 네트워크를 차단했다. 브라우저 요청은 localhost만 사용했다. 호스트 Windows 전체 방화벽 검증은 별도다. 원래 SQLite는 읽기 전용 backup하고 격리 환경의 별도 DB에 검증했다. 운영 키를 사용하지 않았으며 임시 개인 키는 evidence에 포함하지 않는다.

## 호환성과 실행 증거

기존 schema 67개(계약 파일 68개), fixture 파일 475개 SHA를 보존했다. SQLite schema 변경·기존 작성본 재작성 없이 기존 버전과 CAS/시나리오 경로를 검증했다. Bifrost의 2.13 schema 사본은 Týr와 byte hash가 같다. 최종 입력 파일 전체와 JAR가 수용 snapshot hash에 일치한다.

- [전체 수용](p3fb-full-acceptance.json), [기존 701 검증](p3fb-regression.json), [A07](p3fb-a07.json)
- [신규 39 검증 로그](p3fb-new-tests.log), [논리 구조 회귀](p3fb-logical-structure-regression.log), [수학 연산 회귀](p3fb-bounded-math-regression.log)
- [Java 수신/승인/발행](p3fb-java-MappingPublicationTest.xml), [논리 구조](p3fb-java-LogicalStructureTest.xml), [CLI](p3fb-java-MappingGateTest.xml)
- [미리보기 화면](p3fb-preview.png), [실행 이력](p3fb-run-history.json)

첫 전체 실행은 신규 38개·기존 787개를 통과했다. 이후 제어 입력 단계 분리의 독립 회귀 1개와 Java 수정을 추가하고, 최종 JAR로 전체 수용/회귀 및 Java 전체를 다시 실행했다. 첫 실행과 최종 실행을 각각 보존하며 최종 숫자에 반복 실행을 중복 합산하지 않는다.

## 별도 현장 PoV와 제외 범위

현장 자료 없이 완료한 것은 bounded scalar DAG 정의와 가상 입력 수용이다. 타입·단위 일치는 실제 물리적 의미 동등성의 자동 증명이 아니다. fixture의 pressure.selected는 가상 선택기 출력이며 차압 후보를 절대압의 의미 수렴 정답으로 간주하지 않는다. 실제 canonical 개념·운전모드별 후보 의미, fallback 합의, 실제 timestamp/quality 수집과 동시성은 담당자 독립 정답으로 검증해야 한다.

vendor native UDT/DB packing·alignment·export, 임의 주소식/동적 PLC read, cross-value-graph endpoint, 자동 failover, 실행 간 lineage 자동 감사는 이번 완료 범위에 포함하지 않는다. 실제 장치 통신·외부 SQL·쓰기 실행은 계속 제외한다.

로컬 데모는 http://127.0.0.1:59777/ 이며 별도 build/p3fb-ui/editor.sqlite3와 가상 시나리오를 사용한다.
