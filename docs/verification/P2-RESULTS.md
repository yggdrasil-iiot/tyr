# P2 실행 결과

초기 P2 기록이다. 최신 다중 프로퍼티 기능과 검증은 [확장 결과](P2-EXPANDED-RESULTS.md)를 따른다.

실행일: 2026년 10월 17일 Asia/Seoul
자동 시험 시각 UTC: 2026-10-17T00:10:05.884755+00:00
자동 시험: **14/14 통과**, 실패·오류 0, 종료 코드 0.
P1 회귀: **93/93 통과**, 종료 코드 0.
JavaScript 문법 검사: node --check frontend/app.js, 종료 코드 0.

## 자동 시험

[소스 해시와 결과](p2-validation.json)에 서버·화면·시험 파일 해시를 고정했다. 저장 직후 파일 해시를 재대조했다.

네 접근·동일 의미의 저장과 SQLite 재열기, stale revision 409와 기존 데이터 보존, null 접근 초안 저장·제출 제한, 없는 문맥·잘못된 스키마·설비 불일치 거부, 의미 단위 변경의 매핑 불일치, 수동 근거 패키지 검증, 로컬 API GET/PUT, 다른 origin/Host 거부, 장치 연결 경로 없음, 지원하지 않는 다중 멤버/변환의 손실 없는 거부를 확인했다.

## 브라우저 직접 검증

빈 SQLite에서 UI로 다음을 직접 작성했다.

- 설비 4개, 논리 연결 4개.
- AB 심볼, S7-1500 OPC UA, S7-300 DB, MELSEC 디바이스 소스 각 1개.
- motor-actual-speed 의미 1개, Double/rpm, measurement, 범위 0~3000.
- 네 매핑. MELSEC은 linear factor=0.1, offset=0과 cast를 저장했다.
- 의미 검색과 기존 항목 재열기에서 입력 필드를 확인했다.

서버 프로세스를 종료하고 같은 DB로 새 프로세스를 시작한 뒤 브라우저를 다시 열어 revision 20, 소스 4개·매핑 4개, MELSEC 계수 0.1 복원을 확인했다.

두 번째 창의 revision 20에서 첫 창 저장으로 revision 21을 만든 뒤, 오래된 창의 저장이 충돌 안내로 차단되고 입력값이 유지되는 것을 확인했다. DB에 충돌 검증용 항목은 저장하지 않았다.

AB 심볼을 null/draft로 바꿔 저장했을 때 source.draft와 mapping.source-not-ready가 화면에 나타났다. 심볼과 ready를 복구한 revision 23에서는 차단 항목이 없었다.

[저장된 네 매핑 화면](p2-browser.png)을 캡처했다. 좁은 브라우저 패널에서도 폼과 목록이 한 열로 표시되는 반응형 레이아웃을 확인했다.

## 완료 판정

MVP-PLAN.md P2의 수동 작성·저장·재조회·재시작 복원·동시 편집 충돌 검출을 충족한다. 실제 장치 통신은 제외한다. 모든 브라우저 자료는 synthetic 수동 선언이다.

P2는 단일 멤버 의미·단일 연결 매핑과 linear/cast 작성에 한정한다. 원본 importer, 값 preview, 전체 변경 검토 화면과 실제 Bifrost 승인은 각 후속 단계다. 다른 앱과 공유 코드를 추가하지 않았고 Git 초기화·커밋·push도 수행하지 않았다.
