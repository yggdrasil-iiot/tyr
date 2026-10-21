# P3-E B 논리 구조·중첩·고정 구조 배열 수용 결과

2026-10-18 직접 실행. [기계 판정](p3eb-validation.json) · [설계](../P3-E-LOGICAL-STRUCTURES.md) · [fixture](../../fixtures/p3eb/README.md).

| 검증 | 결과 |
|---|---|
| 새 Python | 30/30. 네 profile 공통 객체 정답·중첩 다차원 배열·경로/인덱스/의미/타입/단위/깊이·결측·SQLite/API |
| 기존 P3-C B | 17/17 |
| 기존 A07 | 39/39 |
| 기존 P1~P6 | 701/701 |
| 독립 Java | 75/75: mapping/publication 70, CLI 2, 다차원/음수 하한/깊이·시그니처 3 |
| 최종 브라우저 UI | 20/20. 전체 회귀를 포함한 이전 full-run orchestration은 별도 23/23이며 중복 합산하지 않음 |

16개 가상 source 정의와 4개 target, 40개 전체 member/index 바인딩이 동일한 객체 정답으로 수렴했다. process 실제값/목표값/편차는 150/180/-30, 상태 false이고 modules는 [100/110/true, 220/210/true]다. source의 물리 배열 좌표와 target 논리 배열 좌표를 각각 명시한다. nested fixture는 음수 하한의 racks 안에 rank-2 slots를 가진 8말단이다.

브라우저에서 새 모델을 builder로 작성하고, 구조 배열의 중첩 pressure 실제값/목표값을 각 인덱스별로 source/array-element에 매핑했다. 재개방 시 선택을 유지했고, modules[2].pressure.actual의 temporalPolicy가 동명 modules[1] 멤버에 섞이지 않는지 확인했다. 모델 트리 자체의 readback도 확인했다.

전체 객체 oracle은 process.actual 150, modules[1] pressure 100/110, modules[2] pressure 220/210이다. 09 말단 preview에서도 원시 배열→요소 선택→Float32 decode→Double cast→220 결과를 확인했다. 객체/말단 preview는 workspace revision/body를 변경하지 않는다. 미매핑/결측/bad는 전체 result null과 진단 partialResult로 구분한다. source DataValue의 bad/stale 및 cast 손실 전파도 검사했다.

범위 초과/하한 미만·rank 오류·index 누락·없는/추가 멤버 경로·컨테이너 전체 매핑·전체 경로 중복·형제 ID 중복·semanticId의 단위/컨테이너 shape 충돌·깊이/확장 크기 제한을 검사했다. literal a.b 필드와 a→b 경로도 구분했다. 구버전 schema는 새 구조/경로를 거부한다. 과거 flat schema의 표현 한도는 새 제한을 소급하지 않고 유지했다.

Bifrost는 동일한 JSON wire data를 독립 Java 코드로 검증했다. 완전한 제안은 두 등록 키로 서명 승인·파일 발행하고 UI에서 published를 재조회했다. 중복/범위 초과/필수 말단 누락 등의 제안은 승인·발행 전에 거부했다. activation은 not-performed이며 native 값 수집이나 객체 계산 실행을 뜻하지 않는다.

기존 schema 64개와 fixture 파일 467개는 P3-C B 기준 SHA-256이 유지된다. 신규 2.12 schema 3개만 추가했고 Bifrost bundled copies와 바이트가 같다. workspace envelope 2.0.0·SQLite 테이블은 유지하며 자동 migration/행 재작성은 없다. 재시작 roundtrip, 이전 DB 개방 바이트 보존, stale CAS와 잘못된 index 저장의 원자 거부, read-only 객체 API를 확인했다.

실행은 기존 tyr-a14:20261018 이미지의 Docker --network none, loopback DNS, cap-drop ALL에서 했다. 실제 localhost 브라우저·Python·Java·SQLite/registry를 사용했으며 원본 사용자 DB는 건드리지 않는 별도 데이터로 검증했다. A14 OS 네트워크 부정 대조 자체를 다시 수행하거나 호스트 Windows 전체 방화벽을 검증한 것은 아니다.

전체 회귀 원본은 build/p3eb/20261018-020836, 화면 표시 보완 후 최종 UI 원본은 build/p3eb/20261018-021134이다. 두 실행의 차이는 신규 화면의 긴 경로 표 scroll containment와 UI harness/launcher뿐이다. Python/Java 수치·경로 로직, 계약, fixture data는 같다. 최종 UI 실행의 product pins는 현재 파일과 일치한다. [full 실행](p3eb-full-acceptance.json) · [최종 UI](p3eb-ui-acceptance.json) · [기존 회귀](p3eb-regression.json) · [새 테스트 로그](p3eb-new-tests.log) · [화면](p3eb-preview.png) · [초기 오류/수정 이력](p3eb-run-history.json).

vendor native UDT/DB offset·packing/alignment·BOOL/endianness·실제 export/ExtensionObject decoding과 현장 담당자의 독립 정답/시간 비교 PoV는 별도 미완료다. 장치 통신·외부 SQL·쓰기 실행·Muninn 활성화는 제외한다. 이 수용 결과는 bounded 논리 정준 모델의 오프라인 구현 범위이며 native array-of-struct 수집이나 현장 수요를 검증 완료로 확대하지 않는다.
