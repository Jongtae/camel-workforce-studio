#!/usr/bin/env python3
"""
AI-Fashion-Forum — Workforce 기반 시뮬레이션 환경 토론 엔진

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
from difflib import SequenceMatcher
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from workforce_artifacts import (
    ArtifactBundle,
    append_run_ledger_entry,
    bullet_lines,
    build_handoff_markdown,
    first_section,
    load_context_pack,
    load_handoff,
    parse_topic_catalog_items,
    parse_commitment_decision,
    write_run_artifacts,
)


# ── Config ─────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


def camel_runtime():
    """CAMEL 의존성을 실제 실행 시점에만 로드합니다."""
    try:
        from camel.agents import ChatAgent
        from camel.models import ModelFactory
        from camel.societies.workforce import (
            SingleAgentWorker,
            Workforce,
            FailureHandlingConfig,
        )
        from camel.tasks import Task
        from camel.types import ModelPlatformType, ModelType
    except ImportError as exc:
        raise RuntimeError(
            "CAMEL-AI 의존성이 설치되지 않았습니다. `pip install -e .` 후 다시 실행하세요."
        ) from exc

    return {
        "ChatAgent": ChatAgent,
        "ModelFactory": ModelFactory,
        "SingleAgentWorker": SingleAgentWorker,
        "FailureHandlingConfig": FailureHandlingConfig,
        "Task": Task,
        "Workforce": Workforce,
        "ModelPlatformType": ModelPlatformType,
        "ModelType": ModelType,
    }

WORKER_OUTPUT_RULES = """공통 출력 규칙:
- 반드시 한국어로만 작성한다.
- 반드시 일반 텍스트만 사용한다.
- JSON, Python dict, YAML, 마크다운 표를 쓰지 않는다.
- diagram, visual representation, 도식 같은 요구가 있어도 텍스트 헤더와 불릿으로 대체한다.
- "다이어그램을 그리겠다" 같은 계획 문장이 아니라 지금 제출 가능한 요구사항 내용만 쓴다.
- 불필요한 서론 없이 바로 본문을 작성한다.
- 패션 취향 분화나 특정 현상 하나를 최상위 목표처럼 다루지 않는다.
- 현상보다 환경, 메커니즘, 관찰 신호, 개입 수단을 우선 정리한다.
- 추천 기능, 앱 기능 목록, 일반 MVP 기능 정의로 너무 빨리 수렴하지 않는다.
- 상위 목표는 제시하되, 최종 결론은 지금 바로 issue-ready한 가장 작은 구현 slice로 압축한다.
- 현재 답변이 다루는 범위와 다루지 않는 범위를 함께 써서 전체 그림 안에서의 위치를 드러낸다.
- 반드시 시뮬레이션 환경 규칙, 상태, 기억, 관계, 행동, 관찰 가능성 중 최소 두 가지 이상을 다룬다.
"""

EPIC_FRAME_OUTPUT_FORMAT = """## Program Goal
(이 논의가 속한 상위 제품 목표 또는 운영 목표)

## Epic Landscape
- (전체 그림에서 함께 고려해야 할 주요 epic 3~5개)

## This Epic
- (이번 답변이 책임지는 epic과 그 범위)

## Adjacent Epics / Dependencies
- (연결된 상위/하위/평행 epic 및 의존성)

## Out of Scope
- (이번 답변에서 intentionally 다루지 않는 것)
"""

COMMON_COORDINATOR_PROMPT = """당신은 AI-Fashion-Forum 프로젝트의 시뮬레이션 설계 토론 코디네이터입니다.

여러 역할의 의견을 종합하여
시뮬레이션 환경 설계안과 실행 이슈 초안을 정리합니다.

중요 규칙:
- 반드시 한국어로만 작성한다.
- 반드시 일반 텍스트와 마크다운 헤더/불릿만 사용한다.
- JSON, dict, YAML, 표, 코드블록을 쓰지 않는다.
- 각 역할의 핵심 주장과 리스크를 통합해서 하나의 일관된 문서로 만든다.
- 구현 불가능한 요구나 "추후 작성" 같은 문장을 넣지 않는다.
- 기능 요구사항 목록보다 환경 설계와 검증 프레임을 우선한다.
- 각 답변은 먼저 Program Goal과 Epic Landscape를 세운 다음, 그 안에서 이번 slice를 명시한다.

최종 출력 형식:
## Program Goal
(이번 논의가 속한 상위 제품 목표 또는 운영 목표)

## Epic Landscape
- (전체 그림에서 함께 고려해야 할 주요 epic 3~5개)

## This Epic
- (이번 답변이 책임지는 epic과 그 범위)

## Adjacent Epics / Dependencies
- (연결된 상위/하위/평행 epic 및 의존성)

## Out of Scope
- (이번 답변에서 intentionally 다루지 않는 것)

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
- 최종 결과는 항상 상위 목표와 epic 구도를 먼저 보여주고, 그 다음 이번 slice를 정리해야 한다.

최종 출력 형식:
# Multi-Round Debate Summary

## Program Goal
(이번 실행이 속한 상위 제품 목표 또는 운영 목표)

## Epic Landscape
- (전체 그림에서 함께 고려해야 할 주요 epic 3~5개)

## This Epic
- (이번 답변이 책임지는 epic과 그 범위)

## Adjacent Epics / Dependencies
- (연결된 상위/하위/평행 epic 및 의존성)

