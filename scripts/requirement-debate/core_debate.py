#!/usr/bin/env python3
"""코어 플랫폼 개발 Workforce 실행기."""

import sys

from debate import main


if __name__ == "__main__":
    main(["--workforce", "core", *sys.argv[1:]])
