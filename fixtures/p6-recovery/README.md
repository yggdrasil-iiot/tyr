# P6 recovery fault scenarios

`fault-matrix.json`은 합성 중단/손상/GC 기대 결과다. `scripts/test_p6_recovery.py`는 기존 p4b workspace로 실제 SQLite/파일/프로세스 종료를 재현하며 기존 계약·fixture SHA를 확인한다. Java MappingPublicationTest/MappingCrashProbe는 독립 기존 valid wire fixture와 임시 등록 키로 실제 별도 JVM 종료·서명 검증·복구·과거 릴리스 보존을 검사한다. `scripts/p6r/run.ps1`은 기존 p4ab 검토/병합 fixture를 이용해 Chromium부터 발행/복구/GC까지 격리 검증한다. 새 vendor 메모리맵이나 실제 현장 정답은 아니다. 장치·외부 SQL·쓰기 실행은 제외한다.
