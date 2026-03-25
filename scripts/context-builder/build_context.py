#!/usr/bin/env python3
"""Build normalized context packs for workforce runs."""

import argparse
import json
import subprocess
from pathlib import Path
from typing import Iterable, List


ROOT_DIR = Path(__file__).resolve().parents[2]
CONTEXT_DIR = ROOT_DIR / "context"
RAW_DIR = CONTEXT_DIR / "raw"
NORMALIZED_DIR = CONTEXT_DIR / "normalized"
WORKFLOW_INPUTS_DIR = CONTEXT_DIR / "workflow-inputs"


WORKFLOW_OBJECTIVES = {
    "commitment": "현재 프로젝트에서 가장 중요한 gap을 식별하고 다음 workforce와 topic을 결정한다.",
    "core": "mock-to-service 전환 관점에서 실제 구현과 아키텍처 결정을 구체화한다.",
    "operator": "운영 조직의 관찰 프레임, 메트릭, 개입 레버를 정리한다.",
    "society": "이용자 조직의 사회 규칙, 상태, 기억, 관계 모델을 정리한다.",
}


def ensure_dirs() -> None:
    for path in [
        RAW_DIR / "github",
        RAW_DIR / "reports",
        RAW_DIR / "progress",
        NORMALIZED_DIR,
        WORKFLOW_INPUTS_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def run_gh_json(repo: str, args: List[str]) -> list:
    cmd = ["gh", "issue", "list", "--repo", repo, *args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return []
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return []


def collect_github_issues(repo: str) -> list:
    issues = run_gh_json(
        repo,
        [
            "--state",
            "open",
            "--limit",
            "100",
            "--json",
            "number,title,body,labels,assignees,updatedAt,url",
        ],
    )
    issues_path = RAW_DIR / "github" / "issues.json"
    issues_path.write_text(
        json.dumps(issues, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return issues


def read_text_files(paths: Iterable[Path]) -> list:
    items = []
    for path in paths:
        if not path.is_file():
            continue
        items.append(
            {
                "name": path.name,
                "path": str(path),
                "text": path.read_text(encoding="utf-8", errors="ignore"),
            }
        )
    return items


def collect_reports() -> list:
    report_dir = RAW_DIR / "reports"
    files = sorted(
        [
            *report_dir.glob("*.md"),
            *report_dir.glob("*.txt"),
        ]
    )
    return read_text_files(files)


def collect_progress_logs() -> list:
    progress_dir = RAW_DIR / "progress"
    items = []
    for path in sorted(progress_dir.iterdir() if progress_dir.exists() else []):
        if path.suffix in {".md", ".txt"}:
            items.extend(read_text_files([path]))
            continue
        if path.suffix == ".json":
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if isinstance(payload, list):
                for entry in payload:
                    items.append({"name": path.name, "entry": entry})
            elif isinstance(payload, dict):
                items.append({"name": path.name, "entry": payload})
    return items


def trim(text: str, max_lines: int = 12) -> str:
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines[:max_lines]).strip()


def render_project_snapshot(repo: str, issues: list) -> str:
    return (
        "# Project Snapshot\n\n"
        f"- Source repository: {repo}\n"
        "- This workspace acts as a companion decision studio for AI-Fashion-Forum.\n"
        "- Workforce runs are expected to consume normalized context rather than raw issue or report dumps.\n"
        f"- Open GitHub issues collected for this build: {len(issues)}\n"
    )


def render_active_issues(issues: list) -> str:
    lines = ["# Active Issues", ""]
    if not issues:
        lines.append("- No GitHub issues were collected. Add `--repo` or run `gh auth login` if needed.")
        return "\n".join(lines) + "\n"

    for issue in issues:
        labels = ", ".join(label["name"] for label in issue.get("labels", [])) or "no labels"
        lines.extend(
            [
                f"## #{issue['number']} {issue['title']}",
                f"- Updated: {issue.get('updatedAt', '')}",
                f"- Labels: {labels}",
                f"- URL: {issue.get('url', '')}",
                trim(issue.get("body", "") or "No body provided.", max_lines=8) or "No body provided.",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def render_recent_progress(progress_items: list) -> str:
    lines = ["# Recent Progress", ""]
    if not progress_items:
        lines.append("- No local progress logs found in `context/raw/progress`.")
        return "\n".join(lines) + "\n"

    for item in progress_items:
        lines.append(f"## {item['name']}")
        entry = item.get("entry")
        if entry is not None:
            for key, value in entry.items():
                lines.append(f"- {key}: {value}")
        else:
            lines.append(trim(item.get("text", ""), max_lines=10) or "- Empty progress note")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def render_external_report_briefs(reports: list) -> str:
    lines = ["# External Report Briefs", ""]
    if not reports:
        lines.append("- No report files found in `context/raw/reports`.")
        return "\n".join(lines) + "\n"

    for report in reports:
        lines.extend(
            [
                f"## {report['name']}",
                trim(report["text"], max_lines=12) or "No extractable text.",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def render_open_questions(issues: list, progress_items: list) -> str:
    lines = ["# Open Questions", ""]
    if not issues and not progress_items:
        lines.append("- No structured open questions were found. Add issue bodies or progress logs with explicit gaps.")
        return "\n".join(lines) + "\n"

    for issue in issues[:10]:
        lines.append(f"- Issue #{issue['number']}에서 아직 풀리지 않은 결정: {issue['title']}")
    if progress_items:
        lines.append("- Progress logs에서 드러난 검증 공백과 미해결 항목을 다음 workforce에서 정리해야 한다.")
    return "\n".join(lines).strip() + "\n"


def write_normalized_file(name: str, content: str) -> Path:
    path = NORMALIZED_DIR / name
    path.write_text(content, encoding="utf-8")
    return path


def build_workflow_input(workforce: str, normalized: dict) -> str:
    return f"""# Workflow Input

## Workflow
{workforce}

## Objective
{WORKFLOW_OBJECTIVES[workforce]}

## Project Snapshot
{normalized['project_snapshot']}

## Active Issues
{normalized['active_issues']}

## Recent Progress
{normalized['recent_progress']}

## External Evidence
{normalized['external_report_briefs']}

## Open Questions
{normalized['open_questions']}

## Constraints
- 이미 정리된 normalized context를 우선 근거로 사용한다.
- raw source 전체를 다시 요약하지 말고, 이번 workforce에 필요한 결정을 우선한다.

## Expected Output
- `decision.md`
- `handoff.md`
- `next_questions.md`
- `round_summary.md`
""".strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="GitHub issues, reports, and progress logs into workforce-ready context packs"
    )
    parser.add_argument(
        "--repo",
        type=str,
        default="Jongtae/AI-Fashion-Forum",
        help="수집할 GitHub repository (owner/name)",
    )
    args = parser.parse_args()

    ensure_dirs()

    issues = collect_github_issues(args.repo)
    reports = collect_reports()
    progress_items = collect_progress_logs()

    normalized = {
        "project_snapshot": render_project_snapshot(args.repo, issues),
        "active_issues": render_active_issues(issues),
        "recent_progress": render_recent_progress(progress_items),
        "external_report_briefs": render_external_report_briefs(reports),
        "open_questions": render_open_questions(issues, progress_items),
    }

    for filename, content in [
        ("project_snapshot.md", normalized["project_snapshot"]),
        ("active_issues.md", normalized["active_issues"]),
        ("recent_progress.md", normalized["recent_progress"]),
        ("external_report_briefs.md", normalized["external_report_briefs"]),
        ("open_questions.md", normalized["open_questions"]),
    ]:
        write_normalized_file(filename, content)

    for workforce in WORKFLOW_OBJECTIVES:
        path = WORKFLOW_INPUTS_DIR / f"{workforce}.md"
        path.write_text(build_workflow_input(workforce, normalized), encoding="utf-8")
        print(f"✓ workflow input 생성: {path}")

    print(f"✓ normalized context 생성 완료: {NORMALIZED_DIR}")


if __name__ == "__main__":
    main()