## Out of Scope
- (이번 답변에서 intentionally 다루지 않는 것)

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
- diagram, visual representation, 도식 같은 산출물을 요구하는 태스크는 텍스트 헤더/불릿 기반 설명 태스크로 재작성한다.
- society workforce 태스크를 재작성할 때는 action loop만 남기지 말고 state model, state transitions, content consumption, required backend artifacts를 함께 보존하라.
- society workforce 태스크에는 가능하면 post/comment/react/lurk/silence와 internal forum content/external web content를 직접 포함하라.
- society workforce 태스크에는 가능하면 각 action이 어떤 state를 읽고 어떤 state를 쓰며 어떤 artifact를 남기는지도 포함하라.
- society workforce 태스크에서 action loop를 요구할 때는 가능하면 정확한 필드명 Trigger Condition, State Read, State Write, Example State Transition A, Example State Transition B, Successful Outcome, Success Metric, Artifact를 유지하라.
- society workforce 태스크에서 required backend artifacts를 언급할 때는 trace/snapshot/event/forum artifact의 필요성까지 남겨라.
- society workforce 태스크에서 Required Backend Artifacts를 요구할 때는 가능하면 Connected Action, Captured State Change, Why It Is Operationally Required 같은 필드 구조를 유지하라.
- operator workforce 태스크에는 moderation/monitoring/policy/improvement 중 최소 두 가지 이상을 남겨라.
- core workforce 태스크에는 mock-to-service/API/migration/execution loop 중 최소 두 가지 이상을 남겨라.
"""

SECTION_ORDER = [
    "Issue Title",
    "Summary",
    "Acceptance Criteria",
    "Technical Notes",
    "Open Questions",
    "Priority",
]

ISSUE_TYPE_CHOICES = ["single", "task", "epic", "sprint", "bundle"]


def default_issue_repo() -> str:
    return os.environ.get("WORKFORCE_TARGET_REPO", "Jongtae/AI-Fashion-Forum")

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
- source repo intent가 agent-loop, action-space, identity-update-rules, state-schema를 가리키면 society 토픽을 추상 현상이 아니라 backend requirement 문장으로 작성한다.
- Topic Catalog Selection이 있으면 새 topic을 창작하지 말고 selection에 있는 Issue Topic 중 하나를 그대로 선택한다.
- 요구사항이 넓어 보여도, 다음 workforce가 바로 issue-ready로 내릴 수 있는 가장 작은 구현 slice를 우선한다.
- 넓은 epic은 별도 노트나 adjacent epic으로 남기고, commit 단계에서는 하나의 bounded slice만 고른다.
- Soft Guidance가 있으면 그것은 우선순위 힌트로만 사용하고, 실제 선택은 repo 상태와 issue-ready slice 기준으로 확정한다.

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
- (이 토픽이 전체 그림 또는 epic 구조를 어떻게 드러내는지)

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
- society를 선택했다면 Topic에는 action/state/memory/internal-external content/backend requirement 관점이 직접 드러나야 한다.
- Topic Catalog Selection이 있으면 Topic은 selection에 있는 Issue Topic 중 하나와 같아야 한다.
- 요구사항이 넓어 보여도, 최종 Topic은 지금 바로 issue-ready로 내릴 수 있는 가장 작은 implementation slice를 향해야 한다.
- 상위 목표와 epic 구조는 참고용으로만 제시하고, commit 결과는 하나의 bounded slice로 압축한다.
- Soft Guidance가 있으면 그것은 토픽 생성의 방향성 힌트로만 사용하고, 최종 선택은 issue-ready slice 기준으로 확정한다.

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
- (이 토픽이 전체 그림 또는 epic 구조를 어떻게 드러내는지)

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

SOCIETY_TOPIC_KEYWORDS = [
    "action",
    "state",
    "memory",
    "backend",
    "forum",
    "content",
    "characteristic",
    "api",
    "행동",
    "상태",
    "기억",
    "백엔드",
    "콘텐츠",
    "특성",
]


def looks_like_society_backend_topic(topic: str) -> bool:
    lowered = topic.lower()
    matches = sum(1 for keyword in SOCIETY_TOPIC_KEYWORDS if keyword in lowered)
    return matches >= 2


def replace_markdown_section(text: str, section_name: str, new_value: str) -> str:
    pattern = re.compile(
        rf"(^##\s+{re.escape(section_name)}\s*\n)(.*?)(?=\n##\s+|\Z)",
        re.M | re.S,
    )
    return pattern.sub(lambda match: match.group(1) + new_value.strip() + "\n", text, count=1)


def enforce_commitment_decision_constraints(text: str) -> str:
    workforce, topic = parse_commitment_decision(text)
    if workforce != "society" or not topic:
        return text
    if looks_like_society_backend_topic(topic):
        return text

    fallback_topic = SCENARIOS["society"]["default_topic"]
    return replace_markdown_section(text, "Topic", fallback_topic)


def normalize_topic_text(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"[\W_]+", " ", lowered, flags=re.U)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered


def parse_topic_catalog_from_context(context_pack_text: str) -> list[dict[str, str]]:
    return parse_topic_catalog_items(context_pack_text)


def parse_active_issue_titles_from_context(context_pack_text: str) -> list[str]:
    titles: list[str] = []
    for section_name in ("Active Issues", "Workspace Open Issues"):
        section = first_section(context_pack_text, section_name)
        if not section:
            continue
        for raw_line in section.splitlines():
            line = raw_line.strip()
            if not line.startswith("## #"):
                continue
            match = re.match(r"^##\s+#\d+\s+(.+)$", line)
            if match:
                titles.append(match.group(1).strip())
    return titles


def score_topic_catalog_match(candidate_text: str, topic: str) -> float:
    candidate_norm = normalize_topic_text(candidate_text)
    topic_norm = normalize_topic_text(topic)
    if not candidate_norm or not topic_norm:
        return 0.0
    if candidate_norm == topic_norm:
        return 1.0
    if candidate_norm in topic_norm or topic_norm in candidate_norm:
        return 0.95
    return SequenceMatcher(None, candidate_norm, topic_norm).ratio()


def choose_catalog_topic(topic: str, workforce: str, context_pack_text: str) -> str:
    items = parse_topic_catalog_from_context(context_pack_text)
    if not items:
        return topic

    open_issue_titles = parse_active_issue_titles_from_context(context_pack_text)
    guidance_text = context_pack_text.lower()
    operator_hub_guidance = any(
        phrase in guidance_text
        for phrase in [
            "operator hub",
            "운영 도구 허브",
            "admin surface",
            "replay viewer",
            "sprint summary",
            "state restore",
            "state 복원",
            "링크",
            "linkage",
            "continuity",
            "빈 상태",
            "empty state",
            "카드 배치",
        ]
    )
    if operator_hub_guidance:
        if any(phrase in guidance_text for phrase in ["state restore", "state 복원"]):
            operator_hub_priority = [
                "Replay viewer last viewed anchor persistence minimum",
                "Replay viewer state restore minimum",
                "Sprint summary linkage minimum",
                "Replay viewer continuity minimum",
                "Sprint summary and replay viewer continuity minimum",
                "Operator hub landing and navigation coherence minimum",
                "Metric card and empty state completeness minimum",
            ]
        elif any(phrase in guidance_text for phrase in ["linkage", "링크"]):
            operator_hub_priority = [
                "Sprint summary linkage minimum",
                "Replay viewer last viewed anchor persistence minimum",
                "Replay viewer state restore minimum",
                "Replay viewer continuity minimum",
                "Sprint summary and replay viewer continuity minimum",
                "Operator hub landing and navigation coherence minimum",
                "Metric card and empty state completeness minimum",
            ]
        else:
            operator_hub_priority = [
                "Replay viewer continuity minimum",
                "Sprint summary and replay viewer continuity minimum",
                "Operator hub landing and navigation coherence minimum",
                "Metric card and empty state completeness minimum",
                "Minimal operator visibility API",
            ]
        for preferred_topic in operator_hub_priority:
            for item in items:
                issue_topic = item.get("issue_topic", "").strip()
                if normalize_topic_text(issue_topic) == normalize_topic_text(preferred_topic):
                    return issue_topic

    if any(
        phrase in guidance_text
        for phrase in [
            "초기 운영 가능한 시스템",
            "initial operational",
            "initial operating",
            "basic crud",
            "기본 crud",
            "최소 운영 slice",
        ]
    ):
        for item in items:
            issue_topic = item.get("issue_topic", "").strip()
            if issue_topic == "Basic forum CRUD minimum":
                return issue_topic

    preferred = [
        item
        for item in items
        if item.get("preferred_workforce", "").strip().lower() == workforce.lower()
    ]
    candidates = preferred or items

    best_item = None
    best_score = 0.0
    best_non_overlapping_item = None
    best_non_overlapping_score = 0.0
    for item in candidates:
        candidate_text = " ".join(
            [
                item.get("issue_topic", "").strip(),
                item.get("title", "").strip(),
                item.get("goal", "").strip(),
                item.get("why_now", "").strip(),
            ]
        ).strip()
        score = score_topic_catalog_match(candidate_text, topic)
        if open_issue_titles:
            overlap_score = max(
                (
                    score_topic_catalog_match(candidate_text, open_issue_title)
                    for open_issue_title in open_issue_titles
                ),
                default=0.0,
            )
        else:
            overlap_score = 0.0
        if score > best_score:
            best_score = score
            best_item = item
        if overlap_score < 0.75 and score > best_non_overlapping_score:
            best_non_overlapping_score = score
            best_non_overlapping_item = item

    if best_non_overlapping_item:
        best_item = best_non_overlapping_item
    if not best_item:
        return topic

    issue_topic = best_item.get("issue_topic", "").strip() or best_item.get("key", "").strip()
    return issue_topic or topic


def enforce_commitment_topic_catalog(text: str, workforce: str, context_pack_text: str) -> str:
    parsed_workforce, topic = parse_commitment_decision(text)
    if not topic:
        return text

    selected_topic = choose_catalog_topic(topic, workforce, context_pack_text)
    if normalize_topic_text(selected_topic) == normalize_topic_text(topic):
        return text

    catalog_items = parse_topic_catalog_from_context(context_pack_text)
    selected_item = None
    for item in catalog_items:
        item_topic = item.get("issue_topic", "").strip() or item.get("key", "").strip()
        if normalize_topic_text(item_topic) == normalize_topic_text(selected_topic):
            selected_item = item
            break
    if not selected_item:
        return replace_markdown_section(text, "Topic", selected_topic)

    chosen_workforce = selected_item.get("preferred_workforce", "").strip() or parsed_workforce or workforce
    goal = selected_item.get("goal", "").strip()
    why_now = selected_item.get("why_now", "").strip()
    excludes = selected_item.get("excludes", "").strip()
    key = selected_item.get("key", "").strip() or selected_topic

    rewritten = text
    rewritten = replace_markdown_section(rewritten, "Selected Workforce", chosen_workforce)
    rewritten = replace_markdown_section(rewritten, "Topic", selected_topic)
    rewritten = replace_markdown_section(
        rewritten,
        "Why This Workforce",
        "\n".join(
            [
                f"- Topic Catalog Selection의 {key}가 현재 stage에서 가장 작은 issue-ready slice이기 때문이다.",
                f"- {chosen_workforce} 워크포스가 이 slice의 implementation boundary를 가장 직접적으로 닫을 수 있다.",
            ]
        ),
    )
    rewritten = replace_markdown_section(
        rewritten,
        "Why This Topic",
        "\n".join(
            [
                f"- {goal or selected_topic}를 지금 바로 검증 가능한 최소 구현 단위로 닫을 수 있다.",
                f"- Why now: {why_now or '현재 단계에서 가장 작은 운영 slice를 먼저 닫아야 하기 때문이다.'}",
                f"- Excludes: {excludes or '고도화 주제와 later slice는 다음 단계로 미룬다.'}",
            ]
        ),
    )
    rewritten = replace_markdown_section(
        rewritten,
        "Required Decisions",
        "\n".join(
            [
                f"- {goal or selected_topic}를 지금 수행 가능한 최소 구현 단위로 어떻게 닫을지 결정한다.",
                f"- {excludes or '고도화 주제'}를 이번 slice에서 명시적으로 제외한다.",
            ]
        ),
    )
    rewritten = replace_markdown_section(
        rewritten,
        "Risks",
        "\n".join(
            [
                f"- {selected_topic}보다 넓은 범위를 끌어오면 bounded slice가 다시 epic으로 커질 수 있다.",
                "- 카탈로그 외부의 고도화 토픽은 다음 RFC나 later slice로 넘겨야 한다.",
            ]
        ),
    )
    rewritten = replace_markdown_section(
        rewritten,
        "Issue Title",
        selected_topic,
    )
    rewritten = replace_markdown_section(
        rewritten,
        "Summary",
        "\n".join(
            [
                f"- {goal or selected_topic}",
                f"- {why_now or '초기 운영 가능한 시스템을 먼저 닫아야 한다.'}",
                f"- {excludes or '고도화 주제는 이번 범위 밖이다.'}",
            ]
        ),
    )
    rewritten = replace_markdown_section(rewritten, "Priority", "High")
    return rewritten


def ensure_section_has_bullets(text: str, section_name: str, bullets: list[str]) -> str:
    current = first_section(text, section_name)
    if not current:
        block = "## " + section_name + "\n" + "\n".join(f"- {item}" for item in bullets) + "\n"
        return text.strip() + "\n\n" + block

    existing_lines = bullet_lines(current)
    missing = [item for item in bullets if item not in existing_lines]
    if not missing:
        return text

    augmented = current.rstrip() + "\n" + "\n".join(f"- {item}" for item in missing)
    return replace_markdown_section(text, section_name, augmented)


def enforce_society_decision_constraints(text: str) -> str:
    if not text.strip():
        return text

    enforced = text
    enforced = ensure_section_has_bullets(
        enforced,
        "Technical Notes",
        [
            "forum 내부 콘텐츠 소비와 외부 web 콘텐츠 소비를 같은 state model과 memory writeback 경로에 연결해야 한다.",
            "API contract는 action request, state snapshot, trace/event 저장 경로를 함께 정의해야 한다.",
        ],
    )
    enforced = ensure_section_has_bullets(
        enforced,
        "Required Artifacts",
        [
            "internal forum content consumption trace",
            "external web content ingestion/event trace",
            "state snapshot 및 action/event 저장 구조",
            "forum artifact(post/comment/react) 생성 및 기록 규약",
        ],
    )
    enforced = ensure_section_has_bullets(
        enforced,
        "Acceptance Criteria",
        [
            "[ ] forum 내부 콘텐츠 소비와 외부 web 콘텐츠 소비가 같은 state model에 누적되는 방식이 정의되었다.",
            "[ ] action request, trace, snapshot, forum artifact를 포함한 API/backend contract가 정의되었다.",
        ],
    )
    enforced = ensure_section_has_bullets(
        enforced,
        "Next Actions",
        [
            "internal/external content ingestion과 memory writeback을 포함한 action-state contract를 문서화한다.",
            "trace, snapshot, event, forum artifact를 저장할 backend/API schema를 정의한다.",
        ],
    )
    enforced = ensure_section_has_bullets(
        enforced,
        "Summary",
        [
            "forum 내부 콘텐츠와 외부 web 콘텐츠 소비를 같은 state/action backend로 연결해야 한다.",
        ],
    )
    return enforced

SCENARIOS = {
    "commitment": {
        "label": "논의 방향 결정",
        "roles_file": SCRIPT_DIR / "commitment_roles.yaml",
        "default_topic": "현재 프로젝트에서 결정되지 않은 가장 중요한 gap은 무엇이며, 어떤 workforce로 어떤 토픽을 논의해야 하는가?",
        "workforce_description": "AI-Fashion-Forum Commitment Workforce: Project State Analyst, Workforce Selector, Topic Architect, Commitment Critic이 협력하여 다음 논의의 workforce와 토픽을 결정합니다.",
        "participants": "Project State Analyst, Workforce Selector, Topic Architect, Commitment Critic",
        "title": "🎯 AI-Fashion-Forum — Commitment Workforce",
        "arg_description": "CAMEL Workforce 기반 논의 방향 결정 엔진",
        "build_task_prompt": lambda topic: f"""AI-Fashion-Forum 프로젝트의 다음 논의 방향을 결정하세요.

## 현재 상황 / 결정해야 할 것
{topic}

