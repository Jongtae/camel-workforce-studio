# Topic Catalog

이 카탈로그는 `commitment`가 새 topic을 자유 창작하지 않고, 지금 단계에서 바로 issue-ready로 발급 가능한 가장 작은 slice만 선택하도록 돕기 위한 운영 기준이다.

## Post-CRUD Follow-up Slice

이 카탈로그는 이미 issue `#295`로 다루고 있는 basic CRUD 범위를 넘어서, 그 다음에 바로 이어질 수 있는 가장 작은 후속 slice를 고르기 위한 운영 기준이다.

### TC-1. Agent action execution contract
- Issue Topic: Agent action execution contract
- Goal: AI agent가 post/comment/react/lurk/silence를 어떤 request/response 계약으로 수행하는지 고정한다.
- Preferred Workforce: society
- Why now: action loop의 최소 실행 계약이 아직 완전히 닫히지 않았기 때문이다.
- Excludes: 감정 해석, 불쾌감 감지, 고급 상태 추론

### TC-2. State snapshot and memory writeback minimum
- Issue Topic: State snapshot and memory writeback minimum
- Goal: action 후 state snapshot과 memory writeback의 저장 계약을 닫는다.
- Preferred Workforce: society
- Why now: 행동 재현 가능성과 replay 가능성을 확보해야 하기 때문이다.
- Excludes: 고급 reflection policy, 장기 선호도 최적화

### TC-3. Internal/external ingestion envelope
- Issue Topic: Internal/external ingestion envelope
- Goal: forum 내부 콘텐츠와 외부 콘텐츠를 하나의 입력 계약으로 합친다.
- Preferred Workforce: society
- Why now: content consumption merge가 action/state loop의 최소 기반이기 때문이다.
- Excludes: sentiment inference, 불쾌감 감지, 추천 고도화

### TC-4. Agent batch execution minimum
- Issue Topic: Agent batch execution minimum
- Goal: agent batch가 실제로 실행되고 최소 상태 전이가 일어나도록 한다.
- Preferred Workforce: core
- Why now: 초기 운영 가능한 시스템의 실제 가동 기준을 먼저 확보해야 하기 때문이다.
- Excludes: moderation analytics, operator dashboard, advanced intervention

### TC-5. Minimal operator visibility API
- Issue Topic: Minimal operator visibility API
- Goal: 운영자가 최소 지표만 조회할 수 있는 read-only API를 만든다.
- Preferred Workforce: operator
- Why now: 운영 가능한 시스템인지 확인하는 최소 관측면이 필요하기 때문이다.
- Excludes: full analytics suite, policy experimentation platform, advanced tuning

### TC-6. Basic auth and access control minimum
- Issue Topic: Basic auth and access control minimum
- Goal: 최소한의 접근 제어와 인증 계약을 닫는다.
- Preferred Workforce: core
- Why now: 기본 운영 slice 이후에 안전하게 확장하려면 가장 작은 보호막이 필요하기 때문이다.
- Excludes: role-based policy platform, advanced permissions matrix, enterprise SSO

## Selection Rules

- commitment는 새 topic을 invent하지 말고 위 항목 중 하나만 고른다.
- 가장 넓은 질문보다 지금 바로 issue-ready한 가장 작은 slice를 우선한다.
- 불쾌감 감지, 감정 해석, 고도화된 사회 행동 해석은 이 카탈로그의 범위를 벗어나면 다음 epic 또는 later slice로 넘긴다.
