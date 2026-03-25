#!/usr/bin/env python3
"""
AI Fashion Forum — Workforce 기반 시뮬레이션 환경 토론 엔진

CAMEL-AI Workforce를 사용하여 여러 역할 에이전트가
시뮬레이션 환경, 관찰 신호, 개입 루프, 실행 이슈를 논의합니다.

사용법:
  # 기본 실행 (기본 주제)
  python scripts/requirement-debate/debate.py

  # 커스텀 주제
  python scripts/requirement-debate/debate.py --topic "에이전트 간 취향 전파(taste contagion) 메커니즘"

  # 결과를 GitHub Issue로 자동 등록
  python scripts/requirement-debate/debate.py --topic "브랜드 충성도 모델링" --create-issue
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

# ── CAMEL imports ──────────────────────────────────────────────
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.societies.workforce import Workforce, SingleAgentWorker
from camel.tasks import Task
from camel.types import ModelPlatformType, ModelType


# ── Config ─────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

WORKER_OUTPUT_RULES = """공통 출력 규칙:
- 반드시 한국어로만 작성한다.
- 반드시 일반 텍스트만 사용한다.
- JSON, Python dict, YAML, 마크다운 표를 쓰지 않는다.
- "다이어그램을 그리겠다" 같은 계획 문장이 아니라 지금 제출 가능한 요구사항 내용만 쓴다.
- 불필요한 서론 없이 바로 본문을 작성한다.
- 패션 취향 분화나 특정 현상 하나를 최상위 목표처럼 다루지 않는다.
- 현상보다 환경, 메커니즘, 관찰 신호, 개입 수단을 우선 정리한다.
- 추천 기능, 앱 기능 목록, 일반 MVP 기능 정의로 너무 빨리 수렴하지 않는다.
- 반드시 시뮬레이션 환경 규칙, 상태, 기억, 관계, 행동, 관찰 가능성 중 최소 두 가지 이상을 다룬다.
"""

COMMON_COORDINATOR_PROMPT = """당신은 AI Fashion Forum 프로젝트의 시뮬레이션 설계 토론 코디네이터입니다.

여러 역할의 의견을 종합하여
시뮬레이션 환경 설계안과 실행 이슈 초안을 정리합니다.

중요 규칙:
- 반드시 한국어로만 작성한다.
- 반드시 일반 텍스트와 마크다운 헤더/불릿만 사용한다.
- JSON, dict, YAML, 표, 코드블록을 쓰지 않는다.
- 각 역할의 핵심 주장과 리스크를 통합해서 하나의 일관된 문서로 만든다.
- 구현 불가능한 요구나 "추후 작성" 같은 문장을 넣지 않는다.
- 기능 요구사항 목록보다 환경 설계와 검증 프레임을 우선한다.

최종 출력 형식:
## Simulation Question
(이번 토론이 답하려는 시뮬레이션 질문)

## Environment Design
- (환경 규칙, 상태, 기억, 관계, 행동 스키마 핵심)

## Observable Signals
- (무엇을 보면 환경이 작동한다고 볼 수 있는가)

## Intervention Levers
- (어떤 개입 수단을 시험할 수 있는가)

## Required Artifacts
- (로그, 트레이스, 이벤트, 인터뷰, 대시보드 등)

## Issue Title
(한 줄 제목)

## Summary
- (핵심 요약 3-5개)

## Acceptance Criteria
- [ ] (체크리스트)

## Technical Notes
- (구현 참고사항)

## Open Questions
- (미결 이슈)

## Priority
High / Medium / Low
"""

COMMON_FINAL_SYNTHESIZER_PROMPT = """당신은 여러 라운드의 Workforce 토론 결과를 정리하는 수석 시뮬레이션 전략가입니다.

당신의 목표:
- 여러 라운드에서 반복 등장한 합의 사항을 추출한다.
- 충돌하는 의견은 핵심 trade-off와 함께 요약한다.
- 바로 실행 가능한 환경 설계 작업과 개입 실험을 우선순위 순으로 정리한다.
- 최종적으로 GitHub Issue로 등록 가능한 실행 초안을 작성한다.

중요 규칙:
- 반드시 한국어로만 작성한다.
- 일반 텍스트와 마크다운 헤더/불릿만 사용한다.
- JSON, dict, YAML, 표, 코드블록을 쓰지 않는다.
- 애매한 표현 대신 실행 가능한 문장으로 쓴다.
- "추후 논의" 같은 문장만 남기지 말고, 지금 결정 가능한 내용은 결정해서 적는다.
- 결과를 일반 제품 기능 목록으로 축소하지 않는다.

최종 출력 형식:
# Multi-Round Debate Summary

## Key Decisions
- (라운드 전반에서 합의된 핵심 결정)

## Remaining Tensions
- (여전히 남아 있는 충돌/선택지)

## Environment Priorities
- (먼저 설계하거나 고정해야 할 환경 요소)

## Observable Signals
- (측정/관찰해야 할 신호)

## Intervention Plan
- (시험할 개입)

## Next Actions
1. (바로 해야 할 일)
2. (그 다음 할 일)

## Required Artifacts
- (반드시 남겨야 할 산출물)

## Simulation Question
(이번 실행이 답해야 할 질문)

