#!/usr/bin/env python3
"""Commitment Workforce 실행기 — 다음 논의의 workforce와 토픽을 결정한다."""

import sys

from debate import main


if __name__ == "__main__":
    main(["--workforce", "commitment", *sys.argv[1:]])
