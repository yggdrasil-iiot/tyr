# P3-B 가상 바이트·변환 미리보기

2026-10-17. 실제 장치 통신 제외. 09 가상 값 미리보기에서 저장된 매핑을 고르고 가상 HEX/Typed 값을 입력한다. 입력·계산 결과는 SQLite에 저장하지 않는다.

## 처리 경로

가상 원본 바이트 → byte/word 정렬 → 저장 타입 디코딩 → bit/codec → low/high·identity 그래프 → linear/unit-convert/enum/bit-select → 최종 cast → 정준 타입·단위·범위 검증 순서다. 각 소스의 바이트와 정렬 결과, 중간 타입/값/단위, 그래프 입력 역할, 실패 단계와 손실을 함께 보여준다.

- UInt16/Int16, UInt32/Int32, Int64, Float32/Float64, Boolean을 지원한다.
- byteOrder는 워드 안의 바이트, wordOrder는 워드 배열의 순서다. 두 UInt16 입력의 low/high 역할은 이 순서와 별도다.
- AB Logix/OPC UA의 typed 정의는 Typed 샘플을 받고 바이트 순서를 적용하지 않는다. Float32/64 Typed 샘플의 십진 입력은 해당 IEEE 폭으로 양자화하며 손실을 표시한다.
- 분산 UInt16 low=1/high=2는 UInt32 131073이다. UInt32 4294967295는 조합 단계에서 유효하지만 Int32 cast에서 overflow다.
- signed 연속 저장 타입의 디코딩은 지원한다. 분산 signed word 재해석·UInt64·임의 연산/코드는 지원하지 않는다.

처리 흐름 카드와 상세 trace는 같은 평가 결과다. 숫자는 JSON number로 축소하지 않고 정확한 십진 문자열로 전달한다. 입력을 바꾸면 이전 결과를 무효화하며 다시 계산해야 한다.

## 오류·손실·품질

| 항목 | 동작 |
|---|---|
| HEX 문법·폭·필수 입력 오류 | 해당 소스 단계에서 중단 |
| NaN/Infinity·overflow·범위 위반 | 결과 없음, bad |
| Int32 소수 변환 | half-even 반올림과 loss.rounding. exact면 value.inexact로 중단 |
| Decimal/Int64 → Double | 실제 binary64 값과 비교해 loss.precision. exact면 중단 |
| Typed Float32/64 입력 양자화 | loss.input-precision, 0으로 소실되면 loss.underflow |
| unknown enum·BCD digit·잘못된 날짜/weekday·ASCII | 명시적 오류 |
| ASCII NUL 뒤의 nonzero 바이트 제거 | 원시 HEX 보존 및 loss.truncation |
| 단위 변환 누락·잘못된 변환 쌍 | 결과 없음 |
| 이미 engineering 값의 중복 스케일 | 직접 소스/identity 그래프 모두 차단 |
| 원시 단위 unknown | 원문 상태를 보존하고 warning. 단위를 추정하지 않음 |

good는 오류/손실/경고 없음, uncertain은 허용한 손실 또는 경고가 있음, bad는 오류로 정준 결과를 만들지 못함을 뜻한다. 실제 OPC 품질·수집 freshness·동시성 판단이 아니며 P3-D 정책을 대신하지 않는다.

기존 P1 표본 harness의 Typed 입력은 Decimal 가정이었다. 새 preview는 선언된 Float32/64 폭을 실제 적용한다. 예를 들어 Float32 입력 338.15는 정확한 338.15가 아니므로 K→Cel 계산에서도 정밀도 손실을 드러낼 수 있다. 기존 P1 oracle을 같은 의미의 bit 단위 정밀도 증명으로 확대하지 않는다. 네 PLC의 representable 속도 2400 rpm 수렴은 별도로 검증한다.

## 2.1 소스 계약

기존 1.0/1.1/2.0 Schema는 보존하고 contracts/2.1.0의 common·source-definition을 추가했다. workspaceVersion과 mapping-set/value-graph는 2.0을 유지한다. 일반 숫자 정의는 기존 버전도 그대로 읽는다.

