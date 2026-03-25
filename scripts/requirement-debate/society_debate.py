#!/usr/bin/env python3
"""이용자 조직 시뮬레이션 Workforce 실행기."""

import sys

from debate import main


if __name__ == "__main__":
    main(["--workforce", "society", *sys.argv[1:]])
