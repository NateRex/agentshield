# AgentShield

AgentShield is a development tool for inspecting and security-testing configured
agents. The current implementation provides metadata inspection for Microsoft
Agent Framework (MAF). Inspection requires no interpreter settings or live model.

Install in the same Python 3.12 environment as your application:

```sh
pip install 'agentshield[maf]'
```

The framework-independent core has no runtime dependencies. The MAF extra pins
`agent-framework-core==1.22.0` and `agent-framework-openai==1.17.0`. Inspection
rejects missing packages and other version pairs with installation guidance.
These versions have deterministic inspection coverage; conversation execution
and model-backed release validation are separate work.

Expose a dedicated integration in an importable module, for example `myapp/shield.py`:

```python
from agentshield import target_factory

def build():
    """Construct the application's configured MAF Agent with test dependencies."""
    from myapp.agents import create_agent
    return create_agent()

target = target_factory(build, agent_id="support")
```

Then run from your application environment:

```sh
agentshield inspect myapp.shield:target --timeout 10
```

`target_factory` returns the public `Target` interface. A module must expose this
explicit integration, rather than an arbitrary callable or live agent instance.
`build()` may return an agent or an awaitable agent. For asynchronous resources:

```python
from agentshield import Target

async def build():
    """Construct the configured agent without starting conversations."""
    from myapp.agents import create_agent_async
    return await create_agent_async()

async def cleanup(agent):
    """Release application-owned resources, excluding framework-owned contexts."""
    from myapp.resources import close_application_resources
    await close_application_resources()

target = Target(build=build, agent_id="support", cleanup=cleanup)
```

The build and cleanup hooks run in the spawned worker. Construction must clean up
its own partial resources if it fails before returning an agent. AgentShield calls
MAF `agent.close()` for framework-owned contexts, followed by your optional
`cleanup(agent)` hook even when metadata inspection fails. Do not close those same
contexts in your hook. Both sync and async cleanup are supported. An optional
`reset(agent)` hook can declare application state reset behavior for future
scenario execution; inspection never invokes it. Inspection never calls
`agent.open()`: opening MAF also opens external MCP integrations. If construction
itself opens resources, it owns any consequences and partial failure handling.

The command writes JSON to stdout, warnings and application construction prints
to stderr, and exits 0 on success or 2 on an inspection failure. The deadline
covers process startup, imports, construction, metadata inspection, and cleanup.
Import failures, unsupported target shapes, ambiguous identities, cleanup errors,
worker crashes, and timeouts are errors. For Python use:

```python
from agentshield import inspect_target

if __name__ == "__main__":
    print(inspect_target("myapp.shield:target", timeout=10))
```

The main guard is required for spawn-safe Python callers, including Windows.
Neither the CLI coordinator nor `inspect_target` imports the application's module
in its own process. Only JSON metadata crosses the worker boundary.

Inspection output includes a logical agent identity, per-tool registered names,
descriptions, Python docstrings, available input schemas, metadata provenance,
observation/replacement seam support, known result encoding, and authorization
limitations. Qualified identities such as `support/lookup` use your explicit
stable logical agent ID and MAF's registered tool name. IDs allow letters, digits,
underscores, dots, and hyphens. Collisions and unnameable tools fail inspection;
AgentShield never derives identities from generated agent UUIDs or list positions.

Plain local MAF FunctionTools advertise the function-middleware seam. Their
default parser encodes results as MAF content lists; custom parsers and external
tools have unknown return contracts. Metadata does not prove runtime behavior.
Hosted tools, MCP integrations, agent-as-tool wrappers, custom subclasses, context
providers, and dynamically introduced tools have no deep inspection guarantee.
Inventory completeness is always `partial`: absent metadata is not proof of an
absent capability. Tool-body and inner authorization checks are not established
by reaching function middleware. Inspection never runs conversations, tools, reset
hooks, or an interpreter, and does not open integrations to discover more tools.

Application imports and construction **can cause real effects**. Workers and
best-effort interception are **not a sandbox**. Forced termination cannot guarantee
resource cleanup, stop descendant processes, or roll back external state. Use
external restrictions when containment is required.

For deterministic development validation (no model endpoint):

```sh
uv sync --locked --extra maf
uv run --locked --extra maf mypy src/agentshield
uv run --locked --extra maf pytest
```

Windows/Python 3.12 spawn inspection is checked locally; Linux/Python 3.12 uses the
same tests in CI. To evaluate a candidate MAF pair, update the pins and adapter
compatibility metadata together, run these contracts on both platforms, then run
the model-backed reference evaluation release gate before advertising broader
execution support. Successful imports alone do not establish compatibility.
