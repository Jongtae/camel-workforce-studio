# RFC: Topic Selection And Slice Gating For Workforce Runs

## Summary

이 RFC는 `commitment`가 topic을 자유롭게 창작하는 대신, 사전에 정의된 topic catalog에서 가장 작은 issue-ready slice만 고르게 하는 운영 규칙을 제안한다. 목표는 `camel-workforce-studio`가 `AI-Fashion-Forum`에 대해 실제로 가동 가능한 구현 단위만 선택하도록 만들고, 이미 다루고 있는 CRUD slice와 겹치지 않는 다음 후속 slice로 자연스럽게 이동하게 하는 것이다.
이때 선택 기준은 단순 백엔드 구현보다, threads와 Twitter처럼 실제로 쓰고 싶은 포럼 UX를 먼저 닫는 방향을 포함한다. 즉 `thread continuity`, `reply context`, `compact compose entrypoint`, `tag navigation`, `feed clarity` 같은 바로 체감되는 forum service slice를 우선하고, 불쾌감 감지나 고도화된 분석은 뒤로 미룬다.
무엇보다도 이 RFC의 전제는 **서비스 완성도를 먼저 닫고, 그 다음에 시뮬레이션과 고도화 토픽을 논의한다**는 점이다. 서비스가 아직 안정적으로 돌아가지 않는 상태라면 시뮬레이션 주제는 우선순위에서 제외하고, 실제로 쓸 수 있는 forum service slice를 먼저 닫는다.

## Problem

이 저장소는 반복적으로 다음 문제를 겪었다.

- `commitment`가 “현재 가장 큰 gap”을 찾는 과정에서 너무 넓은 topic을 만들기 쉽다.
- `society`와 `core`는 강한 역할 프롬프트 때문에 상위 주제로 자연스럽게 수렴한다.
- issue-ready gate는 topic이 정해진 뒤에야 동작하므로, topic drift 자체를 막지 못한다.
- 결과적으로 `사용자 불쾌감 감지`, `운영 대시보드`, `behavior analysis` 같은 고도화 토픽이 먼저 나오고, 기본 CRUD나 최소 실행 루프가 뒤로 밀린다.
- 또한 forum 서비스 품질을 높이는 UI/UX slice가 backend slice에 밀려, 실제 사용감이 먼저 좋아지는 방향으로 토론이 열리지 않는다.
- 서비스가 충분히 닫히기 전에는 시뮬레이션이나 행동 해석이 먼저 전면에 등장해, 실제로 쓸 수 있는 forum service 개선이 늦어진다.

## Goals

- `commitment`가 새 topic을 invent하지 않게 한다.
- topic 생성 공간을 bounded slice로 제한한다.
- issue 발급은 실제로 바로 구현 가능한 최소 slice에만 허용한다.
- 고도화 토픽은 epic candidate 또는 later slice로 남긴다.
- 서비스 완성도가 먼저 닫히기 전에는 시뮬레이션, 불쾌감 감지, 행동 해석을 우선하지 않는다.
- threads/twitter식 forum UX를 참고한 사용성 slice가 우선 선택되도록 한다.
- service-first rule: forum service UX slice와 기본 운영 slice를 먼저 닫고, 그 뒤에 시뮬레이션/고도화 토픽을 논의한다.

## Non-Goals

- `topic catalog`를 CAMEL core protocol로 만들지 않는다.
- 모든 future roadmap을 자동 분해하지 않는다.
- issue sizing을 완전히 자동화하지 않는다.

## Proposal

### 1. Topic Catalog As The Only Selection Space

`commitment`는 `docs/topic-catalog.md`에 정의된 항목 중 하나만 고른다.  
이 단계에서 topic을 새로 창작하지 않는다.
topic catalog는 backend-only backlog가 아니라 forum UX slice를 포함할 수 있다.

### 2. Soft Guidance As A Hint, Not A Constraint

`soft guidance`는 여전히 유지하지만, 다음 의미만 가진다.

- 지금 우선해야 할 운영 단계
- 피해야 할 고도화 범위
- issue-ready slice의 우선순위 힌트

soft guidance는 catalog를 대체하지 않는다.

### 3. Separate Issue-Ready Gate

topic 선택과 issue 발급 사이에 별도 gate를 둔다.

- topic이 catalog 안에 있어도 issue-ready가 아니면 발급하지 않는다.
- 기존 issue와 중복되면 continuation comment 또는 draft only로 멈춘다.
- 발급 가능한 경우에만 GitHub issue를 만든다.

### 4. Role Responsibilities

- `commitment`: catalog 안에서 bounded slice 하나를 선택한다.
- `society`: action/state/memory contract 같은 실행 요구사항을 정리한다.
- `core`: 최소 구현 단위와 API/persistence boundary, UI/UX와 연결되는 서비스 진입점도 닫는다.
- `operator`: 최소 관측/개입 API를 정의한다.
- 시뮬레이션은 서비스 완성도와 기본 운영 루프가 닫힌 뒤에만 논의한다.

## Why This Fits CAMEL

이 제안은 CAMEL의 다음 철학과 잘 맞는다.

- role separation and role-based collaboration
- explicit memory and workflow reuse
- verifier / terminator 분리

다만 `topic catalog` 자체는 CAMEL 문서에 직접 등장하는 개념은 아니다.  
이건 CAMEL의 memory/workflow/verification 철학 위에 얹는 **애플리케이션 레벨 orchestration policy**다.

CAMEL references:

- [CAMEL paper](https://arxiv.org/abs/2303.17760)
- [CAMEL memory docs](https://docs.camel-ai.org/key_modules/memory)
- [CAMEL workflow memory manager](https://docs.camel-ai.org/reference/camel.societies.workforce.workflow_memory_manager)
- [CAMEL response terminator](https://docs.camel-ai.org/reference/camel.terminators.response_terminator)
- [CAMEL verifiers](https://docs.camel-ai.org/reference/camel.verifiers.base)

## Recommended Workflow

1. Build context from the target repo.
2. Load `topic catalog` and `soft guidance`.
3. Run `commitment` once.
4. If the selected slice is catalog-compliant and issue-ready, continue to the selected workforce.
5. If the run resolves to a duplicate or closed issue, emit continuation comments instead of a fresh issue.
6. Only issue bounded implementation slices.

## Adoption Notes

If this RFC is adopted, the next cleanup steps are:

- Keep `docs/topic-catalog.md` small and explicit.
- Keep `commitment` focused on selection, not broad roadmap creation.
- Keep issue-ready checks separate from topic selection.
- Treat large or forward-looking ideas as epic candidates, not immediate issue targets.
- Treat simulation and behavior-analysis topics as post-service-completion follow-ups, not first-wave issues.
- Encourage forum-service UX slices when they are the smallest useful issue-ready unit.

## Open Questions

- Should `topic catalog` stay static, or should it be curated per project stage?
- Should issue-ready gating be role-specific or shared across all workforces?
- When a topic is too large for one slice, should the system auto-split or just defer?
