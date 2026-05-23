#!/usr/bin/env python3
"""하위 호환 alias — Hermes는 Bucky로 대체됨. 직접 사용 금지."""

from bucky_client import BuckyError as HermesError, run_bucky as run_hermes

__all__ = ["HermesError", "run_hermes"]
