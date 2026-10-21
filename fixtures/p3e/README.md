# P3-E 독립 고정 배열 fixture

workspace.json은 네 PLC 접근 정의의 2×3 Float32 배열과 first/last 채널 객체 8개를 정의한다. 원문 접근 방식과 logical lowerBounds/stride가 달라도 첫/마지막 값 100/220 kPa는 같은 의미로 수렴한다. 모든 자료는 가상이다.

| 접근 | lowerBounds | strides / unit | range | 마지막 요소 |
|---|---|---|---|---|
| AB symbol | [0,0] | [4,1] element | [0,7) | [1,2] → slot6 → 220 |
| OPC UA Typed | [0,0] | [4,1] element | [0,7) | [1,2] → slot6 → 220 |
| S7 DB | [1,10] | [16,4] byte | [64,92) | [2,12] → byte88 → 220 |
| MELSEC | [1,10] | [8,2] word16 | [7000,7014) | [2,12] → D7012 → 220 |

samples.json의 값은 순서대로 100,110,120,패딩,200,210,220이다. DB는 big/high-first, MELSEC은 little/low-first이며 기대 Float32 bytes를 수동 기입했다. Typed slots는 숫자 문자열과 null 패딩이다.

cases.json의 23개 기대값은 수동 작성한 독립 oracle이다. 하한/상한·exclusive upper·rank·분수 인덱스·요소 결측·버퍼 길이·중첩 배열 금지·Boolean/NaN/HEX 오류·중간 슬롯·nonzero lower를 포함한다. 테스트는 column-major·rank3·stride 중첩/저장 범위·타입/단위·whole-array cast 금지·같은 배열의 두 요소 파생값도 확인한다.

timed-workspace.json/scenario.json은 Typed 배열과 P3-D 가상 시간·품질의 저장 연계를 검증한다. metadata는 전체 버퍼 단위이며 요소별 시각을 추정하지 않는다.

python -B scripts/test_p3e.py --report docs/verification/p3e-validation.json

기존 Schema 39개 보존, SQLite 왕복/수정/오류 저장 원자성·CAS, index probe 및 preview의 DB 파일 해시 불변, Typed scenario 2.4 왕복·기존 2.3 scenario 거부를 시험한다. 기존 계획 array-shape-stride/array-out-of-range와 대응하며 native-structure-select/array-of-struct-to-objects는 구현 성공으로 계산하지 않는다.
