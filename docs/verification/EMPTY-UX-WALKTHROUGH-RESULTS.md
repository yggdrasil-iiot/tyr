# 빈 작업본·가상 엑셀 UX 검증 기록

2026-10-20. **빈 작업본에서 자료 준비 → 객체 선택 → 연결 → 검증 → 검토·로컬 제출까지 브라우저 직접 수행 완료**. 현장 자료/작업자 PoV와 서명 승인·발행은 별도다. 장치 통신·외부 SQL·쓰기 실행·운영 활성화는 제외했다.

## 직접 수행한 경로

1. 별도 SQLite revision0, 설비/소스/객체가 없는 상태에서 기존 이전 API로 백업 후 빈2.0 작업본을 명시적으로 시작했다.
2. pump-line 가상 펌프 설비와 pump-melsec MELSEC 논리 연결을 등록했다. 논리 연결은 문맥 정의이며 실제 접속하지 않는다.
3. CUA 파일 선택으로 한글 열 memorymap.xlsx를 가져왔다. 열 대응 표의 제안을 명시적으로 적용·재해석했다. D1000 압력/D1001 운전/D1002 알람을 초안으로 채택하고 원본·셀 위치·원본 열·주소/타입/폭/단위를 검토한 뒤 ready로 저장했다.
4. baseline-pressure 상수100 kPa와 external-pressure 외부 제공자 참조를 저장했다. 표현식 없음인데 빈 원문이 required로 저장을 막던 문제를 재현·수정하고 실제 저장 성공을 확인했다.
5. pump-object@1.0.0의 actual/running/target/baseline/external을 각각 작성·저장했다. 첫 저장 후 같은 객체를 유지하고 다음 프로퍼티를 빈 폼에서 연속 추가하는 동작을 확인했다.
6. 기존20 레코드 매핑 없이 pump-results@1.0.0 결과 스키마를 독립 작성했다. record_id는 NULL 불가 String 키, target은 원시 Double/kPa이며 두 필드의 키·타입·단위를 검증·저장했다.
7. 객체 선택에서 설비·모델을 선택하고 배열 연결로 이동했다. 독립 스키마가 이어졌고 아래 연결을 검증·저장했다. 고정 템플릿 empty-kit@1.0.0, 배열 empty-array@1.0.0이 생성됐다.
8. 검증 단계에서 작성 폼이 접히고 저장된 연결·변환 요약이 표시됐다. 레코드 표에 PUMP-1/900, PUMP-2/950을 입력하고 PLC HEX b004/0100, 외부 값101을 입력했다. 상수100은 정의에서 가져왔다.
9. 두 객체·good·손실0건을 확인했다. 두 번째 키를 PUMP-1로 바꾸자 이전 결과가 무효화됐다. 재검증에서 record.duplicate-key, 출력0/전체 차단과 한국어 수정 안내가 표시됐다. PUMP-2로 복구하고 good 결과를 다시 확인했다.
10. 가상 입력 empty-start-final r1을 SQLite에 저장했다. 새 브라우저 탭에서 저장 시나리오를 선택하자 HEX/Typed/두 레코드가 복구됐고 재검증도 동일한 두 객체·good·손실0건이었다. 검토 화면에서 현재 배열·프로퍼티별 연결·변환과 세션 미리보기 통과 상태를 확인했다. 제출 화면은 record:empty-array@1.0.0을 선택했다.
11. empty-start-offline / 스트림 empty-start-line / 제안자 operator로 로컬 제출 파일을 저장하고 Bifrost 재검증·상태 조회를 실행했다. **accepted=true, findings=[], awaiting-approval**이다. 승인·발행 완료를 의미하지 않는다.

