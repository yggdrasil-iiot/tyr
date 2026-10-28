# P4-F SI11 개정 간 검토 이전(review transfer)

## 1. 목적과 범위

Mimir가 S1과 동일한 소스의 후속 개정판인 S2를 발행할 때, Tyr는 S1 검토 문서가 S2에 여전히 적용되는지 각 문서 단위로 판단한다.

- 입력은 두 스냅샷, 각 번들과 profile, S1 문서(`review-decision` 체인, `endpoint-assessment`, `conversion-plan`), 검토자 선언만 사용한다. Tyr는 벤더 파일을 직접 열지 않는다.
- Mimir 계약에는 S2가 S1의 소스를 개정한 판본임을 명시하는 필드가 없다. 따라서 소스 연속성은 검토자가 직접 선언한다(`sourceContinuity`, evidenceBasis는 `declared-by-reviewer`).
- Phase A의 범위는 계약 정의, 순수 함수 구현, 검사기(`checker`), fixture로 한정한다. 아무것도 저장하지 않는다.
- 전체 규칙 본문은 영문 규칙 본문 `fixtures/solution-intake/revision-1.1.0/RULES.md`(identityRule `si11-1`)에 정의한다.
- 코드는 `backend/interpretation_transfer.py`에 `transfer` 및 `check_transfer` 함수로 구현한다.

## 2. 동일성

스냅샷 로컬 식별자(`nodeId`, `edgeId` 등)와 위치 지정자(`locator`)는 동일성 기준이 아니다. 모든 S2 fixture는 로컬 ID를 전면 재부여하고 위치 지정자를 이동시킨다. 동일성은 복합 키로 판별한다.

- 노드 키: (`namespace`, `nativeId`) 구조를 취한다.
- edge 키: (소유자 노드 키, `owner.field`, `relation`) 조합으로 식별한다. 두 edge가 해당 조합을 공유하면 `targetText`를 추가한다. 여전히 충돌하면 명시적 매핑을 요구한다.
- claim 키: (대상 노드 키, `subject.field`) 구조를 취하며, 키가 공유될 때에 한하여 `evidenceBasis`를 추가한다.
- 이슈 키: (`code`, 앵커 노드 또는 edge 키, `field`) 조합으로 식별한다. `locator`로만 앵커링된 이슈는 식별 키를 생성할 수 없으므로 이전 대상에서 제외한다.
- 이름이 변경된 노드는 오직 검토자 매핑(`mappings`, `declared-by-reviewer` 전용)을 통해서만 동일성을 유지한다. 누락된 S1 노드와 내용이 동일한 S2 노드는 `candidates`로만 보고하며, 시스템이 자동으로 선택하지 않는다.
- 각 S1 항목의 식별 결과는 `same`, `changed`, `absent`, `ambiguous` 중 하나로 귀결된다.
- `absent`는 삭제가 아니다. 시스템은 어떤 데이터도 임의로 삭제하지 않으며, `retired`는 검토자가 누락된 키를 인지했음을 기록하는 용도로만 동작한다.

## 3. 근거 비교

근거는 벤더 원본 파일이 아닌 해석된 내용(interpreted content)을 기준으로 비교한다. 비교 대상 필드를 JCS(JSON Canonicalization Scheme)로 직렬화한 후 SHA-256 해시를 계산하여 일치 여부를 대조한다.

- 대조 대상 필드:
  - 노드: kind, state, outputs
  - edge: relation, access, targetText, resolution, target key
  - claim: value, evidenceBasis, status, rule id 및 version, dependencies
