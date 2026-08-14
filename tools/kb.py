#!/usr/bin/env python3
"""Entry point so the tooling runs with no install: `python3 tools/kb.py check`."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from kbtool.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
