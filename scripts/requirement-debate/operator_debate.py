#!/usr/bin/env python3
"""운영 조직 Workforce 실행기."""

import sys

from debate import main


if __name__ == "__main__":
    main(["--workforce", "operator", *sys.argv[1:]])
