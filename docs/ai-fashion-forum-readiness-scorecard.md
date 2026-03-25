# AI-Fashion-Forum 활용 가능 판정표

이 문서는 `camel-workforce-studio`를 AI-Fashion-Forum 실전에 붙여도 되는지 판단하기 위한 기준선이다.
목표는 "그럴듯한 토론"이 아니라 "반복 실행 가능한 의사결정 보조"다.

## 활용 가능 기준

실전 활용 가능으로 판단하려면 아래 조건을 만족해야 한다.

1. 총점 25점 만점 중 18점 이상
2. `commitment 안정성`과 `다음 액션 연결성`은 각각 4점 이상
3. 같은 iteration에서 나온 산출물이 바로 다음 workforce나 GitHub issue 초안으로 옮겨질 수 있어야 함

## 평가 항목

### 1. Commitment 안정성
- 0점: workforce 선택이나 topic이 자주 틀어지고 프로젝트 의도와 무관한 방향으로 감
- 1점: workforce는 맞지만 topic이 자주 추상적이거나 흔들림
- 2점: 대체로 맞지만 handoff 가능한 수준으로는 불안정함
- 3점: 대체로 올바른 workforce와 topic을 선택함
- 4점: source repo intent를 근거로 일관되게 올바른 workforce와 topic을 선택함
- 5점: 반복 실행에서도 거의 흔들리지 않고, 변경 이유까지 명확히 설명함

### 2. Workforce 역할 일치
- 0점: society/operator/core가 자주 역할을 벗어남
- 1점: 역할 이름은 맞지만 실제 출력은 섞임
- 2점: 방향은 맞지만 일반론으로 자주 흐름
- 3점: 역할에 맞는 출력이 주로 나옴
- 4점: 대부분의 출력이 각 workforce 고유 역할에 맞음
- 5점: 반복 실행에서도 역할 정체성이 매우 선명함

### 3. 입력 컨텍스트 활용
- 0점: repo 상태, handoff, context pack을 거의 반영하지 않음
- 1점: 일부 키워드만 되풀이함
- 2점: source repo 정보를 언급하지만 결정으로 잘 연결하지 못함
- 3점: repo 상태와 handoff를 근거로 사용함
- 4점: source repo intent, 최근 상태, latest workforce state를 모두 일관되게 반영함
- 5점: 입력 컨텍스트를 근거로 선택 변경 이유까지 명확히 설명함

### 4. 다음 액션 연결성
- 0점: 읽고 나서 무엇을 해야 할지 모르겠음
- 1점: 방향은 있으나 issue나 handoff로 옮기기 어려움
- 2점: 일부 실행 가능 항목이 있으나 정리가 부족함
- 3점: handoff나 issue 초안으로 옮길 수 있는 수준
- 4점: 다음 workforce 또는 개발/운영 이슈로 바로 분해 가능함
- 5점: 반복 실행 가능한 운영 루프로 바로 편입 가능함

### 5. 출력 구조 품질
- 0점: 섹션 누락이 많고 품질이 들쭉날쭉함
- 1점: 형식은 있으나 핵심 섹션이 자주 비어 있음
- 2점: 기본 형식은 지키지만 요구한 정보가 누락됨
- 3점: 주요 섹션이 대체로 채워짐
- 4점: Action Loop / State Model / State Transitions / Content Consumption / Required Backend Artifacts 같은 핵심 구조가 안정적으로 나옴
- 5점: 실행 품질과 구조 품질이 모두 안정적임

## 실전 사용 판정

- `18점 이상`: AI-Fashion-Forum 의사결정 보조에 실험적 실전 사용 가능
- `21점 이상`: 실전 사용 추천
- `17점 이하`: 튜닝 지속 필요

## 현재 목표

현재 목표는 `AI-Fashion-Forum 의사결정 보조에 실험적 실전 사용 가능` 수준인 18점 이상이다.
