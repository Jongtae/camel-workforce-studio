#!/usr/bin/env python3
"""범용 workforce bridge 실행기."""

import argparse
from pathlib import Path

from debate import run_workforce
from workforce_artifacts import load_handoff


DEFAULT_BRIDGE_TOPICS = {
    ("society", "operator"): (
        "이용자 조직 시뮬레이션 결과를 바탕으로 운영 조직이 먼저 정의해야 할 "
        "관찰 프레임과 개입 레버는 무엇인가?"
    ),
    ("core", "operator"): (
        "mock-to-service 전환 계획을 바탕으로 운영 조직이 어떤 메트릭, trace, "
        "개입 레버를 먼저 갖춰야 하는가?"
    ),
    ("core", "society"): (
        "현재 구현 가능한 시스템 경계를 바탕으로, 어떤 사회 규칙과 기억 구조를 "
        "먼저 시뮬레이션해야 하는가?"
    ),
}


def build_bridge_topic(
    source_workforce: str,
    target_workforce: str,
    original_topic: str,
    handoff_text: str,
) -> str:
    default_topic = DEFAULT_BRIDGE_TOPICS.get(
        (source_workforce, target_workforce),
        (
            f"{source_workforce} workforce 결과를 바탕으로 {target_workforce} workforce가 "
            "다음에 결정해야 할 핵심 질문은 무엇인가?"
        ),
    )
    return f"""{default_topic}

## Original Topic
{original_topic}

## Source Handoff
{handoff_text}

## Bridge Instruction
- source workforce에서 이미 확정한 결정을 불필요하게 다시 논쟁하지 말라
- target workforce의 전문 레이어에서 새로 결정해야 할 것을 우선하라
- source 결과를 target workforce의 질문 구조로 다시 해석하라
"""


def main():
    parser = argparse.ArgumentParser(
        description="범용 CAMEL Workforce bridge: 한 workforce 결과를 다른 workforce로 연결"
    )
    parser.add_argument(
        "--from-workforce",
        type=str,
        default="society",
        help="먼저 실행할 source workforce",
    )
    parser.add_argument(
        "--to-workforce",
        type=str,
        default="operator",
        help="뒤이어 실행할 target workforce",
    )
    parser.add_argument(
        "--topic",
        type=str,
        default=None,
        help="source workforce에 전달할 주제",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-mini",
        choices=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        help="사용할 모델",
    )
    parser.add_argument(
        "--source-rounds",
        type=int,
        default=3,
        help="source workforce 라운드 수",
    )
    parser.add_argument(
        "--target-rounds",
        type=int,
        default=3,
        help="target workforce 라운드 수",
    )
    parser.add_argument(
        "--source-handoff",
        type=str,
        default=None,
        help="이미 존재하는 source handoff.md를 재사용할 때 경로 지정",
    )
    parser.add_argument(
        "--context-pack",
        type=str,
        default=None,
        help="target workforce에 함께 전달할 context pack 경로",
    )
    parser.add_argument(
        "--share-memory",
        action="store_true",
        help="두 workforce 실행 모두에 share_memory를 적용",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("🌉 AI Fashion Forum — Generic Workforce Bridge")
    print("=" * 60)

    if args.source_handoff:
        handoff_path = Path(args.source_handoff)
        if not handoff_path.exists():
            raise FileNotFoundError(f"source handoff not found: {handoff_path}")
        source_topic = args.topic or "기존 handoff를 재사용하는 bridge 실행"
        source_handoff_text = load_handoff(str(handoff_path))
        source_result = {
            "topic": source_topic,
            "handoff_path": handoff_path,
            "filepath": handoff_path.parent / "full_report.md",
        }
    else:
        print("1단계: source workforce 실행")
        print()
        source_result = run_workforce(
            workforce_key=args.from_workforce,
            topic=args.topic,
            model_name=args.model,
            rounds=args.source_rounds,
            handoff_path=None,
            context_pack_path=args.context_pack,
            share_memory=args.share_memory,
        )
        source_handoff_text = load_handoff(str(source_result["handoff_path"]))

    target_topic = build_bridge_topic(
        source_workforce=args.from_workforce,
        target_workforce=args.to_workforce,
        original_topic=source_result["topic"],
        handoff_text=source_handoff_text,
    )

    print()
    print("2단계: target workforce 실행")
    print()

    target_result = run_workforce(
        workforce_key=args.to_workforce,
        topic=target_topic,
        model_name=args.model,
        rounds=args.target_rounds,
        handoff_path=str(source_result["handoff_path"]),
        context_pack_path=args.context_pack,
        share_memory=args.share_memory,
    )

    print()
    print("🌉 Bridge 완료")
    print(f"- source handoff: {source_result['handoff_path']}")
    print(f"- target report: {target_result['filepath']}")


if __name__ == "__main__":
    main()
