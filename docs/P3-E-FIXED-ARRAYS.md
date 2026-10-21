# P3-E 고정 scalar 배열

2026-10-17. 문서·수동 정의와 가상 입력만 다룬다. 실제 장치 통신·browse/read/write·활성화는 제외한다.

## 계약과 지원 범위

새 2.4.0 common/source-definition/value-graph/mapping-set/preview-scenario 5개 Schema를 추가했다. 기존 1.x/2.0/2.1/2.2/2.3 Schema 39개는 수정하지 않는다. workspace envelope와 target/proposal는 2.0, 의미 모델은 기존 scalar 프로퍼티를 재사용한다.

source-definition의 선택 fixedArray가 배열 저장 형상을 선언한다. array-element 노드가 고정 인덱스의 요소 하나를 골라 기존 targetInstance/memberPath에 매핑한다. 같은 배열의 서로 다른 요소를 같은 설비의 다른 객체 또는 다른 프로퍼티에 연결할 수 있다. 전체 배열을 scalar로 자동 cast하지 않는다.

rank 1~3, 총 요소 최대 256, 가상 버퍼 최대 4096 bytes 또는 Typed slots다. 요소는 기존 수치 타입/Boolean subset이며 codec·문자열·packed bit·native structure·array-of-struct·중첩 객체·가변 배열·런타임 인덱스는 제외한다. fixedArray가 없는 2.4 scalar 정의도 허용한다.

Týr가 정의·근거와 오프라인 검증을 소유한다. Mímir 후보, Bifrost 승인·release, Muninn 실행 및 실제 vendor array 지원을 자동 확장하지 않는다. 다른 앱 코드를 공유하지 않는다.

## shape·stride·범위

    "fixedArray": {
      "shape": [2, 3],
      "lowerBounds": [1, 10],
      "strides": [8, 2],
      "strideUnit": "word16",
      "range": {"start": 7000, "endExclusive": 7014}
    }

shape는 각 축의 요소 수다. 허용 인덱스는 lowerBounds부터 lowerBounds+shape−1까지 포함하며, 배열 길이와 상한 인덱스를 혼용하지 않는다. shape/lowerBounds/strides는 같은 rank·축 순서를 사용한다. 인덱스 좌표는 signed Int32 범위에 있어야 한다.

offset = Σ((index−lowerBound)×stride)다. row-major/column-major를 추정하지 않는다. stride는 양의 정수이며 byte/word16/element 중 좌표 단위를 명시한다. 요소 폭을 포함한 저장 구간끼리 겹치면 차단한다. 패딩과 축별 비연속 배치를 허용한다.

| 접근 정의 | strideUnit | range.start | 요소 폭 |
|---|---|---|---|
| S7-300 DB byteOffset | byte | 첫 요소 byteOffset | raw 타입의 byte 폭 |
| MELSEC word16 register | word16 | 첫 요소 addressIndex | raw 타입 byte 폭 / 2 |
| AB symbol / S7-1500 OPC UA Typed 배열 | element | 논리 슬롯 0 | 1 Typed slot |

access와 rawRepresentation은 첫 요소의 주소·타입·폭을 정의한다. DB byteLength, register wordCount를 전체 배열 폭으로 바꾸지 않는다. range는 첫 주소에서 시작하는 선언된 가상 저장 구간 [start,endExclusive)이며 전체 버퍼 크기를 결정한다. 마지막 요소 끝이 endExclusive를 넘거나 start가 첫 주소와 다르면 차단한다. 뒤쪽 패딩도 허용한다.

예: Float32 2워드, D7000, 위 형상에서 [2,12]의 offset은 12 word16 = 24 bytes다. 요소는 D7012~D7013이며 범위 끝 7014와 정확히 일치한다. [2,13]은 주소가 예약 범위 안에 보이더라도 논리 shape 상한을 초과하므로 거부한다. DB base byte64/strides [16,4]의 같은 요소는 byte88이다.

Typed element stride는 가상 평면 슬롯 배치다. symbolPath나 OPC UA NodeId를 임의로 고치거나 실제 IndexRange/장치 read를 생성하지 않는다. 논리 인덱스·slot과 실제 프로토콜 표현의 검증은 구분한다.

## 요소 선택과 값 처리

    {
      "nodeId": "last",
      "op": "array-element",
      "inputs": {"value": {"kind": "source", "sourceRef": {"id": "array-pressures-melsec", "version": "1.0.0"}}},
      "indices": [2, 12],
      "valueType": "Float32",
      "unit": {"status": "known", "code": "kPa"},
      "evidenceRefs": [{"artifactId":"manual-array-pressures-melsec","locator":{"kind":"text-line","line":1}}]
    }