## Issue Title
(한 줄 제목)

## Summary
- (핵심 요약 3-5개)

## Acceptance Criteria
- [ ] (체크리스트)

## Technical Notes
- (구현 참고사항)

## Open Questions
- (미결 이슈)

## Priority
High / Medium / Low
"""

TASK_AGENT_SYSTEM_PROMPT = """당신은 Workforce 태스크 라우터입니다.

규칙:
- 작업을 적절한 워커에게 배정한다.
- worker id는 반드시 유효한 후보 중에서만 선택한다.
- worker가 없는 경우 임의 값이나 none을 쓰지 않는다.
- 태스크가 충분히 구체적이지 않으면 더 구체적인 텍스트 태스크로 재작성한다.
"""

SECTION_ORDER = [
    "Issue Title",
    "Summary",
    "Acceptance Criteria",
    "Technical Notes",
    "Open Questions",
    "Priority",
]

ROUND_FOCUS_GUIDE = {
    1: "이번 라운드는 어떤 시뮬레이션 질문을 풀고 어떤 환경이 있어야 하는지 정의하는 데 집중하라.",
    2: "환경 규칙, 상태, 기억, 관계, 행동 스키마, 관찰 신호를 구체화하라.",
    3: "개입 수단, 실패 시나리오, 누락된 아티팩트, 설명 불가능한 부분을 점검하라.",
    4: "반복 실험에 필요한 우선순위, 측정 프레임, 실행 순서를 압축하라.",
    5: "이슈로 바로 옮길 수 있도록 환경 설계안, 관찰 신호, 개입 계획, 산출물을 정리하라.",
}

COMMITMENT_COORDINATOR_PROMPT = """당신은 Commitment Workforce 코디네이터입니다.

여러 역할의 의견을 종합하여 다음 논의에 사용할 workforce와 토픽을 확정합니다.

중요 규칙:
- 반드시 한국어로만 작성한다.
- 일반 텍스트와 마크다운 헤더/불릿만 사용한다.
- JSON, dict, YAML, 표, 코드블록을 쓰지 않는다.
- 토픽은 --topic 인자로 바로 복사해서 쓸 수 있는 완성된 문장으로 작성한다.
- "추후 결정" 같은 표현을 쓰지 않는다. 지금 결정 가능한 것은 결정해서 적는다.

최종 출력 형식:
## Selected Workforce
(society / operator / core / default 중 하나)

## Topic
(--topic 인자로 바로 사용 가능한 완성된 토픽 문자열)

## Why This Workforce
- (이 workforce를 선택한 근거)
- (이 gap이 해당 workforce의 어떤 역할 충돌을 유발하는가)

## Why This Topic
- (이 토픽이 각 역할에게 서로 다른 답을 유도하는 이유)
- (토픽에 포함된 제약 조건과 그 근거)

## Required Decisions
- (이 논의에서 반드시 결정되어야 할 것들)

## Risks
- (이 workforce + 토픽 선택이 틀릴 수 있는 시나리오)

## Issue Title
(이번 commitment 결정의 한 줄 제목)

## Summary
- (핵심 요약 3개 이하)

## Priority
High / Medium / Low
"""

COMMITMENT_FINAL_SYNTHESIZER_PROMPT = """당신은 Commitment Workforce 최종 결정자입니다.

여러 라운드의 토론 결과를 종합하여 다음 논의에 사용할 workforce와 토픽을 최종 확정합니다.

중요 규칙:
- 반드시 한국어로만 작성한다.
- 일반 텍스트와 마크다운 헤더/불릿만 사용한다.
- JSON, dict, YAML, 표, 코드블록을 쓰지 않는다.
- 토픽은 --topic 인자로 바로 복사해서 쓸 수 있는 완성된 문장으로 작성한다.
- 여러 라운드에서 충돌한 의견이 있으면 Commitment Critic의 검증 결과를 우선한다.

최종 출력 형식:
# Commitment Decision

## Selected Workforce
(society / operator / core / default 중 하나)

## Topic
(--topic 인자로 바로 사용 가능한 완성된 토픽 문자열)

## Why This Workforce
- (최종 선택 근거)

## Why This Topic
- (토픽 설계 근거)
- (이 토픽이 선택된 workforce의 역할 충돌을 유발하는 이유)

## Required Decisions
- (이 논의에서 반드시 결정되어야 할 것들)

## Risks
- (이 선택이 틀릴 수 있는 시나리오와 그때의 대안)

## Issue Title
(이번 commitment 결정의 한 줄 제목)

## Summary
- (핵심 요약 3개 이하)

## Priority
High / Medium / Low
"""

SCENARIOS = {
    "commitment": {
        "label": "논의 방향 결정",
        "roles_file": SCRIPT_DIR / "commitment_roles.yaml",
        "default_topic": "현재 프로젝트에서 결정되지 않은 가장 중요한 gap은 무엇이며, 어떤 workforce로 어떤 토픽을 논의해야 하는가?",
        "workforce_description": "AI Fashion Forum Commitment Workforce: Project State Analyst, Workforce Selector, Topic Architect, Commitment Critic이 협력하여 다음 논의의 workforce와 토픽을 결정합니다.",
        "participants": "Project State Analyst, Workforce Selector, Topic Architect, Commitment Critic",
        "title": "🎯 AI Fashion Forum — Commitment Workforce",
        "arg_description": "CAMEL Workforce 기반 논의 방향 결정 엔진",
        "build_task_prompt": lambda topic: f"""AI Fashion Forum 프로젝트의 다음 논의 방향을 결정하세요.

