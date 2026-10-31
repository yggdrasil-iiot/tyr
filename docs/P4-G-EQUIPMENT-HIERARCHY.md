# P4-G ISA-95 설비 계층

## 범위
Tyr는 ISA-95(IEC 62264) 설비 계층을 거버넌스 대상 메타데이터로 작성한다. 검토자는 근거를 첨부하여 각 노드의 계층 수준과 부모 노드를 명시한다. 승인 권한은 Bifrost에 두며, Bifrost는 기존 두 키 매핑 릴리스 절차로 승인을 확정한다. Tyr는 설비 계층 수준을 임의로 추론하지 않는다.

설계 결정에 따라 다음 항목은 작업 범위에서 제외한다.
- Sparkplug `group_id`와 에지 노드 ID, MQTT 토픽, 인가 키 `Target(group, edge, device)`는 변경 없이 유지한다.
- Muninn 전송은 후속 과제로 분리하며, 이번 변경 작업은 Bifrost 릴리스에서 끝난다.

## 계약 2.23.0
새로운 전역 계약 버전 디렉터리 `contracts/2.23.0/`에 다음 세 파일을 정의한다.
- `equipment-hierarchy.schema.json`: 새 kind `equipment-hierarchy`를 선언한다.
- `common.schema.json`: 2.22.0 판 사본에서 `$id`를 갱신하고 파일 항목 kind 열거형 끝에 `equipment-hierarchy`를 추가한다.
- `mapping-proposal.schema.json`: 2.22.0 판 사본에서 `$id`와 `schemaVersion` 상수를 2.23.0으로 갱신한다.

계층 문서는 다음 필드를 모두 필수로 요구하며 추가 필드를 허용하지 않는다.
- `kind`: `equipment-hierarchy`
- `schemaVersion`: "2.23.0"
- `id`
- `version`
- `label`
- `levelVocabulary`: 상수 `opc-10030-1.00-isa95-equipment-element-level-enum`
- `nodes`: 1개 이상 2048개 이하 노드 배열
- `evidenceRefs`: 문서 수준 근거 참조 배열(0개 이상 64개 이하)

각 노드는 다음 필드로 구성한다.
- `equipmentInstanceId`: 설비 인스턴스 식별자
- `label`: 노드 표시 명칭
- `equipmentLevel`: 설비 계층 수준 토큰
- `parentEquipmentInstanceId`: 부모 노드 식별자(루트 노드는 null)
- `evidenceRefs`: 노드 수준 근거 참조 배열(노드당 1개 이상 64개 이하 필수)
- `otherLevel`: `equipmentLevel` 값이 `OTHER_14`일 때 1자 이상 128자 이하 문자열로 반드시 명시하며, 그 외 수준에서는 지정을 금지한다. OPC 10030 규격은 OTHER 수준에 응용 고유 명칭을 요구한다.

