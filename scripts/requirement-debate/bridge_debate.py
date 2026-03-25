#!/usr/bin/env python3
"""이용자 조직 결과를 바탕으로 운영 조직을 이어서 토론하는 bridge 실행기."""

import argparse
import re
from datetime import datetime

from debate import OUTPUT_DIR, run_workforce


def extract_final_synthesis(report_text: str) -> str:
    match = re.search(r"# Final Synthesis\s*(.*)\Z", report_text, re.S)
    if match:
        return match.group(1).strip()
    return report_text.strip()


def build_operator_topic(user_topic: str, society_summary: str) -> str:
    return f"""다음 이용자 조직 시뮬레이션 결과를 바탕으로 운영 조직이 먼저 정의해야 할 관찰 프레임과 개입 레버를 설계하라.

## 원래 이용자 조직 질문
{user_topic}

## 이용자 조직 요약
{society_summary}

## 운영 조직에게 요구되는 일
- 어떤 메트릭, 인터뷰, trace, dashboard를 먼저 봐야 하는지 정의
- 어떤 개입 레버(온보딩, 카테고리, 추천, moderation, 실험 플래그)를 먼저 가질지 정의
- 다음 런에서 무엇을 바꿔볼지 우선순위화
"""


def save_bridge_report(user_result: dict, operator_result: dict) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_bridge_society_to_operator.md"
    filepath = OUTPUT_DIR / filename
    user_summary = extract_final_synthesis(user_result["result_text"])
    operator_summary = extract_final_synthesis(operator_result["result_text"])
    content = f"""# Bridge Debate Report

- **일시**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **Bridge 흐름**: society -> operator

---

# Society Workforce

## Topic
{user_result['topic']}

## Saved Report
{user_result['filepath']}

## Final Synthesis
{user_summary}

---

# Operator Workforce

## Topic
{operator_result['topic']}

## Saved Report
{operator_result['filepath']}

## Final Synthesis
{operator_summary}

---

# Bridge Action Plan

1. 이용자 조직 Workforce가 정의한 사회 모델을 다음 실행의 기준선으로 사용한다.
2. 운영 조직 Workforce가 정의한 관찰 프레임과 개입 레버를 다음 런 설정에 연결한다.
3. 이후 반복 실행에서는 society -> operator 순서를 유지하고, 각 실행의 trace와 artifact를 비교 가능하게 저장한다.
"""
    filepath.write_text(content, encoding="utf-8")
    return str(filepath)


def main():
    parser = argparse.ArgumentParser(
        description="CAMEL Workforce bridge: society 결과를 operator로 연결"
    )
    parser.add_argument(
        "--topic",
        type=str,
        default="이용자 조직과 운영 조직의 선후 관계를 고려할 때 먼저 어떤 사회 모델을 고정해야 하는가?",
        help="society Workforce에 전달할 주제",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-mini",
        choices=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        help="사용할 모델",
    )
    parser.add_argument(
        "--society-rounds",
        type=int,
        default=3,
        help="society Workforce 라운드 수",
    )
    parser.add_argument(
        "--operator-rounds",
        type=int,
        default=3,
        help="operator Workforce 라운드 수",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("🌉 AI Fashion Forum — Bridge Debate")
    print("=" * 60)
    print("1단계: 이용자 조직 Workforce 실행")
    print()

    society_result = run_workforce(
        workforce_key="society",
        topic=args.topic,
        model_name=args.model,
        rounds=args.society_rounds,
    )

    society_summary = extract_final_synthesis(society_result["result_text"])
    operator_topic = build_operator_topic(args.topic, society_summary)

    print()
    print("=" * 60)
    print("2단계: 운영 조직 Workforce 실행")
    print("=" * 60)
    print()

    operator_result = run_workforce(
        workforce_key="operator",
        topic=operator_topic,
        model_name=args.model,
        rounds=args.operator_rounds,
    )

    bridge_path = save_bridge_report(society_result, operator_result)
    print()
    print(f"🌉 Bridge 리포트 저장: {bridge_path}")


if __name__ == "__main__":
    main()
