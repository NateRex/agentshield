"""MAF-specific metadata discovery; never opens integrations or invokes tools."""

import inspect
import re
from importlib.metadata import PackageNotFoundError, version
from typing import Any

# Keep the extra in pyproject.toml in sync; expand only after compatibility checks.
SUPPORTED_VERSIONS = {"agent-framework-core": "1.22.0", "agent-framework-openai": "1.17.0"}


def check_versions() -> None:
    """Reject missing extras and unvalidated framework/client package pairs."""
    for package, expected in SUPPORTED_VERSIONS.items():
        try:
            installed = version(package)
        except PackageNotFoundError as exc:
            raise ValueError("MAF inspection requires pip install 'agentshield[maf]'") from exc
        if installed != expected:
            raise ValueError(
                f"Unsupported {package} {installed}; expected {expected}. "
                "Install the tested pair with pip install 'agentshield[maf]'."
            )


def validate_identity(value: str) -> None:
    """Reject ambiguous qualification separators and empty or unstable names."""
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
        raise ValueError(f"Invalid logical identity {value!r}; use letters, digits, _, . or -")


def describe(agent: Any, agent_id: str) -> dict[str, Any]:
    """Inspect registered MAF metadata with explicit discovery and seam limits."""
    from agent_framework import Agent, FunctionTool

    if type(agent) is not Agent:
        raise ValueError("Expected a configured MAF Agent; custom agent subclasses are unsupported")
    validate_identity(agent_id)
    tools = []
    identities: set[str] = set()
    for registered in [*agent.default_options.get("tools", []), *agent.mcp_tools]:
        name = getattr(registered, "name", None)
        if name is None and isinstance(registered, dict):
            name = registered.get("name")
        if name is None:
            raise ValueError("Registered tool has no stable name; expose a named tool or wrapper")
        validate_identity(name)
        identity = f"{agent_id}/{name}"
        if identity in identities:
            raise ValueError(f"Ambiguous tool identity collision: {identity}")
        identities.add(identity)
        local = type(registered) is FunctionTool and registered.func is not None
        schema = registered.parameters() if isinstance(registered, FunctionTool) else None
        parser = getattr(registered, "result_parser", None)
        tools.append({
            "identity": identity, "registered_name": name,
            "description": getattr(registered, "description", None),
            "docstring": inspect.getdoc(registered.func) if local else None,
            "input_schema": schema,
            "metadata_provenance": ["maf.registration", "python.docstring"] if local else ["maf.registration"],
            "observation_support": "function_middleware" if local else "unsupported",
            "replacement_support": "function_middleware" if local else "unsupported",
            "result_encoding": "maf_content_list" if local and parser is None else "unknown_custom_or_external",
            "authorization_limitations": "Middleware does not prove tool-body or inner authorization checks ran.",
        })
    return {
        "format_version": 1,
        "framework_versions": SUPPORTED_VERSIONS,
        "agent": {"identity": agent_id, "name": agent.name, "description": agent.description},
        "tools": tools,
        "inventory_completeness": "partial",
        "limitations": [
            "Only construction-time registered metadata is visible; runtime/context-provider tools may differ.",
            "External integrations are not opened; hidden tools and I/O are not discovered.",
            "Capabilities describe the adapter seam, not verified behavior or authorization.",
            "Application import/construction can have real effects. This is not a sandbox.",
            "Termination does not guarantee cleanup or external-state rollback.",
        ],
    }
