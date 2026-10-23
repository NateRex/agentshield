"""Observe framework and application ownership through a real MAF lifecycle."""

import os
from pathlib import Path

from agent_framework import Agent
from agentshield import target_factory
from tests.inspection.adapters.maf.reference_sync import OfflineClient, lookup


def record(event):
    """Record resource release for deterministic ownership assertions."""
    with Path(os.environ["AGENTSHIELD_LIFECYCLE_MARKER"]).open("a", encoding="utf-8") as stream:
        stream.write(event + "\n")


class ManagedClient(OfflineClient):
    """Client whose framework-owned context must be closed exactly once."""

    async def __aenter__(self):
        """Acquire the application-configured client context."""
        return self

    async def __aexit__(self, *exc):
        """Release the context through the framework's agent.close operation."""
        record("framework")


async def build():
    """Return an application-opened agent without connecting to a service."""
    agent = Agent(client=ManagedClient(), tools=[lookup], name="Managed")
    await agent.open()
    return agent


async def duplicate():
    """Trigger discovery failure after construction has acquired resources."""
    agent = await build()
    agent.default_options["tools"] = [lookup, lookup]
    return agent


def cleanup(agent):
    """Release only the application-owned resources."""
    record("application")


target = target_factory(build, agent_id="managed", cleanup=cleanup)
collision = target_factory(duplicate, agent_id="managed", cleanup=cleanup)
