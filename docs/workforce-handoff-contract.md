# Workforce Handoff Contract

이 저장소의 workforce는 긴 자유형 리포트만 남기지 않고, 다음 workforce가 바로 이어받을 수 있는 구조화된 handoff를 함께 남긴다.

## Required Sections

모든 `handoff.md`는 아래 섹션을 가진다.

### `Source Workforce`
- handoff를 만든 workforce key

### `Source Label`
- 사람이 읽는 workforce 레이블

### `Source Topic`
- 이번 실행의 원래 topic

### `Target Workforce`
- 다음에 이어받아야 할 workforce
- 아직 확정되지 않았으면 `TBD`

### `Next Topic`
- 다음 workforce가 그대로 사용할 수 있는 topic
- 아직 확정되지 않았으면 `TBD`

### `Why This Handoff`
- 왜 다음 workforce로 이어져야 하는지
- 이전 workforce의 어떤 결정이 다음 레이어에 영향을 주는지

### `Decisions Already Fixed`
- 다음 workforce가 다시 논쟁하지 말아야 하는 합의 사항

### `Open Questions For Target Workforce`
- 다음 workforce가 해결해야 할 질문

### `Constraints`
- 다음 workforce가 지켜야 할 제약

### `Relevant Evidence`
- `decision.md`, `full_report.md`, 외부 context pack 등 근거 위치

### `Do Not Re-litigate`
- 이미 결정된 전제를 처음부터 다시 토론하지 않기 위한 명시 규칙

## Artifact Set

각 실행은 아래 산출물을 같은 run 디렉터리에 저장한다.

- `full_report.md`
- `decision.md`
- `round_summary.md`
- `next_questions.md`
- `handoff.md`
- `metadata.json`

## Current Policy

- `commitment` workforce는 `Target Workforce`와 `Next Topic`을 반드시 채우는 첫 번째 생산자다.
- 다른 workforce도 handoff를 남기지만, target이 아직 확정되지 않았다면 `TBD`로 남길 수 있다.
- 외부 context의 source of truth는 CAMEL 내부 memory보다 `handoff.md`, `decision.md`, `context pack` 같은 명시적 문서가 우선이다.
