# Shared Memory Evaluation

이 저장소는 CAMEL `share_memory`를 선택적으로 실험할 수 있지만, 기본 구조는 explicit handoff 중심으로 설계한다.

## Current Recommendation

- 기본값: `share_memory` 비활성화
- 선택적 사용: `python3 scripts/requirement-debate/debate.py --share-memory ...`
- 우선순위: `handoff.md`와 `context pack`이 먼저, CAMEL memory는 나중

## Why It Can Help

- 한 라운드 안에서 worker들이 같은 맥락을 보게 해 반복 설명을 줄일 수 있다
- `commitment` 같은 메타 토론에서 역할 간 공통 상황 인식이 더 잘 맞을 수 있다
- round-level coherence를 높일 가능성이 있다

## Why It Is Not The Default

- 이 프로젝트의 핵심 컨텍스트는 GitHub issue, external report, progress log, handoff 문서처럼 바깥에 있는 truth source다
- 내부 memory는 실행 후 무엇이 남았는지 사람이 검토하기 어렵다
- workforce 간 전달 문제는 memory보다 handoff contract 부재에서 더 크게 발생한다
- 장기 컨텍스트는 workflow memory보다 파일 기반 산출물과 normalized context가 더 투명하다

## Safe Usage Boundary

- 써도 좋은 경우:
  - 같은 workforce 안에서 역할 간 반복 맥락 전달이 많은 경우
  - 짧은 라운드에서 논의 일관성을 개선하고 싶은 경우
- 아직 미루는 것이 좋은 경우:
  - workforce 간 handoff contract가 불완전한 경우
  - 외부 source of truth를 먼저 정규화해야 하는 경우
  - 결과를 재검토 가능하게 남기는 것이 더 중요한 경우

## Workflow Memory

`workflow memory`는 현재 기본 범위 밖이다.

- 이유: 이 저장소는 장기 기억을 CAMEL 내부 상태보다 `decision.md`, `handoff.md`, `context/workflow-inputs/*.md` 같은 명시적 문서로 유지하려고 한다
- 향후 조건:
  - handoff contract가 안정화된 뒤
  - context builder가 충분히 갖춰진 뒤
  - 문서 기반 흐름과 충돌하지 않는다는 것이 확인될 때
