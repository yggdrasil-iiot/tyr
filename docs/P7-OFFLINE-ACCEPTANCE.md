# P7 오프라인 수용 검증과 현장 PoV

이 단계는 기존 가상 fixture의 계약·값·변경·근거·저장 경로를 재검증한다. 실제 설비 통신, 외부 SQL 실행, 쓰기 실행, 운영 활성화는 제외한다. SQLite 내부 저장 SQL은 이 제외 대상인 외부 값 소스의 SQL 실행과 구분한다.

## 재현

Tyr (Týr) 루트에서 Python으로 scripts/test_p7.py를 실행한다. 기본 결과는 docs/verification/p7-validation.json이며 개별 시험 ID·실패·입력 SHA-256·Python 버전을 기록한다. 기존 P1 gate·P3-A 별도 CLI와 P2~P6 unittest를 그대로 실행하며 제품 코드나 fixture를 수정하지 않는다. 실패를 격리 재검증할 때 --resume에 최초 JSON 경로를 전달한다. 제품/fixture/계약의 hash가 달라지면 resume를 거부한다. 최초 실패와 유지한 성공·재실행 ID를 기록하고 P1/P3-A는 다시 검사한다. 보고서 집계는 scripts/report_p7.py로 실행한다. Windows에서 임시 파일 권한이 필요한 경우 작업 디렉터리 및 OS 임시 디렉터리 접근을 허용한다.

이 runner는 Python의 connect/connect_ex/DNS를 차단하고 숫자 loopback만 허용한다. 192.0.2.1:102 접속 거부를 negative control로 먼저 확인한다. HTTP API 시험은 loopback에서 수행한다. Java와 브라우저를 포함한 OS 전체 네트워크 차단을 입증하는 검증은 별도다. JVM은 로컬 jar/classpath로, Maven은 -o로 실행한다. 이를 PC 전체의 방화벽 시험 통과로 해석하지 않는다.

Bifrost 루트에서 다음 시험을 실행한다. PowerShell에서는 -D 인수를 따옴표로 묶는다.

~~~powershell
mvn -o -pl gates -am test '-Dtest=MappingPublicationTest,MappingGateTest' '-Dsurefire.failIfNoSpecifiedTests=false'
~~~

A11은 검사·승인 뒤 파일 변경, A12는 릴리스 파일/manifest 변조와 staging 실패, A16은 SQLite revision 및 릴리스 base 충돌을 각각 별개 시험으로 평가한다. Tyr와 Bifrost는 JSON·파일·CLI로만 연결한다.

## 화면 수용 순서

원본 DB를 SQLite backup으로 복제한 build/p7-ui/editor.sqlite3에서 수행한다. P6 원본 및 서명 registry는 변경하지 않는다. 복제본에서 편집하면 기존 불변 제출본은 오래된 작성본이 될 수 있으며, 이 상태를 확인하는 것은 새 승인을 받는 행위가 아니다.

1. 01 설비 편집·저장 → revision 증가 → 최신 저장본 재조회.
2. 02 네 접근 정의, 04 객체, 05 그래프, 06 프로퍼티 매핑을 조회.
3. 07 이름·의미·단위·스케일 비교를 조회.
4. 09 가상 바이트/typed 입력의 단계별 계산·품질·손실을 확인. preview 전후 revision 유지.
5. 10 원본 근거와 미해석 항목, 11 별도 읽기/쓰기 정의를 조회.
6. 12 기준본·변경·재검토 상태, 13 기존 승인 릴리스와 작성본 stale 상태를 조회.
7. SQLite를 다시 열어 저장값과 모든 부가 테이블의 보존을 비교. 실제 브라우저 관찰은 자동 API 시험과 별도로 기록한다.

전체 폼 조합에 대한 브라우저 자동화 coverage를 주장하지 않는다. 저장/API의 경우 기존 각 단계의 임시 SQLite 회귀 시험으로 더 넓게 검사한다.