- 파일 SHA-256 핀은 개정마다 매번 변경되므로 출처 기록(`artifactPins`)으로만 보존하며, 결코 이전 유지 조건으로 삼지 않는다. 자유 형식의 텍스트인 `evidenceRefs`는 복사본과 함께 그대로 이전한다.
- 결정(`decision`)별 유지 범위(keep scope):
  - claim: 해당 claim 및 `dependsOn`을 통해 도달하는 claim과 edge
  - edge: 해당 edge 자체
  - 노드(`declared-by-reviewer`): 해당 노드, 노드의 claim, 소유한 edge, 앵커링된 이슈(`oneHop`)
  - 노드(`verified-by-virtual-case`): `oneHop` 항목 전체 및 endpoint closure(구성원, edge, 완전성, 사유, 캡처 범위, stateful/state-unknown, 이벤트, 쓰기)
  - 이슈: 해당 이슈 및 앵커
- 평가는 모든 closure 노드를 `oneHop` 지문으로 대조하고 모든 closure edge를 비교한다.
- 계획은 매핑된 노드를 `oneHop` 지문, 연관 평가, 작업 공간, 결정과 함께 비교한다.
- 전역 규칙:
  - profile digest 변경(`profile-changed`) 또는 스냅샷 `context` 변경(`context-changed`)은 모든 결정을 재검토 대상으로 만들고 모든 평가와 계획을 무효화(`stale`)한다. profile에는 개별 claim에 귀속되지 않는 해석기 버전, 지원 제품, 알려진 공백(`knownGaps`)가 포함되기 때문이다.
  - 캡처 범위 변경(`capture-changed`)은 평가와 계획을 무효화(`stale`)한다.

## 4. 판정

문서별 판정은 정해진 우선순위 규칙에 따라 단일 값을 부여하며, 사유는 13개 닫힌 코드 목록에서 해당하는 항목을 모두 나열한다.

| 문서 유형 | 허용 판정(Verdicts) |
| :--- | :--- |
| 결정(`decision`) | `carried`, `re-review`, `needs-mapping`, `orphaned` |
| 평가(`assessment`), 계획(`plan`) | `reusable`, `stale`, `needs-mapping`, `orphaned` |

- 판정 우선순위: `orphaned` > `needs-mapping` > `re-review` / `stale` > `carried` / `reusable` 순서로 적용하며, 선순위 판정 조건이 충족되면 후순위 판정은 배제한다.
- 사유 코드(13종): `target-absent`, `target-ambiguous`, `target-unkeyed`, `scope-item-absent`, `scope-item-ambiguous`, `evidence-changed`, `closure-changed`, `profile-changed`, `context-changed`, `capture-changed`, `decision-not-carried`, `assessment-not-reusable`, `workspace-changed`.
- 대상(`target`)이 누락된 경우 내용 비교를 중단한다. 단, 범위 내 항목 분류는 계속 진행한다.
- 결정 체인 내 대체(supersession): S1 체인에서 후속 결정이 동일 대상을 지정하면 이전 결정은 대체된다. 오직 체인의 마지막 결정(head)에 대해서만 판정을 내리며, 대체된 결정은 결코 이전하지 않는다. 대체된 결정을 인용하는 평가는 무효화(`stale`, 사유: `decision-not-carried`) 처리한다.

## 5. `review-transfer` 계약 2.1.0

`editor-contracts/2.1.0/`(`common.schema.json`, `review-transfer.schema.json`)에 신규 문서 종류인 `review-transfer`를 추가한다. 2.0.0 스키마는 수정 없이 유지한다. 문서의 본문(body) 구성은 다음과 같다.

- S1 및 S2의 snapshot·bundle·profile 핀과 artifact 핀
- `sourceContinuity`, `workspace`, `mappings`, `retired`, `globals`
- 모든 S1 항목의 대응 관계(correspondence)
- decision chain head, `superseded`, `verdicts`, `carried`

digest는 `digest`와 `envelope`를 제외한 JCS에 대해 계산한 SHA-256이다. Intake 검사는 이제 editor 2.1.0을 등록하며, 스키마 검사 전 단계에서 `declared-by-reviewer`로 선언되지 않은 mapping이나 source continuity를 즉시 거부한다.

## 6. 검사기