## 현재 상황 / 결정해야 할 것
{topic}

## 이번 토론의 목적
이 토론은 시뮬레이션 환경을 직접 설계하는 것이 아닙니다.
"어떤 workforce로 어떤 토픽을 논의해야 하는가"를 결정하는 메타 토론입니다.

## 사용 가능한 workforce
- society: 이용자 조직 사회 시뮬레이션 설계 (행태, 상태, 기억, 관계, 군집, 갈등)
- operator: 운영 조직 관찰·개입 루프 설계 (메트릭, 트레이스, 개입 레버, 운영 정책)
- core: mock → 실서비스 전환 코어 개발 (기술 스택, 아키텍처, 구현 범위, 배포)
- default: 시뮬레이션 환경 범용 설계 (위 세 가지에 속하지 않는 범용 설계)

## 토론 규칙
1. Project State Analyst: 현재 상황에서 결정되지 않은 gap을 분석하라
2. Workforce Selector: 이 gap의 성격에 맞는 workforce를 선택하고 근거를 제시하라
3. Topic Architect: 선택된 workforce의 역할 충돌이 드러나는 토픽 문자열을 설계하라
4. Commitment Critic: workforce 선택과 토픽의 품질을 검증하고 문제점을 지적하라

## 기대 산출물
- Selected Workforce (society / operator / core / default)
- Topic (--topic 인자로 바로 사용 가능한 완성된 문자열)
- Why This Workforce
- Why This Topic
- Required Decisions
- Risks
- Issue Title
- Summary
- Priority

## 출력 제약
- 토픽은 반드시 완성된 문장으로 작성하라 (--topic 인자로 바로 복사 가능해야 함)
- 시뮬레이션 환경 규칙을 직접 설계하지 말고 workforce와 토픽 선택에 집중하라
- "추후 결정" 같은 표현 없이 지금 결정 가능한 것을 결정하라
""",
        "coordinator_prompt": COMMITMENT_COORDINATOR_PROMPT,
        "final_prompt": COMMITMENT_FINAL_SYNTHESIZER_PROMPT,
        "round_focus_guide": {
            1: "현재 상황에서 결정되지 않은 gap을 파악하고 workforce 후보를 압축하라.",
            2: "workforce를 확정하고 토픽 초안을 구체화하라.",
            3: "토픽의 제약 조건을 검증하고 Commitment Critic의 반론을 반영하라.",
            4: "최종 workforce와 토픽을 확정하고 Required Decisions를 정리하라.",
            5: "바로 실행 가능한 --workforce / --topic 조합으로 정리하라.",
        },
        "synthesis_prompt": """위 결과를 바탕으로:
1. 여러 라운드에서 합의된 workforce 선택과 그 근거를 추출하고
2. Commitment Critic의 검증을 통과한 최종 토픽 문자열을 확정하고
3. 이 논의에서 반드시 결정되어야 할 것들과 리스크를 정리하고
4. --workforce / --topic 인자로 바로 실행 가능한 형태로 최종 결론을 작성하라.

토픽은 반드시 완성된 문장으로 작성하라.
""",
    },
    "society": {
        "label": "이용자 조직 시뮬레이션",
        "roles_file": SCRIPT_DIR / "society_roles.yaml",
        "default_topic": "패션 커뮤니티를 도메인 언어로 쓰는 이용자 조직 시뮬레이션에서 먼저 정의해야 할 행태, 상태, 관계 규칙은 무엇인가?",
        "workforce_description": "AI Fashion Forum 이용자 조직 시뮬레이션 토론 팀: Society Modeling Lead, Identity & Memory Architect, Community Dynamics Researcher, Simulation Critic이 협력하여 이용자 조직 환경 설계안을 도출합니다.",
        "participants": "Society Modeling Lead, Identity & Memory Architect, Community Dynamics Researcher, Simulation Critic",
        "title": "🏢 AI Fashion Forum — 이용자 조직 시뮬레이션 토론",
        "arg_description": "CAMEL Workforce 기반 이용자 조직 시뮬레이션 토론 엔진",
        "build_task_prompt": lambda topic: f"""AI Fashion Forum 프로젝트의 이용자 조직 시뮬레이션 환경을 토론하세요.

## 토론 주제
{topic}

## 프로젝트 맥락
- 패션 커뮤니티를 도메인 언어로 사용하는 AI-native 사회 시뮬레이션 환경을 만든다
- 이용자 조직은 포스트, 댓글, 반응, 침묵, 군집, 갈등, 지위, 정체성 변화를 만들어내는 사회 레이어다
- 패션 취향 분화는 목표가 아니라 가능한 emergent phenomenon 중 하나다
- 핵심은 어떤 상태, 기억, 관계, 노출, 행동 규칙이 있어야 설명 가능한 사회 동학이 반복적으로 나타나는지 정의하는 것이다

