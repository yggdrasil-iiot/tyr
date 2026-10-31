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
- `hierarchy.evidence-scope`: 원시 작업 공간이 아니라 근거 아티팩트가 포함된 패키지 검사 시 모든 노드는 자신의 `equipmentInstanceId`를 `scope`에 포함하는 근거 아티팩트를 적어도 하나 인용해야 한다.

노드 근거 참조는 다른 문서와 동일한 근거 검사 로직(`evidence.missing`, `evidence.locator`)을 거쳐 확인한다. `OTHER_14` 지정 시 `otherLevel` 규칙과 토큰 철자 규칙은 스키마 자체로 강제한다.

## 작성 공간과 발행
작업 공간은 선택 항목인 `equipmentHierarchies` 목록(최대 1개)을 둔다. `backend/workspace_v2.py`는 스키마 검증, 노드-설비 일치 규칙, 모듈 검사를 확인하고, 제안서 `schemaVersion`에 2.23.0을 지정하여 패키지 내 `hierarchy/<i>.json` 경로에 문서를 기록한다. 계층 문서를 두지 않은 작업 공간은 기존 방식 그대로 빌드하여 2.22.0 버전을 유지한다.

`backend/publication.py`는 제출물 생성 시 계층 문서를 각 노드가 인용한 근거 아티팩트와 함께 항상 포함한다.

Bifrost는 `core/src/main/resources/mapping-contracts/2.23.0/` 경로 아래 바이트 단위로 동일한 스키마 사본과 자체 Java 코드(`EquipmentHierarchy.java`, 동일 거부 코드)를 두고 패키지 묶음을 자체 검증한다. 두 저장소 사이에 코드를 공유하지 않는다.

## 작성 화면과 계층 근거

Tyr 편집기의 자료 준비(prepare) 그룹에서 "설비와 논리 연결" 바로 뒤에 "설비 계층" 탭을 추가한다. 구현 파일은 `frontend/hierarchy.js`이다.

검토자는 화면에서 각 노드마다 설비(작업 공간 설비 목록에서 선택), 표시 레이블, ISA-95 수준(공식 발행 토큰 15개 중 선택하며 Tyr은 수준을 추론하지 않음), `OTHER_14` 지정 시 `otherLevel` 이름, 부모 노드(루트 노드는 비워 둠), 하나 이상의 근거 인용을 설정한다. 인용 항목은 근거 아티팩트와 위치 지정자를 지정하며, 위치 지정자는 텍스트 줄 번호, xlsx `시트!셀`, JSON 포인터를 사용한다.

미리보기 패널은 각 근거 아티팩트에서 인용할 본문 내용을 보여준다. 텍스트와 CSV는 줄 번호가 붙은 본문을 표시하고, xlsx는 값이 채워진 셀 목록을 표시한다.

검토자는 기존 근거 아티팩트(파일 가져오기 `import-*` 및 수동 정의 `manual-*`) 외에 두 가지 계층 근거 레코드를 추가한다. 하나는 화면에서 직접 작성하는 텍스트 형식의 검토자 메모이며, Tyr이 검토자, 작성 시각, 제목을 담은 세 줄의 헤더와 빈 줄 하나를 앞에 추가하므로 본문은 5번째 줄부터 시작한다. 다른 하나는 CSV 또는 xlsx 형식으로 업로드하는 공장 설비 대장 파일이다. 파일과 텍스트의 바이트는 작성하거나 내보낸 그대로 보존한다.

각 레코드는 안정적인 고유 ID(위치 기반이 아님), 버전, 레이블, 검토자, 출처(synthetic 또는 field), 수집 시각, 적용 범위(포함하는 설비 ID 목록)를 명시한다. 스키마는 `editor-contracts/1.0.0/hierarchy-evidence.schema.json`이며, 작업 공간 키는 `hierarchyEvidence`이다.