| 프로퍼티 | 입력과 변환 | PUMP-1 | PUMP-2 |
|---|---|---|---|
| actual | 공통 PLC D1000 UInt16 little decode1200 ×0.1 → Double/kPa | 120 | 120 |
| running | 공통 PLC D1001 UInt16 little decode1 → Int32/1 | 1 | 1 |
| target | 행별 target Double/kPa ×0.1 → Double/kPa | 90 | 95 |
| baseline | 공통 상수 Double/kPa → cast Double | 100 | 100 |
| external | 공통 외부 값 Double/kPa → cast Double | 101 | 101 |

## 반영한 UX

- 빈 작업본 시작 안내·시작 버튼. 기존 migrate/CAS/백업 계약 재사용, 자동 마이그레이션 없음.
- 설비 없는 가져오기 사전 안내와 설비/PLC 논리 연결 등록 경로.
- 한글/사용자 열 대응 표와 명시적 적용·재해석. 고급 JSON 유지, 원본/미해석 열 자동 삭제 없음.
- 파일·설비·열 대응 조건 변경 시 이전 해석/선택 무효화.
- 가져온 소스의 초안/완료 목록과 개별 원본 근거 검토 경로. 자동 ready 처리 없음.
- 같은 객체에 프로퍼티 연속 추가와 객체 선택 이동.
- 표현식 없음일 때 필수 입력 제거·비활성화, 기타 형식일 때 원문 필수.
- 초기 작업본 로딩 중 메뉴 비활성화.

변경은 frontend/empty-start.js, index 스크립트 등록, server 정적 경로 등록이다. 기존 계약·SQLite DDL·승인 권한 변경은 없다. 앞선 operator-ux의 검증 전용 요약/행 표/결과 무효화/문맥 유지도 이번 새 작업본에서 사용했다.

## 검증과 증거

기존 가져오기58 + 독립 스키마13 + 배열30 = **101/101**. 기존 계약/fixture918개 SHA와 Bifrost JAR를 유지했다. 이번에 전체 Python/Java 단위 테스트를 재실행했다는 의미는 아니다.

별도 임시 DB의 contract_check.py도 동일 XLSX→객체/독립 스키마/배열/미리보기/Java accepted=true를 통과했다. 보완 계약 검사이며 위 브라우저 직접 검증과 구분한다.

직접 작성 DB: build/empty-ux-20261020/editor.sqlite3, workspace revision16. 설비1/연결1/소스5, 작성 의미 모델1+배열 생성 모델1, 독립 스키마1, 배열1/템플릿1. 가상 시나리오·제출본은 별도 테이블에 저장한다.

- 원본 XLSX SHA256: 0ec4e05d57f8b06d518435ced04cf086d646dea2816558c65cc8b8c7b44f199d
- 제출 제안 SHA256: 0369d1b68972348a45ecc305634719e66c81a8d2ebe3a504fb9157e0863d2531
- 제출 묶음 SHA256: 0893d7ffd3e4edec4371308ae5a2a8f70dc65c654d33272a78a75d1636234bb6
- Bifrost JAR SHA256: 1811e443b1f6993d94a3e2f536f08648124ce7f0229cc2cc0cd54ac3ee16ea0d

같은 build 폴더에 before/ 수정 전 코드, memorymap.xlsx·PNG, revision0 백업, Python 로그, integrity.json, direct-results.json, progress-summary.json, empty-ux-preview.jpg/DOM, empty-ux-final.jpg/DOM을 보존한다. contract-bundle은 보완 계약 검증 전용이다.

## 재개와 현장 PoV

http://127.0.0.1:59794/ 저장본에서 검증 → 객체 배열 가상 검증 → empty-array → 저장된 가상 입력 empty-start-final로 재검증할 수 있다. 검토·제출 → Bifrost 제출·릴리스에서 저장된 제출본을 확인한다.

실제 현장 문서의 열/주소/단위 정답, vendor native export 배치, 작업자의 과제 수행 시간·오선택률·검토 편의는 별도 현장 PoV다. 합성 직접 조작 성공으로 현장 적합성이나 운영 동시 취득을 입증하지 않는다.
