# camel-workforce-studio

CAMEL-AI Workforce 기반 토론 실행기를 분리해 둔 경량 레포입니다.

이 레포는 제품 자체를 구현하는 곳이 아니라, 시뮬레이션/운영/코어 개발 논의를 여러 역할 에이전트로 실행하고 결과를 산출물로 남기는 companion workspace 역할을 합니다.

## 현재 포함된 구성

- `scripts/requirement-debate/`
  - `debate.py`: 메인 Workforce 실행기
  - `society_debate.py`: 이용자 조직 시뮬레이션 토론 실행기
  - `operator_debate.py`: 운영 조직 설계 토론 실행기
  - `core_debate.py`: 코어 플랫폼 개발 토론 실행기
  - `bridge_debate.py`: society 결과를 operator 토론으로 넘기는 bridge 실행기
  - `*_roles.yaml`: 역할 정의
  - `outputs/`: 실행 결과 저장 경로

## 목적

- 외부 이슈나 요구사항을 Workforce 토론으로 정리한다.
- 여러 관점의 역할을 통해 실행 가능한 설계 초안을 만든다.
- 결과를 markdown 산출물이나 GitHub issue 초안으로 남긴다.

## 빠른 시작

### 1. Python 환경 준비

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

환경 변수로 OpenAI API 키가 필요합니다.

```bash
export OPENAI_API_KEY=your_key_here
```

### 2. 기본 실행

```bash
python scripts/requirement-debate/society_debate.py
```

### 3. 운영 조직 토론 실행

```bash
python scripts/requirement-debate/operator_debate.py --topic "포럼 운영 조직이 먼저 정의해야 할 관찰 프레임은 무엇인가?"
```

### 4. 코어 개발 토론 실행

```bash
python scripts/requirement-debate/core_debate.py --rounds 4
```

### 5. society -> operator bridge 실행

```bash
python scripts/requirement-debate/bridge_debate.py --society-rounds 3 --operator-rounds 3
```

## 출력 위치

실행 결과는 기본적으로 `scripts/requirement-debate/outputs/` 아래에 저장됩니다.

## 메모

- 현재 코드는 AI Fashion Forum 맥락이 강하게 들어가 있습니다.
- 이후 범용 orchestrator로 확장하려면 scenario/adapters 레이어를 분리하는 방향이 자연스럽습니다.
