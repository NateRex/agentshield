"""Application construction and resource ownership contracts."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class Target:
    """Explicit target integration, constructed only in a worker.

    ``build`` returns an agent or awaitable agent. ``cleanup(agent)`` releases
    application-owned resources; it must not close the agent's framework-owned
    contexts, which AgentShield closes. Construction that fails before returning
    must release its own partial resources. ``reset(agent)`` is an optional hook
    for future scenario execution and is never called by inspection.
    """

    build: Callable[[], Any]
    agent_id: str
    cleanup: Callable[[Any], Any] | None = None
    reset: Callable[[Any], Any] | None = None


def target_factory(
    build: Callable[[], Any], *, agent_id: str,
    cleanup: Callable[[Any], Any] | None = None,
    reset: Callable[[Any], Any] | None = None,
) -> Target:
    """Expose a sync or async configured-agent factory with stable logical ID."""
    return Target(build=build, agent_id=agent_id, cleanup=cleanup, reset=reset)
