# Topic Catalog

이 카탈로그는 `commitment`가 새 topic을 자유 창작하지 않고, 지금 단계에서 바로 issue-ready로 발급 가능한 가장 작은 slice만 선택하도록 돕기 위한 운영 기준이다.
핵심 원칙은 **서비스 완성도를 먼저 닫고, 그 다음에 시뮬레이션이나 고도화를 논의하는 것**이다. 따라서 이 카탈로그는 실제로 쓸 수 있는 포럼 서비스 slice를 먼저 닫는 데 집중하고, 시뮬레이션, 불쾌감 감지, 고급 행동 해석은 서비스가 닫힌 뒤에만 다룬다.

## Operator Hub Completion Slices

이 섹션은 운영 도구가 만들다 만 것처럼 보이지 않도록, operator hub의 첫인상과 연결 구조를 먼저 닫기 위한 slice들이다. 여기서는 시뮬레이션보다 운영 도구의 완성도가 우선이다.

### TC-1. Replay viewer last viewed anchor persistence minimum
- Issue Topic: Replay viewer last viewed anchor persistence minimum
- Goal: replay viewer가 마지막으로 본 run, 패널, 스크롤 anchor를 기억하고 다시 열릴 때 같은 지점으로 복원한다.
- Preferred Workforce: ux
- Why now: 운영자는 replay를 이어서 봐야 할 때가 많아서, 가장 작은 복원 단위부터 닫아야 맥락이 끊기지 않는다.
- Excludes: 복잡한 차트 시스템, 상세 인사이트 엔진, 행동 해석 고도화, 전체 재생 경험 재설계

### TC-2. Replay viewer state restore minimum
- Issue Topic: Replay viewer state restore minimum
- Goal: replay viewer가 마지막으로 본 run과 위치를 기억하고 다시 열릴 때 같은 상태를 복원한다.
- Preferred Workforce: ux
- Why now: 운영자는 replay를 이어서 봐야 할 때가 많아서, 상태 복원이 안 되면 맥락이 끊긴다.
- Excludes: 복잡한 차트 시스템, 상세 인사이트 엔진, 행동 해석 고도화

### TC-3. Sprint summary linkage minimum
- Issue Topic: Sprint summary linkage minimum
- Goal: Sprint 1 요약이 replay viewer와 서로 왕복 이동 가능한 링크 구조를 갖게 한다.
- Preferred Workforce: ux
- Why now: 요약과 replay가 분리되면 운영자는 실제 근거를 빠르게 확인할 수 없다.
- Excludes: 복잡한 차트 시스템, 상세 인사이트 엔진, 행동 해석 고도화

### TC-4. Replay viewer continuity minimum
- Issue Topic: Replay viewer continuity minimum
- Goal: 최신 run replay의 연속성, 재생 흐름, 이전/다음 run 연결을 매끄럽게 만든다.
- Preferred Workforce: ux
- Why now: replay 흐름이 끊기면 운영자는 어느 구간이 바뀌었는지 빠르게 파악할 수 없기 때문이다.
- Excludes: 복잡한 차트 시스템, 상세 인사이트 엔진, 행동 해석 고도화

### TC-5. Sprint summary and replay viewer continuity minimum
- Issue Topic: Sprint summary and replay viewer continuity minimum
- Goal: Sprint 1 요약, replay viewer, 평가 지표가 한 흐름으로 이어지게 한다.
- Preferred Workforce: ux
- Why now: 운영 도구의 핵심 정보가 분절되면 아직 완성되지 않은 인상을 주기 때문이다.
- Excludes: 복잡한 차트 시스템, 상세 인사이트 엔진, 행동 해석 고도화

### TC-6. Operator hub landing and navigation coherence minimum
- Issue Topic: Operator hub landing and navigation coherence minimum
- Goal: 운영 도구 허브의 첫 화면, 카드 배치, 섹션 전환, 현재 위치 표시를 정리한다.
- Preferred Workforce: ux
- Why now: 운영 도구의 핵심 정보가 이미 있더라도, 첫 화면이 조각나 보이면 전체 허브 신뢰가 깨지기 때문이다.
- Excludes: 고급 분석, 정책 실험 플랫폼, 시뮬레이션 고도화

### TC-7. Metric card and empty state completeness minimum
- Issue Topic: Metric card and empty state completeness minimum
- Goal: metric 카드와 빈 상태를 일관된 메시지와 레이아웃으로 채운다.
- Preferred Workforce: ux
- Why now: 비어 보이는 카드와 어색한 빈 상태가 만들다 만 느낌을 가장 강하게 주기 때문이다.
- Excludes: 전체 대시보드 재설계, 추천 고도화, advanced visualization


## Forum Service UX Slices