입력은 고정 배열 소스 또는 FixedArray identity 노드다. 요소 선택의 선언 타입·단위가 소스 요소와 맞아야 한다. 이후 기존 low/high·파생값·scale·unit-convert·cast를 연결할 수 있다.

바이트 입력은 선언 range 전체의 HEX다. 배열 전체에 endian을 적용하지 않고 선택 요소의 바이트를 먼저 자른 뒤 기존 디코더로 byte/word 순서를 해석한다. Typed 입력은 typedValues의 평면 저장 슬롯 목록이다. shape [2,3], strides [4,1], range 0..7이라면 ["100","110","120",null,"200","210","220"]에서 [1,2]는 slot6의 220이다. null 패딩은 허용하지만 선택한 null은 array.element-missing이다. 중첩 JSON을 shape로 추정하지 않는다. 화면의 숫자는 정확한 문자열로 입력한다.

preview는 배열 버퍼/형상 → 인덱스·상한·offset·유효 주소 → 요소 바이트/Typed 값 → 디코딩 → scalar 그래프 → 최종 cast 순서다. 전체 배열을 수정하거나 가상 소스를 workspace에 추가하지 않는다. 두 요소를 선택해 차이를 계산해도 원래 배열 버퍼는 변경되지 않는다. Float/정수의 기존 손실·overflow 정책을 유지한다.

## 저장과 화면

02에서 배열 활성화, shape/lowerBounds/strides/unit/range를 작성한다. 프로필을 바꾸면 strideUnit과 range를 다시 확인해야 한다. 저장한 배열 인덱스 검사 버튼은 저장된 정의 기준으로 주소·범위를 읽기 전용 검사한다.

05에서 array-element와 indices를 작성한다. 범위 초과 노드는 SQLite 저장 전에 차단한다. 06에서는 scalar 요소 노드를 객체의 의미 프로퍼티에 연결한다. 원시 배열 전체는 scalar 매핑 선택지에서 제외한다. 07에서 원문과 indices 경로를 조회하고 09에서 실제 값·오류·손실을 확인한다.

POST /api/array-index는 revision/sourceRef(id/version)/indices를 받아 저장된 형상의 주소를 검사한다. 범위 오류는 bad/진단으로 반환하고 stale revision은 409다. 실제 값을 읽거나 DB를 수정하지 않는다.

SQLite의 workspace JSON/revision/CAS와 기존 시나리오 테이블을 재사용한다. 새 테이블이나 기존 데이터 자동 재작성이 없다. 1.x 작성본은 기존 명시적 이전 경로를 따른다. 이전 없이 고정 배열을 저장하거나 legacy 파일 게이트에서 scalar로 해석하는 경로는 거부한다. 2.0 envelope에서 문서별 새 버전을 검증한다.

검증 화면은 기존 build/p3a-ui/editor.sqlite3 revision20을 SQLite backup으로 복제한 build/p3e-ui/editor.sqlite3을 사용한다. 기존 DB는 보존했다. http://127.0.0.1:59772/는 새 복제본을 제공한다. 새 배열을 추가한 작성본의 hash가 달라 기존 시나리오는 복제본에서 stale로 표시되며 원래 DB의 시나리오는 유지된다.

## P3-D 연계와 한계

배열 전체 가상 버퍼에 하나의 입력 시각·품질·sequence를 선언한다. root source lineage로 freshness/skew·bad/결측을 검사하며 개별 요소의 시각이나 동시성을 추정하지 않는다. Typed slots를 저장하는 가상 시나리오는 2.4 계약을 사용한다. preview는 저장하지 않고, 명시적 시나리오 저장만 입력·가상 기준을 보관한다.

이번 구현은 고정 scalar 배열의 요소를 기존 scalar 의미로 연결하는 A 범위다. canonical 배열 결과 타입·중첩 memberPath·native 구조체·구조체 배열·동적 selector·장치별 native 배열 수집은 후속 B 범위다. MP06 전체 제품/표현 지원은 partial을 유지한다.

[독립 fixture](../fixtures/p3e/README.md) · [검증 결과](verification/P3-E-RESULTS.md) · [계획](../MVP-PLAN.md).


## P3-E B 후속과의 구분

위 문서는 2.4 고정 scalar source 배열 A의 실행 시점 범위다. [2.12 논리 구조·구조 배열](P3-E-LOGICAL-STRUCTURES.md)에서 정준 target의 inline 중첩 멤버와 고정 StructureArray, 전체 member/index 경로를 별도로 추가했다. 기존 source stride와 논리 target shape는 바인딩으로 연결하며 같은 배치로 추정하지 않는다. native UDT/DB 구조 수집·vendor packing/alignment와 실제 현장 PoV는 계속 미검증이다.
