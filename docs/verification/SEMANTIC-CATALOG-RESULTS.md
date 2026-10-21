# P6 registry 전체 의미 카탈로그 수용 결과

2026-10-18. 구성된 한 registry의 교차 스트림·전체 보존 이력에 한정한다. 현장 PoV는 미수행이다.

| 구분 | 최종 실측 |
|---|---:|
| 새 Python 카탈로그 검사 | 15 / 15 |
| 기존 Python·fixture 회귀 | 960 / 960 |
| Python·fixture 합계 | 975 / 975 |
| 매핑 관련 Java | 138 / 138 (신규 catalog 11 + 기존 127) |
| 격리 브라우저·HTTP·SQLite·실제 Java CLI 연계 | 27 / 27 |

Java는 MappingPublicationTest 133, LogicalStructureTest 3, MappingGateTest 2다. 실패·오류·스킵 0이다. 이 수치를 Bifrost 리포 전체 테스트 수로 간주하지 않는다. Python은 새 15, 산술 28, 평가 35, 복구 13, import 58, graph 39, structure 30, math 17, A07 39, 기본 수용 701의 합계다.

## 확인한 경로

기존 네 PLC 정의의 그래프 작성/SQLite 저장/재개방·가상 산술/손실 preview·stale revision 거부·전체 근거 export·독립 Java 검사·두 등록 키 승인·파일 발행·상태 조회·ZIP 파일 hash·평가 양식을 재검증했다. 카탈로그 계약 일치와 현재 작성본 충돌을 화면에서 확인했고, 손상된 역사 파일의 조회 거부·복원 후 재검증·SQLite 무변경을 확인했다.

독립 Java 시험은 실제 파일 registry 두 스트림에서 같은 계약 재사용, 역할 충돌, 이름/URI 분리, 다른 스트림 발행 후 기존 승인으로 발행 우회 불가, 중첩 말단 변경, unheaded 역사, 기존 충돌 역사 표시/새 승인 차단, pending 복구, 손상 거부를 검증했다. 별도 CLI 프로세스 사이의 카탈로그 결과도 동일했다.

기존 canonical 계약 파일 74개(스키마 73개 포함)·fixture 511개·평가 계약 1개의 SHA가 유지됐다. 현재 스키마 74개는 Týr/Java 사본이 바이트 동일하다. 새 SQLite 테이블·migration은 없고 기존 DB 사본의 재개방 전후 행이 동일했다. 원래 사용자 DB/registry는 수정하지 않았다.

## 재현과 증거

최종 실행: `build/catalog/20261018-081700`. `scripts/catalog/run.ps1`은 기존 로컬 이미지·network=none·DNS localhost·cap-drop ALL·no-new-privileges·읽기 전용 입력 archive를 사용했다. image ID와 실행 인자는 별도 JSON에 보존했다. Python의 loopback guard와 브라우저 요청 검사를 실제 OS namespace 격리 안에서 실행했다. 호스트 Windows 전체 방화벽이나 실제 장치 격리를 수용한 결과가 아니다.

- [최종 연계·전체 입력 SHA](catalog-full-acceptance.json), [검증 소스/JAR SHA](catalog-validation-pins.json)
- [Java 집계](catalog-java-summary.json), [신규 Python 로그](catalog-python-tests.log), [기본 수용](catalog-baseline.json), [A07](catalog-a07.json)
- [기존 계약·fixture 보존](catalog-compatibility.json), [이전 입력 SHA](catalog-baseline-pins.json)
- [격리 인자](catalog-docker-arguments.json), [컨테이너 설정](catalog-docker-inspect.json), [이미지](catalog-image-inspect.json)
- [실행 이력](catalog-run-history.json), [최초 시험 실패](catalog-initial-failure.json)

최초 실행은 테스트가 SQLite 작성본을 복원한 뒤 브라우저 revision을 새로 읽지 않고 평가 양식을 요청해 실패했다. 시험에 reload를 추가한 뒤 전체 실행을 다시 수행했다. 두 실행 사이 변경 파일은 scripts/catalog/accept.py 하나이며 제품 코드·CAS 규칙은 완화하지 않았다. 최종 입력 SHA는 현재 제품/fixture/검증 코드와 일치한다. 새 기능만 재시도한 부분 성공으로 완료 판정하지 않았다.

Windows 매핑 관련 Java 클래스 실행 시간은 약 915초였다. 전 역사 파일/서명을 반복 재검증하는 제한 MVP이며 이 결과를 처리량/SLA 수용으로 해석하지 않는다. 256 릴리스·4096 URI·보고서 4MiB를 넘는 입력은 거부한다. 대량 성능·배포/스토리지·운영 IAM·외부 rollback anchor는 별도 검증이다.

별도 합성 시연은 http://127.0.0.1:59782/ 의 13 화면이다. 새 DB에는 기존 arithmetic fixture만 저장했고, 합성 검증 registry의 공개 키/서명/파일 이력을 별도 복사했다. 개인 키는 시연 DB/registry에 저장하지 않았다. 카탈로그 조회와 URI별 타입·단위·역할 표시를 실제 앱 브라우저에서도 확인했다.

현장 URI 소유권·물리적 의미 동등성·의미 개정 정책·검토 시간/오매핑률·vendor native/export 정답·여러 registry 연합은 미완료다. 장치 통신·외부 SQL·쓰기 실행·runtime 활성화는 계속 제외한다.
