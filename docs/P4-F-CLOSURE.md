# P4-F endpoint closure 계산과 독립 oracle

- 날짜: 2026-10-22
- 상태: 구현과 로컬 검증을 마쳤다(PR 검토 전).
- 상위 설계: `docs/P4-F-SOLUTION-INTERPRETATION.md` §5 를 실행 가능한 규칙으로 정했다.
- 코드: `backend/interpretation_closure.py`

## 1. 입력과 탐색 규칙

계산기는 다음 입력을 받는다.
- Mímir 해석 스냅샷(계약 1.0.0)을 받는다.
- endpoint `nodeId` 를 받는다.
- profile 의 `limits.maxReferenceDepth`(D) 를 받는다.

너비 우선 탐색으로 최단 깊이를 계산한다.
- **평가 edge 만 closure edge 로 넣는다.** relation 이 `input`, `reference`, `inherits`, `overrides`, `policy`, `external` 인 edge 다.
- 구조 edge 인 `contains` 는 평가 edge 로 따라가지 않는다.
- 깊이 d < D 인 노드에서는 평가 edge 를 모두 closure edge 로 넣고, `resolved` 인 edge 대상만 노드로 넣는다.
- 모호한 edge 의 후보는 넣지 않는다. 해석기도 Týr 도 고르지 않는다.
- 깊이 D 에서 평가 edge 를 가진 노드는 더 펼치지 않고 `depth-limit` 사유를 남긴다.

## 2. 불완전 사유와 완결성

**사유가 없을 때만 complete 다.** 사유가 있으면 incomplete 이며, 사유 코드와 참조(`ref`)를 남긴다.

- `edge-missing`: 대상 노드가 빠진 그 edge 다.
- `edge-ambiguous`: 대상이 모호한 그 edge 다.
- `edge-external-required`: 외부 참조가 필요한 그 edge 다.
- `edge-unsupported`: 미지원인 그 edge 다.
- `evaluation-cycle`: closure 안의 강연결 요소다. 노드 id 를 정렬해 쉼표로 잇는다.
- `unresolved-issue`: closure 노드와 edge 에 걸린 미해석 항목이다.
- `unexplained-leaf`: 평가 edge 가 하나도 없고 status `asserted` 인 claim 도 없는 노드다. **edge 가 없다는 사실은 근거가 아니다.**
- `depth-limit`: 깊이 D 에서 평가 edge 를 가진 노드다(더 펼치지 않는다).

## 3. 분리 보고와 계약 1.0.0 공백

완결성과 따로 보고하는 항목은 다음과 같다.
- `captureScope`: 스냅샷 `coverage.capture` 값을 그대로 남긴다. **complete 는 "확보한 자료 안에서" complete 다.**
- `statefulNodeIds`: 상태를 가진 노드 id 집합이다.
- `structuralCycles`: `contains` 로 이어진 순환이다. 사유가 아니다.
- `outsideUnresolved`: endpoint 의 사유가 되지 않은 미해석 항목 수다.

계약 1.0.0 의 공백은 다음과 같이 처리한다(사용자 결정에 따라 1.0.0 으로 진행).
- edge 에 읽기·쓰기·event 구분이 없어 셋을 가르지 못한다.
- stateful 을 직접 표시하는 필드가 없다. opaque 노드이면서 `behavior-unknown` 미해석 항목이 걸린 노드를 대신 stateful 로 본다.
- 두 가지는 실제 해석기를 만들기 전에 Mímir 계약 1.1.0 에서 다룬다.

## 4. A2 검증 강화

사용자 결정에 따라 A2 검사를 강화했다.
- `endpoint-assessment` 에 선언한 closure(노드·edge 집합과 완결성)가 계산 결과와 같아야 한다.
- **선언이 complete 인데 계산이 incomplete 면 `editor.closure-overclaimed` 오류를 낸다.**
- 그 밖에 다르면 `editor.closure-mismatch` 오류를 낸다.
- 깊이 한도가 profile 에 있으므로 `check_assessment` 와 `check_plan` 이 profile 을 받는다.
- 기존 A2 fixture 는 바꾸지 않고 그대로 통과했다.

## 5. 독립 oracle 과 사례

사용자 결정에 따라 독립 oracle 을 마련했다.
- 합성 스냅샷 두 세트 `fixtures/solution-intake/closure-1.0.0/closure-a`(`capture` declared-complete, D=3), `closure-b`(`capture` partial, D=8) 와 endpoint 12개(`cases.json`)를 쓴다.
- 기대 결과 `oracle.json` 은 별도 검토자(Codex)가 규칙과 fixture 만 보고 손으로 도출했다. 검토자는 구현을 본 적이 없다.
- **구현 결과와 12건 모두 필드 단위로 일치했다.** 검토자는 이 fixture 에서 규칙이 모호한 곳이 없다고 보고했다.

| endpoint | 특징 | 결과 |
| --- | --- | --- |
| `n.final` | 다단 참조·상속·override·정책 | complete |
| `n.deep0` | 깊이 한도 | `depth-limit` |
| `n.cyc-a` | 평가 순환 | `evaluation-cycle` |
| `n.obj` | 구조 순환은 사유가 아님 | complete |
| `n.lonely` | edge 0개·claim 상태 unknown | `unexplained-leaf` |
| `n.avg` | 같은 이름 Temp 두 개, 후보를 고르지 않음 | `edge-ambiguous` |
| `n.line1.temp` | 같은 이름의 다른 설비는 따로 | complete |
| `n.b-tag` | 누락 파일 | `edge-missing` |
| `n.b-ext` | 외부 코드 | `edge-external-required` |
| `n.b-uns` | 미지원 | `edge-unsupported` |
| `n.b-cnt` | stateful 스크립트(`n.b-cnt.script`) | incomplete |
| `n.b-ok` | complete 이지만 captureScope partial | complete |

## 6. 검증과 범위 밖

2026-10-22 로컬 검증 결과는 다음과 같다.
- `scripts/test_p4f_closure.py` 8개 시험을 통과했다(oracle 일치, 입력 목록 순서를 섞어도 같은 결과, edge 0개가 완결이 아님, 모호 후보 미선택, captureScope 분리, 모르는 endpoint).
- A2 시험 11개를 통과했다. A2 거부 사례 30건을 확인했다(새 사례 2건: 선언이 계산보다 넓음, 선언 incomplete·계산 complete).
- 결함 주입 4건(깊이 한도 제거, `contains` 를 평가로 따라감, 모호 후보 선택, edge 없음을 설명으로 봄) 모두 closure 시험이 실패했다. closure 일치 검사를 지우면 A2 시험이 실패했다.

다음 항목은 범위 밖으로 둔다.
- native ID 의 개정 간 동일성과 rename(SI11)을 다루지 않는다.
- 근거 전이를 계산하지 않는다.
- 읽기·쓰기·event 구분을 하지 않는다(계약 공백).
- synthetic-pio-like·kepware-like 독립 입력을 다루지 않는다.
- sidecar(B) 를 다루지 않는다.
