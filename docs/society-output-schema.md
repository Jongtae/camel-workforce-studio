# Society Output Schema

이 문서는 `society` workforce 결과를 구조화해서 다시 사용할 수 있게 만드는 계약이다.

## 목적

- `society` 논의 결과를 다음 workforce가 재사용할 수 있는 JSON/YAML 형태로 고정한다.
- AI-Fashion-Forum 쪽에서 `agent_seed`, `identity_update_rules`, `content_consumption_rules`, `state_model`을 재구성할 때 기준점으로 삼는다.
- `decision.md`에만 머무르지 않고, 기계가 읽는 계약 파일을 함께 남긴다.

## 생성물

- `context/normalized/society_output_contract.json`
- `context/schemas/society-output.schema.json`
- `context/schemas/society-output.template.yaml`

## 필드 의미

- `version`: 계약 버전
- `source_run_dir`: society run 결과 디렉터리
- `decision_path`: 원본 decision.md 경로
- `issue_title`: society가 도출한 작업 제목
- `summary`: 핵심 요약
- `acceptance_criteria`: 검증 가능한 완료 기준
- `technical_notes`: 구현 시 참고할 메모
- `open_questions`: 후속 논의가 필요한 질문
- `priority`: 우선순위
- `agent_seed.identity`: agent 정체성/초기 상태를 설명하는 원문 블록
- `agent_seed.memory_initial`: 초기 memory/writeback 규칙을 설명하는 원문 블록
- `agent_seed.characteristic`: characteristic 형성과 변화에 대한 원문 블록
- `action_loop`: `post/comment/react/lurk/silence` 중심 action loop
- `state_model`: characteristic, belief, memory, mutable axes, relationship state
- `state_transitions`: 다음 행동 선택에 영향을 주는 상태 전이
- `memory_writeback_rules`: 상태와 기억 업데이트 규칙
- `action_selection_links`: 행동별 state read / bias 연결
- `content_consumption`: 내부/외부 콘텐츠 소비 규칙
- `required_backend_artifacts`: trace / snapshot / event / stored action / forum artifact

## 사용 방식

`build_context.py`는 최신 `society` run이 있으면 위 계약을 JSON으로 다시 저장하고, workflow input에도 요약해 넣는다.

이후 다른 workforce는 `context/workflow-inputs/*.md`와 `context/normalized/society_output_contract.json`을 함께 읽어, 사회적 토론 결과를 바로 구현/운영 결정으로 연결한다.
