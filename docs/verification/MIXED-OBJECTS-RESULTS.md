# 여러 소스 객체 매핑 — 오프라인 수용 결과

2026-10-18. 장치 통신·외부 SQL·쓰기 실행·runtime 활성화는 제외했다. 실제 현장 PoV는 미수행이다.

## 최종 검증

- **Python·fixture 고유1,165/1,165**: 기존 unit406 + 기존 record30 + 기존 P7 fixture701 + 신규 mixed28. `build/mixed-objects/20261018-142324-c0f4d227/mixed-results.json`의17 suite 전부 통과, `regression.json` 701/701. 그 실행의 mixed27은 이후 Boolean record 슬롯 사례를 포함한 `python-final-mixed.log`의28로 대체하여 합산했다. 동등한 timezone instant 수용/실제 위조 차단을 보완한 동일 사례는 `python-clock-focus.log`로 확인했고 중복 계산하지 않았다.
- **Java 고유219/219**: 전체 package에서 기존 Publication133을 포함한 회귀 통과 후 최종 package86(Logical3/CrossGraph18/Mixed17/Records15/Lifecycle18/Templates13/Gate2)으로 새17 검사와 현재 JAR을 확인했다. 중복 클래스 실행은 합산하지 않았다. `build/mixed-objects/java-logs/`의 Maven 로그·8개 JUnit XML. 실제 registry에 발행한 후, standalone 검증은 통과하는2.7 일반 외부 값 downgrade도 승인에서 record-field.history-conflict로 차단했다.
- **브라우저·HTTP·SQLite·실제 Java 연계33/33**: `build/mixed-objects/20261018-143934-1fad723f/mixed-results.json`. 프로퍼티별4소스 계열·DB2필드 입력창 공유·단위/스케일/cast/정밀도 손실·출처 즉시 표시·읽기 전용 비교/preview·plan 변조/stale CAS·신규 소스/객체/template/application 원자 저장·중복/0건/bad DB/bad PLC/stale 입력·별도 scene 저장/CAS/재개방/재생/stale 관리·기존19 재사용과20 호환·source→record proof closure·두 키 서명 승인·불변 발행/상태 조회. 브라우저 JS 오류0, localhost 외 요청0, evidence private key0.
- Docker input archive/driver/seed는 readonly, network=none, cap-drop=ALL이다. 원본 seed SQLite는 backup으로 복제하여 이전 행/스키마와 revision을 보존했다. 최종 브라우저가 사용한 JAR SHA는 아래 최종 파일과 같다.

## 보존과 바이너리

`mixed-objects-baseline-pins.json`의 기존819파일 SHA를 유지했다(contracts88=87schema+README, fixtures728, evaluation1, editor2).2.21 source/proposal/common 및 object/scalar preview-scenario5개를 추가하여 현재92schema가 있다. 기존 schema를 수정하지 않았다. Týr↔Bifrost resource↔최종 JAR의92schema bytes 및 Java mapping compiled class bytes가 일치한다.

최종 bifrost-gates.jar SHA256: `7f16fbf29f9ab8db0e2e56d95e900932097af48507dcad41ef037150bcef43d6`.

## 검증 의미와 화면 QA

기본 fixture는 PLC1200×0.1→120, raw DB950×0.1→95, 숫자 상수100, 외부101, String 상수 LINE-A를 하나의 객체로 조립한다. golden 수치 기대값을 preview 결과로 덮어쓰지 않는다. DB 필드는 기존 record template의95를 다시0.1배 하는 것이 아니라 원본950를 사용한다.

브라우저 사례는 기존 baseline 프로퍼티에 별도 DB pressure 필드를 연결하여, target/pressure2필드가 같은 result-set 입력을 공유하도록 검증했다.123450Pa→123.45kPa→Double의 정확한 binary64 값과 loss.precision을 uncertain으로 표시한다. 동일 pinned record의 서로 다른 snapshot은 graph/객체 전체에서 차단한다. 기본값은 필드 NULL에만 적용하며0건 레코드는 scalar값으로 만들지 않는다.

최종 screenshot의 프로퍼티별 PLC/DB 필드/상수/외부 출처, 정확한 cast와 ≈ 표시, 긴 정밀도 진단 줄바꿈을 시각 확인했다. 원본 record/schema/evidence와 template pin은 발행 closure에 포함하지만 가상 행·scene은 발행하지 않는다.

## 별도 로컬 시연

http://127.0.0.1:59789/ · 21 여러 소스 객체 매핑. `build/mixed-objects-ui/`에 최종 검증 DB revision4·public-key registry·불변 제출본을 복제했다. 기존59788 및 다른 DB/registry는 변경하지 않았다. Docker 내부의 로컬 submission path handle만 재배치하고 workspace revision/body를 보존했다(`relocations.json`). private key는 복제하지 않았다.

원본 mixed-scene은 revision3의 stale 검증 자료로 남겼다. 별도 복제 DB에서 현재 revision4에 명시적으로 재평가한 새 mixed-scene-current를 저장했다. 해당 scene을 선택해 불러오기→객체 미리보기로 재현할 수 있다. 시나리오 저장은 workspace와 이미 발행된 release를 변경하지 않았다.

마지막 clock 비교 보완은 `python-clock-focus.log`와 새 로컬 서버의 `demo-http-final.json`에서 검증했다. Z/+00:00/+09:00이 같은 instant이면 수용하고 실제400ms 시각 변경은 거부한다. 두 HTTP preview 후 workspace가 같고 publicationState=published인 것도 확인했다. 기존 브라우저가 사용한 동일 timestamp 입력의 의미는 유지된다.

## 사전 실패와 수정

새 source schema를 기존2.7 oneOf의 external-value 분기로 구성하도록 초기 생성기를 정정했고, API allowlist/실제 request 변수 연결을 사전 점검에서 보완했다. 처음 고정 oracle의 baseline은 원본 상수 선언100으로 바로잡았다. 첫 browser driver는19의 JSON sourceRef option을 ID 문자열로 선택하여 실패했으며 실제 저장 형식으로 수정했다. 실패 run `20261018-142246-4b305931`은 보존하고 통과 수에 합산하지 않았다. 이후 shared-record 입력·visible 출처·긴 진단 줄바꿈 QA와 최종 JAR run을 분리해 확인했다.

## 현장 PoV 및 후속 범위

미완료: 실제 의미·단위·계수 정답, DB key/NULL 안정성·조회 시각과 PLC 시각의 정합성, vendor/provider export, 소비자 계약, 작업자의 작성/검토 편의와 오류율. 타입/단위 일치만으로 실제 의미가 같다고 인증하지 않는다. per-binding/graph 시간 정책은 객체 전체 원자성이나 서로 다른 프로퍼티 간 skew 보장이 아니다. 자동 join/집계·array fan-out/broadcast·cross-equipment 결합·native DB 타입 전체·실제 커넥터/SQL/쓰기/운영 활성화는 구현 범위에서 제외했다.
