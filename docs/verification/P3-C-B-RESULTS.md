# P3-C B 제한 sqrt·clamp 검증 결과

2026-10-18 실행. [기계 판정](p3cb-validation.json), [수용 경로](p3cb-acceptance.json), [설계](../P3-C-BOUNDED-MATH.md).

| 구분 | 판정 |
|---|---|
| 새 Python 검증 | 17/17 통과. 7개 독립 decimal oracle 및 네 접근 profile 수렴의 subtest 포함 |
| 기존 P1~P6 수용·회귀 | 701/701 통과 |
| 기존 A07 | 39/39 통과 |
| 독립 Java mapping/CLI | 64/64 통과: core 62 + gates 2 |
| 격리 브라우저·SQLite·preview·승인·파일 발행 | 17/17 수용 체크 통과. 이 체크에는 위 Python 회귀 실행 판정도 포함하므로 숫자를 별개 테스트로 합산하지 않는다 |

브라우저에서 sqrt → clamp 그래프를 새로 작성하고 2.11.0으로 저장했다. 객체 프로퍼티에 결과를 매핑하고 다시 로드해 bounds를 확인했다. 가상 HEX 09 00은 UInt16 9 → sqrt 3 → clamp [1, 2]의 2 → Double 2로 평가했다. loss.clamp와 uncertain을 표시하고 before/bounds/after/branch를 읽을 수 있는 문장으로 확인했다. 미리보기 전후 SQLite 작성본과 revision은 동일하다.

부정 검증은 음수 sqrt, 단위/타입 불일치, 경계 역전, old graph version의 새 op, 고정 precision/rounding 위반, 포트·참조·근거·순환, 결측/bad/freshness/skew, exact cast의 근사 거부를 포함한다. 동일 bounds·분수/음수 bounds·단위 변환 후 clamp도 검사했다. 원래 네 접근 profile의 가상 9는 모두 sqrt 3으로 수렴했다. 실제 프로토콜 통신 검증은 아니다.

Bifrost는 새 그래프 JSON을 독립 검증하고 별도의 두 등록 키로 승인·파일 릴리스를 발행했다. UI 재조회에서도 published 상태를 확인했다. activation은 not-performed이며 Java가 가상 수치 계산을 수행한 것으로 해석하지 않는다.

기존 schema 62개와 fixture 462개 파일의 SHA-256은 A14 기준과 같다. 새 schema 2종만 추가했고 workspace envelope 2.0.0·SQLite 테이블은 유지했다. 이전 fixture 저장 → 새 fixture 저장 → 재시작 복원, stale CAS/잘못된 범위 거부의 원자성, preview DB 바이트 무변경을 검사했다. 검사한 product source pins와 최종 파일의 해시도 일치한다.

검증은 기존 이미지 tyr-a14:20261018에 --network none, loopback DNS, cap-drop ALL을 적용하고 별도 Linux 로컬 SQLite/registry로 실행했다. 기존 A14 OS 네트워크 부정 대조를 다시 수행한 것은 아니며, 이번 launcher의 Docker inspect와 browser localhost-only 요청 기록을 근거로 격리 범위를 명시한다. 호스트 Windows 전체 방화벽·실제 현장 PoV는 미수행이다. 장치 통신·외부 SQL·쓰기 실행·Muninn 활성화는 제외한다.

원본 실행은 build/p3cb/20261018-013634에 보존했다. 초기 harness 오류·의도적 중단을 포함한 실행 이력은 [run history](p3cb-run-history.json)에 구분했다. 기존 A07/A14 판정을 덮어쓰지 않았다. [화면](p3cb-preview.png), [새 테스트 로그](p3cb-new-tests.log), [Java 로그](p3cb-java-tests.log), [기존 회귀](p3cb-regression.json), [A07](p3cb-a07.json).

현장 PoV는 실제 문서/설정 파일과 담당자의 독립 정답을 받아 수렴·오매핑·누락·손실·검토 시간을 비교하는 별도 단계다. 이번 수용 결과를 vendor importer/native 배치·현장 수요·운영 활성화 검증으로 확대하지 않는다.
