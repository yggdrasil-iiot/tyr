# P3-C C 제한 산술 수용 결과 · 2026-10-18

판정: add·multiply·divide의 제한된 오프라인 구현 범위 충족. 일반 식/차원 추론·온도 delta·실제 현장 PoV는 별도 미완료다.

| 검증 | 최종 결과 | 근거 |
|---|---:|---|
| 신규 Python/SQLite | 28/28 | 네 profile·16 binding, 1/3·0 분모·좌우 순서·단위/타입/정밀도/근거·lazy selector·시간/품질·CAS·원자성·제출 closure |
| 기존 Python·fixture 회귀 | 932/932 | 평가 준비 35 + 복구 13 + 가져오기 58 + 후보 그래프 39 + 구조 30 + 제한 연산 17 + A07 39 + 기본 701 |
| 매핑 관련 Java | 127/127, 실패/오류/스킵 0 | MappingPublicationTest 122 + LogicalStructureTest 3 + MappingGateTest 2; 새 산술 11 포함 |
| 격리 브라우저·HTTP·SQLite·Java CLI | 21/21 | 작성·저장 거부/성공·재개방·가상 trace/오류/손실·독립 검증·두 키 승인·파일 발행·상태/ZIP·P7 template |
| 실제 이전 수신자 | 2/2 | 이전 JAR의 구 wire 정상 수신과 2.15 새 wire capability 거부 |
| 기존 입력 보존 | 변경 0 | canonical 계약 파일 72개·평가 계약 1개·기존 fixture 507개 SHA 유지, 현재 schema 사본 73개 동일 |

Python·fixture 합계는 960이다. 전체 수용 JSON의 30행 중 9행은 suite exit 표식이며 추가 검사로 중복 합산하지 않았다. Java targeted/중간 실행을 최종 127에 더하지 않았다. Java 수치는 매핑 관련 선택 suite이며 Bifrost 전체 타 모듈 수용이라는 주장은 아니다.

## 확인한 동작과 경계

- schema 2.15.0의 세 산술 노드를 Python과 독립 Java가 같은 타입·단위·출력·policy·DAG·설비/근거 규칙으로 검사한다. 2.13 이하 문서에 새 op를 넣으면 거부한다. 기존 schema는 수정하지 않았다.
- 네 접근 profile의 가상 150 kPa/50 kPa/gain 2에서 sum 200, scaled 400, quotient 200, ratio 3의 별도 기대값이 일치했다. 입력 이름이나 JSON 속성 순서가 계산의 left/right를 바꾸지 않는다.
- 1/3의 graph 값은 34자리 half-even이며 최종 Double 값과 다르다. 두 precision loss를 각각 보존하며 exact cast는 거부한다. 0/-0 분모는 오류·bad·result:null이다.
- 임의 표현 문자열·지원하지 않는 복합/역단위·Cel/K/unknown·암묵적 Pa/kPa 상쇄를 거부한다. 같은 단위가 물리적 의미 동등성을 자동 증명하지 않는다.
- bad/stale/skew는 산술 전에 차단하며, 선택하지 않은 0 나누기 후보는 실행하지 않는다. 기존 범위/cast/invalidValuePolicy와 시간/품질·출처 추적을 유지한다.
- 실제 화면에서 부정한 단위 곱 저장은 422/원자적 무변경이고, multiply를 divide로 편집해 precision/rounding과 입력 port를 저장·재조회했다. 같은 SQLite 테이블/JSON/CAS이며 기존 DB 개방 시 행을 재작성하지 않았다.
- 실제 화면 저장본을 p3cc-release@1.0.0으로 시험 registry에 발행하고 두 등록 키 승인·published 상태·ZIP 51개 파일 hash를 확인했다. 운영 활성화는 not-performed다. 임시 개인 키는 evidence 밖에서 생성 후 삭제했다.
- 기존 16 평가 화면은 새 graph의 16 멤버에 대해 기대값 없는 양식을 생성하며 의미 정답을 자동 채우지 않는다.

## 실행과 증거

최종 전체 실행: build/p3cc/20261018-062911. scripts/p3cc/run.ps1, 로컬 이미지 tyr-a14:20261018, --network none / localhost DNS / cap-drop ALL / readonly inputs. 실제 Chromium·Python·Java가 같은 격리 namespace에서 localhost 흐름을 수행했다. Java JUnit은 별도 Windows Maven -o 실행이다.

- [전체 수용·입력 pin](p3cc-full-acceptance.json), [집계](p3cc-run-history.json), [신규 28](p3cc-arithmetic-tests.log), [기본 701](p3cc-regression.json), [Java 집계](p3cc-java-summary.json).
- [제품/Java/fixture/JAR pin](p3cc-validation.json), [이전 입력 보존](p3cc-compatibility.json), [이전 실제 JAR 수신](p3cc-old-receiver.json).
- [Docker 설정](p3cc-docker-inspect.json), [실행 인자](p3cc-docker-arguments.json), [미리보기](p3cc-preview.png), [설계](../P3-C-BOUNDED-ARITHMETIC.md).

Windows 중간 신규 검사에서 Boolean 타입 거부 probe가 숫자 2를 넣어 디코더의 sample.boolean에서 먼저 실패한 1건이 있었다. 유효한 Boolean true로 fixture 전제를 수정해 산술 input-type 거부를 검사했고, 제품 코드 변경 없이 최종 Linux 28개를 모두 통과했다. [중간 기록](p3cc-initial-host-failure.json)은 최종 수용으로 계산하지 않는다.

기존 P7 평가 준비 테스트의 당시 고정 JAR hash 단언은 새 수신 기능을 영구히 막지 않도록 구 canonical schema 사본 보존으로 바꿨다. 해당 테스트를 제거하거나 수를 줄이지 않았고 35개를 다시 통과했다. 과거 P7 결과와 당시 JAR hash는 유지했다. 실제 이전 JAR 510485...의 양성/음성 수신 control도 별도로 확인했다.

최종 JAR SHA-256: `2770b0fd998eb1253e3d49290ff433baec2530dcd70022c73134b35e5a3e5fb5`.

## 별도 미완료

일반 식/eval·일반 차원 추론/복합 단위·온도 delta·cross-value-graph endpoint, 실제 source/계수/운전 정책/허용 오차의 의미 정답·vendor native/export 검증, 전체 검토 시간·재사용성 PoV, 목표 Windows 배포·전원 손실/운영 IAM/외부 anchor·실제 활성화는 별도다. Java 정적 승인은 모든 실제 입력에서 0 분모가 없다는 보장이 아니다.

장치 통신·외부 SQL·쓰기 실행을 추가하거나 실행하지 않았다. 기존 사용자 DB/registry를 보존했고 새 데모는 build/p3cc-ui/editor.sqlite3와 localhost:59781의 05/09 화면이다. Bifrost feature 브랜치를 유지하며 commit/push/merge는 수행하지 않았다.