## 이번 토론의 목적
이 토론은 시뮬레이션 환경을 직접 설계하는 것이 아닙니다.
"어떤 workforce로 어떤 토픽을 논의해야 하는가"를 결정하는 메타 토론입니다.
commitment는 방향만 정하고, issue-ready 판정과 issue 발급은 별도 단계에서 처리합니다.
commitment는 가능한 한 가장 작은 issue-ready slice를 고르는 데 집중하고, 넓은 epic은 이후 작업이나 노트로 넘기십시오.

## 사용 가능한 workforce
- society: stateful AI agent 행동/정체성 backend 설계 (행동 루프, 상태, 기억, 내부/외부 콘텐츠 소비)
- operator: 운영자 관점의 컨텐츠 자정, 모니터링, 기능 개선 설계 (메트릭, 트레이스, 개입 레버, 운영 정책)
- core: development 팀의 mock → 실서비스 전환 설계 (기술 스택, 아키텍처, 구현 범위, 배포)
- default: 시뮬레이션 환경 범용 설계 (위 세 가지에 속하지 않는 범용 설계)

## 중요한 라우팅 규칙
- source repo intent에 agent-loop, action-space, identity-update-rules, state-schema 같은 구현 신호가 있으면 society 논의는 추상 사회 현상보다 agent backend requirement를 우선해야 한다
- society를 선택했다면 topic은 "어떤 상태/기억/행동/API contract가 필요한가" 형태여야 하며, 단순 갈등/현상 묘사로 끝나면 안 된다
- operator를 선택했다면 topic은 운영자가 관찰/개입/자정/개선할 레버를 포함해야 한다
- core를 선택했다면 topic은 development 팀이 실제로 구현하고 마이그레이션할 범위를 포함해야 한다
- issue-ready 여부는 별도 게이트가 판단한다. commitment는 workforce와 토픽을 정하고, 실제 발급은 bounded implementation slice에 대해서만 진행한다.

## 토론 규칙
1. Project State Analyst: 현재 상황에서 결정되지 않은 gap을 분석하라
2. Workforce Selector: 이 gap의 성격에 맞는 workforce를 선택하고 근거를 제시하라
3. Topic Architect: 선택된 workforce의 역할 충돌이 드러나는 토픽 문자열을 설계하라
4. Commitment Critic: workforce 선택과 토픽의 품질을 검증하고 문제점을 지적하라

