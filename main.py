# -*- coding: utf-8 -*-
"""Rhine-Lore startup entry."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rhine_lore.core import main


if __name__ == "__main__":
    main()

