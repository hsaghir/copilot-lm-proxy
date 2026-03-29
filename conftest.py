"""Root conftest.py — ensures the local src/ takes priority over any installed package."""

from __future__ import annotations

import sys
from pathlib import Path

# Insert this worktree's src/ at the front of sys.path so that
# `import copilot_proxy` resolves to the local development copy rather than
# any previously installed version of the package.
_src = str(Path(__file__).parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)
