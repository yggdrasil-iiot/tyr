# P7 오프라인 수용 결과

A01~A16 중 14개 충족, A07·A14 부분 충족이다. 실제 현장 PoV는 미수행이다. 각 시험 ID는 [수용 기록](p7-acceptance.json)에 연결했다. 부분 충족을 전체 지원 성공으로 계산하지 않는다.

| ID | 시험 | 판정 | 근거·범위 |
|---|---|---|---|
| A01 | 네 접근의 공통 의미 수렴 | pass | 네 PLC 표현과 개별 접근 보존 |
| A02 | 다른 PLC의 같은 주소 | pass | 설비/연결 문맥이 다른 소스 유지 |
| A03 | 다른 이름·같은 의미 / 같은 이름·다른 의미 | pass | 명시적 의미 ID로 수렴·구분 |
| A04 | 주소 변경 | pass | 의미 유지와 전이 영향 재검토 |
| A05 | 스케일 변경 | pass | 타입이 같아도 읽기/쓰기 변환 영향 표시 |
| A06 | 진법·단위·타입 미확인 | pass | 초안 보존, 제출/수신 검증 차단 |
| A07 | 전체 워드·비트 view | partial | alias import·legacy 진단은 검증. 신규 2.x word/bit view 작성·발행 미지원 |
| A08 | 이미 변환된 태그 | pass | 단계 미확인·이중 변환 근거/거부 |
| A09 | 파일·상속·참조 누락 | pass | bounded template/alias 범위의 누락 표시. 실제 vendor 상속은 PoV |
| A10 | 독립 기준값 | pass | 값·타입·단위·품질·손실의 저장된 oracle |
| A11 | 검사·승인 뒤 파일 변경 | pass | 이전 결과/승인 재사용 거부 |
| A12 | 릴리스 일부 누락·변조 | pass | Bifrost 파일 소비 검증·HEAD 보존. 운영 적용 제외 |
| A13 | 동일 자료 재처리 | pass | 고정 입력·프로파일의 동일 결과 |
| A14 | 네트워크 차단 | partial | Python 외부 접속 차단/negative control 및 loopback API 통과. Java·브라우저 OS 전체 격리 미수행 |
| A15 | 미지원 행·속성 | pass | 미해석·원문 보존 및 처리 상태 |
| A16 | 동시 수정·오래된 기준 | pass | SQLite revision과 발행 base 충돌, 덮어쓰기 거부 |

## 실행 근거

- 기존 P1~P6: 701/701 통과. [개별 결과·입력 hash](p7-validation.json), [log](p7-validation.log).
- Bifrost mapping 수용 회귀: 47/47 통과, Maven offline BUILD SUCCESS. [log](bifrost-p7-tests.log). 기존 전체 reactor 회귀 기록은 P6 결과를 참조하며 P7에서 전체 reactor를 재실행했다고 주장하지 않는다.
- Python 외부 connect/connect_ex/DNS 차단 및 거부 negative control. loopback HTTP 허용. PC 전체 방화벽/Java/브라우저 격리는 미수행.
- [화면 관찰](p7-ui-observation.json): 네 PLC 접근·객체·그래프·매핑·이름/의미/단위/스케일 비교·가져오기 근거/미해석·읽기쓰기·검토·릴리스 조회. 가상 9600 → 150, 상수 110, subtract → 40, cast Double/kPa/good. 미리보기 revision 40 유지.
- [SQLite](p7-sqlite.json): 원본 P6 revision 39 보존, 복제본 설비 표시 이름만 저장해 40으로 재조회. migrations·시나리오 4·기준본 1·검토 2·제출 1의 전체 행 동일.

## 최초 오류와 재실행

최초 실행은 unittest 544개 중 543개 성공·로컬 HTTP 연결 중단 WinError 10053 한 건과 P1 105개 성공이었다. 최초 [JSON](p7-initial-validation.json)·[log](p7-initial-validation.log)를 보존했다. 제품·계약·fixture 변경 없이 실패 시험만 격리 재실행해 성공했다. 통합 runner에서 누락된 별도 P3-A CLI 52개도 추가 실행해 52/52를 확인했다. 최종 701개는 최초 성공 543 + 격리 재실행 1 + P1 105 + P3-A 52의 중복 없는 합계다. 단일 실행에서 701개가 모두 성공했다고 주장하지 않는다. [P3-A 결과](p7-p3a.json), [CLI log](p7-p3a.log). resume는 기존 코드 hash가 달라지면 runner 자체를 제외하고 거부한다.

## 패턴 카탈로그 해석

[p7-patterns.json](p7-patterns.json)의 current 14/14·gap-probe 8/8·planned 34는 기존 1.x/P2 카탈로그의 역사적 시험 분류다. gap 재현과 planned를 지원 성공으로 세지 않는다. 이후 P3~P6의 구현은 이번 701개 경로의 개별 회귀 ID로 평가한다. 이 오래된 카탈로그 숫자를 현재 지원률로 사용하지 않는다. native/nested 구조·추가 vendor 형식은 계속 후속이다.

## 화면 결함과 수정

짧은 화면에서 고정 사이드바 하단 10~13 메뉴가 viewport 밖으로 밀려 마우스 클릭할 수 없었다. 데스크톱 사이드바를 세로 스크롤 가능하게 보완하고 최종 브라우저에서 하단 메뉴 클릭을 재확인했다. CSS 수정 후 화면 관찰은 별도 증거이며 최초 회귀 실행의 입력 SHA와 최종 CSS SHA를 구분한다. 계약·backend·fixture는 수정하지 않았다.

## 현장 PoV

실제 파일·버전·개정본·독립 담당자·holdout 설비가 필요하다. 정답 대비 수렴/오매핑/누락/손실과 import·수정·문의·재검토 전체 시간을 측정한다. [절차·필요 자료](../P7-OFFLINE-ACCEPTANCE.md)를 따른다. 현장 정확도·시간 절감률·전체 vendor 지원·운영 활성화는 이번 결과로 주장하지 않는다.


![최종 화면: 스크롤 가능한 메뉴와 기존 릴리스/변경 작성본 구분](p7-offline.png)

[최종 artifact hash·버전](p7-final-artifacts.json).