## 현재 상황 해석 규칙
- Current Situation, Source Repo State, Latest Workforce State에 있는 내용을 최우선 근거로 사용하라
- 최신 handoff에 이미 있는 결정을 반복하지 말고, 아직 비어 있는 다음 결정을 찾는 데 집중하라
- Git 상태가 clean이면 "코드 변경 자체"보다 "다음에 어떤 결정을 내려야 구현/운영이 이어지는가"를 우선 판단하라
- 최근 커밋이나 latest workforce state가 특정 방향을 가리키면, 그 방향을 그대로 따를지 수정할지 명시적으로 판단하라
- Issue Execution History는 이미 처리된 내용의 맥락으로만 사용하고, society 재선택을 금지하는 신호로 쓰지 말라

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
- 현재 상황 요약 없이 곧바로 일반론적인 gap을 제시하지 말라
- society를 선택했다면 토픽에 action loop, state, memory, characteristic, internal/external content, backend requirement 중 여러 요소가 직접 드러나야 한다
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
        "default_topic": "API 기반 forum 위에서 AI agent가 실제로 post/comment/react/lurk/silence를 수행하면서 내부 forum 콘텐츠와 외부 web 콘텐츠를 소비하고, stateful characteristic을 유지하거나 발전시키려면 어떤 상태, 기억, 행동 규칙을 backend에 구현해야 하는가?",
        "workforce_description": "AI-Fashion-Forum 이용자 조직 시뮬레이션 토론 팀: Society Modeling Lead, Identity & Memory Architect, Community Dynamics Researcher, Simulation Critic이 협력하여 API 기반 forum 위에서 action하는 stateful AI agent backend 요구사항을 도출합니다.",
        "participants": "Society Modeling Lead, Identity & Memory Architect, Community Dynamics Researcher, Simulation Critic",
        "title": "🏢 AI-Fashion-Forum — 이용자 조직 시뮬레이션 토론",
        "arg_description": "CAMEL Workforce 기반 이용자 조직 시뮬레이션 토론 엔진",
        "build_task_prompt": lambda topic: f"""AI-Fashion-Forum 프로젝트의 forum 안에서 action하는 AI agent backend 요구사항을 토론하세요.

## 토론 주제
{topic}

## 프로젝트 맥락
- AI-Fashion-Forum에는 이미 sim-server의 agent-loop, agent-core의 action-space, memory-stack, identity-update-rules, forum-generation이 존재한다
- 목표는 development 팀이 마이그레이션한 API 기반 forum 위에서 AI agent가 실제로 post/comment/react/lurk/silence를 수행하는 backend 시스템을 만드는 것이다
- agent는 특정 취향 경향성, belief, social posture, self narrative를 가져야 하고, 콘텐츠 노출과 memory writeback을 통해 그 경향성이 유지되거나 바뀌어야 한다
- agent는 forum 내부 콘텐츠와 필요시 외부 web 콘텐츠를 모두 소비할 수 있어야 하며, 그 소비 결과가 같은 state 모델에 누적되어야 한다
- 패션 취향 분화나 갈등은 목표가 아니라, 이런 backend가 잘 동작할 때 나타나는 관찰 가능한 결과다
- 이번 토론의 핵심은 "어떤 사회 현상이 재미있는가?"가 아니라 "어떤 agent state/action backend requirement가 있어야 포럼 안에서 살아 있는 행동이 나오나?"이다
- 그리고 그 요구사항이 전체 제품 그림에서 어떤 epic을 이루는지도 함께 드러내라
- 이 답변은 구현 세부보다 capability 수준의 epic discovery가 우선이다
- 최소 3개 이상의 capability epic 후보를 먼저 제시하고, 그중 하나를 This Epic으로 고르라

## 토론 규칙
1. Society Modeling Lead: agent backend가 먼저 지원해야 할 action loop를 정의하라
2. Identity & Memory Architect: 상태, 기억, 노출, 관계, 행동 규칙을 설계하라
3. Community Dynamics Researcher: 실제 패션 커뮤니티와 맞는 backend action/state 모델인지 검증하라
4. Simulation Critic: 설명 불가능성, 누락된 action/state, 실패 시나리오를 지적하라

## 기대 산출물
- Program Goal / Epic Landscape / This Epic / Adjacent Epics / Dependencies / Out of Scope
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
- 사회 일반론보다 agent backend requirement를 우선하라
- post/comment/react/lurk/silence/action trace/state snapshot/internal-external consumption loop 같은 구체적인 backend 단위를 반드시 포함하라
- agent의 취향 경향성, belief 변화, memory writeback이 action 선택과 어떻게 연결되는지 구체적으로 적어라
- forum 내부 콘텐츠 소비와 외부 web 콘텐츠 소비가 같은 characteristic 진화 루프에 어떻게 연결되는지 구체적으로 적어라
- 단순 추천 앱 기능 논의나 커뮤니티 일반론으로 축소하지 말라
- Action Loop, State Model, State Transitions, Content Consumption, Required Backend Artifacts를 빠뜨리지 말라
- Action Loop에서는 반드시 아래 필드명을 그대로 사용하라: Trigger Condition, State Read, State Write, Example State Transition A, Example State Transition B, Successful Outcome, Success Metric, Artifact
- Action Loop에서는 post/comment/react/lurk/silence 각각을 별도 소제목으로 나눠라
- Example State Transition A/B에는 이 action이 어떤 state를 바꾸고 다음 action bias를 어떻게 만드는지 서로 다른 예시로 적어라
- Success Metric에는 포럼에서 관찰 가능한 성공 기준을 적어라
- Required Backend Artifacts에서는 각 artifact가 왜 필요한지 적어라
- Required Backend Artifacts에서는 trace / snapshot / event / stored action / forum artifact 각각에 대해, 어떤 action/state와 연결되는지와 왜 운영적으로 필수인지 적어라
- State Transitions에서는 state change가 다음 행동 선택에 어떤 영향을 주는지 적어라
- State Model에는 characteristic, belief, memory, mutable axes, relationship state를 모두 포함하라
- Identity & Memory Architect 관련 응답에서는 State Model, Memory Writeback Rules, Action Selection Links, Content Consumption Merge, Replayable Backend Requirements를 빠뜨리지 말라
- Identity & Memory Architect 관련 응답에서는 각 state field가 어떤 행동 결과를 만들고, 각 action이 어떤 state를 읽어 어떤 bias를 만드는지까지 적어라
- Identity & Memory Architect 관련 응답에서는 각 state field마다 어떤 trace/snapshot/event/stored action이 필요한지도 적어라
- 먼저 상위 목표와 epic 지도를 제시한 뒤, 이번 backend contract가 그중 어디에 속하는지 밝혀라
- Required output은 capability-level epic landscape를 먼저 쓰고, 그 다음 implementation hints를 적는 순서여야 한다
""",
        "coordinator_prompt": COMMON_COORDINATOR_PROMPT + "\n추가 규칙: 이번 토론은 forum 안에서 action하는 AI agent backend 요구사항에 집중한다. 추상적인 사회 현상보다 action loop, state schema, memory writeback, observable trace를 우선한다. 상위 epic 구조는 참고로만 보여주고, 최종 issue는 반드시 가장 작은 bounded slice로 압축하라. capability 후보는 3개 이내로 제한하고, 이번 run에서 실제로 발급 가능한 slice만 남겨라.\n",
        "final_prompt": COMMON_FINAL_SYNTHESIZER_PROMPT + "\n추가 규칙: 최종 결과는 AI agent backend가 구현해야 할 action loop, state/memory requirement, observable trace, forum artifact 생성을 우선 정리하되, 먼저 Program Goal과 Epic Landscape를 제시하고 capability-level epic 후보는 3개 이내로 제한하라. 최종 issue는 반드시 지금 바로 발급 가능한 가장 작은 bounded slice여야 한다.\n",
        "round_focus_guide": {
            1: "agent가 forum 안에서 어떤 action loop를 가져야 하는지 정의하되, 이번 run에서 실제로 issue-ready로 압축할 수 있는 가장 작은 backend slice가 무엇인지 먼저 고르라.",
            2: "상태, 기억, 관계, 노출, 행동 스키마와 action 선택 규칙을 구체화하되, epic map은 참고용으로만 두고 하나의 bounded slice로 좁혀라.",
            3: "agent의 경향성 형성, belief 변화, 실패 시나리오, 하드코딩처럼 보이는 위험을 점검하되, 나머지 capability는 adjacent epic으로 남기고 이번 slice의 경계만 확정하라.",
            4: "trace, snapshot, metric, artifact를 구체화하되, 운영 가능한 최소 계약 하나만 남기고 그 외는 다음 issue로 미뤄라.",
            5: "이슈로 옮길 수 있게 AI agent backend 요구사항과 epic 경계를 정리하되, 최종 결과는 단일 bounded slice여야 한다.",
        },
        "synthesis_prompt": """위 결과를 바탕으로:
1. forum 안에서 AI agent가 먼저 지원해야 할 action loop를 추출하고
2. capability-level epic 후보를 3개 이내로 정리하고
3. 이 backend contract가 속한 상위 목표와 epic landscape를 간단히 정리한 뒤 This Epic을 선택하되
4. 최종 결과는 지금 바로 GitHub Issue로 등록 가능한 가장 작은 bounded slice로 압축하고
5. 필요한 상태, 기억, 관계, 행동 규칙과 trace/snapshot/forum artifact를 그 slice에 필요한 만큼만 적고
6. 나머지 범위는 adjacent epic 또는 open question으로 넘겨라.

Acceptance Criteria는 실제 구현/검증 가능한 체크리스트로 작성하라.
agent backend requirement와 반복 실험 가능성을 우선하라.
""",
    },
    "core": {
        "label": "Development 팀",
        "roles_file": SCRIPT_DIR / "core_roles.yaml",
        "default_topic": "현재 mock으로 구현된 패션 포럼을 실제 동작하는 API 기반 서비스로 만들기 위해 먼저 결정해야 할 development 계획은 무엇인가?",
        "workforce_description": "AI-Fashion-Forum Development 팀 토론: CTO, Backend Engineer, Product Manager, Development Critic이 협력하여 현재 mock을 실제 동작하는 서비스로 전환하는 핵심 개발 계획을 도출합니다.",
        "participants": "CTO, Backend Engineer, Product Manager, Development Critic",
        "title": "🚀 AI-Fashion-Forum — Development 팀 토론",
        "arg_description": "CAMEL Workforce 기반 development 팀 토론 엔진",
        "build_task_prompt": lambda topic: f"""AI-Fashion-Forum 프로젝트에서 현재 mock을 실제 서비스로 전환하는 development 계획을 토론하세요.

## 토론 주제
{topic}

## 프로젝트 맥락
- 현재 상태: React mock UI + 바닐라 Node.js 시뮬레이션 서버 + agent-core JS 모듈로 구성된 npm 모노레포
- mock은 정적 시드 데이터로 UI를 렌더링하는 수준이며, 에이전트가 실시간으로 동작하지 않는다
- agent-core에는 content-pipeline, memory-stack, identity-update-rules, forum-generation 등의 로직이 이미 있다
- 목표: AI 에이전트가 실제로 포럼에서 포스트를 작성하고 상호작용하는 동작하는 서비스를 만든다
- 이번 Workforce의 핵심 질문은 "이 mock을 어떻게 실제 서비스로 전환할 것인가?"이다
- 운영 조직 설계나 이용자 조직 모델 일반론보다 먼저, 현재 코드베이스를 어떻게 서비스로 연결할지에 집중하라
- 이 계획이 전체 서비스 로드맵에서 어떤 epic 묶음을 이루는지도 함께 보여줘야 한다
- 이번 답변은 구현 슬라이스보다 먼저 전체 제품 그림을 그리는 epic discovery 단계다
- 최소 3개에서 5개의 epic 후보를 먼저 제시한 뒤, 그중 하나를 This Epic으로 선택하라
- 구현 세부를 말하더라도 반드시 어떤 상위 epic을 위한 것인지 먼저 밝혀라
- Epic Landscape는 기술 스택이 아니라 제품 capability / data contract / operational capability 수준으로만 적어라
- Express.js, MongoDB, WebSocket 같은 구현 선택은 Epic Landscape가 아니라 Technical Notes나 Migration Plan에 둬라
- This Epic은 "무엇을 가능하게 하는가"로 표현하고, "어떻게 구현하는가"는 뒤로 미뤄라

## 토론 규칙
1. CTO: 기술 스택 선택과 아키텍처 결정을 주도하라
2. Backend Engineer: 첫 번째로 구현할 코드 범위와 실제 동작 루프를 정의하라
3. Product Manager: 개발 범위와 우선순위, 성공 기준을 정의하라
4. Development Critic: 각 결정의 위험성, 실패 시나리오, 대안을 제시하라

## 기대 산출물
- Program Goal / Epic Landscape / This Epic / Adjacent Epics / Dependencies / Out of Scope
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
- 이 답변이 담당하는 epic이 무엇인지와, 옆에 존재해야 하는 다른 epic이 무엇인지 구분하라
- 구현 슬라이스를 너무 빨리 확정하지 말고, 먼저 Epic Landscape를 넓게 펼친 뒤 This Epic을 선택하라
- Epic Landscape는 반드시 capability 수준의 불릿 4~7개로만 작성하라
- Technology choices는 반드시 `Technical Notes`에만 남겨라
""",
        "coordinator_prompt": COMMON_COORDINATOR_PROMPT + "\n추가 규칙: 이번 토론은 development 팀이 현재 mock을 실제 서비스로 전환하는 계획에 집중한다. 추상적인 설계보다 실제 구현 가능한 첫 번째 동작 루프와 전환 단계를 우선하되, 결과는 반드시 하나의 bounded implementation slice로 압축하라. 전체 로드맵은 참고로만 두어라.\n",
        "final_prompt": COMMON_FINAL_SYNTHESIZER_PROMPT + "\n추가 규칙: 최종 결과는 mock-to-service 전환 목표, 첫 번째 구현 범위, 코드베이스 전환 계획을 중심으로 development 계획을 정리하되, 먼저 Program Goal과 Epic Landscape를 제시하고 최종 issue는 가장 작은 구현 slice로 제한하라.\n",
        "round_focus_guide": {
            1: "현재 mock이 왜 아직 서비스가 아닌지와 development 팀의 정확한 범위를 정의하되, 이번 run에서 실제로 구현 가능한 가장 작은 slice를 먼저 찾으라.",
            2: "후보 epic들을 capability 수준으로 비교하되, This Epic은 하나의 직접 구현 가능한 루프만 남기고 나머지는 Adjacent Epics / Dependencies로 남겨라.",
            3: "mock-to-service 전환 과정의 리스크, 기술 부채, 실패 시나리오를 점검하되, 이번 slice의 경계를 흐리지 않도록 하라.",
            4: "개발 우선순위와 마이그레이션 순서를 압축하되, 실제 issue로 옮길 수 있는 최소 범위를 고정하라.",
            5: "이슈로 옮길 수 있게 mock-to-service 실행 계획과 epic 경계를 정리하되, 결과는 단일 bounded slice여야 한다.",
        },
        "synthesis_prompt": """위 결과를 바탕으로:
1. 현재 mock을 실제 서비스로 전환하기 위한 핵심 목표와 성공 기준을 추출하고
2. 후보 epic과 전체 서비스화 epic landscape를 간단히 정리한 뒤
3. 이 중 하나의 This Epic을 선택하되, 선택 이유와 제외한 epic을 함께 적고
4. 기술 스택 선택과 첫 번째 구현 범위를 정리하고
5. mock-to-service 마이그레이션 순서와 개발 우선순위를 제시하되
6. 바로 GitHub Issue로 등록 가능한 가장 작은 실행 초안으로 압축하라.

Acceptance Criteria는 실제 구현/검증 가능한 체크리스트로 작성하라.
"지금 당장 작동하는 것"을 만드는 데 필요한 최소 범위를 우선하라.
""",
    },
    "operator": {
        "label": "운영자 조직",
        "roles_file": SCRIPT_DIR / "operator_roles.yaml",
        "default_topic": "포럼 운영자가 컨텐츠 자정, 모니터링, 기능 개선사항 도출을 위해 먼저 정의해야 할 관찰 프레임, 개입 레버, 운영 루프는 무엇인가?",
        "workforce_description": "AI-Fashion-Forum 운영자 조직 토론 팀: Operator Strategy Lead, Measurement & Intervention Architect, Moderation & Policy Designer, Operator Critic이 협력하여 운영자 관점의 자정/모니터링/개선 설계안을 도출합니다.",
        "participants": "Operator Strategy Lead, Measurement & Intervention Architect, Moderation & Policy Designer, Operator Critic",
        "title": "🏢 AI-Fashion-Forum — 운영자 조직 토론",
        "arg_description": "CAMEL Workforce 기반 운영자 조직 토론 엔진",
        "build_task_prompt": lambda topic: f"""AI-Fashion-Forum 프로젝트의 운영자 조직(포럼을 모니터링하고 자정하며 개선 포인트를 도출하는 조직)을 토론하세요.

## 토론 주제
{topic}

## 프로젝트 맥락
- 운영자 조직은 이용자 조직의 행동, 로그, 인터뷰, 트레이스, 메트릭을 관찰한다
- 운영자 조직은 온보딩, 카테고리, 추천 설정, 개입 정책, moderation rule, 실험 플래그, 기능 개선 후보를 다룬다
- 목표는 포럼을 단순 구축하는 것이 아니라, 컨텐츠 자정과 모니터링을 수행하고 다음 기능 개선사항을 도출하는 것이다
- 핵심은 어떤 운영 루프와 개입 수단이 있어야 다음 시뮬레이션/제품 개선 런을 설계할 수 있는지 정의하는 것이다
- 이 운영 설계가 전체 제품 전략에서 어떤 epic 묶음을 이루는지도 함께 드러내라
- 이 답변은 구현 디테일보다는 capability 수준의 운영 epic discovery가 우선이다
- 최소 3개 이상의 운영 capability epic 후보를 먼저 제시하고, 그중 하나를 This Epic으로 고르라

## 토론 규칙
1. Operator Strategy Lead: 운영자 조직이 먼저 풀어야 할 운영 질문을 정의하라
2. Measurement & Intervention Architect: 메트릭, 트레이스, 대시보드, 실험 레버를 설계하라
3. Moderation & Policy Designer: 카테고리, 온보딩, 추천, moderation, 자정 정책을 설계하라
4. Operator Critic: 설명 불가능한 개입, 측정 불가능한 운영 루프, 잘못된 개선 결론, 누락된 관찰 프레임을 지적하라

## 기대 산출물
- Program Goal / Epic Landscape / This Epic / Adjacent Epics / Dependencies / Out of Scope
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
- 운영자 조직의 관찰 루프와 개입 루프를 우선 정리하라
- 일반 제품 기능 우선순위 회의로 축소하지 말라
- 컨텐츠 자정, 모니터링, 개선사항 도출이 어떤 artifact와 기준으로 이뤄지는지 구체적으로 적어라
- 이 답변이 전체 운영 epic map에서 어디에 위치하는지 보여줘야 한다
- Required output은 capability-level epic landscape를 먼저 쓰고, 그 다음 운영 레버를 적는 순서여야 한다
""",
        "coordinator_prompt": COMMON_COORDINATOR_PROMPT + "\n추가 규칙: 이번 토론은 운영자 조직 설계에 집중한다. 포럼 구축보다 컨텐츠 자정, 모니터링, 개선 포인트 도출을 위한 관찰 프레임과 개입 레버를 우선하되, 결과는 하나의 bounded operational slice로 압축하라. 전체 운영 epic map은 참고용으로만 두고 capability 후보는 3개 이내로 정리하라.\n",
        "final_prompt": COMMON_FINAL_SYNTHESIZER_PROMPT + "\n추가 규칙: 최종 결과는 운영자 조직의 관찰 체계, 자정 정책, 개선 레버, 운영 아티팩트를 우선 정리하되, 먼저 Program Goal과 Epic Landscape를 제시하고 capability-level epic 후보는 3개 이내로 제한하라. 최종 issue는 지금 바로 실행 가능한 최소 운영 slice여야 한다.\n",
        "round_focus_guide": {
            1: "운영자 조직이 먼저 답해야 할 운영 질문과 개입 목표를 정의하되, 이번 run에서 바로 issue로 옮길 수 있는 최소 관찰/개입 slice를 먼저 찾으라.",
            2: "메트릭, 대시보드, 인터뷰, 트레이스, 정책 레버를 구체화하되, 전체 운영 구조보다 하나의 bounded 운영 slice를 우선하라.",
            3: "측정 불가능한 개입, 운영 리스크, 정책 충돌을 점검하되, 이번 slice의 경계만 고정하고 나머지는 adjacent epic으로 넘겨라.",
            4: "반복 운영 루프와 기능 개선 우선순위를 압축하되, 실제 issue로 발급할 최소 단위를 정하라.",
            5: "이슈로 옮길 수 있게 운영자 조직 설계안과 개선 계획을 정리하되, 결과는 단일 bounded slice여야 한다.",
        },
        "synthesis_prompt": """위 결과를 바탕으로:
1. 운영자 조직이 먼저 고정해야 할 관찰 프레임과 개입 목표를 추출하고
2. capability-level 운영 epic 후보를 3개 이내로 정리하고
3. 전체 운영 epic landscape를 간단히 정리한 뒤 This Epic을 선택하되
4. 어떤 메트릭, 인터뷰, 트레이스, 자정 정책, 개선 레버가 필요한지 정리하고
5. 어떤 운영 아티팩트와 반복 루프가 있어야 다음 런과 다음 기능 개선을 설계할 수 있는지 정리하되
6. 바로 GitHub Issue로 등록 가능한 가장 작은 실행 초안으로 압축하라.

Acceptance Criteria는 실제 구현/검증 가능한 체크리스트로 작성하라.
운영자 조직의 관찰, 자정, 개선 가능성을 우선하라.
""",
    },
}


