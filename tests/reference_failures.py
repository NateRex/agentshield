"""Deliberately invalid and bounded-failure integrations."""

import os
import time

from agentshield import target_factory
from tests.reference_sync import build, lookup
from agent_framework import FunctionTool, MCPStreamableHTTPTool


def broken():
    """Fail during construction."""
    raise RuntimeError("construction failed deliberately")


def hanging():
    """Block indefinitely until the coordinator terminates the worker."""
    time.sleep(60)


def crash():
    """Exit before sending metadata."""
    os._exit(7)


def duplicates():
    """Expose colliding registered names."""
    agent = build()
    agent.default_options["tools"] = [lookup, lookup]
    return agent


def unsupported():
    """Return a non-framework target."""
    return object()


def external_tools():
    """Register an unreachable external tool without ever connecting to it."""
    agent = build()
    agent.mcp_tools.append(MCPStreamableHTTPTool(name="external", url="http://127.0.0.1:1/mcp"))
    agent.default_options["tools"].append(FunctionTool(name="declaration"))
    return agent


def custom_parser():
    """Expose a custom result contract, which inspection must not guess."""
    agent = build()
    agent.default_options["tools"] = [
        FunctionTool(name="custom", func=lambda: "unused", result_parser=str),
    ]
    return agent


def cleanup_failure(agent):
    """Report a failed application cleanup rather than returning success."""
    raise RuntimeError("application cleanup failed")


failure = target_factory(broken, agent_id="broken")
timeout = target_factory(hanging, agent_id="hanging")
collision = target_factory(duplicates, agent_id="collision")
invalid = target_factory(unsupported, agent_id="invalid")
crashed = target_factory(crash, agent_id="crashed")
ambiguous = target_factory(build, agent_id="ambiguous/name")
external = target_factory(external_tools, agent_id="external")
custom = target_factory(custom_parser, agent_id="custom")
cleanup_error = target_factory(build, agent_id="cleanup-error", cleanup=cleanup_failure)