레코드 검사는 `backend/hierarchy_evidence.py`에서 처리하며, 거부 코드는 `hierarchy-evidence.schema`, `hierarchy-evidence.duplicate`, `hierarchy-evidence.bytes`(유효하지 않은 base64), `hierarchy-evidence.limit`(64개 초과 레코드 또는 1 MiB 초과 파일), `hierarchy-evidence.digest`(SHA-256 불일치), `hierarchy-evidence.encoding`(UTF-8이 아닌 텍스트/CSV), `hierarchy-evidence.xlsx`(읽지 못하는 통합 문서), `hierarchy-evidence.scope`(작업 공간 바깥 설비를 지정한 범위), `hierarchy-evidence.version-required`(내용이 변경되었으나 새 버전을 지정하지 않은 동일 ID)이다.

빌드 시 각 레코드는 ID가 `hierarchy-<record id>`인 일반 evidence-artifact 1.1.0 문서가 되며, 바이트는 `data/hierarchy-<i>.<ext>`에, 아티팩트는 `evidence/hierarchy-<i>.json`에 저장된다. evidence-artifact 계약은 달라지지 않으며, Bifrost는 기존 근거 검사 규칙으로 이 아티팩트들을 읽는다.

인용된 근거는 삭제하지 못한다. 화면에서 삭제를 차단하고, 서버도 따로 `evidence.missing`으로 거부한다.

저장은 작업 공간 revision을 비교하는(compare-and-set) 2단계로, 먼저 검증(plan)하고 이어서 저장(apply)한다. 검증 후 편집하면 계획이 무효화되며, 저장 요청이 검증된 내용과 다르면 `hierarchy.plan-changed`로 저장을 거부한다. 엔드포인트는 GET `/api/equipment-hierarchy`, PUT `/api/equipment-hierarchy-plan`, PUT `/api/equipment-hierarchy-apply`이다. 승인 권한은 계속 Bifrost가 가진다.

## 시험
`scripts/test_equipment_hierarchy.py`는 총 29개 시험을 갖춘다. 이전 19개 시험(2.23.0 패키징과 통과, 발행 묶음 완성도(publication closure), 각 거부 코드, 공식 발행 토큰 철자, 깊이 제한, 하위 버전 봉투 거부, 작업 공간 없는 단독 패키지 검사, 의도한 부분으로 한정한 `2.23.0`과 `2.22.0` 스키마 차이, 픽스처 작업 공간 빌드 결과와 픽스처 번들의 일치, 바이트 단위로 동일하며 Bifrost CLI가 받아들이는 Bifrost 복사본)에 더해, 작성 화면 API를 검증하는 10개 시험을 추가했다. 추가한 시험은 목록 조회, 저장과 초기화, 오래된 리비전 및 변경된 계획 거부, 줄 번호로 인용한 검토자 메모, 셀 위치로 인용한 xlsx 대장, `evidence-scope` 규칙, 레코드 거부, 인용된 근거 삭제 거부, 내용이 변경된 근거의 새 버전 요구, HTTP 라우트이다. 결함 주입 시험에서는 발행 시 계층 포함, 노드 근거 검사, `context-equipment` 검사, 순환 참조 검사, 미해결 인스턴스 검사, 제안 버전을 `2.23.0`으로 설정하는 작업, `evidence-scope` 검사, 근거 기록의 SHA-256·범위·버전 검사, 계획 변경 검사, 근거 아티팩트 생성 중 어느 하나라도 제거하면 적어도 한 시험이 실패한다. 픽스처는 `fixtures/broadcast/workspace.json`을 바탕으로 `fixtures/equipment-hierarchy/hierarchy.json`에서 합성 사이트 `synthetic-site`(`SITE_1`)와 두 생산 라인 `record-line-a`, `record-line-b`(`PRODUCTIONLINE_5`)를 정의한다. 모든 노드는 세 노드 전체를 `scope`로 지정한 합성 공장 대장 `fixtures/equipment-hierarchy/evidence.json`(CSV, ID `plant-register`)을 줄 번호로 인용한다.
