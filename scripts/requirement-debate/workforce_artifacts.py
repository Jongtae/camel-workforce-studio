#!/usr/bin/env python3
"""Workforce handoff parsing and artifact storage helpers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


WORKFORCE_KEYS = {"commitment", "core", "operator", "society", "ux", "default"}
SECTION_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.M)
ROOT_DIR = Path(__file__).resolve().parents[2]
CONTEXT_DIR = ROOT_DIR / "context"
HISTORY_DIR = CONTEXT_DIR / "history"
RUN_LEDGER_PATH = HISTORY_DIR / "run-ledger.jsonl"


@dataclass
class ArtifactBundle:
    run_dir: Path
    full_report: Path
    decision: Path
    round_summary: Path
    next_questions: Path
    reflection: Path
    handoff: Path
    metadata: Path


def ensure_history_dir() -> None:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def slugify(value: str, fallback: str = "run") -> str:
    text = re.sub(r"\s+", "_", value.strip())
    text = re.sub(r"[^0-9A-Za-z._-]+", "-", text)
    text = text.strip("._-")
    return (text[:80] or fallback).lower()


def markdown_sections(text: str) -> dict[str, str]:
    matches = list(SECTION_RE.finditer(text))
    if not matches:
        return {}

    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        title = match.group(2).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[title] = text[start:end].strip()
    return sections


def first_section(text: str, *names: str) -> str:
    sections = markdown_sections(text)
    for name in names:
        for key, value in sections.items():
            if key.lower() == name.lower():
                return value.strip()
    return ""


def bullet_lines(text: str) -> list[str]:
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("- "):
            lines.append(line[2:].strip())
        elif re.match(r"^\d+\.\s+", line):
            lines.append(re.sub(r"^\d+\.\s+", "", line).strip())
        elif line.startswith("[ ] "):
            lines.append(line[4:].strip())
        else:
            lines.append(line)
    return lines


def parse_commitment_decision(text: str) -> tuple[str, str]:
    selected_workforce = first_section(text, "Selected Workforce").splitlines()
    next_topic = first_section(text, "Topic").splitlines()
    workforce = selected_workforce[0].strip() if selected_workforce else ""
    topic = next_topic[0].strip() if next_topic else ""
    if workforce not in WORKFORCE_KEYS:
        workforce = ""
    return workforce, topic


def parse_topic_catalog_items(text: str) -> list[dict[str, str]]:
    """topic catalog markdown에서 선택 가능한 항목들을 추출한다."""
    sections = markdown_sections(text)
    section_items: list[dict[str, str]] = []
    for key, body in sections.items():
        if not key.startswith("TC-"):
            continue
        item = {
            "key": key,
            "issue_topic": "",
            "goal": "",
            "preferred_workforce": "",
            "why_now": "",
            "excludes": "",
        }
        for raw_line in body.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("- Issue Topic:"):
                item["issue_topic"] = line[len("- Issue Topic:") :].strip()
            elif line.startswith("- Goal:"):
                item["goal"] = line[len("- Goal:") :].strip()
            elif line.startswith("- Preferred Workforce:"):
                item["preferred_workforce"] = line[len("- Preferred Workforce:") :].strip()
            elif line.startswith("- Why now:"):
                item["why_now"] = line[len("- Why now:") :].strip()
            elif line.startswith("- Excludes:"):
                item["excludes"] = line[len("- Excludes:") :].strip()
        if item["issue_topic"] or item["goal"] or item["preferred_workforce"]:
            section_items.append(item)

    if section_items:
        return section_items

    items: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    current_key = ""

    def flush_current() -> None:
        nonlocal current, current_key
        if current:
            items.append(current)
        current = None
        current_key = ""

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("### "):
            flush_current()
            current_key = line[4:].strip()
            current = {
                "key": current_key,
                "issue_topic": "",
                "goal": "",
                "preferred_workforce": "",
                "why_now": "",
                "excludes": "",
            }
            continue
        if current is None:
            continue
        if line.startswith("- Issue Topic:"):
            current["issue_topic"] = line[len("- Issue Topic:") :].strip()
        elif line.startswith("- Goal:"):
            current["goal"] = line[len("- Goal:") :].strip()
        elif line.startswith("- Preferred Workforce:"):
            current["preferred_workforce"] = line[len("- Preferred Workforce:") :].strip()
        elif line.startswith("- Why now:"):
            current["why_now"] = line[len("- Why now:") :].strip()
        elif line.startswith("- Excludes:"):
            current["excludes"] = line[len("- Excludes:") :].strip()

    flush_current()
    return items


def build_handoff_markdown(
    source_workforce: str,
    source_label: str,
    topic: str,
    decision_text: str,
    target_workforce: str = "",
    next_topic: str = "",
) -> str:
    decisions = first_section(
        decision_text,
        "Key Decisions",
        "Required Decisions",
        "Environment Priorities",
        "Summary",
    )
    open_questions = first_section(
        decision_text,
        "Open Questions",
        "Remaining Tensions",
        "Risks",
    )
    why_this_handoff = "\n\n".join(
        filter(
            None,
            [
                first_section(decision_text, "Why This Workforce"),
                first_section(decision_text, "Why This Topic"),
                first_section(decision_text, "Summary"),
            ],
        )
    ).strip()

    if source_workforce == "commitment":
        parsed_target, parsed_topic = parse_commitment_decision(decision_text)
        target_workforce = target_workforce or parsed_target
        next_topic = next_topic or parsed_topic

    if not why_this_handoff:
        why_this_handoff = (
            "이번 workforce 결과를 다음 workforce가 이어받아 추가 결정을 내릴 수 있도록 "
            "핵심 판단과 제약을 정리한다."
        )

    decision_items = bullet_lines(decisions)
    question_items = bullet_lines(open_questions)

    lines = [
        "# Workforce Handoff",
        "",
        "## Source Workforce",
        source_workforce,
        "",
        "## Source Label",
        source_label,
        "",
        "## Source Topic",
        topic,
        "",
        "## Target Workforce",
        target_workforce or "TBD",
        "",
        "## Next Topic",
        next_topic or "TBD",
        "",
        "## Why This Handoff",
        why_this_handoff,
        "",
        "## Decisions Already Fixed",
    ]

    if decision_items:
        lines.extend([f"- {item}" for item in decision_items])
    else:
        lines.append("- Final synthesis에서 구조화된 결정 항목을 찾지 못했다.")

    lines.extend(
        [
            "",
            "## Open Questions For Target Workforce",
        ]
    )
    if question_items:
        lines.extend([f"- {item}" for item in question_items])
    else:
        lines.append("- 다음 workforce가 이어서 구체화할 질문을 추가 정리해야 한다.")

    lines.extend(
        [
            "",
            "## Constraints",
            "- 이전 workforce에서 확정된 결정은 불필요하게 다시 논쟁하지 않는다.",
            "- 다음 workforce는 자신의 전문 레이어에 맞는 결정을 우선한다.",
            "",
            "## Relevant Evidence",
            "- 상세 근거는 같은 실행 디렉터리의 `decision.md`와 `full_report.md`를 참고한다.",
            "",
            "## Do Not Re-litigate",
            "- 이미 확정된 source workforce의 핵심 결정을 무시한 채 처음부터 다시 토론하지 않는다.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def write_run_artifacts(
    output_dir: Path,
    workforce_key: str,
    scenario_label: str,
    topic: str,
    rounds: int,
    participants: str,
    full_report_text: str,
    final_result_text: str,
    round_results: list[dict[str, str]],
    handoff_text: str,
    target_workforce: str = "",
    next_topic: str = "",
) -> ArtifactBundle:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = output_dir / f"{timestamp}_{workforce_key}_{slugify(topic, workforce_key)}"
    run_dir.mkdir(parents=True, exist_ok=True)

    full_report = run_dir / "full_report.md"
    decision = run_dir / "decision.md"
    round_summary = run_dir / "round_summary.md"
    next_questions = run_dir / "next_questions.md"
    reflection = run_dir / "reflection.md"
    handoff = run_dir / "handoff.md"
    metadata = run_dir / "metadata.json"

    full_report.write_text(full_report_text, encoding="utf-8")
    decision.write_text(final_result_text.strip() + "\n", encoding="utf-8")

    round_summary_lines = [
        "# Round Summary",
        "",
        f"- Workforce: {workforce_key}",
        f"- Topic: {topic}",
        f"- Rounds: {rounds}",
        f"- Participants: {participants}",
        "",
    ]
    for item in round_results:
        round_summary_lines.extend(
            [
                f"## Round {item['round']}",
                "",
                item["normalized_result"].strip(),
                "",
            ]
        )
    round_summary.write_text("\n".join(round_summary_lines).strip() + "\n", encoding="utf-8")

    extracted_open_questions = first_section(
        final_result_text,
        "Open Questions",
        "Remaining Tensions",
        "Risks",
    )
    if not extracted_open_questions:
        extracted_open_questions = "- 다음 workforce 또는 후속 이슈에서 추가 정리가 필요하다."
    next_questions.write_text(
        "# Next Questions\n\n" + extracted_open_questions.strip() + "\n",
        encoding="utf-8",
    )

    reflection_lines = [
        "# Reflection",
        "",
        f"- Workforce: {workforce_key}",
        f"- Topic: {topic}",
        f"- Target Workforce: {target_workforce or 'TBD'}",
        f"- Next Topic: {next_topic or 'TBD'}",
        "",
        "## What Worked",
        "",
        first_section(
            final_result_text,
            "Summary",
            "Key Decisions",
            "Required Decisions",
        ).strip() or "- No compact decision summary was extracted.",
        "",
        "## What Is Still Blocked",
        "",
        extracted_open_questions.strip() or "- No open questions were extracted.",
        "",
        "## Continuation Hint",
        "",
        (
            f"- The next run should continue toward {target_workforce or 'the next workforce'}"
            f" with topic: {next_topic or 'TBD'}."
        ),
        "",
    ]
    reflection.write_text("\n".join(reflection_lines).strip() + "\n", encoding="utf-8")

    handoff.write_text(handoff_text, encoding="utf-8")

    metadata_payload = {
        "workforce": workforce_key,
        "label": scenario_label,
        "topic": topic,
        "rounds": rounds,
        "participants": participants,
        "target_workforce": target_workforce,
        "next_topic": next_topic,
        "generated_at": datetime.now().isoformat(),
        "artifacts": {
            "full_report": str(full_report),
            "decision": str(decision),
            "round_summary": str(round_summary),
            "next_questions": str(next_questions),
            "reflection": str(reflection),
            "handoff": str(handoff),
        },
    }
    metadata.write_text(
        json.dumps(metadata_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return ArtifactBundle(
        run_dir=run_dir,
        full_report=full_report,
        decision=decision,
        round_summary=round_summary,
        next_questions=next_questions,
        reflection=reflection,
        handoff=handoff,
        metadata=metadata,
    )


def parse_issue_urls(text: str) -> list[str]:
    urls = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("http://") or line.startswith("https://"):
            urls.append(line)
    return urls


def issue_number_from_url(url: str) -> Optional[int]:
    match = re.search(r"/issues/(\d+)$", url.strip())
    if not match:
        return None
    return int(match.group(1))


def append_run_ledger_entry(
    artifacts: ArtifactBundle,
    workforce_key: str,
    scenario_label: str,
    topic: str,
    repo: str,
    issue_type: str,
    issue_urls: list[str],
    rounds: int,
    issue_status: str = "created",
    labels: Optional[list[str]] = None,
    milestone: Optional[str] = None,
) -> dict:
    ensure_history_dir()
    issue_numbers = [number for number in (issue_number_from_url(url) for url in issue_urls) if number]
    entry = {
        "recorded_at": datetime.now().isoformat(),
        "run_dir": str(artifacts.run_dir),
        "metadata_path": str(artifacts.metadata),
        "decision_path": str(artifacts.decision),
        "handoff_path": str(artifacts.handoff),
        "workforce": workforce_key,
        "label": scenario_label,
        "topic": topic,
        "issue_repo": repo,
        "issue_type": issue_type,
        "rounds": rounds,
        "issue_status": issue_status,
        "labels": labels or [],
        "milestone": milestone or "",
        "issue_urls": issue_urls,
        "issue_numbers": issue_numbers,
    }
    with RUN_LEDGER_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    try:
        metadata_payload = json.loads(artifacts.metadata.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        metadata_payload = {}
    metadata_payload["issue_history"] = {
        "ledger_path": str(RUN_LEDGER_PATH),
        "issue_repo": repo,
        "issue_type": issue_type,
        "issue_status": issue_status,
        "issue_urls": issue_urls,
        "issue_numbers": issue_numbers,
        "labels": labels or [],
        "milestone": milestone or "",
    }
    artifacts.metadata.write_text(
        json.dumps(metadata_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return entry


def load_run_ledger(limit: Optional[int] = None) -> list[dict]:
    if not RUN_LEDGER_PATH.exists():
        return []

    entries = []
    for line in RUN_LEDGER_PATH.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text:
            continue
        try:
            entries.append(json.loads(text))
        except json.JSONDecodeError:
            continue
    entries.sort(key=lambda item: item.get("recorded_at", ""), reverse=True)
    if limit is not None:
        return entries[:limit]
    return entries


def load_handoff(path: Optional[str]) -> str:
    if not path:
        return ""
    return Path(path).read_text(encoding="utf-8").strip()


def load_context_pack(path: Optional[str]) -> str:
    if not path:
        return ""
    return Path(path).read_text(encoding="utf-8").strip()


def discover_latest_run(output_dir: Path) -> Optional[Path]:
    if not output_dir.exists():
        return None
    run_dirs = sorted([path for path in output_dir.iterdir() if path.is_dir()], reverse=True)
    return run_dirs[0] if run_dirs else None


def discover_latest_run_for_workforce(output_dir: Path, workforce_key: str) -> Optional[Path]:
    if not output_dir.exists():
        return None

    run_dirs = sorted([path for path in output_dir.iterdir() if path.is_dir()], reverse=True)
    for run_dir in run_dirs:
        metadata_path = run_dir / "metadata.json"
        if not metadata_path.exists():
            continue
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if payload.get("workforce") == workforce_key:
            return run_dir
    return None


def discover_latest_handoff(output_dir: Path) -> Optional[Path]:
    latest_run = discover_latest_run(output_dir)
    if not latest_run:
        return None
    handoff = latest_run / "handoff.md"
    return handoff if handoff.exists() else None


def summarize_latest_run(output_dir: Path) -> str:
    latest_run = discover_latest_run(output_dir)
    if not latest_run:
        return "# Latest Workforce State\n\n- No previous workforce run artifacts were found.\n"

    metadata_path = latest_run / "metadata.json"
    decision_path = latest_run / "decision.md"
    reflection_path = latest_run / "reflection.md"
    handoff_path = latest_run / "handoff.md"

    workforce = "unknown"
    topic = ""
    target_workforce = ""
    next_topic = ""
    if metadata_path.exists():
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            workforce = payload.get("workforce", workforce)
            topic = payload.get("topic", "")
            target_workforce = payload.get("target_workforce", "")
            next_topic = payload.get("next_topic", "")
        except json.JSONDecodeError:
            pass

    decision_summary = ""
    if decision_path.exists():
        decision_summary = first_section(
            decision_path.read_text(encoding="utf-8"),
            "Summary",
            "Key Decisions",
            "Required Decisions",
        )
    if not decision_summary and handoff_path.exists():
        decision_summary = first_section(
            handoff_path.read_text(encoding="utf-8"),
            "Decisions Already Fixed",
            "Why This Handoff",
        )
    reflection_summary = ""
    if reflection_path.exists():
        reflection_summary = first_section(
            reflection_path.read_text(encoding="utf-8"),
            "What Worked",
            "What Is Still Blocked",
            "Continuation Hint",
        )

    lines = [
        "# Latest Workforce State",
        "",
        f"- Latest run directory: {latest_run}",
        f"- Workforce: {workforce}",
        f"- Topic: {topic or 'unknown'}",
        f"- Suggested next workforce: {target_workforce or 'TBD'}",
        f"- Suggested next topic: {next_topic or 'TBD'}",
        "",
        "## Latest Decision Summary",
        decision_summary.strip() if decision_summary else "- No previous decision summary found.",
        "",
        "## Latest Reflection",
        reflection_summary.strip() if reflection_summary else "- No previous reflection found.",
        "",
    ]
    return "\n".join(lines)
