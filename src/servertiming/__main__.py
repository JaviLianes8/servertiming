"""Run the command line checker: ``python -m servertiming``."""

from __future__ import annotations

import sys

from ._cli import main

if __name__ == "__main__":
    sys.exit(main())
