#!/usr/bin/env python3
"""Local wrapper for the modular offline CLI app."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from wordlist_cli_app import main


if __name__ == "__main__":
    raise SystemExit(main())