## 토론 규칙
1. Society Modeling Lead: 먼저 검증해야 할 사회 시뮬레이션 질문을 정의하라
2. Identity & Memory Architect: 상태, 기억, 노출, 관계, 행동 규칙을 설계하라
3. Community Dynamics Researcher: 실제 패션 커뮤니티의 규범, 갈등, 지위 형성과의 정합성을 검증하라
4. Simulation Critic: 설명 불가능성, 누락된 행태, 실패 시나리오를 지적하라

## 기대 산출물
- Simulation Question
- Environment Design
- Observable Signals
- Intervention Levers
- Required Artifacts
- Issue Title
- Summary
- Acceptance Criteria
- Technical Notes
- Open Questions
- Priority

## 출력 제약
- 기능 목록보다 사회 환경 규칙과 관찰 가능성을 우선하라
- 추천 앱 MVP 논의로 축소하지 말라
- 이용자 조직이 어떤 행동 단위와 사회 동학을 가지는지 구체적으로 적어라
""",
        "coordinator_prompt": COMMON_COORDINATOR_PROMPT + "\n추가 규칙: 이번 토론은 이용자 조직 시뮬레이션 설계에 집중한다. 운영 조직의 기능 목록보다 사회 행태 모델을 우선한다.\n",
        "final_prompt": COMMON_FINAL_SYNTHESIZER_PROMPT + "\n추가 규칙: 최종 결과는 이용자 조직의 행태 모델, 관찰 신호, 필수 시뮬레이션 아티팩트를 우선 정리하라.\n",
        "round_focus_guide": {
            1: "이용자 조직이 어떤 사회 질문을 풀어야 하는지와 핵심 행태 단위를 정의하라.",
            2: "상태, 기억, 관계, 노출, 행동 스키마와 관찰 신호를 구체화하라.",
            3: "규범, 갈등, 군집, 지위 형성에서 누락된 요소와 실패 시나리오를 점검하라.",
            4: "반복 실험에 필요한 측정 프레임, 데이터, 아티팩트를 압축하라.",
            5: "이슈로 옮길 수 있게 이용자 조직 시뮬레이션 설계안을 정리하라.",
        },
        "synthesis_prompt": """위 결과를 바탕으로:
1. 이용자 조직이 먼저 설명해야 할 사회 동학을 추출하고
2. 필요한 상태, 기억, 관계, 행동 규칙을 정리하고
3. 어떤 관찰 신호와 아티팩트가 있어야 설명 가능한지 우선순위를 정한 뒤
4. 바로 GitHub Issue로 등록 가능한 실행 초안을 작성하라.

Acceptance Criteria는 실제 구현/검증 가능한 체크리스트로 작성하라.
이용자 조직의 행태 모델과 반복 실험 가능성을 우선하라.
""",
    },
    "core": {
        "label": "코어 플랫폼 개발",
        "roles_file": SCRIPT_DIR / "core_roles.yaml",
        "default_topic": "현재 mock으로 구현된 패션 포럼을 실제 동작하는 서비스로 만들기 위해 먼저 결정해야 할 코어 개발 계획은 무엇인가?",
        "workforce_description": "AI Fashion Forum 코어 플랫폼 개발 토론 팀: CTO, Backend Engineer, Product Manager, Core Critic이 협력하여 현재 mock을 실제 동작하는 서비스로 전환하는 핵심 개발 계획을 도출합니다.",
        "participants": "CTO, Backend Engineer, Product Manager, Core Critic",
        "title": "🚀 AI Fashion Forum — Core 플랫폼 개발 토론",
        "arg_description": "CAMEL Workforce 기반 코어 플랫폼 개발 토론 엔진",
        "build_task_prompt": lambda topic: f"""AI Fashion Forum 프로젝트에서 현재 mock을 실제 서비스로 전환하는 코어 개발 계획을 토론하세요.

## 토론 주제
{topic}

## 프로젝트 맥락
- 현재 상태: React mock UI + 바닐라 Node.js 시뮬레이션 서버 + agent-core JS 모듈로 구성된 npm 모노레포
- mock은 정적 시드 데이터로 UI를 렌더링하는 수준이며, 에이전트가 실시간으로 동작하지 않는다
- agent-core에는 content-pipeline, memory-stack, identity-update-rules, forum-generation 등의 로직이 이미 있다
- 목표: AI 에이전트가 실제로 포럼에서 포스트를 작성하고 상호작용하는 동작하는 서비스를 만든다
- 이번 Workforce의 핵심 질문은 "이 mock을 어떻게 실제 서비스로 전환할 것인가?"이다
- 운영 조직 설계나 이용자 조직 모델 일반론보다 먼저, 현재 코드베이스를 어떻게 서비스로 연결할지에 집중하라

## 토론 규칙
1. CTO: 기술 스택 선택과 아키텍처 결정을 주도하라
2. Backend Engineer: 첫 번째로 구현할 코드 범위와 실제 동작 루프를 정의하라
3. Product Manager: 코어 범위와 개발 우선순위, 성공 기준을 정의하라
4. Core Critic: 각 결정의 위험성, 실패 시나리오, 대안을 제시하라