| 추가 표현 | 계약과 제한 |
|---|---|
| native bit | device-register addressUnit=bit, bitCount=1, Boolean. M/X/Y/L/S/B 영역 subset. 가상 샘플은 00/01 한 바이트 carrier이며 실제 MC frame 포맷이 아님 |
| bitCoordinate | decoded-value 또는 native-byte + byteIndex. 2.1의 bitOffset에는 좌표를 명시. 1.x는 기존 decoded-value 의미 유지 |
| BCD16 | raw valueType UInt16 + codec.kind=bcd16, 디코딩 결과 Int32 |
| ASCII | raw valueType String + ascii-fixed(length 1..256, termination fixed/nul). 바이트 원문 순서대로 해석 |
| S7 DATE_AND_TIME | DB 접근 8바이트, String + s7-date-time(timezone UTC/Asia/Seoul/미확인). UTC ISO 문자열 결과 |

ASCII/S7 날짜는 numeric shuffle을 하지 않으므로 byteOrder=big, wordOrder=high-first를 선언한다. BCD16은 숫자 byte/word 정렬 후 BCD digit을 해석한다. 날짜의 원문 시간대가 미확인이면 계산하지 않는다. 날짜·요일·BCD를 검증하며 1990~2089만 다룬다. String 결과와 source codec에 시간 의미를 보존하며 별도 DateTime 결과 타입은 아직 없다.

S7 날짜 배치는 [Siemens 시간 형식 설명](https://support.industry.siemens.com/cs/attachments/69864408/69864408_TimeSynchronization_en.pdf)과 [공식 DT 문서](https://docs.tia.siemens.cloud/r/es-es/v20/tipos-de-datos/fecha-y-hora/dt-date_and_time?contentId=onzWVeo0NKhLzYQh57hB6A)를 확인했다. 시간대 해석은 ZoneInfo와 고정한 tzdata 의존성을 사용한다.

02 접근 정의 화면에서 codec/주소 단위/bit 좌표를 작성·저장한다. 선택한 방식에 필요한 필드만 표시한다. 현재 지원한 CPU 메모리 범위·통신 payload·native 구조체·제품별 설정 export를 검증했다는 뜻은 아니다.

## API와 저장 경계

POST /api/preview 요청은 revision, mappingSetId, mappingId, samples다. samples는 source ID별 {bytesHex} 또는 {typedValue}다. 실제 바이트 정의에는 bytesHex, typed 정의에는 typedValue를 사용하며 혼용하지 않는다. 수치 Typed 값은 문자열로 보내 JS 정수 정밀도 손실을 피한다.

응답은 result, quality, trace, issues, losses, revision, workspaceSha256, sampleSha256, persisted=false, deviceCommunication=excluded를 포함한다. 요청 revision이 현재 저장본과 다르면 409다. 입력값 오류는 200 응답의 bad/trace이며 잘못된 요청·참조는 422다. Host/Origin·로컬 작성 헤더 경계는 기존 API와 같다.

각 요청은 저장된 작성본 snapshot으로만 계산한다. 사용자 표현식 실행·파일 읽기·장치 read/write를 수행하지 않는다. 사용자 입력 길이·폭·개수와 중간 Decimal 정밀도에 한계를 두며 초과하면 명시적 오류를 낸다. 다른 앱 승인·릴리스 형식으로 이 응답을 자동 승격하지 않는다.

## 검증과 재현

```text
python scripts/test_p3b.py --report docs/verification/p3b-validation.json
```

[독립 oracle](../fixtures/p3b/cases.json) 50건과 API/저장/네 프로파일 수렴 경계를 검증한다. [codec workspace](../fixtures/p3b/workspace.json)는 별도 가상 검사 레코드다. 주 작성본 build/p3a-ui/editor.sqlite3는 preview 검증 중 revision 13을 유지한다. codec 작성 화면 검증은 독립 build/p3b-ui/editor.sqlite3에서 수행했다.

[실행 결과](verification/P3-B-RESULTS.md). P3-C 파생식·P3-D 시간/품질·P3-E 배열/중첩·P6 승인은 후속이다.