def load_roles(roles_file: Path) -> dict:
    """역할 정의 파일을 로드합니다."""
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError(
            "PyYAML 의존성이 설치되지 않았습니다. `pip install -e .` 후 다시 실행하세요."
        ) from exc

    with open(roles_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_model(model_name: str = "gpt-4o-mini"):
    """OpenAI 모델을 생성합니다."""
    runtime = camel_runtime()
    ModelFactory = runtime["ModelFactory"]
    ModelPlatformType = runtime["ModelPlatformType"]
    ModelType = runtime["ModelType"]
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


def extract_agent_text(response: Any) -> str:
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
    share_memory: bool = False,
) -> Any:
    """역할 설정을 기반으로 Workforce를 구성합니다."""
    runtime = camel_runtime()
    ChatAgent = runtime["ChatAgent"]
    SingleAgentWorker = runtime["SingleAgentWorker"]
    Workforce = runtime["Workforce"]
    FailureHandlingConfig = runtime["FailureHandlingConfig"]

    roles = roles_config["roles"]
    model = create_model(model_name)

    workers = []
    for role_key, role_def in roles.items():
        agent = ChatAgent(
            system_message=(
                role_def["system_prompt"].strip()
                + "\n\n"
                + WORKER_OUTPUT_RULES
                + "\n\n"
                + EPIC_FRAME_OUTPUT_FORMAT
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

    # replan/decompose 전략은 새 task 인스턴스를 생성하여 failure_count를 0으로
    # 리셋하므로 retry limit에 도달하지 못하는 무한 루프를 유발한다.
    # enabled_strategies=[] 로 설정하면 품질 평가 자체를 건너뛰고 task를
    # 즉시 완료 처리하여 무한 루프를 방지한다.
    failure_config = FailureHandlingConfig(
        max_retries=2,
        enabled_strategies=[],
        halt_on_max_retries=False,
    )

    workforce = Workforce(
        description=scenario["workforce_description"],
        children=workers,
        coordinator_agent=coordinator,
        task_agent=task_agent,
        use_structured_output_handler=False,
        share_memory=share_memory,
        failure_handling_config=failure_config,
    )

    return workforce


def run_commitment_decision(
    scenario: dict,
    model_name: str,
    topic: str,
    handoff_text: str = "",
    context_pack_text: str = "",
) -> tuple[list[dict[str, str]], str]:
    """commitment는 단일 decision agent로 실행한다."""
    ChatAgent = camel_runtime()["ChatAgent"]
    model = create_model(model_name)
    decision_agent = ChatAgent(system_message=scenario["final_prompt"], model=model)

    prompt = f"""{scenario["build_task_prompt"](topic)}

## Operating Mode
- 이번 commitment 실행은 다중 workforce orchestration이 아니라 단일 decision agent 모드다.
- Current Situation, Source Repo State, Latest Workforce State를 먼저 읽고 이미 제안된 방향을 그대로 유지할지 수정할지 판단하라.
- 일반론이 아니라 현재 입력에 있는 근거를 직접 인용하듯 활용하라.

## Handoff Context
{handoff_text if handoff_text else "- 이전 workforce handoff 없음"}

## External Context Pack
{context_pack_text if context_pack_text else "- external context pack 없음"}

## Additional Instructions
- 먼저 현재 상황에서 이미 결정된 것과 아직 막힌 것을 짧게 식별하라.
- 그 다음 하나의 workforce와 하나의 topic만 확정하라.
- Topic에는 `--topic` 접두사를 넣지 말고 완성된 문장만 적어라.
- Latest Workforce State의 제안을 그대로 유지한다면 그 이유를 쓰고, 바꾼다면 왜 바꾸는지 명시하라.
- Topic Catalog Selection이 있으면 selection 외부의 새 topic을 만들지 말고 가장 작은 selection item을 선택하라.
- Soft Guidance가 있으면 그 문장을 그대로 따르기보다, 이번 run에서 가장 작은 issue-ready slice를 고르는 방향으로 반영하라.
"""
    response = decision_agent.step(prompt)
    final_result = enforce_commitment_decision_constraints(extract_agent_text(response))
    final_result = enforce_commitment_topic_catalog(final_result, "commitment", context_pack_text)
    round_results = [
        {
            "round": "1",
            "raw_result": final_result,
            "normalized_result": normalize_issue_text(final_result),
        }
    ]
    return round_results, final_result


def build_round_task_prompt(
    scenario: dict,
    topic: str,
    round_number: int,
    total_rounds: int,
    history: list[str],
    handoff_text: str = "",
    context_pack_text: str = "",
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

## Input Contract
- 이 workforce는 현재 topic만 보는 것이 아니라, 이전 workforce handoff와 external context pack이 있으면 함께 반영해야 한다.
- 이미 확정된 결정은 불필요하게 다시 논쟁하지 말고, 이번 workforce의 전문 레이어에서 필요한 다음 결정을 우선한다.

## Handoff Context
{handoff_text if handoff_text else "- 이전 workforce handoff 없음"}

## External Context Pack
{context_pack_text if context_pack_text else "- external context pack 없음"}

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
    workforce: Any,
    scenario: dict,
    topic: str,
    rounds: int,
    handoff_text: str = "",
    context_pack_text: str = "",
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
            handoff_text=handoff_text,
            context_pack_text=context_pack_text,
        )
        Task = camel_runtime()["Task"]
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
    handoff_text: str = "",
    context_pack_text: str = "",
) -> str:
    """라운드별 토론 결과를 최종 환경 설계 + 실행 Issue 초안으로 합성합니다."""
    model = create_model(model_name)
    ChatAgent = camel_runtime()["ChatAgent"]
    synthesizer = ChatAgent(system_message=scenario["final_prompt"], model=model)
    compiled_rounds = "\n\n".join(
        [
            f"## Round {item['round']}\n{item['normalized_result']}"
            for item in round_results
        ]
    )
    prompt = f"""다음은 AI-Fashion-Forum 프로젝트 주제에 대한 다중 라운드 Workforce 토론 결과다.

## Topic
{topic}

## Handoff Context
{handoff_text if handoff_text else "- 이전 workforce handoff 없음"}

## External Context Pack
{context_pack_text if context_pack_text else "- external context pack 없음"}

## Round Results
    {compiled_rounds}

{scenario["synthesis_prompt"]}"""
    response = synthesizer.step(prompt)
    final_text = extract_agent_text(response)
    if scenario.get("label") == "이용자 조직 시뮬레이션":
        final_text = enforce_society_decision_constraints(final_text)
    return final_text


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


def extract_handoff_targets(workforce_key: str, decision_text: str) -> tuple[str, str]:
    """최종 결정문에서 다음 workforce와 topic 후보를 추출합니다."""
    if workforce_key == "commitment":
        return parse_commitment_decision(decision_text)
    return "", ""

def clean_issue_item(text: str) -> str:
    stripped = text.strip()
    stripped = re.sub(r"^\[[ xX]\]\s*", "", stripped)
    stripped = re.sub(r"^\d+\.\s*", "", stripped)
    return stripped.strip(" -")


def unique_nonempty(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = clean_issue_item(item)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def rotate_assignee(task_assignees: list[str], index: int) -> str:
    if not task_assignees:
        return ""
    return task_assignees[index % len(task_assignees)]


def shorten_title(text: str, prefix: str = "", limit: int = 90) -> str:
    full = f"{prefix}{text}".strip()
    if len(full) <= limit:
        return full
    return full[: limit - 1].rstrip() + "…"


def extract_issue_title(result_text: str, default: str = "feat: requirement from workforce debate") -> str:
    title = first_section(result_text, "Issue Title").splitlines()
    if title:
        return title[0].strip().strip("#").strip().strip('"')
    return default


def extract_issue_summary_items(result_text: str) -> list[str]:
    return unique_nonempty(bullet_lines(first_section(result_text, "Summary")))


def extract_next_action_items(result_text: str) -> list[str]:
    candidates = bullet_lines(first_section(result_text, "Next Actions"))
    if not candidates:
        candidates = bullet_lines(first_section(result_text, "Acceptance Criteria"))
    return unique_nonempty(candidates)


def extract_acceptance_criteria_items(result_text: str) -> list[str]:
    return unique_nonempty(bullet_lines(first_section(result_text, "Acceptance Criteria")))


def extract_open_question_items(result_text: str) -> list[str]:
    return unique_nonempty(bullet_lines(first_section(result_text, "Open Questions")))


def assess_issue_readiness(
    result_text: str,
    workforce_key: str,
    issue_type: str,
) -> tuple[bool, list[str]]:
    title = extract_issue_title(result_text, default="").strip()
    summary_items = extract_issue_summary_items(result_text)
    next_actions = extract_next_action_items(result_text)
    acceptance_items = extract_acceptance_criteria_items(result_text)
    open_questions = extract_open_question_items(result_text)

    reasons: list[str] = []
    if not title or title.lower() == "feat: requirement from workforce debate":
        reasons.append("Issue Title이 비어 있거나 기본값 수준이다.")
    if workforce_key == "commitment":
        reasons.append("commitment 결과는 직접 issue보다 다음 workforce handoff에 더 적합하다.")
    if len(summary_items) < 2 and len(first_section(result_text, "Summary").strip().splitlines()) < 2:
        reasons.append("Summary가 너무 얕아서 작업 배경 설명이 부족하다.")
    if len(acceptance_items) < 2:
        reasons.append("Acceptance Criteria가 최소 2개 미만이라 완료 기준이 불명확하다.")
    if issue_type == "bundle":
        if len(next_actions) < 2:
            reasons.append("bundle issue를 만들 만큼 분리된 Next Actions가 충분하지 않다.")
    else:
        if not next_actions:
            reasons.append("바로 착수할 Next Actions가 없다.")

    placeholder_markers = ("TBD", "추후", "나중", "미정")
    placeholder_hits = sum(
        1
        for item in [title, *summary_items, *next_actions, *acceptance_items, *open_questions]
        if any(marker in item for marker in placeholder_markers)
    )
    if placeholder_hits >= 2:
        reasons.append("결과에 placeholder 성격의 표현이 많아 아직 작업 단위로 굳지 않았다.")

    return (len(reasons) == 0, reasons)


def issue_labels_for_type(
    issue_type: str,
    extra_labels: Optional[list[str]] = None,
    epic_label: Optional[str] = None,
) -> list[str]:
    labels = ["enhancement", "project:catalog-loop"]
    if issue_type == "epic":
        labels.append("type:epic")
    if epic_label:
        labels.append(epic_label)
    if extra_labels:
        labels.extend(extra_labels)
    return unique_nonempty(labels)


def normalize_issue_title(title: str) -> str:
    text = title.strip()
    text = re.sub(r"^(epic|task|sprint)\s*:\s*", "", text, flags=re.I)
    text = re.sub(r"^\s*[•\-*#]+\s*", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.lower().strip()


def load_existing_github_issues(repo: str, limit: int = 300) -> list[dict[str, Any]]:
    base_cmd = [
        "gh",
        "issue",
        "list",
        "--repo",
        repo,
        "--state",
        "all",
        "--limit",
        str(limit),
    ]
    for json_fields in (
        "number,title,state,url,body",
        "number,title,state,url",
    ):
        cmd = [*base_cmd, "--json", json_fields]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            continue

        try:
            payload = json.loads(result.stdout or "[]")
        except json.JSONDecodeError:
            continue

        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]

    print("  ⚠ GitHub Issue 목록 조회 실패: gh issue list 응답을 가져오지 못했습니다.")
    return []


def build_issue_index(issues: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for issue in issues:
        title = str(issue.get("title", "")).strip()
        normalized = normalize_issue_title(title)
        if normalized and normalized not in index:
            index[normalized] = issue
    return index


def issue_signal_tokens(text: str) -> set[str]:
    raw_tokens = re.findall(r"[0-9A-Za-z가-힣]+", text.lower())
    signal_tokens = {
        "action",
        "행동",
        "state",
        "상태",
        "memory",
        "기억",
        "trace",
        "snapshot",
        "event",
        "artifact",
        "contract",
        "override",
        "persona",
        "character",
        "content",
        "ingestion",
        "writeback",
        "loop",
        "backend",
        "api",
        "schema",
        "identity",
        "feedback",
        "monitoring",
        "moderation",
        "policy",
        "behavior",
        "behavioral",
        "interaction",
        "forum",
        "post",
        "comment",
        "react",
        "lurk",
        "silence",
    }
    return {token for token in raw_tokens if token in signal_tokens}


def issue_match_score(candidate_title: str, candidate_body: str, existing_issue: dict[str, Any]) -> tuple[float, int]:
    existing_title = str(existing_issue.get("title", "")).strip()
    existing_body = str(existing_issue.get("body", "")).strip()

    candidate_norm = normalize_issue_title(candidate_title)
    existing_norm = normalize_issue_title(existing_title)
    title_score = SequenceMatcher(None, candidate_norm, existing_norm).ratio()

    candidate_tokens = issue_signal_tokens(f"{candidate_title}\n{candidate_body}")
    existing_tokens = issue_signal_tokens(f"{existing_title}\n{existing_body}")
    overlap_count = len(candidate_tokens & existing_tokens)
    return title_score, overlap_count


def resolve_existing_issue(
    issue_index: dict[str, dict[str, Any]],
    title: str,
    body: str = "",
) -> Optional[dict[str, Any]]:
    normalized = normalize_issue_title(title)
    if not normalized:
        return None
    exact_match = issue_index.get(normalized)
    if exact_match:
        return exact_match

    best_match: Optional[dict[str, Any]] = None
    best_score = 0.0
    best_overlap = 0
    for existing in issue_index.values():
        title_score, overlap_count = issue_match_score(title, body, existing)
        if title_score >= 0.88 or overlap_count >= 7:
            if title_score > best_score or (title_score == best_score and overlap_count > best_overlap):
                best_match = existing
                best_score = title_score
                best_overlap = overlap_count

    return best_match


def build_issue_body(
    result_text: str,
    workforce_key: str,
    topic: str,
    parent_epic_url: str = "",
    parent_epic_title: str = "",
    task_goal: str = "",
    execution_order: Optional[int] = None,
    suggested_assignee: str = "",
    child_links: Optional[list[str]] = None,
) -> str:
    lines = [
        "## Workforce Debate 결과",
        "",
        f"- Source Workforce: {workforce_key}",
        f"- Source Topic: {topic}",
    ]
    if parent_epic_url:
        lines.append(f"- Parent Epic: {parent_epic_url}")
    if parent_epic_title:
        lines.append(f"- Parent Epic Title: {parent_epic_title}")
    if execution_order is not None:
        lines.append(f"- Execution Order: {execution_order}")
    if suggested_assignee:
        lines.append(f"- Suggested Assignee: {suggested_assignee}")
    if task_goal:
        lines.extend(["", "## Task Goal", "", task_goal])
    if child_links:
        lines.extend(["", "## Child Issues", ""])
        lines.extend([f"- {item}" for item in child_links])
    lines.extend(
        [
            "",
            "---",
            "",
            result_text.strip(),
            "",
            "---",
            "🤖 Generated by CAMEL Workforce Debate Engine",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def run_gh_issue_create(
    repo: str,
    title: str,
    body: str,
    labels: list[str],
    assignees: Optional[list[str]] = None,
    milestone: Optional[str] = None,
    project: Optional[str] = None,
) -> str:
    cmd = ["gh", "issue", "create", "--repo", repo, "--title", title, "--body", body]
    for label in labels:
        cmd.extend(["--label", label])
    if assignees:
        cmd.extend(["--assignee", ",".join(assignees)])
    if milestone:
        cmd.extend(["--milestone", milestone])
    if project:
        cmd.extend(["--project", project])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()

    if project and (
        "project scope" in result.stderr.lower()
        or "resource not accessible by personal access token" in result.stderr.lower()
    ):
        fallback_cmd = [arg for arg in cmd if arg not in ["--project", project]]
        retry = subprocess.run(fallback_cmd, capture_output=True, text=True)
        if retry.returncode == 0:
            print("  ⚠ project 추가는 권한 부족으로 건너뛰고 issue만 생성했습니다.")
            return retry.stdout.strip()
        result = retry

    print(f"  ⚠ GitHub Issue 생성 실패: {result.stderr}")
    return ""


def run_gh_issue_comment(repo: str, issue_number: int, body: str) -> str:
    cmd = [
        "gh",
        "issue",
        "comment",
        str(issue_number),
        "--repo",
        repo,
        "--body",
        body,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    print(f"  ⚠ GitHub Issue comment 실패: {result.stderr}")
    return ""


def run_gh_issue_reopen(repo: str, issue_number: int) -> str:
    cmd = [
        "gh",
        "issue",
        "reopen",
        str(issue_number),
        "--repo",
        repo,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ⚠ GitHub Issue reopen 실패: {result.stderr}")
        return ""
    view = subprocess.run(
        [
            "gh",
            "issue",
            "view",
            str(issue_number),
            "--repo",
            repo,
            "--json",
            "url,state",
        ],
        capture_output=True,
        text=True,
    )
    if view.returncode != 0:
        return ""
    try:
        payload = json.loads(view.stdout or "{}")
    except json.JSONDecodeError:
        return ""
    if isinstance(payload, dict):
        return str(payload.get("url", "")).strip()
    return ""


def is_closed_issue_state(state: str) -> bool:
    normalized = state.strip().lower()
    return bool(normalized) and normalized != "open"


def build_continuation_comment(
    current_title: str,
    current_body: str,
    matched_issue_number: Any,
    matched_issue_title: str,
    matched_issue_state: str,
) -> str:
    return (
        "## Workforce Continuation Note\n\n"
        f"- Current Run Topic: {current_title}\n"
        f"- Current Run State: continuation_check\n"
        f"- Matched Issue: #{matched_issue_number} [{matched_issue_state}] {matched_issue_title}\n"
        "\n"
        "이번 실행은 동일하거나 매우 유사한 주제를 새로 발급하기보다, "
        "기존 이슈의 맥락을 이어서 다음 판단에 재사용하기 위한 continuation note입니다.\n\n"
        "## Current Draft Body\n\n"
        f"{current_body.strip()}\n"
    )


def create_or_reuse_issue(
    repo: str,
    title: str,
    body: str,
    labels: list[str],
    issue_index: dict[str, dict[str, Any]],
    assignees: Optional[list[str]] = None,
    milestone: Optional[str] = None,
    project: Optional[str] = None,
) -> tuple[str, str]:
    existing = resolve_existing_issue(issue_index, title, body=body)
    if existing:
        url = str(existing.get("url", "")).strip()
        number = existing.get("number", "?")
        state = str(existing.get("state", "unknown")).strip()
        existing_title = str(existing.get("title", "")).strip()
        continuation_comment = build_continuation_comment(
            current_title=title,
            current_body=body,
            matched_issue_number=number,
            matched_issue_title=existing_title,
            matched_issue_state=state,
        )
        comment_url = ""
        if str(number).isdigit():
            comment_url = run_gh_issue_comment(
                repo=repo,
                issue_number=int(number),
                body=continuation_comment,
            )
        if is_closed_issue_state(state):
            print(f"  ⏭ 닫힌 유사 issue 발견: #{number} [{state}] {existing_title}")
            if comment_url:
                print(f"    → 기존 닫힌 issue에 continuation comment를 남겼습니다: {comment_url}")
            reopened_url = ""
            if str(number).isdigit():
                reopened_url = run_gh_issue_reopen(repo=repo, issue_number=int(number))
            if reopened_url:
                print(f"    → 기존 닫힌 issue를 다시 열었습니다: {reopened_url}")
                issue_index[normalize_issue_title(existing_title)] = {
                    "title": existing_title,
                    "body": str(existing.get("body", "")),
                    "url": reopened_url,
                    "state": "open",
                }
                return reopened_url, "reopened_closed_duplicate_commented"
            print("    → 새 발급은 중단하고 draft만 유지합니다.")
            return "", "blocked_closed_duplicate_commented"
        if url:
            print(f"  ↪ 기존 issue 재사용: #{number} [{state}] {existing_title}")
            if comment_url:
                print(f"    → 기존 issue에 continuation comment를 남겼습니다: {comment_url}")
            return url, "reused_open_commented" if comment_url else "reused_open"

    created = run_gh_issue_create(
        repo=repo,
        title=title,
        body=body,
        labels=labels,
        assignees=assignees,
        milestone=milestone,
        project=project,
    )
    if created:
        issue_index[normalize_issue_title(title)] = {
            "title": title,
            "body": body,
            "url": created,
            "state": "OPEN",
        }
        return created, "created"
    return "", "failed"


def create_task_issue_specs(
    result_text: str,
    epic_title: str,
    max_child_issues: int,
    task_assignees: Optional[list[str]] = None,
) -> list[dict[str, Any]]:
    next_actions = extract_next_action_items(result_text)
    if not next_actions:
        next_actions = [extract_issue_title(result_text)]
    specs = []
    for index, item in enumerate(next_actions[:max_child_issues], start=1):
        task_title = shorten_title(item, prefix="Task: ")
        task_goal = item
        specs.append(
            {
                "title": task_title,
                "goal": task_goal,
                "order": index,
                "assignee": rotate_assignee(task_assignees or [], index - 1),
            }
        )
    return specs


def create_sprint_issue_body(
    epic_title: str,
    epic_url: str,
    child_links: list[str],
    assignee_queues: dict[str, list[str]],
    milestone: Optional[str],
) -> str:
    lines = [
        "## Sprint Planning",
        "",
        f"- Epic: {epic_title}",
        f"- Epic URL: {epic_url}",
    ]
    if milestone:
        lines.append(f"- Milestone: {milestone}")
    lines.extend(["", "## Planned Tasks", ""])
    lines.extend([f"- {item}" for item in child_links] if child_links else ["- Child task issues were not created."])
    if assignee_queues:
        lines.extend(["", "## By Assignee", ""])
        for assignee, queue in assignee_queues.items():
            lines.append(f"### {assignee}")
            lines.extend([f"- {item}" for item in queue])
            lines.append("")
    lines.extend(
        [
            "",
            "## Goal",
            "",
            "이번 sprint에서 수행할 AI-Fashion-Forum 구현/운영 작업을 정리하고 실행 순서를 맞춘다.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def write_issue_plan_preview(
    artifacts: ArtifactBundle,
    result_text: str,
    workforce_key: str,
    topic: str,
    repo: str,
    issue_type: str,
    labels: Optional[list[str]] = None,
    issue_assignees: Optional[list[str]] = None,
    task_assignees: Optional[list[str]] = None,
    milestone: Optional[str] = None,
    project: Optional[str] = None,
    epic_label: Optional[str] = None,
    with_sprint: bool = False,
    max_child_issues: int = 5,
) -> Path:
    preview_path = artifacts.run_dir / "issue_plan.md"
    base_title = extract_issue_title(result_text)
    lines = [
        "# Issue Plan",
        "",
        f"- Target Repo: {repo}",
        f"- Issue Type: {issue_type}",
        f"- Source Workforce: {workforce_key}",
        f"- Source Topic: {topic}",
        f"- Labels: {', '.join(issue_labels_for_type(issue_type if issue_type in {'epic', 'bundle'} else 'task', labels, epic_label=epic_label))}",
        f"- Milestone: {milestone or '(none)'}",
        f"- Project: {project or '(none)'}",
        f"- Approval Required: yes",
        "- Closed Duplicate Policy: closed or highly similar issues are blocked and kept as draft only.",
        "",
    ]
    if issue_assignees:
        lines.append(f"- Issue Assignees: {', '.join(issue_assignees)}")
    if task_assignees:
        lines.append(f"- Task Assignees: {', '.join(task_assignees)}")
    if issue_type in {"single", "task", "epic", "sprint"}:
        title_prefix = {
            "single": "",
            "task": "Task: ",
            "epic": "Epic: ",
            "sprint": "Sprint: ",
        }[issue_type]
        lines.extend(
            [
                "",
                "## Planned Issue",
                "",
                f"- Title: {shorten_title(base_title, prefix=title_prefix) if title_prefix else base_title}",
            ]
        )
    else:
        task_specs = create_task_issue_specs(
            result_text,
            shorten_title(base_title, prefix="Epic: "),
            max_child_issues=max_child_issues,
            task_assignees=task_assignees,
        )
        lines.extend(
            [
                "",
                "## Planned Epic",
                "",
                f"- Title: {shorten_title(base_title, prefix='Epic: ')}",
                "",
                "## Planned Child Tasks",
                "",
            ]
        )
        if task_specs:
            for spec in task_specs:
                assignee = spec["assignee"] or "(unassigned)"
                lines.append(f"- {spec['order']}. {spec['title']} [{assignee}]")
                lines.append(f"  Goal: {spec['goal']}")
        else:
            lines.append("- No child tasks were extracted.")
        if with_sprint:
            lines.extend(
                [
                    "",
                    "## Planned Sprint Issue",
                    "",
                    f"- Title: {shorten_title(milestone or base_title, prefix='Sprint: ')}",
                ]
            )
    lines.extend(["", "## Source Decision", "", result_text.strip(), ""])
    preview_path.write_text("\n".join(lines), encoding="utf-8")
    return preview_path


def create_github_issues(
    result_text: str,
    workforce_key: str,
    topic: str,
    repo: str,
    issue_type: str = "task",
    labels: Optional[list[str]] = None,
    issue_assignees: Optional[list[str]] = None,
    task_assignees: Optional[list[str]] = None,
    milestone: Optional[str] = None,
    project: Optional[str] = None,
    epic_label: Optional[str] = None,
    with_sprint: bool = False,
    max_child_issues: int = 5,
) -> tuple[str, str]:
    """토론 결과를 GitHub Issue 또는 issue bundle로 등록합니다."""
    if issue_type not in ISSUE_TYPE_CHOICES:
        raise ValueError(f"Unknown issue_type: {issue_type}")

    base_title = extract_issue_title(result_text)
    existing_issues = build_issue_index(load_existing_github_issues(repo))

    if issue_type in {"single", "task"}:
        title = base_title if issue_type == "single" else shorten_title(base_title, prefix="Task: ")
        body = build_issue_body(result_text, workforce_key, topic)
        return create_or_reuse_issue(
            repo=repo,
            title=title,
            body=body,
            labels=issue_labels_for_type("task", labels),
            issue_index=existing_issues,
            assignees=issue_assignees,
            milestone=milestone,
            project=project,
        )

    if issue_type == "epic":
        title = shorten_title(base_title, prefix="Epic: ")
        body = build_issue_body(result_text, workforce_key, topic)
        return create_or_reuse_issue(
            repo=repo,
            title=title,
            body=body,
            labels=issue_labels_for_type("epic", labels, epic_label=epic_label),
            issue_index=existing_issues,
            assignees=issue_assignees,
            milestone=milestone,
            project=project,
        )

    if issue_type == "sprint":
        title = shorten_title(milestone or base_title, prefix="Sprint: ")
        body = create_sprint_issue_body(base_title, "(not linked)", [], {}, milestone)
        return create_or_reuse_issue(
            repo=repo,
            title=title,
            body=body,
            labels=issue_labels_for_type("task", labels),
            issue_index=existing_issues,
            assignees=issue_assignees,
            milestone=milestone,
            project=project,
        )

    epic_title = shorten_title(base_title, prefix="Epic: ")
    task_specs = create_task_issue_specs(
        result_text,
        epic_title,
        max_child_issues=max_child_issues,
        task_assignees=task_assignees,
    )
    planned_task_lines = []
    for spec in task_specs:
        assignee_note = f" [{spec['assignee']}]" if spec["assignee"] else ""
        planned_task_lines.append(f"{spec['order']}. {spec['title']}{assignee_note}: {spec['goal']}")
    epic_body = build_issue_body(
        result_text,
        workforce_key,
        topic,
        child_links=planned_task_lines,
    )
    epic_url, epic_status = create_or_reuse_issue(
        repo=repo,
        title=epic_title,
        body=epic_body,
        labels=issue_labels_for_type("epic", labels, epic_label=epic_label),
        issue_index=existing_issues,
        assignees=issue_assignees,
        milestone=milestone,
        project=project,
    )
    if not epic_url:
        return "", epic_status

    created_links = [epic_url]
    child_issue_links: list[str] = []
    assignee_queues: dict[str, list[str]] = {}
    issue_statuses = [epic_status]
    for spec in task_specs:
        task_title = spec["title"]
        task_goal = spec["goal"]
        task_order = spec["order"]
        task_assignee = spec["assignee"]
        task_body = build_issue_body(
            result_text,
            workforce_key,
            topic,
            parent_epic_url=epic_url,
            parent_epic_title=epic_title,
            task_goal=task_goal,
            execution_order=task_order,
            suggested_assignee=task_assignee,
        )
        task_url, task_status = create_or_reuse_issue(
            repo=repo,
            title=task_title,
            body=task_body,
            labels=issue_labels_for_type("task", labels, epic_label=epic_label),
            issue_index=existing_issues,
            assignees=[task_assignee] if task_assignee else issue_assignees,
            milestone=milestone,
            project=project,
        )
        issue_statuses.append(task_status)
        if task_url:
            queue_line = f"{task_order}. {task_title} -> {task_url}"
            child_issue_links.append(queue_line)
            created_links.append(task_url)
            if task_assignee:
                assignee_queues.setdefault(task_assignee, []).append(queue_line)

    if with_sprint:
        sprint_title = shorten_title(milestone or base_title, prefix="Sprint: ")
        sprint_body = create_sprint_issue_body(
            epic_title,
            epic_url,
            child_issue_links,
            assignee_queues,
            milestone,
        )
        sprint_url, sprint_status = create_or_reuse_issue(
            repo=repo,
            title=sprint_title,
            body=sprint_body,
            labels=issue_labels_for_type("task", labels),
            issue_index=existing_issues,
            assignees=issue_assignees,
            milestone=milestone,
            project=project,
        )
        issue_statuses.append(sprint_status)
        if sprint_url:
            created_links.append(sprint_url)

    if not created_links:
        return "", "+".join(unique_nonempty(issue_statuses)) or "failed"
    return "\n".join(created_links), "+".join(unique_nonempty(issue_statuses)) or "created"


def run_workforce(
    workforce_key: str,
    topic: Optional[str] = None,
    model_name: str = "gpt-4o-mini",
    rounds: int = 1,
    create_issue: bool = False,
    approve_issue: bool = False,
    issue_repo: Optional[str] = None,
    issue_type: str = "task",
    issue_labels: Optional[list[str]] = None,
    issue_assignees: Optional[list[str]] = None,
    task_assignees: Optional[list[str]] = None,
    issue_milestone: Optional[str] = None,
    issue_project: Optional[str] = None,
    epic_label: Optional[str] = None,
    with_sprint: bool = False,
    max_child_issues: int = 5,
    handoff_path: Optional[str] = None,
    context_pack_path: Optional[str] = None,
    share_memory: bool = False,
    auto_run_next: bool = False,
):
    """선택한 Workforce를 실행하고 결과 텍스트와 저장 경로를 반환합니다."""
    if workforce_key not in SCENARIOS:
        raise ValueError(f"Unknown workforce: {workforce_key}")
    if rounds < 1 or rounds > 5:
        raise ValueError("rounds must be between 1 and 5")

    scenario = SCENARIOS[workforce_key]
    resolved_topic = topic or scenario["default_topic"]
    handoff_text = load_handoff(handoff_path)
    context_pack_text = load_context_pack(context_pack_path)

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

    if workforce_key == "commitment":
        print("🧭 Commitment는 단일 decision agent 모드로 실행합니다...")
        print("-" * 60)
        round_results, final_result = run_commitment_decision(
            scenario=scenario,
            model_name=model_name,
            topic=resolved_topic,
            handoff_text=handoff_text,
            context_pack_text=context_pack_text,
        )
    else:
        print("🔧 Workforce 구성 중...")
        workforce = build_workforce(
            roles_config,
            scenario,
            model_name,
            share_memory=share_memory,
        )
        print()

        print("🚀 토론 시작...")
        print("-" * 60)
        round_results = run_multi_round_debate(
            workforce=workforce,
            scenario=scenario,
            topic=resolved_topic,
            rounds=rounds,
            handoff_text=handoff_text,
            context_pack_text=context_pack_text,
        )

        print("🧠 최종 합성 중...")
        final_result = synthesize_multi_round_result(
            scenario=scenario,
            model_name=model_name,
            topic=resolved_topic,
            round_results=round_results,
            handoff_text=handoff_text,
            context_pack_text=context_pack_text,
        )
    result_text = render_full_report(
        scenario=scenario,
        topic=resolved_topic,
        rounds=len(round_results),
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

    target_workforce, next_topic = extract_handoff_targets(workforce_key, final_result)
    handoff_text = build_handoff_markdown(
        source_workforce=workforce_key,
        source_label=scenario["label"],
        topic=resolved_topic,
        decision_text=final_result,
        target_workforce=target_workforce,
        next_topic=next_topic,
    )
    artifacts = write_run_artifacts(
        output_dir=OUTPUT_DIR,
        workforce_key=workforce_key,
        scenario_label=scenario["label"],
        topic=resolved_topic,
        rounds=len(round_results),
        participants=scenario["participants"],
        full_report_text=result_text,
        final_result_text=final_result,
        round_results=round_results,
        handoff_text=handoff_text,
        target_workforce=target_workforce,
        next_topic=next_topic,
    )
    print(f"💾 결과 저장: {artifacts.run_dir}")
    print(f"  - full_report: {artifacts.full_report}")
    print(f"  - decision: {artifacts.decision}")
    print(f"  - handoff: {artifacts.handoff}")

    deferred_issue_creation = create_issue and workforce_key == "commitment" and auto_run_next
    if create_issue and not deferred_issue_creation:
        print()
        ready_for_issue, readiness_reasons = assess_issue_readiness(
            result_text=final_result,
            workforce_key=workforce_key,
            issue_type=issue_type,
        )
        if ready_for_issue:
            preview_path = write_issue_plan_preview(
                artifacts=artifacts,
                result_text=final_result,
                workforce_key=workforce_key,
                topic=resolved_topic,
                repo=issue_repo or default_issue_repo(),
                issue_type=issue_type,
                labels=issue_labels,
                issue_assignees=issue_assignees,
                task_assignees=task_assignees,
                milestone=issue_milestone,
                project=issue_project,
                epic_label=epic_label,
                with_sprint=with_sprint,
                max_child_issues=max_child_issues,
            )
            print(f"📝 Issue draft 저장: {preview_path}")
            if not approve_issue:
                print("⏸️ GitHub 발급은 보류했습니다. draft를 검토한 뒤 --approve-issue로 승인해 주세요.")
            else:
                print("📌 GitHub Issue 생성 중...")
                issue_output, issue_status = create_github_issues(
                    result_text=final_result,
                    workforce_key=workforce_key,
                    topic=resolved_topic,
                    repo=issue_repo or default_issue_repo(),
                    issue_type=issue_type,
                    labels=issue_labels,
                    issue_assignees=issue_assignees,
                    task_assignees=task_assignees,
                    milestone=issue_milestone,
                    project=issue_project,
                    epic_label=epic_label,
                    with_sprint=with_sprint,
                    max_child_issues=max_child_issues,
                )
                issue_urls = [line.strip() for line in issue_output.splitlines() if line.strip()]
                if issue_output:
                    if issue_status.startswith("reused_open"):
                        print(f"  ↪ 기존 issue 재사용 완료:\n{issue_output}")
                    else:
                        print(f"  ✓ Issue 생성 완료:\n{issue_output}")
                elif issue_status == "blocked_closed_duplicate_commented":
                    print("  ⏭ 닫힌 유사 issue에는 continuation comment를 남기고 새 issue 발급은 건너뛰었습니다.")
                append_run_ledger_entry(
                    artifacts=artifacts,
                    workforce_key=workforce_key,
                    scenario_label=scenario["label"],
                    topic=resolved_topic,
                    repo=issue_repo or default_issue_repo(),
                    issue_type=issue_type,
                    issue_urls=issue_urls,
                    issue_status=issue_status,
                    rounds=len(round_results),
                    labels=issue_labels,
                    milestone=issue_milestone,
                )
                if not issue_output and issue_status != "blocked_closed_duplicate_commented":
                    print("  ⚠ GitHub Issue 생성 결과가 비어 있습니다.")
        else:
            print("⏭️ Issue 발급 건너뜀: 아직 작업 단위로 굳지 않았습니다.")
            for reason in readiness_reasons:
                print(f"  - {reason}")

    next_run = None
    if auto_run_next:
        if workforce_key != "commitment":
            print("  ⚠ --run-next는 commitment workforce에서만 지원됩니다.")
        elif not target_workforce or not next_topic:
            print("  ⚠ commitment 결과에서 다음 workforce/topic을 추출하지 못했습니다.")
        else:
            print()
            print("🔀 commitment 결과를 다음 workforce로 전달합니다...")
            next_run = run_workforce(
                workforce_key=target_workforce,
                topic=next_topic,
                model_name=model_name,
                rounds=rounds,
                create_issue=create_issue,
                approve_issue=approve_issue,
                issue_repo=issue_repo,
                issue_type=issue_type,
                issue_labels=issue_labels,
                issue_assignees=issue_assignees,
                task_assignees=task_assignees,
                issue_milestone=issue_milestone,
                issue_project=issue_project,
                epic_label=epic_label,
                with_sprint=with_sprint,
                max_child_issues=max_child_issues,
                handoff_path=str(artifacts.handoff),
                context_pack_path=context_pack_path,
                share_memory=share_memory,
                auto_run_next=False,
            )

    print()
    print("✅ 토론 완료!")
    return {
        "scenario": scenario,
        "topic": resolved_topic,
        "result_text": result_text,
        "final_result": final_result,
        "filepath": artifacts.full_report,
        "artifacts": artifacts,
        "handoff_path": artifacts.handoff,
        "next_workforce": target_workforce,
        "next_topic": next_topic,
        "next_run": next_run,
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
        help="토론 결과가 issue-ready면 issue draft를 만들고, 승인 시 GitHub Issue로 등록",
    )
    parser.add_argument(
        "--approve-issue",
        action="store_true",
        help="issue draft를 검토했다고 보고 실제 GitHub Issue 생성을 승인",
    )
    parser.add_argument(
        "--issue-repo",
        type=str,
        default=default_issue_repo(),
        help="Issue를 생성할 대상 GitHub repo (기본: Jongtae/AI-Fashion-Forum)",
    )
    parser.add_argument(
        "--issue-type",
        type=str,
        default="task",
        choices=ISSUE_TYPE_CHOICES,
        help="생성할 issue 형태: single, task, epic, sprint, bundle",
    )
    parser.add_argument(
        "--issue-label",
        action="append",
        default=[],
        help="추가 GitHub label (여러 번 지정 가능)",
    )
    parser.add_argument(
        "--issue-assignee",
        action="append",
        default=[],
        help="single/epic/sprint에 붙일 담당자 login (여러 번 지정 가능)",
    )
    parser.add_argument(
        "--task-assignee",
        action="append",
        default=[],
        help="bundle child task를 순서대로 분배할 담당자 login (여러 번 지정 가능)",
    )
    parser.add_argument(
        "--issue-milestone",
        type=str,
        default=None,
        help="GitHub milestone 이름",
    )
    parser.add_argument(
        "--issue-project",
        type=str,
        default=None,
        help="GitHub project 제목 (project scope 권한이 없으면 자동 생략)",
    )
    parser.add_argument(
        "--epic-label",
        type=str,
        default=None,
        help="Epic에 추가할 label 예: epic:forum-actions",
    )
    parser.add_argument(
        "--with-sprint",
        action="store_true",
        help="bundle 생성 시 sprint planning issue도 함께 생성",
    )
    parser.add_argument(
        "--max-child-issues",
        type=int,
        default=5,
        help="bundle 생성 시 child issue 최대 개수",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=1,
        help="토론 라운드 수 (기본: 1, 필요 시 증설)",
    )
    parser.add_argument(
        "--handoff",
        type=str,
        default=None,
        help="이전 workforce가 남긴 handoff.md 경로",
    )
    parser.add_argument(
        "--context-pack",
        type=str,
        default=None,
        help="context builder가 생성한 workflow input markdown 경로",
    )
    parser.add_argument(
        "--share-memory",
        action="store_true",
        help="CAMEL share_memory를 실험적으로 활성화",
    )
    parser.add_argument(
        "--run-next",
        action="store_true",
        help="commitment workforce 결과를 바로 다음 workforce 실행으로 연결",
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
        approve_issue=args.approve_issue,
        issue_repo=args.issue_repo,
        issue_type=args.issue_type,
        issue_labels=args.issue_label,
        issue_assignees=args.issue_assignee,
        task_assignees=args.task_assignee,
        issue_milestone=args.issue_milestone,
        issue_project=args.issue_project,
        epic_label=args.epic_label,
        with_sprint=args.with_sprint,
        max_child_issues=args.max_child_issues,
        handoff_path=args.handoff,
        context_pack_path=args.context_pack,
        share_memory=args.share_memory,
        auto_run_next=args.run_next,
    )


if __name__ == "__main__":
    main()