## 기대 산출물
- Mock-to-Service Goal (무엇이 되면 mock이 실제 서비스가 되었다고 볼 수 있는가)
- Current Mock Constraints (현재 mock이 실제 서비스가 아닌 이유)
- Service Architecture Choice (어떤 구조로 실제 서비스화할 것인가)
- First Working Loop (가장 먼저 end-to-end로 작동시킬 루프)
- Migration Plan (기존 mock 코드와 실제 서비스 코드를 어떻게 연결/교체할 것인가)
- 개발 우선순위 (Must Have / Should Have / Nice to Have)
- 리스크와 대응 방안
- Issue Title
- Summary
- Acceptance Criteria
- Technical Notes
- Open Questions
- Priority

## 출력 제약
- 추상적인 아키텍처 다이어그램 설명보다 실제 코드와 파일 수준의 구현 계획을 우선하라
- "나중에 결정한다"는 표현 대신 지금 결정 가능한 내용은 결정해서 적어라
- 기존 mock 코드(forum-web, sim-server, agent-core)를 어떻게 활용하거나 교체할지 구체적으로 적어라
- 현재 mock이 왜 아직 서비스가 아닌지, 무엇이 연결되면 서비스가 되는지 반드시 적어라
- 이미 운영 중인 서비스의 개선안처럼 말하지 말고, mock에서 서비스로 넘어가는 전환 계획으로 답하라
""",
        "coordinator_prompt": COMMON_COORDINATOR_PROMPT + "\n추가 규칙: 이번 토론은 현재 mock을 실제 서비스로 전환하는 계획에 집중한다. 추상적인 설계보다 실제 구현 가능한 첫 번째 동작 루프와 전환 단계를 우선한다.\n",
        "final_prompt": COMMON_FINAL_SYNTHESIZER_PROMPT + "\n추가 규칙: 최종 결과는 mock-to-service 전환 목표, 첫 번째 구현 범위, 코드베이스 전환 계획을 중심으로 코어 플랫폼 계획을 정리하라.\n",
        "round_focus_guide": {
            1: "현재 mock이 왜 아직 서비스가 아닌지와 코어 플랫폼의 정확한 범위를 정의하라.",
            2: "첫 번째 구현할 코드 범위와 실제 동작 루프를 구체화하라.",
            3: "mock-to-service 전환 과정의 리스크, 기술 부채, 실패 시나리오를 점검하라.",
            4: "개발 우선순위, 마이그레이션 순서, 스프린트 계획을 압축하라.",
            5: "이슈로 옮길 수 있게 mock-to-service 실행 계획을 정리하라.",
        },
        "synthesis_prompt": """위 결과를 바탕으로:
1. 현재 mock을 실제 서비스로 전환하기 위한 핵심 목표와 성공 기준을 추출하고
2. 기술 스택 선택과 첫 번째 구현 범위를 정리하고
3. mock-to-service 마이그레이션 순서와 개발 우선순위를 제시하고
4. 바로 GitHub Issue로 등록 가능한 실행 초안을 작성하라.

Acceptance Criteria는 실제 구현/검증 가능한 체크리스트로 작성하라.
"지금 당장 작동하는 것"을 만드는 데 필요한 최소 범위를 우선하라.
""",
    },
    "operator": {
        "label": "운영 조직 설계",
        "roles_file": SCRIPT_DIR / "operator_roles.yaml",
        "default_topic": "포럼 운영 조직이 먼저 정의해야 할 관찰 프레임, 개입 레버, 운영 루프는 무엇인가?",
        "workforce_description": "AI Fashion Forum 운영 조직 토론 팀: Operator Strategy Lead, Measurement & Intervention Architect, Moderation & Policy Designer, Operator Critic이 협력하여 운영 조직 설계안을 도출합니다.",
        "participants": "Operator Strategy Lead, Measurement & Intervention Architect, Moderation & Policy Designer, Operator Critic",
        "title": "🏢 AI Fashion Forum — 운영 조직 설계 토론",
        "arg_description": "CAMEL Workforce 기반 운영 조직 설계 토론 엔진",
        "build_task_prompt": lambda topic: f"""AI Fashion Forum 프로젝트의 운영 조직(포럼 웹 페이지를 운영하고 개입하는 조직)을 토론하세요.

## 토론 주제
{topic}

## 프로젝트 맥락
- 운영 조직은 이용자 조직의 행동, 로그, 인터뷰, 트레이스, 메트릭을 관찰한다
- 운영 조직은 온보딩, 카테고리, 추천 설정, 개입 정책, moderation rule, 실험 플래그를 바꿀 수 있다
- 목표는 포럼을 예쁘게 운영하는 것이 아니라, 이용자 조직의 변화를 설명 가능하게 관찰하고 실험하는 것이다
- 핵심은 어떤 운영 루프와 개입 수단이 있어야 다음 시뮬레이션/제품 런을 설계할 수 있는지 정의하는 것이다

## 토론 규칙
1. Operator Strategy Lead: 운영 조직이 먼저 풀어야 할 운영 질문을 정의하라
2. Measurement & Intervention Architect: 메트릭, 트레이스, 대시보드, 실험 레버를 설계하라
3. Moderation & Policy Designer: 카테고리, 온보딩, 추천, moderation의 운영 정책을 설계하라
4. Operator Critic: 설명 불가능한 개입, 측정 불가능한 운영 루프, 누락된 관찰 프레임을 지적하라

