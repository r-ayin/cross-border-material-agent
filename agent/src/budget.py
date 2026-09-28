# -*- coding: utf-8 -*-
"""Time budget guard and structured logging for the agent pipeline."""
import logging
import os
import sys
import time

TOTAL_BUDGET_SECONDS = 28 * 60  # hard cap 30min; keep 2min safety margin


class Budget:
    """Global time budget monitor shared across pipeline phases."""

    def __init__(self, total_seconds: float = TOTAL_BUDGET_SECONDS):
        self.start = time.monotonic()
        self.total = total_seconds

    def elapsed(self) -> float:
        return time.monotonic() - self.start

    def remaining(self) -> float:
        return max(0.0, self.total - self.elapsed())

    def enough(self, required_seconds: float) -> bool:
        return self.remaining() >= required_seconds

    def report(self) -> str:
        return f"elapsed={self.elapsed():.0f}s remaining={self.remaining():.0f}s"


def setup_logging() -> logging.Logger:
    """Logger writes to $AGENT_LOG_DIR/agent.log when available, else stderr."""
    logger = logging.getLogger("agent")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    log_dir = os.environ.get("AGENT_LOG_DIR", "").strip()
    if log_dir:
        try:
            os.makedirs(log_dir, exist_ok=True)
            fh = logging.FileHandler(os.path.join(log_dir, "agent.log"), encoding="utf-8")
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(fmt)
            logger.addHandler(fh)
        except OSError:
            pass

    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger
