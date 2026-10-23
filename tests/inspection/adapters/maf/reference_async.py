"""Async construction and application-owned cleanup reference target."""

import os
from pathlib import Path

from agentshield import target_factory
from tests.inspection.adapters.maf.reference_sync import build


async def construct():
    """Build asynchronously and record construction inside the worker."""
    print("application construction output")
    return build()


async def cleanup(agent):
    """Record completed application cleanup when requested by the test."""
    if path := os.environ.get("AGENTSHIELD_CLEANUP_MARKER"):
        Path(path).write_text("closed", encoding="utf-8")


async def reset(agent):
    """Reject state resets during metadata-only inspection."""
    raise AssertionError("Inspection must not reset state")


target = target_factory(construct, agent_id="async-reference", cleanup=cleanup, reset=reset)
