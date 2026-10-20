# P3-C D 제한 수식 작성 → 기존 정준 DAG

## 선택한 미완료 범위

MVP-PLAN의 일반 식 작성 공백 중 유한한 작성 문법만 구현한다. 계산기나 실행 언어를 새로 만들지 않는다. 사용자가 입력한 수식 원문은 로컬 작성 근거이며 canonical 값 정의는 기존 2.15 value-graph다. 일반 차원 분석·복합/역단위·온도 delta·cross-value-graph endpoint와 현장 PoV는 미완료다.

## 지원 문법

```
expression = term (('+' | '-') term)*
term       = primary (('*' | '/') primary)*
primary    = '[' sourceId ']' | '(' expression ')'
           | sqrt '(' expression ')'
           | clamp '(' expression ',' decimal ',' decimal ')'
           | linear '(' expression ',' decimal ',' decimal ')'
decimal    = '-'? ('0' | nonzeroDigit digit*) ('.' digit+)?
```

곱셈/나눗셈이 덧셈/뺄셈보다 우선하며 같은 우선순위는 좌결합이다. 소스 ID는 기존 ASCII ID를 명시하며 이름·주소를 추측하거나 최신 버전을 임의 선택하지 않는다. 중복 ID는 모호성 오류로 거부한다. 숫자는 clamp 범위와 linear 계수/offset 위치에서만 허용한다. 독립 상수는 기존 constant source로 정의하고 `[id]`로 참조한다. unary 부호를 값 식에 직접 쓰거나 임의 함수·문자열·속성 접근·인덱싱·댓글·비교/조건식·SQL·코드 eval을 실행하지 않는다.

입력 4096자·512 토큰·64 연산·괄호/함수 중첩 32단계·decimal 인수 64자·소스 closure 128개·노드당 근거 256개·컴파일 graph 256KiB·작성본 2MiB의 제한이다. 제한 초과는 truncation 없이 거부한다. 숫자 지수/NaN/Infinity/선행 0/생략 소수점 표기는 받지 않는다.

## 계약과 재사용 경계

컴파일러는 기존 schemaVersion 2.15.0 graph의 add/subtract/multiply/divide/sqrt/clamp/linear/identity만 만든다. root ID는 항상 `expr-result`이고 중간 노드는 postorder로 결정한다. 명명된 입력 포트·원본 근거·source id/version·타입·known 단위와 그래프 SHA·참조 소스 context SHA·원문 위치를 보고한다. 입력은 준비된 읽기 가능한 numeric scalar만 받으며 array/Boolean/String/unknown 단위·다른 설비·view 부모의 준비/읽기 오류를 거부한다. 원본 evidence가 없는 노드는 만들지 않는다.

단위/타입 정책과 가상 계산은 기존 bounded arithmetic·source view·preview와 독립 Bifrost 검증을 재사용한다. add는 같은 허용 선형 단위, subtract는 같은 Pa/kPa/bar/1, multiply는 한쪽이 1, divide는 분모 1 또는 같은 단위 비율이다. sqrt는 무차원 1, clamp는 입력과 같은 단위의 범위, linear는 기존 이중 변환 제한을 따른다. 자동 단위 변환은 없고 필요하면 기존 그래프 편집기에서 명시적으로 작성한다. divide/sqrt의 34자리 half-even과 0 분모·근사·clipping·최종 cast·시각·품질은 기존 09 preview가 검사한다.

Bifrost는 수식 원문을 파싱하거나 실행하지 않는다. 기존 2.15 wire DAG를 독립 검증하고 기존 2.9 승인/릴리스를 사용한다. 두 앱 사이 공유 코드나 새 canonical 계약은 없다. 기존 receiver JAR를 수정하지 않아도 새 컴파일 결과를 검증·승인·파일 발행할 수 있다. 손으로 만든 잘못된 컴파일 결과도 receiver가 거부하는 음성 control을 둔다.

## 화면·API·SQLite

17 화면에서 설비·새 graph ID·원문을 입력하고 컴파일 결과의 각 연산·타입·단위·원문 범위를 확인한다. 저장하면 05 그래프·06 객체 매핑·09 preview·13 제출에서 기존과 같이 사용한다. 기존 수동 그래프의 덮어쓰기는 거부한다. 수식으로 만든 그래프만 명시적으로 재컴파일할 수 있다. root를 제외한 중간 노드는 재컴파일 시 바뀔 수 있으므로 외부 binding이 제거된 중간 노드를 참조하면 기존 참조 검사가 거부한다.

`POST /api/expression-compile`와 `/api/expression-apply`는 `{revision,graphId,equipmentInstanceId,expression}`만 받는다. Origin/Editor 헤더·workspace revision CAS를 유지한다. compile은 읽기만 하고 apply는 같은 snapshot에서 다시 컴파일해 기존 workspace 저장을 사용한다. 소스나 다른 창이 변경됐으면 409로 다시 검토하게 한다.

첫 명시적 apply 때만 `expression_recipes(graph_id,revision,body)`를 같은 SQLite 트랜잭션에서 추가한다. 원래 workspace·migrations·submissions·scenario 행/버전은 보존한다. 기존 DB 재개방·compile·이력 조회만으로 schema를 바꾸지 않는다. 오류가 나면 새 테이블/recipe/workspace 변경이 함께 rollback된다. recipe당 512KiB·전체 이력 16MiB·최대 1000 revisions 제한을 넘으면 저장을 거부하며 기존 이력을 삭제/압축하지 않는다.

로컬 작성 계약은 editor-contracts/1.0.0/expression-recipe.schema.json이다. 원문·compilerVersion·DAG snapshot·graph SHA·source context SHA·원문 위치와 저장 revision을 append-only로 보존한다. canonical proposal에는 이 로컬 recipe를 넣지 않는다. 로컬 이력은 서명된 Bifrost 사실이 아니며 원본 source snapshot 전체를 복제한 저장소도 아니다.

GET /api/expressions는 latest recipe와 전체 이력을 읽고 current/stale/missing-graph를 구분한다. 현재 그래프 SHA와 직접/부모 source 정의·설비·참조 논리 연결 context를 비교한다. 소스의 표시 정보 변경도 보수적으로 stale로 표시할 수 있으며 이를 물리적 의미 변경으로 자동 판정하지 않는다. 자동 재컴파일/덮어쓰기는 없다. 과거 원문을 다시 열고 명시적으로 컴파일·저장해야 최신 계약과 일치한 것으로 표시한다.

## 수용과 현장 분리

[합성 fixture](../fixtures/expression/README.md) · [수용 결과](verification/BOUNDED-EXPRESSION-RESULTS.md). 실제 현장 용어/계수/단위 정답·운전 정책·문의/수정/재검토 시간·vendor native/export 검증은 별도다. 장치 통신·외부 SQL·쓰기 실행·runtime 활성화는 계속 제외한다.