## 기대 산출물
- Simulation Question
- Environment Design
- Observable Signals
- Intervention Levers
- Required Artifacts
- Issue Title
- Summary
- Acceptance Criteria
- Technical Notes
- Open Questions
- Priority

## 출력 제약
- 운영 조직의 관찰 루프와 개입 루프를 우선 정리하라
- 일반 제품 기능 우선순위 회의로 축소하지 말라
- 이용자 조직을 어떻게 읽고 어떻게 바꿀 수 있는지 구체적으로 적어라
""",
        "coordinator_prompt": COMMON_COORDINATOR_PROMPT + "\n추가 규칙: 이번 토론은 운영 조직 설계에 집중한다. 이용자 조직 기능보다 관찰 프레임, 개입 레버, 운영 루프를 우선한다.\n",
        "final_prompt": COMMON_FINAL_SYNTHESIZER_PROMPT + "\n추가 규칙: 최종 결과는 운영 조직의 관찰 체계, 개입 레버, 운영 아티팩트를 우선 정리하라.\n",
        "round_focus_guide": {
            1: "운영 조직이 먼저 답해야 할 운영 질문과 개입 목표를 정의하라.",
            2: "메트릭, 대시보드, 인터뷰, 트레이스, 정책 레버를 구체화하라.",
            3: "측정 불가능한 개입, 운영 리스크, 정책 충돌을 점검하라.",
            4: "반복 운영 루프와 실험 우선순위를 압축하라.",
            5: "이슈로 옮길 수 있게 운영 조직 설계안과 개입 계획을 정리하라.",
        },
        "synthesis_prompt": """위 결과를 바탕으로:
1. 운영 조직이 먼저 고정해야 할 관찰 프레임과 개입 목표를 추출하고
2. 어떤 메트릭, 인터뷰, 트레이스, 정책 레버가 필요한지 정리하고
3. 어떤 운영 아티팩트와 반복 루프가 있어야 다음 런을 설계할 수 있는지 우선순위를 정한 뒤
4. 바로 GitHub Issue로 등록 가능한 실행 초안을 작성하라.

Acceptance Criteria는 실제 구현/검증 가능한 체크리스트로 작성하라.
운영 조직의 관찰과 개입 가능성을 우선하라.
""",
    },
}


def load_roles(roles_file: Path) -> dict:
    """역할 정의 파일을 로드합니다."""
    with open(roles_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_model(model_name: str = "gpt-4o-mini"):
    """OpenAI 모델을 생성합니다."""
    model_map = {
        "gpt-4o": ModelType.GPT_4O,
        "gpt-4o-mini": ModelType.GPT_4O_MINI,
        "gpt-4-turbo": ModelType.GPT_4_TURBO,
    }
    model_type = model_map.get(model_name, ModelType.GPT_4O_MINI)
    return ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=model_type,
    )


def extract_agent_text(response) -> str:
    """ChatAgent.step() 응답에서 텍스트를 추출합니다."""
    if hasattr(response, "msgs") and response.msgs:
        return response.msgs[0].content.strip()
    if hasattr(response, "msg") and response.msg:
        return response.msg.content.strip()
    return str(response).strip()


def build_workforce(
    roles_config: dict,
    scenario: dict,
    model_name: str = "gpt-4o-mini",
) -> Workforce:
    """역할 설정을 기반으로 Workforce를 구성합니다."""
    roles = roles_config["roles"]
    model = create_model(model_name)

    workers = []
    for role_key, role_def in roles.items():
        agent = ChatAgent(
            system_message=(
                role_def["system_prompt"].strip() + "\n\n" + WORKER_OUTPUT_RULES
            ),
            model=model,
        )
        worker = SingleAgentWorker(
            description=role_def["description"].strip(),
            worker=agent,
            use_structured_output_handler=False,
        )
        workers.append(worker)
        print(f"  ✓ {role_def['name']} 에이전트 생성 완료")

    coordinator = ChatAgent(system_message=scenario["coordinator_prompt"], model=model)
    task_agent = ChatAgent(
        system_message=TASK_AGENT_SYSTEM_PROMPT,
        model=model,
    )

    workforce = Workforce(
        description=scenario["workforce_description"],
        children=workers,
        coordinator_agent=coordinator,
        task_agent=task_agent,
        use_structured_output_handler=False,
    )

    return workforce


def build_round_task_prompt(
    scenario: dict,
    topic: str,
    round_number: int,
    total_rounds: int,
    history: list[str],
) -> str:
    """라운드별 누적 토론 프롬프트를 생성합니다."""
    history_text = "\n\n".join(
        [f"### Round {idx + 1} 결과\n{item}" for idx, item in enumerate(history)]
    )
    focus = scenario["round_focus_guide"].get(
        round_number,
        "앞선 논의를 바탕으로 더 구체적이고 실행 가능한 환경 설계안으로 다듬어라.",
    )

    return f"""{scenario["build_task_prompt"](topic)}

## 현재 라운드
- 현재 라운드: {round_number} / 총 {total_rounds} 라운드
- 이번 라운드 초점: {focus}