`equipmentLevel` 토큰은 OPC 10030 v1.00 ISA95EquipmentElementLevelEnum Table 36에 인쇄된 명칭을 그대로 쓴다.
- 토큰 목록: `ENTERPRISE_0`, `SITE_1`, `AREA_2`, `PROCESSCELL_3`, `UNIT_4`, `PRODUCTIONLINE_5`, `WORKCELL_6`, `PRODUCTIONUINT_7`, `STORAGEZONE_8`, `STORAGEUNIT_9`, `WORKCENTER_10`, `WORKUNIT_11`, `EQUIPMENTMODULE_12`, `CONTROLMODULE_13`, `OTHER_14`
- `PRODUCTIONUINT_7`은 공식 발행 명세에 실린 철자이므로 원본 그대로 유지한다. 수정한 철자인 `PRODUCTIONUNIT_7`은 거부한다. (출처: https://reference.opcfoundation.org/specs/OPC-10030/7.4.1)

부모와 자식 간 계층 수준 쌍 행렬은 두지 않는다. 열거형 번호는 서열이나 포함 문법을 정의하지 않는다. 검사는 포레스트 구조(부모 참조, 순환 여부, 깊이)와 근거 확인에 집중한다.

봉투 규칙:
- 2.23.0 계층 문서를 담으려면 2.23.0 제안서가 필요하다. 2.22.0 제안서는 `equipment-hierarchy` kind를 나열할 수 없어 스키마 검증에서 거부된다.
- 2.21.0 및 2.22.0 봉투 검사기는 2.23.0 제안서도 받아들이므로 내부 레코드 필드 문서와 브로드캐스트 문서는 정상 동작을 유지한다.

## 검사
새 모듈 `scripts/equipment_hierarchy.py`에 다음 거부 코드를 구현한다.
- `hierarchy.multiple`: 작업 공간이나 패키지 하나에 계층 문서를 최대 하나만 허용한다.
- `hierarchy.duplicate-node`: 노드 식별자 중복을 금지한다.
- `hierarchy.parent-missing`: null이 아닌 부모 식별자는 동일 문서 안에 있는 노드를 가리켜야 한다.
- `hierarchy.cycle`: 자기 자신을 부모로 지정하는 경우를 포함해 순환 참조를 금지한다.
- `hierarchy.depth`: 루트에서 노드에 이르는 경로 길이를 최대 64개 노드로 제한한다.
- `hierarchy.context-equipment`: 작업 공간 검사 시 모든 노드 식별자가 작업 공간 설비 목록에 포함되어야 한다.
- `hierarchy.unresolved-instance`: 계층 문서를 포함할 때, `equipmentInstanceId`를 명시한 다른 모든 문서는 계층 내 노드와 정확히 일치해야 한다.

노드 근거 참조는 다른 문서와 동일한 근거 검사 로직(`evidence.missing`, `evidence.locator`)을 거쳐 확인한다. `OTHER_14` 지정 시 `otherLevel` 규칙과 토큰 철자 규칙은 스키마 자체로 강제한다.

## 작성 공간과 발행
작업 공간은 선택 항목인 `equipmentHierarchies` 목록(최대 1개)을 둔다. `backend/workspace_v2.py`는 스키마 검증, 노드-설비 일치 규칙, 모듈 검사를 확인하고, 제안서 `schemaVersion`에 2.23.0을 지정하여 패키지 내 `hierarchy/<i>.json` 경로에 문서를 기록한다. 계층 문서를 두지 않은 작업 공간은 기존 방식 그대로 빌드하여 2.22.0 버전을 유지한다.

`backend/publication.py`는 제출물 생성 시 계층 문서를 각 노드가 인용한 근거 아티팩트와 함께 항상 포함한다.

Bifrost는 `core/src/main/resources/mapping-contracts/2.23.0/` 경로 아래 바이트 단위로 동일한 스키마 사본과 자체 Java 코드(`EquipmentHierarchy.java`, 동일 거부 코드)를 두고 패키지 묶음을 자체 검증한다. 두 저장소 사이에 코드를 공유하지 않는다.

## 시험
`scripts/test_equipment_hierarchy.py`에 총 19개 시험을 작성한다. 시험은 다음 항목을 검증한다.
- 2.23.0 패키징과 통과
- 발행 묶음 완성도(publication closure)
- 각 거부 코드별 동작
- 공식 발행 토큰 철자 확인
- 최대 깊이 제한 확인
- 하위 버전 봉투 거부 동작
- 작업 공간 없이 진행하는 단독 패키지 검사
- 2.23.0 스키마와 2.22.0 스키마 간 차이가 의도한 부분에만 머무르는지 대조
- 픽스처 묶음 `fixtures/equipment-hierarchy/bundle`이 픽스처 작업 공간의 정확한 빌드 결과물인지 검증
- Bifrost 묶음 사본이 바이트 단위로 일치하며 Bifrost CLI 도구가 이를 받아들이는지 확인

결함 주입(Fault injection) 시험:
- 발행 시 계층 문서 포함, 노드 근거 검사, 문맥 설비 검사, 순환 검사, 미확인 인스턴스 검사, 제안서 2.23.0 버전 지정을 하나씩 제거할 때마다 적어도 하나 이상의 시험이 실패한다.

검증 픽스처:
- 기존 `fixtures/broadcast/workspace.json` 위에 합성 사이트 `synthetic-site`(`SITE_1`)와 두 개 생산 라인 `record-line-a`, `record-line-b`(`PRODUCTIONLINE_5`)를 정의한 `fixtures/equipment-hierarchy/hierarchy.json`을 얹어 구성한다.
