#!/usr/bin/env python3
"""Run the studio in a semi-autonomous mode."""

import argparse
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
BUILD_CONTEXT = ROOT_DIR / "scripts" / "context-builder" / "build_context.py"
COMMITMENT_RUNNER = ROOT_DIR / "scripts" / "requirement-debate" / "commitment_debate.py"
OUTPUT_DIR = ROOT_DIR / "scripts" / "requirement-debate" / "outputs"
REQUIREMENT_DEBATE_DIR = ROOT_DIR / "scripts" / "requirement-debate"

if str(REQUIREMENT_DEBATE_DIR) not in sys.path:
    sys.path.insert(0, str(REQUIREMENT_DEBATE_DIR))

from workforce_artifacts import discover_latest_handoff


def default_source_dir() -> str:
    candidate = ROOT_DIR.parent / "AI-Fashion-Forum"
    return str(candidate)


def run_command(args: list[str]) -> None:
    result = subprocess.run(args, cwd=ROOT_DIR)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build context and run camel-workforce-studio in semi-autonomous mode"
    )
    parser.add_argument(
        "--repo",
        type=str,
        default="Jongtae/AI-Fashion-Forum",
        help="GitHub repository slug to summarize",
    )
    parser.add_argument(
        "--source-dir",
        type=str,
        default=default_source_dir(),
        help="Local source repository path for git situation checks",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=1,
        help="Round count for commitment and chained next workforce",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-mini",
        help="OpenAI model name",
    )
    parser.add_argument(
        "--no-run-next",
        action="store_true",
        help="Run only commitment without chaining to the selected next workforce",
    )
    parser.add_argument(
        "--share-memory",
        action="store_true",
        help="Enable CAMEL share_memory during workforce runs",
    )
    parser.add_argument(
        "--handoff",
        type=str,
        default=None,
        help="Explicit previous handoff to inject. Defaults to latest discovered handoff.",
    )
    args = parser.parse_args()

    build_context_cmd = [
        sys.executable,
        str(BUILD_CONTEXT),
        "--repo",
        args.repo,
        "--source-dir",
        args.source_dir,
    ]
    run_command(build_context_cmd)

    handoff_path = args.handoff
    if not handoff_path:
        latest_handoff = discover_latest_handoff(OUTPUT_DIR)
        handoff_path = str(latest_handoff) if latest_handoff else None

    commitment_cmd = [
        sys.executable,
        str(COMMITMENT_RUNNER),
        "--rounds",
        str(args.rounds),
        "--model",
        args.model,
        "--context-pack",
        str(ROOT_DIR / "context" / "workflow-inputs" / "commitment.md"),
    ]
    if handoff_path:
        commitment_cmd.extend(["--handoff", handoff_path])
    if not args.no_run_next:
        commitment_cmd.append("--run-next")
    if args.share_memory:
        commitment_cmd.append("--share-memory")

    run_command(commitment_cmd)


if __name__ == "__main__":
    main()
