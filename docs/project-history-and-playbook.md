# Project History And Playbook

이 문서는 `camel-workforce-studio`를 왜 만들었는지, 어떤 시행착오를 거쳐 현재 구조에 도달했는지, 앞으로 누가 이어받더라도 같은 맥락에서 운영할 수 있도록 남기는 운영 기록이다.

## 1. 왜 이 저장소를 따로 만들었나

이 저장소는 범용 CAMEL 예제를 만들기 위해 분리한 것이 아니다.
원래 목적은 `AI-Fashion-Forum` 본 repo 바깥에서 더 긴 컨텍스트를 다루는 companion decision workspace를 만드는 것이었다.

핵심 문제는 다음 세 가지였다.

- GitHub issue
- GitHub PR
- external report
- progress log

이 셋을 단일 prompt로는 안정적으로 다루기 어려웠다.
그래서 이 저장소는 아래 흐름을 담당하도록 설계되었다.

`Context Builder -> Workforce -> Handoff`

즉, 이 저장소의 역할은 제품 본체 구현이 아니라, 여러 truth source를 읽고 다음 논의와 handoff를 구조화하는 것이다.

## 2. 구조가 어떻게 바뀌어 왔나

초기에는 `society`, `operator`, `core`, `bridge` 중심의 토론 스크립트였다.
하지만 단순히 topic을 던지는 방식으로는 "지금 무엇을 누구와 먼저 논의해야 하는가"를 안정적으로 정하지 못했다.

그래서 `commitment workforce`가 추가되었다.
이 단계에서 프로젝트는 단순 토론기보다, 다음 논의 트랙을 고르는 메타 orchestration 구조로 바뀌었다.

이후 실제 운영에 맞추기 위해 다음 변화가 들어갔다.

- 표준 산출물 도입: `decision.md`, `handoff.md`, `next_questions.md`, `round_summary.md`, `full_report.md`
- `Context Builder` 도입: GitHub issue / PR / reports / progress / source repo 상태를 정규화
- `run_studio.py` 도입: context build + commitment + next workforce 체이닝
- `commitment` 단순화: CAMEL workforce 대신 single decision agent로 변경
- run ledger 도입: 어떤 workforce run이 어떤 GitHub issue를 만들었는지 `context/history/run-ledger.jsonl`에 기록
- issue readiness gate 도입: `--create-issue`여도 제목, 요약, 완료 기준, 다음 액션이 충분하지 않으면 발급을 건너뜀

## 3. 왜 CAMEL memory보다 명시적 handoff를 택했나

중간에 CAMEL Workforce의 shared memory / workflow memory를 쓸지 검토했다.
결론은 "보조 수단으로는 가능하지만 기본 구조로는 아니다"였다.

이 프로젝트에서 더 중요한 truth source는 CAMEL 내부 상태보다 다음 문서들이었다.

- `decision.md`
- `handoff.md`
- `context/workflow-inputs/*.md`
- GitHub issues
- GitHub PRs
- external reports
- progress logs

즉, 이 저장소는 memory-first보다 `source-of-truth-first` 구조로 운영한다.

## 4. workforce 역할이 어떻게 정리됐나

### commitment

현재 상황에서 가장 중요한 gap을 찾고, 다음 workforce와 topic을 정한다.
핵심 질문은 항상 이것이다.

`지금 무엇이 막혀 있고, 그걸 풀기 위해 누가 다음에 생각해야 하는가?`

### core

내부 키는 `core`지만 의미는 development 팀이다.
역할은 mock-to-service 전환, API, migration, backend execution loop 등 실제 개발 결정을 다루는 것이다.

### operator

단순 forum 구축이 아니라 운영자 조직이다.
역할은 다음과 같다.

- 컨텐츠 자정
- 모니터링
- moderation / policy
- 기능 개선 포인트 도출

### society

지금은 추상 사회이론 토론이 아니다.
AI-Fashion-Forum의 실제 agent backend 요구사항을 도출하는 팀이다.

핵심 범위는 다음과 같다.

- `post/comment/react/lurk/silence`
- stateful characteristic
- belief / memory / mutable axes / relationship state
- internal forum content consumption
- external web content consumption
- memory writeback
- trace / snapshot / event / forum artifact

