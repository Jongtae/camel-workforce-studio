#!/usr/bin/env python3
"""Shared source repo policy helpers for pipeline entrypoints."""

from pathlib import Path


def resolve_source_dir(path: str) -> Path:
    resolved = Path(path).expanduser().resolve()
    return resolved


def enforce_read_only_source_repo(source_dir: str, source_policy: str = "read-only") -> Path:
    if source_policy != "read-only":
        raise SystemExit(
            "AI-Fashion-Forum source repo 정책은 read-only만 허용됩니다. "
            "직접 수정은 이 워크스페이스에서 실행되지 않습니다."
        )

    resolved = resolve_source_dir(source_dir)
    print(f"✓ Source repo policy: read-only ({resolved})")
    return resolved
