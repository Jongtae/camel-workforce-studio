# Iteration Log

이 문서는 AI-Fashion-Forum 실전 활용 가능 수준에 도달할 때까지 workforce 튜닝 기록을 남긴다.

## Iteration 1

- 날짜: 2026-03-26
- 실행 흐름: `run_studio.py --repo Jongtae/AI-Fashion-Forum --source-dir /Users/jongtaelee/Documents/AI-Fashion-Forum --rounds 1`
- 관찰:
  - commitment는 `society`를 안정적으로 고름
  - commitment topic은 backend/action/state 중심으로 교정됨
  - society는 올바른 topic을 받았고 첫 task도 action loop 관점으로 시작함
  - 다만 첫 subtask가 `action loop` 중심으로 좁아지며 `content consumption`과 `required backend artifacts`가 상대적으로 약해질 위험이 보임
- 점수:
  - Commitment 안정성: 4/5
  - Workforce 역할 일치: 4/5
  - 입력 컨텍스트 활용: 4/5
  - 다음 액션 연결성: 3/5
  - 출력 구조 품질: 2/5
  - 총점: 17/25
- 판정:
  - 방향은 실전 보조 수준에 근접했지만, society first-task decomposition이 아직 좁아서 구조 품질이 부족함
- 다음 조치:
  - society task router와 Society Modeling Lead가 action loop뿐 아니라 state model, content consumption, backend artifacts를 계속 유지하도록 강화

## Iteration 2

- 날짜: 2026-03-26
- 실행 흐름:
  - `commitment_debate.py --context-pack context/workflow-inputs/commitment.md --rounds 1`
  - `society_debate.py --handoff <latest commitment handoff> --context-pack context/workflow-inputs/society.md --rounds 1`
- 적용한 조치:
  - source repo intent를 context pack에 추가
  - commitment가 society를 고를 때 backend/action/state topic으로 교정되도록 후처리 validation 추가
  - society task router와 Society Modeling Lead에 `state model`, `content consumption`, `required backend artifacts` 보존 규칙 추가
- 관찰:
  - commitment topic이 안정적으로 backend requirement 문장으로 고정됨
  - society는 commitment handoff를 받아 backend topic으로 시작함
  - society 첫 task는 여전히 `action loop` 중심으로 좁아지는 경향이 있지만, 최소한 forum action/stateful backend 방향은 유지됨
  - next workforce handoff와 issue 초안으로 이어질 기반은 확보됨
- 점수:
  - Commitment 안정성: 4/5
  - Workforce 역할 일치: 4/5
  - 입력 컨텍스트 활용: 4/5
  - 다음 액션 연결성: 4/5
  - 출력 구조 품질: 3/5
  - 총점: 19/25
- 판정:
  - `실험적 실전 사용 가능` 기준(18점 이상) 도달
  - 다만 society first-task decomposition은 여전히 더 조일 여지가 있음
- 남은 리스크:
  - society 첫 subtask가 action loop 중심으로 좁아질 수 있음
  - CAMEL quality-check/replan 비용이 긴 실행에서 다시 튀어오를 수 있음
