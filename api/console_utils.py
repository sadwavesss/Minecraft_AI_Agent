from __future__ import annotations

import sys
from typing import Any


def make_console_safe(value: Any) -> str:
    text = str(value)
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    return text.encode(encoding, errors="backslashreplace").decode(encoding, errors="strict")
