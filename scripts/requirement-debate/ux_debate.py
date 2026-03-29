#!/usr/bin/env python3
"""UX Workforce 실행기 — UI/UX surface 완성도 토론을 시작한다."""

import sys

from debate import main


if __name__ == "__main__":
    main(["--workforce", "ux", *sys.argv[1:]])
