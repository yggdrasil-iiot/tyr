# P3-C B: 제한된 sqrt·clamp

## 목적과 범위

현장 자료 없이 검증 가능한 미완료 항목 중, P3-C의 제한 비선형식 확장을 선택했다. 가상 입력을 받아 디코딩 → 입력별 변환 → sqrt/clamp → 최종 cast → 의미 멤버의 타입·단위·범위를 검증한다. 실제 측정값의 물리적 정확도나 vendor 지원을 증명하는 단계는 아니다.

## 데이터 계약

value-graph 2.11.0은 2.5.0의 모든 노드를 유지하고 다음 두 노드를 추가한다. 기존 schema 파일은 수정하지 않는다. workspace envelope는 2.0.0, mapping-set·proposal·publication 버전과 SQLite 테이블은 유지한다. 새 노드는 새 graph schemaVersion을 명시해야 하며 구버전 수신기는 거부한다.

| 노드 | 입력·출력 | 추가 필드 | 검증·손실 |
|---|---|---|---|
| sqrt | inputs.value 단일 수치 → Decimal, 단위 1 | precision: 34, rounding: half-even 고정 | 음수 value.sqrt-domain. 제곱근의 근사 loss.precision. 단위가 있는 값은 graph.input-unit |
| clamp | inputs.value 단일 수치 → Decimal, 입력과 동일한 known 단위 | low/high 정확한 십진 문자열, 최대 256자 | low > high는 graph.clamp-range. 경계 포함, 같은 경계 허용. 값이 잘리면 loss.clamp |

sqrt의 34자리 유효숫자와 half-even은 계약에 고정한다. 기존 4096자리 중간 계산 한도는 유지하고 sqrt에서만 별도 Decimal context를 쓴다. sqrt(2)의 34자리 oracle은 1.414213562373095048801688724209698이다. sqrt(0), sqrt(9)는 근사 손실이 없다. 제곱근의 차원 변환을 추정하지 않으므로 압력 차이를 직접 sqrt할 수 없다. 물리적으로 의미 있는 정규화와 출력 단위는 별도 검토 대상이다.

clamp 경계는 입력 단위로 해석한다. bar → kPa 같은 변환을 먼저 명시한 뒤 kPa 경계를 적용한다. clamp는 명시적 값 변환이며 semantic range의 오류 검증을 대체하지 않는다. clipping 손실은 최종 값이 정수여도 사라지지 않는다. 최종 cast의 exact 정책은 기존대로 비정확한 binary64/정수 변환을 거부한다. half-even을 허용해도 근사와 clipping은 손실·uncertain으로 표시한다.

두 노드 모두 source/node 참조·설비 경계·DAG 순환·타입·단위·근거 폐쇄를 기존 검증기로 검사한다. 시간·품질 정책이 있으면 기존 P3-D의 필수 입력 lineage로 freshness/skew/결측/bad를 먼저 평가하고 실패 시 새 연산도 실행하지 않는다.

## 재사용과 새 구현

| 구분 | 내용 |
|---|---|
| 재사용 | 4개 PLC 접근 정의·디코더, 명명된 그래프 입력, source/node 참조, 출처 근거, P3-D 시간·품질, 최종 cast·semantic 범위, revision CAS·SQLite JSON, read-only preview API, Bifrost 파일 제출·서명 승인·릴리스 |
| 신규 | 2.11.0 graph/common schema, Python 정적 검증과 제한 평가 분기, graph 편집 필드·미리보기 요약, 독립 Java 단위/경계 검증, 가상 oracle·부정/시간 fixture, 브라우저→SQLite→Bifrost 수용 경로 |
| 제외 | 일반 식/eval, 임의 정밀도 선택, 단위 제곱근·일반 차원 분석, 온도 delta, 실장치 통신, 외부 SQL, 쓰기 실행, Muninn 활성화 |

Java는 JSON 계약을 독립 검증하며 Python 평가 코드를 공유하지 않는다. Bifrost는 연산 정의를 승인·파일 발행한다. 실제 값의 수치 평가는 Tyr (Týr)의 가상 preview 범위다.

## 화면과 저장

05 값 그래프에서 sqrt 또는 clamp를 선택한다. sqrt는 고정 정밀도 정책을 표시하고, clamp는 하한·상한을 입력한다. 여러 노드를 연결할 수 있다. 새 노드가 있는 그래프는 2.11.0으로 저장하며 기존 그래프의 계약은 임의로 올리지 않는다. 이미 2.11.0인 그래프 편집 시 버전을 유지한다.

06에서 결과 노드를 프로퍼티에 매핑하고 09에서 가상 HEX/Typed 입력을 평가한다. trace에 sqrt의 approximate/precision/rounding과 clamp의 low/high/branch/pass를 표시한다. 손실과 최종 cast 진단을 함께 확인한다. preview 자체는 workspace나 revision을 변경하지 않는다.

기존 workspace JSON이 새 그래프를 담을 수 있으므로 DB migration은 필요 없다. 기존 행을 여는 것만으로 재작성하지 않는다. 이전 fixture 저장 → 새 그래프 저장 → 재시작 복원 → 잘못된 범위/오래된 revision 거부의 원자성을 검사한다.

## 재현

- Python: python -B scripts/test_p3cb.py
- Java: Bifrost에서 mvn -o -pl gates -am package -Dtest=MappingPublicationTest,MappingGateTest -Dsurefire.failIfNoSpecifiedTests=false
- 격리 브라우저·회귀: powershell -NoProfile -ExecutionPolicy Bypass -File scripts/p3cb/run.ps1

기존 A14 Docker 이미지를 재사용하고 --network none으로 실행한다. 원본 사용자 SQLite는 읽기 전용 백업만 만들며 테스트는 별도 /work의 SQLite·registry·임시 키로 수행한다. 입력 패키지, 로그, 가상 preview, 화면, Java 검증·승인·릴리스 응답을 build/p3cb 아래 보존한다. [fixture](../fixtures/p3cb/README.md), [실행 결과](verification/P3-C-B-RESULTS.md)를 따른다.

## 다음 미완료 항목과 현장 PoV

가상 자료로 가능한 후속은 P3-E B의 논리적 중첩/구조 멤버 계약, P3-F의 유한 후보 그래프 확장, P4-A의 미해석 항목 해결·재가져오기 병합, P6의 중단 복구/GC 검증이다. 이번 완료로 이 항목들을 완료 처리하지 않는다.

실제 자료가 필요한 항목은 native UDT/DB 배치와 vendor export의 정확한 해석 검증, 사이트별 alias·단위·스케일 정답 확인, 현장 담당자의 독립 정답과 비교하는 오매핑/누락/손실·검토 시간 PoV다. 운영 IAM과 실제 활성화도 별도다. Linux localhost 격리는 호스트 Windows 전체 방화벽 검증과 구분한다.
