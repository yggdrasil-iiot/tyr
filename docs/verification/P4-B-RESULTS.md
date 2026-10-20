# P4-B 구현 및 검증 결과

2026-10-17. 실제 장치 통신·솔루션 접속·SQL·쓰기 실행은 제외했다.

## 구현 범위

- 계약 2.7.0: PLC·상수·솔루션 태그·외부 값의 scalar 접근 정의와 read/write/read-write 방향을 명시했다. 이전 계약 49개는 변경하지 않았다.
- 읽기: 기존 의미 모델·객체·그래프·변환·시각/품질 검증을 재사용한다. 상수는 정의값으로 평가하고, 솔루션/외부 값은 가상 Typed 입력으로만 평가한다. SQL은 실행하지 않고 원문을 보존한다.
- 쓰기: 의미 member → 목적지의 별도 write-definition을 저장한다. 명시적 변환, 타입·단위·근거·방향·중복을 검증한다. 읽기 변환의 자동 역변환은 없다. execution=excluded를 강제한다.
- 화면: 02 혼합 소스 편집, 09 가상 읽기 미리보기, 11 쓰기 정의 작성·저장·조회.
- SQLite: optional writes 컬렉션을 기존 workspace/CAS 저장 구조에 추가했다. 기존 imports 및 시나리오를 보존한다.

## 검증

신규 **62/62**, 기존 회귀 **530/530**, 합계 **592/592** 통과. 독립적인 기대 결과 oracle 9개를 포함한다. 근거는 [신규 검증 JSON](p4b-validation.json) 및 각 *-p4b-regression.json이다. 매핑 패턴 매트릭스의 planned/gap 항목은 통과 개수에 포함하지 않았다.

숫자·Boolean·String, Double 정밀도 손실, 문자열 공백 보존, 상수 덮어쓰기 거부, 외부 값 결측, 읽기 전용/쓰기 전용 방향, 잘못된 쓰기 타입·단위·참조·근거·중복, CAS·잘못된 저장의 원자성, 실행 API 부재를 검사했다. 순수 미리보기에서 socket/SQLite 접속을 차단하는 검사도 포함한다.

기존 P4-A DB revision 34를 backup으로 복제한 P4-B DB를 사용했다. 원본 workspace SHA-256은 기존 P4-A 관찰 기록과 일치한다. 기존 모든 컬렉션 항목, import 배치 2개, 시나리오 4개의 저장 내용이 유지됨을 읽기 전용 SQLite 조회로 대조했다.

P4-B DB revision 38: 설비 6, 연결 9, 소스 68, 의미 모델 6, 대상 객체 19, 그래프 13, 읽기 매핑 세트 19, import 배치 2, 쓰기 정의 2.

## 화면 저장·재조회 확인

1. revision 35: 가상 fixture 추가.
2. revision 36: 화면에서 상수 baseline 100 → 110 kPa 저장.
3. revision 37: 별도 PLC 쓰기 변환 factor 10 → 20 저장 후 새로고침·재조회.
4. revision 38: 외부 SQL에 앞 공백 2개와 뒤 개행/공백을 추가해 저장. 원문 그대로 SQLite·내보내기에 보존.

PLC 가상 바이트 9600 → UInt16 150 kPa, 상수 110 kPa, subtract 40 kPa, 최종 Double 40의 단계별 읽기 결과를 확인했다. 외부 가상 값 70 kPa는 good 70으로 평가하며 trace에 external-value/read/virtual-input-only와 SQL 원문을 남긴다. 상수는 가상 입력을 요구하지 않으며 관측 timestamp를 생성하지 않는다.

읽기 매핑은 fixture와 동일하게 유지됐다. 쓰기 factor 변경은 읽기 결과를 바꾸지 않았다. 미리보기 및 임시 패키지 생성 전후 DB workspace와 시나리오가 같았다. 내보내기 proposal 2.7.0과 별도 쓰기 문서 2개도 확인했다.

![가상 읽기 미리보기](p4b-read-preview.png)

![별도 쓰기 정의](p4b-write-definition.png)

전체 관찰 근거: [p4b-ui-observation.json](p4b-ui-observation.json).

## 잔여 범위와 해석

현재 UI DB에는 기존 초안의 source.not-ready, import.unresolved 및 mapping.input-unit-unknown-preserved finding이 남아 있다. 보존된 기존 미해결 항목이며 P4-B 완료가 이들을 승인하거나 운영 배포 가능한 상태로 바꾼다는 뜻은 아니다.

MP14/15의 bounded scalar subset을 부분 지원한다. 공급자 연결·폴링·vendor importer, 외부 배열/구조, 쓰기 숫자 평가·바이트 인코딩·승인·명령 전달·재시도·원자적 실행, fan-out 및 주소 범위 overlap 분석은 후속 범위다. 쓰기 접근 방향은 선언 가능한 capability이며 실행 권한을 부여하지 않는다.

설계: [P4-B-MIXED-SOURCES.md](../P4-B-MIXED-SOURCES.md). 범위 및 후속 단계: [MVP-PLAN.md](../../MVP-PLAN.md).