## 이전 라운드 요약
{history_text if history_text else "- 이전 라운드 없음"}

## 이번 라운드 추가 지시
- 이전 라운드와 같은 내용을 반복하지 말고, 더 구체화하거나 보완하라.
- 앞선 결과의 모순, 빈칸, 실행 불가능한 부분을 우선적으로 수정하라.
- 최종 라운드에 가까울수록 바로 이슈로 옮길 수 있는 환경 설계 문장으로 정리하라.
"""


def run_multi_round_debate(
    workforce: Workforce,
    scenario: dict,
    topic: str,
    rounds: int,
) -> list[dict[str, str]]:
    """여러 라운드의 Workforce 토론을 순차 실행합니다."""
    round_results: list[dict[str, str]] = []

    for round_number in range(1, rounds + 1):
        print(f"🔁 Round {round_number}/{rounds} 진행 중...")
        task_prompt = build_round_task_prompt(
            scenario=scenario,
            topic=topic,
            round_number=round_number,
            total_rounds=rounds,
            history=[item["normalized_result"] for item in round_results],
        )
        task = Task(
            content=task_prompt,
            id=f"req-debate-round-{round_number:03d}",
        )
        result = workforce.process_task(task)
        raw_result_text = result.result if result.result else "토론 결과가 비어있습니다."
        normalized_result = synthesize_subtasks(raw_result_text)
        round_results.append(
            {
                "round": str(round_number),
                "raw_result": raw_result_text,
                "normalized_result": normalized_result,
            }
        )
        print(f"  ✓ Round {round_number} 완료")
        print()

    return round_results


def synthesize_multi_round_result(
    scenario: dict,
    model_name: str,
    topic: str,
    round_results: list[dict[str, str]],
) -> str:
    """라운드별 토론 결과를 최종 환경 설계 + 실행 Issue 초안으로 합성합니다."""
    model = create_model(model_name)
    synthesizer = ChatAgent(system_message=scenario["final_prompt"], model=model)
    compiled_rounds = "\n\n".join(
        [
            f"## Round {item['round']}\n{item['normalized_result']}"
            for item in round_results
        ]
    )
    prompt = f"""다음은 AI Fashion Forum 프로젝트 주제에 대한 다중 라운드 Workforce 토론 결과다.

## Topic
{topic}

## Round Results
{compiled_rounds}

{scenario["synthesis_prompt"]}"""
    response = synthesizer.step(prompt)
    return extract_agent_text(response)


def render_full_report(
    scenario: dict,
    topic: str,
    rounds: int,
    round_results: list[dict[str, str]],
    final_result: str,
) -> str:
    """저장/출력용 전체 리포트를 생성합니다."""
    lines = [
        "# 시뮬레이션 환경 토론 결과",
        "",
        f"- **주제**: {topic}",
        f"- **워크포스 타입**: {scenario['label']}",
        f"- **총 라운드 수**: {rounds}",
        f"- **일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **참여 역할**: {scenario['participants']}",
        "",
        "---",
        "",
        "# Round-by-Round Notes",
        "",
    ]

    for item in round_results:
        lines.extend(
            [
                f"## Round {item['round']}",
                "",
                item["normalized_result"],
                "",
            ]
        )

    lines.extend(
        [
            "---",
            "",
            "# Final Synthesis",
            "",
            normalize_issue_text(final_result),
            "",
        ]
    )
    return "\n".join(lines).strip()


def format_issue_dict(data: dict) -> str:
    """dict 형태의 응답을 마크다운 Issue 초안으로 정규화합니다."""
    lines = []
    for section in SECTION_ORDER:
        value = data.get(section)
        if not value:
            continue

        lines.append(f"## {section}")
        if isinstance(value, list):
            prefix = "- [ ]" if section == "Acceptance Criteria" else "-"
            for item in value:
                lines.append(f"{prefix} {str(item).strip()}")
        else:
            text = str(value).strip()
            if section == "Priority":
                lines.append(text)
            else:
                lines.append(text)
        lines.append("")

    return "\n".join(lines).strip()


def normalize_issue_text(text: str) -> str:
    """JSON/평문 응답을 마크다운 Issue 초안으로 최대한 정규화합니다."""
    stripped = text.strip()
    if not stripped:
        return stripped

    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, dict):
                return format_issue_dict(parsed)
        except json.JSONDecodeError:
            pass

    return stripped.replace("\\n", "\n")


def synthesize_subtasks(result_text: str) -> str:
    """Workforce가 서브태스크 묶음을 반환한 경우 사람이 읽기 좋은 형태로 재정리합니다."""
    pattern = re.compile(
        r"--- Subtask (?P<task_id>[^ ]+) Result ---\n(?P<body>.*?)(?=\n--- Subtask |\Z)",
        re.S,
    )
    matches = list(pattern.finditer(result_text))
    if not matches:
        return normalize_issue_text(result_text)

    parts = []
    for match in matches:
        task_id = match.group("task_id")
        body = normalize_issue_text(match.group("body"))
        parts.append(f"# {task_id}\n\n{body}".strip())

    return "\n\n".join(parts).strip()


def save_result(scenario: dict, topic: str, result_text: str) -> Path:
    """토론 결과를 파일로 저장합니다."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_topic = topic[:50].replace(" ", "_").replace("/", "-")
    filename = f"{timestamp}_{safe_topic}.md"
    filepath = OUTPUT_DIR / filename

    content = f"""# 시뮬레이션 환경 토론 결과

- **주제**: {topic}
- **워크포스 타입**: {scenario['label']}
- **일시**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **참여 역할**: {scenario['participants']}

---

{synthesize_subtasks(result_text)}
"""
    filepath.write_text(content, encoding="utf-8")
    return filepath