`backend/interpretation_transfer.py`의 `check_transfer`는 모든 계산을 독립적으로 다시 수행하며, 위반이 발생하면 `transfer.*` 코드로 거부한다. S2 체인 내부에서 S1으로 고정된 결정이 발견되면 `pin.snapshot-mismatch`를 반환한다.

검사기가 거부하는 구체적 조건은 다음과 같다.

- 버전 혼합 및 스냅샷·번들·profile 핀 불일치, artifact 핀 불일치
- `sourceContinuity` 누락
- `declared-by-reviewer`가 아닌 매핑 근거, S1에 없는 매핑 출발 키, S2에 없는 매핑 도착 키, 모호한 타깃, 매핑 충돌
- `retired`로 선언한 키가 S2에 남아 있는 경우
- `workspace` 누락
- 유효하지 않은 S1 체인 또는 문서
- `globals`, correspondence, `superseded`, `verdicts`의 재계산 불일치
- `carried` 소스 누락, 대체(`superseded`)된 항목의 이전 시도, `carried` 판정인데 `carried` 목록에 없는 결정
- 사본 누락, 사본 순서 불일치, 내용 차이
- carried-from 마커 누락

## 7. Fixture와 독립 oracle

테스트 fixture는 `fixtures/solution-intake/revision-1.1.0/`에 위치하며, `scripts/generate_revision_fixtures.py`를 통해 바이트 단위로 안정되게 생성한다. 합성 pio-like 스냅샷 및 closure-c 스냅샷을 기반으로 10개 쌍과 12개 입력 변형을 구성한다. closure-c 대상의 독립 S1 에디터 세트는 `closure-c-s1/`에 배치한다.

fixture가 다루는 10개 시나리오 쌍:
- 단순 순서 변경
- 주소 변경
- 이름 변경(매핑 없는 경우 및 있는 경우)
- 삭제
- 쌍둥이 노드 및 중복 키(매핑 없는 경우 및 있는 경우)
- 타깃 재지정 및 캡처 변경
- profile 변경
- closure-c 상태 및 접근 변경
- closure-c 컨텍스트 변경
- 대체된 결정(`superseded`)

Codex는 Tyr 코드를 보지 않고 오직 `RULES.md`와 fixture만으로 12개 변형 전체에 대한 `oracle-<v>.json`을 독립 작성하였으며, 그 해석 근거는 `ORACLE-NOTES.md`에 정리되어 있다. Tyr 구현체는 모든 필드(`globals`, correspondence, `superseded`, 이유와 후보를 포함한 `verdicts`, `carried`)에서 독립 oracle과 일치한다. 첫 비교 단계에서 이미 모든 판정 범주가 일치하였으며, 두 건의 이유 해석은 규칙 원문에 맞추어 정렬하였다(타깃이 누락되어도 scope 항목을 분류하고, assessment와 plan은 노드를 `oneHop`으로 비교하도록 조정함).

검증은 `scripts/test_p4f_transfer.py`의 11개 테스트로 수행한다. oracle 일치, 전 변형에 대한 검사기 왕복, 22개 거부 사례, `carried` 사본 필드, 키 파생, 원본 입력을 보존하는 순서 불변성, 동일 스냅샷 자기 대조, 후보 미선택 경로를 확인한다. 결함 주입 테스트에서는 16개 변이 중 16개 전부를 감지하였다. 로컬 CI 전체 실행 결과는 32개 모듈, 1,093개 테스트 통과, 0건 실패다.

## 8. B 단계로 넘기는 것

A 단계는 순수 함수 분류까지 완료하며, 영속화 및 인터페이스 작업은 B 단계로 넘겨 처리한다.

- 사이드카 및 CAS 내 transfer와 사본의 저장
- 매핑 및 재검토 화면
- S1 → S2 → S3 연속 체이닝
- 재등장한 키의 연결
- Mimir 측의 안정적 ID 힌트
- 이전된 증거의 계산(A 단계는 분류만 수행함)
- Bifrost 제출 반영 효과