## 5. 가장 큰 시행착오

### 시행착오 1. commitment가 너무 추상적이었다

처음에는 commitment가 `society`를 고르더라도 topic을 "사회적 갈등" 같은 추상 주제로 내보내는 경향이 있었다.
이건 AI-Fashion-Forum의 실제 구현 의도와 어긋났다.

해결:

- source repo intent를 context pack에 넣었다
- commitment prompt에 routing guardrail을 넣었다
- society topic이 backend/action/state와 무관하면 후처리로 교정했다

### 시행착오 2. society가 action loop만 말하고 끝나는 경향

처음 society는 방향은 맞았지만, 종종 `action loop`만 강조하고
다음 요소를 약하게 다루었다.

- state model
- content consumption
- required backend artifacts
- API/backend contract

해결:

- Society Modeling Lead 응답 형식을 강제했다
- task router가 society task를 재작성할 때 위 요소를 보존하도록 바꿨다
- final synthesis 후처리에서 빠진 항목을 보강했다

### 시행착오 3. CAMEL quality check가 너무 쉽게 replan으로 빠졌다

특히 society에서 quality check가 자주 걸렸다.
초기에는 "action과 state 연결 부족", "artifact 필요성 부족" 같은 이유였다.

해결:

- 각 action에 `trigger condition`, `state read`, `state write`, `artifact`, `successful outcome`를 직접 요구
- artifact에는 `necessity`를 직접 요구
- state transition에는 "그래서 다음 행동이 어떻게 달라지는가"를 쓰게 함

## 6. 현재 운영 기준

현재는 아래 문서를 같이 보는 것이 기본 운영 루틴이다.

- [`ai-fashion-forum-readiness-scorecard.md`](/Users/jongtaelee/Documents/camel-workforce-studio/docs/ai-fashion-forum-readiness-scorecard.md)
- [`iteration-log.md`](/Users/jongtaelee/Documents/camel-workforce-studio/docs/iteration-log.md)
- [`workforce-handoff-contract.md`](/Users/jongtaelee/Documents/camel-workforce-studio/docs/workforce-handoff-contract.md)
- [`shared-memory-evaluation.md`](/Users/jongtaelee/Documents/camel-workforce-studio/docs/shared-memory-evaluation.md)

실전 활용 판정 기준은 readiness scorecard를 따르고, 튜닝 과정은 iteration log에 누적한다.
issue 발급 이력과 현재 처리 상태는 run ledger와 `context/normalized/issue_execution_history.md`를 함께 본다.

## 7. 다음 사람이 이어받을 때의 운영 팁

1. 먼저 `AI-Fashion-Forum`의 현재 의도와 최근 변경을 읽어라.
   이 저장소는 일반론보다 source repo intent에 맞게 움직여야 한다.

2. commitment 결과가 맞는 workforce를 고르는지 먼저 보라.
   downstream 출력이 이상할 때 원인은 commitment topic인 경우가 많다.

3. society 품질을 볼 때는 아래 다섯 요소가 동시에 나오는지 보라.

- action loop
- state model
- state transitions
- content consumption
- required backend artifacts

4. CAMEL quality check에 막히면 vague한 prompt를 늘리지 말고, 누락된 필드를 더 직접적으로 강제하라.

5. 장기 기억이 필요해 보여도, 먼저 문서 handoff를 강화하라.
   이 저장소는 CAMEL memory보다 explicit artifact를 우선한다.

## 8. 추천 문서 갱신 규칙

앞으로도 구조를 바꾸면 아래 문서를 같이 갱신하는 것이 좋다.

- `agent.md`와 `CLAUDE.md`: agent 작업 가이드. 둘 중 하나를 바꾸면 반드시 다른 하나도 함께 갱신
- 큰 운영 기준 변경: 이 문서
- 활용 가능성 판정 변경: `ai-fashion-forum-readiness-scorecard.md`
- 튜닝 실행 기록: `iteration-log.md`
- workforce 전달 규약 변경: `workforce-handoff-contract.md`

이렇게 유지하면 GitHub wiki가 없어도, 레포 안에서 충분히 운영 지식이 축적된다.
