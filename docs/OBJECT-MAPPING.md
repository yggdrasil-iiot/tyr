# 여러 주소로 구성하는 공통 의미 객체

상태: P2 확장 구현·검증 완료. 모든 샘플은 synthetic이며 실제 장치 통신을 하지 않는다.

## 모델의 단위

SemanticDefinition은 객체의 프로퍼티 목록 members[]를 가진다. 각 프로퍼티는 memberId·semanticId·role·결과 타입·정준 단위를 가진다.

MappingSet 한 개는 특정 설비 인스턴스에 대한 해당 객체의 프로퍼티 연결 목록 mappings[]를 가진다. 각 연결은 sourceRef와 targetMemberId를 지정한다. 원시 타입·주소·스케일은 프로퍼티별로 독립적이다.

예를 들어 MELSEC 모터 객체는 다음처럼 구성한다.

| 객체 프로퍼티 | 소스 | 저장 표현 | 해석 |
|---|---|---|---|
| actualSpeed | D1000 | UInt16, 1워드 | ×0.1 → Double/rpm |
| targetSpeed | D2000 | UInt16, 1워드 | ×0.1 → Double/rpm |
| operatingState | D3000 | UInt16, 1워드 | 0→stopped, 1→running, 9→fault |

세 주소의 연속성이나 블록 범위를 가정하지 않는다. 세 값을 하나의 스칼라로 합치는 것이 아니라 하나의 객체에서 각각의 프로퍼티를 채운다. 여러 입력의 합계·조건식 등으로 하나의 스칼라를 계산하는 다중 입력 연산은 별도의 후속 계약이다.

접근 정의와 객체의 의미를 분리하므로 주소가 이동해도 프로퍼티 의미를 재사용할 수 있다. 실제 동시 읽기·스냅샷 일관성·읽기 배치는 이 오프라인 작성 모델의 검증 범위에 포함하지 않는다.

## 화면

- **02 PLC 접근 정의**: 현장 신호명과 원문 주소를 별도로 보존한다. source ID는 논리 식별자이며 현장 이름의 중복을 허용한다.
- **03 공통 의미**: 객체 정의 ID로 객체를 만들고, 프로퍼티 선택에서 ‘＋ 새 프로퍼티’를 골라 추가한다. 저장 시 기존 다른 프로퍼티는 유지한다.
- **04 객체 매핑**: 설비와 의미 객체를 선택하면 프로퍼티별 행이 나타난다. 각 행에서 소스·해석·변환을 선택하고 객체 전체를 저장한다.
- **05 메모리맵 비교**: 프로퍼티×설비 주소 행렬과 신호별 이름·입력 단위·변환·정준 의미를 보여준다. 설비 필터로 한 객체 인스턴스만 확인할 수 있다.

비교 화면의 ‘다른 이름·같은 의미’, ‘같은 이름·다른 의미’ 표시는 사용자가 명시한 semanticId 연결을 분석한다. 이름으로 의미를 자동 부여하지 않는다. 부분 객체도 초안으로 저장할 수 있지만 빠진 프로퍼티는 mapping.incomplete-object로 표시한다.

편집 중 설비나 의미 객체를 바꾸면 기존 행을 재구성하므로 확인 후 이동한다. 복잡한 기존 변환 목록은 ‘전체 변환 목록 JSON’으로 그대로 보존하며 단일 연산으로 축약하지 않는다.

## 확장 샘플

fixtures/realistic/workspace.json에 설비 4개·논리 연결 4개·소스 32개·의미 객체 1개(프로퍼티 8개)·객체 매핑 4개를 저장했다. scripts/seed_realistic.py가 동일한 가상 자료를 만든다.

| 정준 프로퍼티 | AB Logix 심볼 | S7-1500 OPC UA 식별자 | S7-300 DB | MELSEC |
|---|---|---|---|---|
| actualSpeed | Drive.ActualSpeed | Motor.N_ACT | DB10.DBW20 | D1000 |
| targetSpeed | Drive.SpeedSetpoint | Motor.N_CMD | DB10.DBW24 | D2000 |
| operatingState | Drive.StatusWord | Motor.Mode | DB10.DBW40 | D3000 |
| alarmActive | Drive.AlarmActive | Motor.Alarm | DB10.DBW42.0 | D3001.0 |
| alarmCode | Drive.AlarmCode | Motor.FaultCode | DB10.DBW44 | D3002 |
| actualTorque | Drive.TorquePV | Motor.Torque | DB10.DBW48 | D4000 |
| windingTemperature | Drive.WindingTemp | Motor.TempK | DB10.DBD52 | D5000 |
| cycleCount | Drive.Cycles | Motor.Cycles | DB10.DBD56 | D6000 |

