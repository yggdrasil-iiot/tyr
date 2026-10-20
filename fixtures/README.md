# P1 검증 fixture

모든 자료와 값은 가상이다. 실제 고객 문서, 실제 XLSX, 정식 제품 export, 실장치·Bifrost 승인 결과가 아니다.

## 구성

- packages/motor: 동일 motor.actualSpeed 의미에 MELSEC·S7-300 DB·AB Logix 심볼·S7-1500 OPC UA를 연결한 패키지.
- packages/motor/data: 가상 주소표 CSV와 중립 설정 JSON. 실제 importer 구현은 P4다.
- packages/motor/sources: 네 프로파일과 다른 PLC에서 같은 D1000을 쓰는 추가 인스턴스.
- valid: 초안·동일 주소의 다른 PLC·관측 묶음·검증 결과·릴리스의 형식 예시.
- invalid: 필드·변환·경로·NodeId·승인·건수 오류 예시.
- cases.json: 스키마·문서·패키지 오류의 기대 규칙.
- oracles.json: 직접 명시한 입력 바이트와 기대값. 생성한 매핑을 실행해 만든 기대값이 아니다.

## 독립 기준값

| 접근 | 저장 또는 값 | 기대 디코딩 | 기대 결과 |
|---|---|---|---|
| MELSEC 예시 | 39 30 00 00, little/low-first INT32 | 12345 | ×0.1 = 1234.5 rpm |
| S7-300 예시 | 44 9A 50 00, big/high-first FLOAT32 | 1234.5 | 1234.5 rpm |
| AB 심볼 예시 | typed 1234.5 | 1234.5 | 1234.5 rpm |
| S7-1500 OPC UA 예시 | typed 1234.5 | 1234.5 | 1234.5 rpm |

12345는 16진수 0x3039이고 1234.5의 IEEE754 binary32 표현은 0x449A5000이다. P1 gate는 stdlib struct·Decimal로 기대 리터럴을 독립 검사한다. 실제 장치 순서의 기본값을 뜻하지 않는다.

package 오류 case는 기준 패키지를 새 임시 폴더에 복사한 뒤 지정한 JSON Pointer를 변경한다. reseal=true는 전송 해시를 갱신해 도메인 오류를 검사하고, false는 해시 변조 검사를 한다. 원본 fixture는 변경하지 않는다.

## 실행

python scripts/validate_contracts.py --deny-network

python scripts/validate_contracts.py --deny-network --report build/p1-validation.json

python scripts/validate_contracts.py --package fixtures/packages/motor --deny-network

필요한 의존성은 requirements-contracts.txt의 jsonschema 4.26.0이다. --deny-network는 시험 프로세스의 socket 생성과 연결을 차단하며 스키마 참조도 로컬 Registry로 제한한다. OS 또는 공장 네트워크의 격리 인증을 뜻하지 않는다.

## 정준 모델 검증 fixture

governance-cases.json은 네 접근의 동일 의미·1234.5 rpm 수렴, 동일 이름의 다른 개념·역할, 정준 ID 충돌, 표시 이름 변경, 단위·타입·범위·변환·주소·디코딩·문맥·근거 변경, precision/rounding/overflow 기대값을 고정한다. 원본 motor 패키지를 직접 해석하고 개정 비교는 메모리 복사에서 수행한다.

기준: [P1-GOVERNANCE-CRITERIA.md](../docs/P1-GOVERNANCE-CRITERIA.md). 가상 입력은 정준화 가설을 검증하는 유효한 자료다. 실제 장치 통신은 완료 조건에 포함하지 않는다.

## 현실성을 보강한 객체 샘플

[realistic/workspace.json](realistic/workspace.json)은 PLC별 실제값·목표값·운전 상태·알람 여부·알람 코드·토크·온도·카운터 8개, 총 32개 신호를 다룬다. 하나의 motor-drive 객체가 8개 프로퍼티를 가지며 각 설비에 독립적인 객체 매핑을 적용한다. D1000/D2000/D3000은 각각 1워드이고 서로 다른 프로퍼티를 채운다.

[realistic/oracles.json](realistic/oracles.json)의 12개 기준값은 서로 다른 단위·스케일·상태 코드를 동일 의미의 값으로 확인한다. 자세한 의미·주소·한계는 [객체 매핑 문서](../docs/OBJECT-MAPPING.md)를 따른다.

## 매핑 패턴 fixture

[mapping-patterns](mapping-patterns/README.md): 18개 지원 항목과 56개 사례. current·gap-probe·planned를 분리한다. 계획 명세는 유효한 현행 wire bundle 또는 구현된 지원으로 간주하지 않는다.

## P3-A 객체·그래프 fixture

[p3a](p3a/README.md): 같은 설비의 두 객체, 분산 word 조합, 오류 32건, 명시적 마이그레이션·기존 계약 바이트 보존 검증. 실제 장치 통신 제외.

## P3-B 독립 oracle

[p3b](p3b/README.md): 바이트/Typed 입력·저장 타입·단위/스케일·cast·오류/손실 기대값 50건 및 codec 예제 workspace.
