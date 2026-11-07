"""Enable ``python -m afterlife.bench <args>``."""

from __future__ import annotations

import sys

from afterlife.bench.cli import main

if __name__ == "__main__":
    sys.exit(main())
