# A07 명시적 word/bit view 수용 결과

2026-10-18. A07을 PLC 정수 워드의 명시적 alias/bit view 범위에서 충족했다. 현재 P7은 15개 충족·A14 부분 충족이며 실제 현장 PoV는 미수행이다. [현재 A01~A16 기록](a07-acceptance.json), [계약·한도](../A07-SOURCE-VIEWS.md). 최초 P7의 14/2 기록은 역사적 증거로 유지한다.

## 구현

기존 계약 60개를 수정하지 않고 2.10.0 source-definition/common 두 스키마를 추가했다. 14 화면에서 alias/bit view를 작성·편집하고, 05 graph/06 객체 프로퍼티에 매핑하며 07에서 관계/논리 타입, 09에서 원본 디코딩부터 view/최종 cast를 확인한다.

부모 id/version·설비/접근 snapshot·정수 폭·단위·읽기 조건·최대 16단계·순환/누락·부모 체인 근거를 Python과 Java가 독립 검사한다. 부모 변경은 미해결 snapshot으로 보존하고 검토·발행을 막는다. 비트 범위 초과/순환 등 구조 오류는 원자적으로 저장을 거부한다.

SQLite 테이블/기존 작성본은 그대로 사용한다. 직접 소스·기존 proposal 2.7.0·승인/릴리스 2.9.0을 유지하고 새 view만 2.10.0이다. Bifrost는 Týr의 검증 결과를 신뢰하지 않고 원본·모든 view·근거 파일을 다시 검사해 서명 승인·파일 발행한다.

## 실행 근거

| 검증 | 결과 | 근거 |
|---|---|---|
| A07 전용 계약·fixture·preview·SQLite/API | 39/39 | [JSON](a07-validation.json), [log](a07-tests.log) |
| 기존 P1~P6 전체 | 701/701 | [개별 ID·입력 hash](a07-regression.json), [log](a07-regression.log), [P3-A CLI](a07-regression-p3a.json) |
| Bifrost 기존 mapping + 새 view 승인/발행 | 60/60 (core 58 + CLI 2) | [Maven offline log](a07-bifrost-tests.log), [core XML](a07-bifrost-core.xml), [CLI XML](a07-bifrost-gates.xml) |
| 32/64비트 경계 | 2/2 | [UInt32 bit31 / signed Int64 bit63](a07-wide-bit-probes.json) |
| 네 PLC 표현·부정 변형 | 4 PLC / 20소스 / 20바인딩 / 12변형 | [fixture](../../fixtures/a07/README.md), [실제 CLI fixture 승인 결과 포함](a07-bifrost-tests.log) |
| 기존 패턴 카탈로그 | current 14/14, gap 재현 8/8, planned 34 pending | [분리 기록](a07-patterns.json); gap/planned는 지원 성공이 아님 |

전체 Bifrost reactor를 다시 실행했다고 주장하지 않는다. 이 범위의 Maven package와 mapping/CLI 회귀를 직접 실행했다. CycloneDX의 offline skip은 SBOM 생성 성공으로 계산하지 않는다.

701 회귀는 실행 중 입력 변경 없이 통과했다. 이후 최종 CSS 줄바꿈과 catalog/README 메타데이터만 보완했고 브라우저/별도 pattern gate로 재검증했다. [최종 코드·jar·문서 hash](a07-final-artifacts.json)는 회귀 실행 당시 hash와 구분한다.

## 실제 UI·파일 발행 경로

P7 DB revision 40을 복제하고 기존 네 PLC의 직접 상태 워드를 재사용해 view를 추가했다. 원본 정의를 복제 소스로 중복 등록하지 않았다.

1. 14에서 a07-ui-alias → a07-melsec-word-alias@1.0.0을 저장해 revision 42.
2. a07-ui-bit → a07-ui-alias@1.0.0, bitIndex=2를 저장해 revision 43.
3. 06에서 a07-melsec-mapping의 running Boolean 의미에 연결해 revision 44.
4. 09에 원본 melsec-state / D3000의 05 80만 입력했다. 32773 디코딩 1회 → word alias → UI alias → bit 2 true → Boolean cast/정준 결과. quality=good, 오류/손실 0, revision 44 유지.
5. 13에서 a07-ui-views로 제출했다. 부모·view·graph·의미·근거가 고정된 묶음을 Bifrost가 독립 검증했다.
6. 별도 시험 registry에서 proposer/approver 두 임시 키로 a07-view-approval을 서명했다. a07-view-release@1.0.0으로 파일 발행하고 UI에서 릴리스 발행됨/현재 작성본과 동일을 확인했다.
발행 범위는 a07-melsec-mapping과 그 의존 closure다. 기존 가져오기 미해석/미확인 22건을 해소하거나 승인한 결과는 아니다.

7. payload 26파일 SHA를 대조했다. 임시 개인/공개 키 파일은 저장소 밖에서 생성한 뒤 삭제했다. 등록 공개 키·서명 이력만 registry에 남겼다.

[브라우저 관찰](a07-ui-observation.json) · [서명 승인](a07-ui-approval.json) · [릴리스](a07-ui-release.json) · [독립 CLI 상태](a07-ui-receiver.json) · [SQLite/26파일 확인](a07-sqlite-release.json).

![원본 워드→alias→bit→정준 Boolean](a07-preview.png)

![저장한 view 편집 화면](a07-view-authoring.png)

좁은 화면의 부모 snapshot 문자열 가로 넘침을 줄바꿈으로 보완했다. 최종 clientWidth=scrollWidth=456, console error 0. 기존 59772/59773 서버도 같은 DB/registry로 새 코드를 적용했다. [재시작 전후 모든 행 hash 동일](a07-server-preservation.json). 검증 작성본은 http://127.0.0.1:59774/ 에 남겼다.

## 완료 경계

PLC Int16/UInt16/Int32/UInt32/Int64 정수 워드의 읽기 alias/bit view를 지원한다. bit view의 alias는 가능하며 bit의 재차 bit 선택, 배열/codec/native 구조 view, 임의 vendor alias importer는 포함하지 않는다.

A14 PC 전체 네트워크 격리 및 실제 자료·독립 담당자의 PoV는 미수행이다. 이번 단계에서 PLC·솔루션 접속·외부 SQL·쓰기 실행·Muninn 활성화를 수행하지 않았다. Bifrost 작업은 기존 로컬 feature 브랜치에 있으며 commit/push/merge는 하지 않았다.