def create_github_issue(result_text: str) -> str:
    """토론 결과를 GitHub Issue로 등록합니다."""
    # Issue title 추출
    lines = result_text.split("\n")
    title = "feat: requirement from workforce debate"
    for line in lines:
        if line.startswith("## Issue Title"):
            idx = lines.index(line)
            if idx + 1 < len(lines):
                title = lines[idx + 1].strip().strip("#").strip()
                break

    # gh 명령으로 Issue 생성
    body = f"""## Workforce Debate 결과

이 이슈는 CAMEL-AI Workforce 토론을 통해 자동 생성되었습니다.

---

{result_text}

---
🤖 Generated by CAMEL Workforce Debate Engine
"""
    try:
        result = subprocess.run(
            ["gh", "issue", "create", "--title", title, "--body", body],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"  ⚠ GitHub Issue 생성 실패: {result.stderr}")
            return ""
    except FileNotFoundError:
        print("  ⚠ gh CLI를 찾을 수 없습니다. brew install gh로 설치하세요.")
        return ""


def run_workforce(
    workforce_key: str,
    topic: str | None = None,
    model_name: str = "gpt-4o-mini",
    rounds: int = 3,
    create_issue: bool = False,
):
    """선택한 Workforce를 실행하고 결과 텍스트와 저장 경로를 반환합니다."""
    if workforce_key not in SCENARIOS:
        raise ValueError(f"Unknown workforce: {workforce_key}")
    if rounds < 1 or rounds > 5:
        raise ValueError("rounds must be between 1 and 5")

    scenario = SCENARIOS[workforce_key]
    resolved_topic = topic or scenario["default_topic"]

    print("=" * 60)
    print(scenario["title"])
    print("=" * 60)
    print(f"🧩 워크포스: {workforce_key} ({scenario['label']})")
    print(f"📋 주제: {resolved_topic}")
    print(f"🤖 모델: {model_name}")
    print(f"🔁 라운드 수: {rounds}")
    print()

    print("📂 역할 설정 로드 중...")
    roles_config = load_roles(scenario["roles_file"])
    print(f"  ✓ {len(roles_config['roles'])}개 역할 로드 완료")
    print()

    print("🔧 Workforce 구성 중...")
    workforce = build_workforce(roles_config, scenario, model_name)
    print()

    print("🚀 토론 시작...")
    print("-" * 60)
    round_results = run_multi_round_debate(
        workforce=workforce,
        scenario=scenario,
        topic=resolved_topic,
        rounds=rounds,
    )

    print("🧠 최종 합성 중...")
    final_result = synthesize_multi_round_result(
        scenario=scenario,
        model_name=model_name,
        topic=resolved_topic,
        round_results=round_results,
    )
    result_text = render_full_report(
        scenario=scenario,
        topic=resolved_topic,
        rounds=rounds,
        round_results=round_results,
        final_result=final_result,
    )

    print("-" * 60)
    print()
    print("📝 토론 결과:")
    print("=" * 60)
    print(result_text)
    print("=" * 60)
    print()

    filepath = save_result(scenario, resolved_topic, result_text)
    print(f"💾 결과 저장: {filepath}")

    if create_issue:
        print()
        print("📌 GitHub Issue 생성 중...")
        issue_url = create_github_issue(result_text)
        if issue_url:
            print(f"  ✓ Issue 생성 완료: {issue_url}")

    print()
    print("✅ 토론 완료!")
    return {
        "scenario": scenario,
        "topic": resolved_topic,
        "result_text": result_text,
        "filepath": filepath,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="CAMEL Workforce 기반 시뮬레이션/운영 조직 토론 엔진"
    )
    parser.add_argument(
        "--workforce",
        type=str,
        default="society",
        choices=sorted(SCENARIOS.keys()),
        help="실행할 Workforce 타입 (기본: society)",
    )
    parser.add_argument(
        "--topic",
        type=str,
        default=None,
        help="토론 주제",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-mini",
        choices=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        help="사용할 모델 (기본: gpt-4o-mini)",
    )
    parser.add_argument(
        "--create-issue",
        action="store_true",
        help="토론 결과를 GitHub Issue로 자동 등록",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=3,
        help="토론 라운드 수 (3-5 권장, 기본: 3)",
    )
    args = parser.parse_args(argv)
    if args.rounds < 1:
        parser.error("--rounds must be at least 1")
    if args.rounds > 5:
        parser.error("--rounds must be 5 or fewer")
    run_workforce(
        workforce_key=args.workforce,
        topic=args.topic,
        model_name=args.model,
        rounds=args.rounds,
        create_issue=args.create_issue,
    )


if __name__ == "__main__":
    main()