## 실제 현장 PoV — 미수행

가상 자료만으로 현장 정확도·검토 시간 절감·타 사이트 재사용성을 결론 내리지 않는다. 다음 자료와 독립 담당자가 필요하다.

| 항목 | 입력/절차 | 측정/완료 근거 |
|---|---|---|
| 자료 고정 | 익명화된 실제 XLSX/PDF·설정 export, 제품/버전·개정 시점·해시 | 문서와 설정의 동시점 여부, 허용된 범위 명시 |
| 독립 정답 | 도구 개발/튜닝에 참여하지 않은 PLC/솔루션 담당자의 소스·의미·단위·변환 매핑 | 불일치의 합의 기록과 근거 위치 |
| 수렴·구분 | 다른 이름의 같은 의미, 같은 이름의 다른 의미, 객체·주소 범위 | 정답 대비 정확/오매핑/누락 수와 분모 |
| 변환·손실 | 정답 계산값·범위·반올림·결측·품질 정책 | 수치·타입·단위·손실 검출 결과 |
| 변경 검토 | 실제 전후 개정본, 순서 효과를 줄인 수작업/도구 비교 | import·해석·수정·문의·재검토 전체 시간, 오류 수 |
| 재사용 | 튜닝에 사용하지 않은 별도 설비 자료 | 프로파일 수정량, 수동 보정량, 미해석 수 |
| 운영 영향 | 파일 전달만 사용하고 장치 접속을 금지 | 평가 중 장치 통신/SQL/쓰기 실행 0회 |
| 완전한 격리 | PC/VM의 외부 네트워크 차단, loopback만 허용 | 브라우저·Java·Python 전체 흐름 성공과 방화벽/캡처 근거 |

PoV 시작 전에 현장 담당자와 오매핑 허용치·누락 처리·시간 절감 목표를 합의하고 결과가 없는 칸은 미수행으로 둔다. 자료와 검토자가 없는 현재는 절감률이나 현장 수용 완료를 기록하지 않는다.

## 남은 공백과 확대 판단

최초 P7 이후 A07 명시적 word/bit view와 A14 테스트 런타임 전체의 OS namespace 격리를 후속 검증했다. [A07 결과](verification/A07-RESULTS.md)와 [A14 현재 결과](verification/A14-RESULTS.md)를 구분해 읽는다. 호스트 Windows 전체 방화벽과 목표 현장 배포 환경의 수용은 별도 미수행이다. native/nested 구조·구조체 배열·임의 주소식·추가 vendor importer는 기존 지원 범위를 유지한다. 현장 확대 판단은 독립 PoV 후에 한다.

실행별 수용 판정과 근거는 verification/P7-RESULTS.md 및 p7-acceptance.json을 참조한다.

## A14 후속 재현과 현재 판정

[실제 OS 격리 재현](A14-NETWORK-ISOLATION.md) · [현재 16개 fixture 수용](verification/a14-acceptance.json). 브라우저·Python·Java 전체를 Linux container의 loopback-only network namespace에서 실행했다. Python guard/Maven -o만으로 OS 차단을 주장하지 않는다. 최초 P7 보고서는 역사적 기록으로 유지한다. 실제 현장 PoV 표의 입력·독립 정답·시간/재사용성 측정과 목표 PC 배포 수용은 여전히 미수행이다.


## P7 독립 평가 준비 후속

[오프라인 평가 도구](P7-EVALUATION-PREPARATION.md), [인수·현장 절차](P7-POV-PROTOCOL.md), [수용 결과](verification/P7-EVALUATION-RESULTS.md)를 추가했다. 16 화면/CLI는 빈 oracle 생성과 독립 기준 대조·집계를 수행하고 기존 SQLite를 읽기만 한다. 실제 현장 PoV 표의 자료/담당자/시간/재사용성은 미완료이며, 가상 확인율은 현장 정확도나 자동 후보 정밀도 실적이 아니다.
