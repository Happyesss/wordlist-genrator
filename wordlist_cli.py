#!/usr/bin/env python3
"""Root launcher for the offline CLI implementation."""

from __future__ import annotations

import sys
from pathlib import Path

OFFLINE_DIR = Path(__file__).resolve().parent / "offline-cli"
sys.path.insert(0, str(OFFLINE_DIR))

from wordlist_cli_app import main


if __name__ == "__main__":
    raise SystemExit(main())
