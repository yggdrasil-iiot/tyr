# P4-F A2 해석 스냅샷 수신과 editor 계약 2.0.0

## 1. 개요

- 날짜: 2026-10-22
- 상태: **완료(tyr PR #4 머지(`fb5f3f7`, 2026-10-22), Bifrost 연동 테스트를 포함한 GitHub CI 통과)**
- 위치: P4-F의 A 단계 중 Týr 측 첫 항목이다.
- 상위 설계: `docs/P4-F-SOLUTION-INTERPRETATION.md`(§3 소유 분리, §4 논리 모델, §7 판정 축, §10 SI19)

## 2. Mímir 계약 사본 관리

- Mímir 소유 해석 스냅샷 계약 1.0.0 스키마 6개를 `vendor-contracts/mimir/interpretation/1.0.0/`에 바이트 그대로 둔다.
- Mímir fixture(JCS 벡터, 합성 세트 `pio-like`·`kepware-like`, 거부 사례 `cases.json`)를 `fixtures/solution-intake/mimir-1.0.0/`에 바이트 그대로 둔다.
- 출처 커밋(`yggdrasil-iiot/mimir` `f8691d0`)과 파일별 SHA-256 목록은 `vendor-contracts/mimir/interpretation/PIN.json`에 기록한다.
- 테스트에서 개별 파일을 이 목록과 대조하며, 누락되거나 추가된 파일이 있으면 실패로 처리한다.
- 사본은 고치지 않으며, Týr 자체 `contracts/`와 섞지 않는다.

## 3. 수신 검사기 (`backend/interpretation_intake.py`)

- Týr 작업대에서는 검사기를 공유 코드 없이 독자적으로 구현했다.
- 단일 문서는 문서 종류, 계약 버전(모르는 버전은 거부), 숫자 규칙(±(2^53−1) 안의 정수만 허용, 소수는 문자열), 증거 소유, 스키마, `digest`, 내부 참조 순으로 검사한다.
- 묶음 단위는 다음 순서로 검사한다.
  - `check_pinned`: 스냅샷과 번들·프로파일 pin을 대조한다.
  - `check_request`: 요청과 번들·프로파일을 대조한다.
  - `check_result`: 결과와 요청·스냅샷을 대조하며, 스냅샷이 요청한 번들·프로파일·아티팩트에서 나왔는지까지 검사한다.
- **벤더 원본 아티팩트는 직접 읽지 않는다.** 테스트에서 검사 도중 파일 읽기 동작을 감시하여 아티팩트 파일을 하나도 열지 않는 점을 확인한다.
- 단일 해석 결정 원칙에 맞춰 해석의 정확성은 검사하지 않는다. 정확성 검증에는 두 번째 파서가 필요하므로 배제한다.

## 4. RFC 8785 (JCS) Digest 규칙

- 최상위 `digest`와 `envelope`를 뺀 문서를 RFC 8785(JCS)로 직렬화한 UTF-8 바이트의 SHA-256을 계산한다(두 계약 공통).
- 사용자 결정에 따라 Týr editor 문서도 같은 규칙을 쓴다.
- Mímir의 Java 및 Python 구현에 이어 Týr 구현은 세 번째 독립 구현이다.
- **세 구현은 동일한 digest를 낸다.** Týr 검사에서 Mímir fixture 6개의 digest를 다시 계산하여 일치함을 확인한다.

## 5. editor 계약 2.0.0 (`editor-contracts/2.0.0/`)

- Týr가 소유하며, 기존 1.0.0 및 1.1.0 계약은 그대로 둔다.
- `review-decision`:
  - 고정된 스냅샷의 한 항목(`node`, `edge`, `claim`, `issue`)을 두고 검토자가 내린 로컬 판단이다.
  - 판단 종류: `confirm`, `hold`, `intended-exception`, `needs-correction`(수정 제안 필수), `refers-elsewhere`, `needs-evidence`.
  - 증거 근거: `declared-by-reviewer`와 `verified-by-virtual-case`만 허용한다.
  - `verified-by-virtual-case`는 가상 사례의 입력·기대·관측 digest와 harness 버전을 고정해야 한다.
  - `previousDecisionDigest`로 앞선 판단과 이어지며(첫 판단은 `null`), 판단을 고치지 않고 덧붙인다. 승인이나 서명이 아니다.
- `endpoint-assessment`:
  - 한 endpoint를 여섯 축(자료 확보, 구조 해석, 계약 표현, 가상 동등성, 의미 확인, 승인 상태)으로 나누어 독립 판정한다.
  - 축마다 상태, 근거, blocker를 둔다. 성공 플래그 하나는 두지 않으며, 스키마에 정의하지 않은 필드는 거부한다.
  - 승인 축은 Bifrost 상태를 확인한 대로 적을 뿐 Týr가 독자적으로 정하지 않는다.
- `conversion-plan`:
  - native 항목을 기존 Týr 계약 후보에 대응시키고 assessment, snapshot, profile, 판단, workspace revision/hash를 pin으로 고정한다.
  - 상태: `draft`, `blocked`, `candidate`.
  - **`candidate` 허용 조건**: closure 완결, 구조 `complete`, 표현 `representable`, 의미 `reviewer-confirmed`, 가상 동등성 `passed-within-scope`, 손실 0, blocker 0일 때만 허용한다.
  - 계획을 적용하는 일은 별도 작업이며, 새 해석 기반 채택과 제출은 P4-F D 전까지 차단한다.

## 6. 증거 소유 및 검사 차단 항목

- **증거 소유 검사는 양방향이다.**
  - 스냅샷에 검토자나 가상 사례 근거가 들어오면 거부한다.
  - Týr 판단에 `observed-in-artifact`나 `derived-by-rule`이 들어오면 거부한다.
- editor 검사에서 잡는 결함:
  - 스냅샷에 없는 대상, 끊긴 판단 사슬, 다른 스냅샷을 가리키는 판단을 거부한다.
  - 누락이나 모호한 참조가 있는데 `complete`라고 선언한 closure, 불완전한 closure 위의 구조 `complete`를 거부한다.
  - 스냅샷 `coverage`보다 넓게 주장한 자료 확보, closure 밖의 endpoint, 모르는 판단 참조를 거부한다.
  - 낡은 assessment나 snapshot 위의 계획, 다른 profile, 모르는 노드 대응, 근거 없는 `candidate`를 거부한다.

## 7. SI19 준수

- Týr 검사 단계에서 pin 변조, 모르는 스냅샷 계약 버전, 증거 소유 위반을 거부한다.
- "기존 sidecar와 작성본을 바꾸지 않는다"는 SI19 요건 절반은 저장 기능(B)이 생기면 함께 시험한다. A2 단계에는 저장이 없어 아무것도 쓰지 않는다.

## 8. Fixture 및 로컬 검증

- editor 2.0.0 fixture(`fixtures/solution-intake/editor-2.0.0/`):
  - `valid/`: 판단 3개, assessment 2개(`Line1.Temp`는 완결 및 `candidate` 계획, `Line1.Count`는 누락 참조로 `incomplete` 및 `blocked` 계획), 계획 2개.
  - `invalid/cases.json`: 30건(거부 29건, 통과 1건). 2건은 closure 일치 검사용이며 [P4-F closure](P4-F-CLOSURE.md) 에서 추가했다.
- Mímir 거부 사례 37건도 Týr 검사기에서 그대로 실행하여 동일한 위반 코드를 확인한다.
- 모든 fixture는 합성 자료이며 실제 제품 형식이 아니다.
- **2026-10-22 로컬 검증**: `python -B scripts/test_p4f_a2.py` 11개 시험을 통과했다.
- 결함 주입 시험 4종(JCS 키 코드 포인트 정렬, closure 과대 주장 검사 제거, 판단 사슬 검사 제거, 스냅샷 증거 소유 검사 제거) 모두 시험 실패를 확인했다.
- 전체 CI 동등 실행 결과는 PR에 기록한다.

## 9. 범위 밖 항목

- sidecar SQLite, 화면, 대조표(B 단계)는 다루지 않는다.
- closure 계산 자체는 A의 다른 항목이며 A2는 선언된 closure의 참조 무결성과 과대 주장만 검사한다.
- SemanticContext 및 Generation 계약은 A의 다른 항목이다.
- Bifrost 수신(D 단계), 해석기(Mímir E 단계), 실제 제품 데이터는 포함하지 않는다.
