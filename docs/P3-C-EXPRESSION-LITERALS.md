# P3-C E 숫자·명시적 단위 상수 작성

## 범위와 기존 기능 재사용

P3-C D의 미완료 숫자 값 식을 제한적으로 확장한다. `[pressure] * 0.1`, `[pressure] + quantity(3, "kPa")`를 작성한다. 기존 2.7 constant source와 2.15 value graph, 05/06 그래프·매핑, 09 Decimal 가상 평가/시간·품질/손실, 13 Bifrost 파일 승인·발행을 재사용한다. 정준 계약과 Java 수신 코드는 변경하지 않는다. 일반 차원 분석, 단위 자동 변환, 조건식, 온도 delta, 그래프 간 참조는 별도 미완료다.

## 작성 계약

기존 API의 네 필드는 compiler 1.0.0으로 계속 처리한다. 선택적 `compilerVersion`은 1.0.0 또는 1.1.0이다. 17 화면의 새 작성 기본은 1.1.0, 기존 원문 다시 열기는 저장된 버전을 선택한다. 이전 editor-contracts/1.0.0은 그대로 보존하며 로컬 recipe 1.1.0만 추가한다. Bifrost에는 recipe나 식 문자열을 전송하지 않는다.

1.1의 bare decimal은 단위 `1`이다. 부호는 숫자 앞에서만 허용한다. `quantity(숫자, "단위")`는 유한 단위 목록 1/Pa/kPa/bar/rpm/1/s/N.m/mN.m/Cel/K를 사용한다. 기존 숫자 문법과 64자 제한, 4096자/512토큰/64연산/중첩32단계를 적용한다. 단위가 다른 덧셈과 압력+bare number는 거부한다. 기존 선형 단위 산술 제한이 그대로 적용되므로 Cel/K를 선언할 수 있어도 온도 delta 산술을 지원한다는 뜻은 아니다. 임의 문자열/함수/코드 eval은 지원하지 않는다.

## 생성 소스와 근거

수식 literal을 canonical decimal 문자열로 정규화한다. normalize의 기본 Decimal context에 의해 긴 숫자가 반올림되지 않게 문자열 기반으로 trailing zero를 제거한다. compiler version/graph ID/equipment/value/unit의 SHA256 앞 40자리로 exprlit 소스 ID를 만든다. graph별 소유권으로 재사용하며 값·단위 변경 시 새 소스가 생긴다. 구 소스나 이력은 자동 삭제하지 않는다. 기존 동일 ID가 내용까지 같을 때만 원래 capturedAt과 함께 재사용한다. ID 충돌 또는 수동 변경은 오류로 거부하고 덮어쓰지 않는다.

생성 소스는 synthetic, read, already-engineered이며 근거 첫 줄 label에 값·단위를 넣고 note에 graph/compiler를 남긴다. capturedAt은 최초 선언 생성 시각이며 가상 샘플 시각이나 장치 관측 시각이 아니다. compile은 임시 선언을 만들어 보여줄 뿐 DB를 쓰지 않는다. apply는 재컴파일 시 생성한 선언과 graph/recipe를 같은 workspace revision CAS 트랜잭션에 저장한다.

기존 2.7 numeric constant 계약은 Int32/Double만 제공하므로 소스 타입은 Double, 값은 숫자 문자열을 사용한다. 기존 preview의 Decimal 해석을 그대로 이용하며 native IEEE 바이너리 저장이나 실제 PLC의 반올림을 보장하지 않는다. 2.15 산술 연산은 Decimal을 출력한다. 단일 상수 identity는 소스 Double 타입을 유지한다. divide/sqrt의 34자리 half-even 및 최종 cast 손실을 기존 경로에서 확인한다. 긴 원문 숫자를 몰래 잘라내지 않는다.

## 로컬 저장·변경 탐지

새 1.1 recipe는 generatedSources와 literalOrigins(sourceId/start/end/value/unit)를 저장한다. 기존 expression_recipes 테이블에 append-only로 기록하며 별도 테이블·기존 행 재작성·schema version 승격은 없다. source context pin에 생성 상수를 포함해 값/타입/단위 수정 시 stale로 표시한다. transaction 실패 시 소스·그래프·recipe 전부 rollback한다. compile/조회/기존 DB 열기는 migration을 만들지 않는다. 생성 상수는 사용자 가상 입력·freshness/skew 대상에 포함하지 않는다.

## 수용과 현장 PoV 경계

합성 4개 PLC fixture는 actual150/target50 kPa에서 `(actual-target)*0.5+quantity(3,"kPa")=53 kPa`를 독립 정답으로 둔다. 타입/단위 거부, 음수·정규화, 원문 위치, 분모 0/결측/손실, ID 충돌, 이력 보존, 구 compiler와 SQLite 왕복을 검사한다. Linux network none 환경의 브라우저→Python→SQLite→독립 Java 검증/두 키 승인/파일 발행을 재검증한다. 실제 현장 계수·단위 정답, 검토 시간과 재사용성, vendor native 배치/설정 export, Windows 호스트 전체 방화벽 검증은 미수행 현장/운영 과제로 분리한다. 장치 통신·외부 SQL·쓰기 실행·runtime 활성화는 계속 제외한다.
