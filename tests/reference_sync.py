"""Synchronous reference integration that must never call a model."""

from agent_framework import Agent, tool
from agentshield import target_factory


class OfflineClient:
    """Fail immediately if inspection starts a conversation."""

    async def get_response(self, *args, **kwargs):
        """Reject model access in deterministic inspection checks."""
        raise AssertionError("Inspection invoked the model")


@tool
def lookup(query: str) -> str:
    """Look up a synthetic document by query."""
    raise AssertionError("Inspection invoked a tool")


def build():
    """Construct an offline MAF target."""
    return Agent(client=OfflineClient(), name="Reference", tools=[lookup])


target = target_factory(build, agent_id="reference")