이 섹션은 threads, Twitter-like reply UX, compact composer, tag navigation처럼 사용자가 실제로 쓰고 싶어지는 포럼 서비스 경험을 먼저 닫기 위한 slice들이다. 여기서 중요한 것은 시뮬레이션이 아니라 서비스 완성도다.

### TC-0. Overall UI/UX layout and information hierarchy minimum
- Issue Topic: Overall UI/UX layout and information hierarchy minimum
- Goal: forum/admin surface의 전체 레이아웃, 정보 구조, 첫 시선 흐름을 먼저 닫는다.
- Preferred Workforce: ux
- Why now: 화면 전체가 반쯤 만들어진 것처럼 보이면 세부 interaction보다 먼저 layout과 information hierarchy가 사용성을 좌우하기 때문이다.
- Excludes: backend contract, 추천 고도화, advanced visualization

### TC-0.5. Shared content consumption and identity feedback loop minimum
- Issue Topic: Shared content consumption and identity feedback loop minimum
- Goal: 사용자가 글을 보고, 선택하고, 좋아요/싫어요/댓글 반응을 남기고, 그 반응이 agent 또는 사용자 캐릭터의 변화 흐름으로 자연스럽게 이어지는 UI/UX 구조를 닫는다.
- Preferred Workforce: ux
- Why now: 포럼 서비스가 단순히 글을 쓰는 곳이 아니라, 다른 사람과 agent가 함께 콘텐츠를 소비하고 반응하면서 경험이 쌓이는 공간이어야 하기 때문이다.
- Excludes: 감정 해석 엔진, 불쾌감 감지, 고급 행동 추론, backend identity synthesis

### TC-1. Threaded reply and comment context minimum
- Issue Topic: Threaded reply and comment context minimum
- Goal: 댓글이 게시글뿐 아니라 다른 댓글에도 자연스럽게 응답할 수 있도록 thread context를 닫는다.
- Preferred Workforce: ux
- Why now: threads 스타일의 대화 연속성이 포럼 UX의 가장 기본적인 품질이기 때문이다.
- Excludes: 감정 해석, 불쾌감 감지, 고도화된 토론 분석

### TC-2. Compact compose entrypoint minimum
- Issue Topic: Compact compose entrypoint minimum
- Goal: 상단 composer 대신 더 가볍고 맥락적인 글쓰기 진입점을 만든다.
- Preferred Workforce: ux
- Why now: Twitter-like compose 흐름처럼 사용자의 글쓰기 마찰을 낮추는 첫 화면 개선이 필요하기 때문이다.
- Excludes: 전체 작성 플로우 개편, 고급 편집기, 추천 고도화

### TC-3. Tag navigation and hashtag search minimum
- Issue Topic: Tag navigation and hashtag search minimum
- Goal: 해시태그와 태그 링크가 검색/필터 결과로 자연스럽게 연결되도록 한다.
- Preferred Workforce: ux
- Why now: 포럼 발견성과 탐색성은 thread와 tag navigation에서 가장 빨리 체감되기 때문이다.
- Excludes: 복잡한 추천 시스템, 개인화 랭킹, 고급 분석

### TC-4. Feed clarity and empty state coherence minimum
- Issue Topic: Feed clarity and empty state coherence minimum
- Goal: 포럼 피드, 빈 상태, 첫 진입 메시지가 사용자를 막지 않도록 정리한다.
- Preferred Workforce: ux
- Why now: 사용자는 비어 있거나 어색한 첫 화면에서 가장 빨리 이탈하기 때문이다.
- Excludes: 추천 고도화, 개인화 랭킹, 고급 분석

### TC-5. Navigation coherence and visual hierarchy minimum
- Issue Topic: Navigation coherence and visual hierarchy minimum
- Goal: 상단 내비게이션, 섹션 전환, 현재 위치 표시, 시각적 우선순위를 정리한다.
- Preferred Workforce: ux
- Why now: 화면이 반쯤 만들어진 것처럼 보이는 가장 빠른 원인이 내비게이션/계층 혼선이기 때문이다.
- Excludes: 전체 정보구조 재설계, 디자인 시스템 전면 개편

### TC-6. Reply-driven agent comment generation minimum
- Issue Topic: Reply-driven agent comment generation minimum
- Goal: agent comment가 parent post 또는 sibling comment 문맥에 반응하도록 한다.
- Preferred Workforce: society
- Why now: thread 맥락에 반응하는 댓글은 forum service의 conversational quality를 가장 직접적으로 드러내기 때문이다.
- Excludes: 불쾌감 감지, 감정 해석, 고도화된 사회 행동 해석

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
- 서비스가 아직 덜 닫혔다면 시뮬레이션, 불쾌감 감지, 행동 해석 같은 고도화 토픽은 고르지 않는다.
- 불쾌감 감지, 감정 해석, 고도화된 사회 행동 해석은 이 카탈로그의 범위를 벗어나면 다음 epic 또는 later slice로 넘긴다.
