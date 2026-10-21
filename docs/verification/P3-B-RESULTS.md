# P3-B 검증 결과

2026-10-17. 가상 바이트/Typed 값의 단계별 디코딩·그래프·변환·cast 미리보기를 구현했다. 실제 장치 통신은 제외한다.

| 검증 | 결과 | 증거 |
|---|---|---|
| P3-B 수용 | 66/66, 독립 oracle 50건 포함 | [결과·코드/fixture 해시](p3b-validation.json) |
| P3-A SQLite/API | 37/37 | [회귀](p3a-workspace-p3b-regression.json) |
| P3-A 계약 | 52/52 | [회귀](p3a-contract-p3b-regression.json) |
| P2 | 24/24 | [회귀](p2-p3b-regression.json) |
| P1 | 105/105 | [회귀](p1-p3b-regression.json) |
| 기존 패턴 baseline | current 14/14, gap 8/8, planned 34 | [회귀](pattern-p3b-regression.json) |

## 독립 기대값

- 가상 low=01 00, high=02 00 → UInt16 1/2 → UInt32 131073 → Int32 131073.
- low=90 01, high=00 00 → 400 → ×0.1 → 40 1/s → 2400 rpm → Double 2400. 하나의 경로에 모든 단계를 연결한 fixture다.
- byte/word 순서에 따른 UInt32 1/65536/65538과 signed -10 → -1.
- Float32 bits 3dcccccd와 Int64 9007199254740993 → Double의 정확한 값/손실.
- Int32 half-even tie·음수 반올림, exact 중단, overflow, NaN/Infinity, underflow, HEX/폭/결측 오류.
- 단위 변환 누락·중복 engineering 스케일·unknown enum·범위 오류.
- native byte bit와 decoded integer bit의 서로 다른 결과, native relay의 00/01 carrier.
- ASCII/NUL 뒤 nonzero 바이트 손실, BCD16 유효/무효 digit, S7 날짜·weekday·미확인 시간대.
- 네 PLC 접근 정의의 속도 2400 rpm 수렴.

숫자는 정확한 문자열로 반환한다. IEEE 정밀도와 단순 십진 Typed 가정의 차이는 [정밀도 정책](../P3-B-PREVIEW.md)에 설명했다.

## API·저장 경계

preview API는 저장된 revision snapshot만 평가한다. 오래된 revision·잘못된 요청·외부 Origin을 거부한다. sample 오류는 500 대신 bad/trace로 반환한다. DB body·revision·DB 파일 해시가 preview 전후 동일함을 테스트했다. 임의 코드·SQL·장치 호출은 없다. 2.1 codec/native bit/좌표 정의의 SQLite 왕복도 검증했다.

## 브라우저에서 확인

- low/high 131073의 원본 HEX·정렬·디코딩·그래프·cast trace.
- UInt32 최댓값 조합 후 Int32 cast의 value.overflow.
- 원시 1×0.1 → Double exact에서 loss.precision + value.inexact.
- OPC UA Typed 40 1/s → 2400 rpm.
- 가상 입력 변경 시 이전 결과를 무효화하고 재계산하도록 표시.
- 별도 codec DB에서 2.1 ASCII 정의를 화면으로 저장한 뒤 ABC를 디코딩.
- BCD 1234, S7 날짜의 Asia/Seoul→UTC 문자열, native bit true.

주 작성본은 build/p3a-ui/editor.sqlite3, revision 13을 유지했다. codec 정의 저장 검증만 독립 build/p3b-ui/editor.sqlite3에서 revision 2→3으로 수행했고, 이후 preview는 3을 유지했다. [화면](p3b-preview.png), [관측 기록](p3b-ui-observation.json).

기존 Schema 1.0/1.1/2.0은 보존하고 2.1 common/source-definition만 추가했다. 다른 앱의 수신·승인 지원을 자동 확장하지 않는다. P3-C 파생식, P3-D 시간/품질·원자성, P3-E 배열/중첩, P6 Bifrost 승인은 후속이다.

[사용·계약](../P3-B-PREVIEW.md) · [MVP 계획](../../MVP-PLAN.md).
