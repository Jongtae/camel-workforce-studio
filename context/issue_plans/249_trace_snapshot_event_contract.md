# Issue #249: trace/snapshot/event replay 저장 계약 정의

## 현재 상태 (society 토론 결과 기반)

### 식별된 Backend Artifacts
- **trace**: 각 행동(post/comment/react)의 상태 변화 추적
- **snapshot**: 특정 행동 후 상태(characteristic, belief, relationship state) 저장
- **event**: 행동 트리거 시 메타데이터 저장
- **stored action**: 행동 이력 저장 및 재읽기
- **forum artifact**: 포스트/댓글 데이터 객체

---

## 최소 Scope (먼저 고정할 것)

### 1. action → trace → snapshot 관계 정의
```
action request
  ↓
stored action (행동 저장)
  ↓
trace (상태 변화 기록) + reference to snapshot_v1
  ↓
snapshot (상태 스냅샷 저장)
  ↓
event (메타데이터 기록)
```

### 2. Snapshot Version / Timestamp Rules
- snapshot_id: uuid or incremental hash
- snapshot.created_at: ISO 8601 timestamp
- snapshot.action_id: reference to the triggering action
- snapshot.version: semantic version for state schema changes
- snapshot.fields: {characteristic, belief, memory, relationship_state, mutable_axes}

### 3. trace와 event의 관계
- trace: full state change record (what changed, from what to what)
- event: lightweight payload for analytics (event_type, affected_fields, delta)
- event.snapshot_id: backref to the snapshot created

### 4. Content Consumption (internal/external) 통합
- internal_consumption_event: post/comment/react observed → state update
- external_consumption_event: web content ingested → state update
- both: memory writeback path는 동일 (characteristic, belief 업데이트)
- storage: 동일한 trace/snapshot/event 저장소 사용

---

## Acceptance Criteria

### Schema Definition
- [ ] action_request schema (id, type, agent_id, timestamp, payload)
- [ ] stored_action schema (extends action_request, outcome fields)
- [ ] trace schema (action_id, state_before, state_after, snapshot_id)
- [ ] snapshot schema (id, created_at, agent_id, version, state fields)
- [ ] event schema (id, trace_id, snapshot_id, event_type, delta_fields)
- [ ] internal/external consumption event schema

### Replay Validation
- [ ] 특정 snapshot을 기준으로 이후 trace들을 재생했을 때 최종 상태 일치 확인
- [ ] internal + external event를 혼합했을 때 state merge 검증
- [ ] trace의 state_before/state_after가 연속성을 유지하는지 확인

### Documentation
- [ ] JSON schema examples for each artifact type
- [ ] state transition diagram (action → trace → snapshot → event 흐름)
- [ ] internal/external content merge 규칙 문서화

---

## Expected Outcome

이후 moderation, agent loop, analytics가 재사용할 수 있는 **재생 가능한 저장 계약** 확정.

---

## Dependencies
- society 워크포스 action/state/memory 설계 (완료)
- #248 갈등 상황 규칙 (선택적, 미포함)

---

## Created
2026-03-28 09:30 (from camel-workforce-studio autonomous decision)