OPC UA namespace URI는 urn:tyr:sample:s7-1500이고 식별자는 string이다. DB/MELSEC의 ‘.0’ 표기는 해당 저장 워드를 디코딩한 뒤 bit0를 선택하는 가상 문서 표기다. 드라이버의 native bit 주소 문자열로 인증한 값이 아니다. 모델에는 저장 길이와 bitOffset을 별도 기록한다. S7의 byte/word order는 big/high-first, MELSEC은 little/low-first로 명시했다.

속도 범위는 0~3000 rpm이다. S7-300 Int16×0.1의 원시 범위로 표현할 수 있도록 정했다. cycleCount는 UInt32 원본을 Int32 정준 타입으로 변환하며 2147483647 초과 시 오류 정책을 가진다.

alarmActive는 불리언, alarmCode는 코드 값으로 구분한다. 알람 코드는 설비별 원래 코드를 보존하며 숫자가 같다는 이유로 동일 고장이라고 해석하지 않는다. 공통 고장 분류 체계와의 별도 매핑은 이번 샘플에 포함하지 않는다.

## 이름과 의미의 반례

| 사례 | 현장 표현 | 정준 의미 |
|---|---|---|
| 다른 이름·같은 의미 | ActualSpeed / IstDrehzahl / PV / 速度実績 | motor-actual-speed |
| 같은 이름·다른 의미 | S7-300의 PV | motor-actual-speed |
| 같은 이름·다른 의미 | AB의 PV | motor-torque |
| 같은 이름·다른 의미 | AB의 Status | motor-state |
| 같은 이름·다른 의미 | S7-1500의 Status | motor-alarm-active |
| 값 역할 구분 | 실제 속도 / 목표 속도 | measurement / setpoint와 별도 semanticId |

## 단위·스케일·코드 해석

| 표현 | 정준화 | 독립 기준 예 |
|---|---|---|
| AB 속도 Float32/rpm | cast Double | 2400 → 2400 rpm |
| S7-1500 속도 Float64/1/s | unit-convert ×60 → rpm | 40 → 2400 rpm |
| DB/MELSEC 속도 raw 정수 | linear ×0.1 → rpm | 24000 → 2400 rpm |
| S7-1500 토크 UInt32/mN.m | unit-convert ×0.001 → N.m | 125000 → 125 N.m |
| S7-1500 온도 Float64/K | unit-convert −273.15 → Cel | 338.15 → 65 Cel |
| 네 PLC의 운전 상태 코드 | enum-map → String | 1 / 20 / 4 / 1 → running |

1/s는 이 샘플에서 모터 축의 기계적 회전수/초다. 전기 주파수와의 변환이나 극수·감속비를 추측하지 않는다. 실제 자료에서는 해당 문맥의 근거가 필요하다.

단위 변환은 unit-convert이고 원시값의 공학값 환산은 linear다. 이미 공학값인 입력에 비항등 linear를 적용하면 기존 이중 스케일 검사가 작동한다. 알려진 입력·결과 단위가 다른데 명시적 변환이 없으면 mapping.unit-conversion-required로 검출한다. 변환 쌍·시작 단위·결과 단위도 검사한다.

## 계약 버전과 보존

- 기존 1.0.0 스키마 파일은 변경하지 않았다. 다중 members/mappings 구조는 기존 계약에 이미 존재했고 이번에 화면의 단일 값 제한을 제거했다.
- contracts/1.1.0은 1/s, mN.m, K 단위 코드와 unit-convert 연산을 추가한다. 계수는 임의 스크립트 대신 허용 변환 표로 고정한다.
- 1.0.0 문서는 계속 검증한다. 새 단위·연산을 1.0.0에서 조용히 허용하지 않는다.
- 현장 신호명 label은 mutable 소스 편집 레코드의 선택 필드다. 기존 레코드도 읽는다. 패키지 검증용 수동 근거 파일 첫 줄에 이름을 보존한다. semanticId의 대체 키로 사용하지 않는다.
- 객체 매핑·근거·변환은 P1과 동일한 참조/해시 규칙을 따른다. Bifrost의 1.1 수신·승인 구현은 아직 P6 범위다.

원래 P2 DB는 build/p2/workspace.sqlite3에 보존했다. 확장 샘플은 build/p2/realistic.sqlite3, 별도 UI 작성 시험은 build/p2/ui-composition.sqlite3을 사용했다.

## 재현

```powershell
python scripts/seed_realistic.py --db build/p2/realistic-new.sqlite3
python backend/server.py --db build/p2/realistic-new.sqlite3
python scripts/test_p2.py --report docs/verification/p2-expanded-validation.json
python scripts/validate_contracts.py --deny-network --report docs/verification/p1-expanded-regression.json
```

seed는 이미 데이터가 있는 DB를 덮어쓰지 않는다. 서버는 출력한 로컬 주소에서만 사용한다. 일반 값 preview는 P3에서 구현하며, 이번의 표본 수치 검증은 오프라인 계약 하네스다.
