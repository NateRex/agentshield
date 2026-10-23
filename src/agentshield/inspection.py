"""Spawn-based inspection coordinator; no live agent crosses process boundaries."""

import asyncio
import contextlib
import importlib
import inspect
import math
import multiprocessing
import time
from multiprocessing.connection import Connection
from typing import Any

from .target import Target


class InspectionError(RuntimeError):
    """Target import, construction, inspection, cleanup, or worker failure."""


async def _resolve(value: Any) -> Any:
    """Normalize synchronous and asynchronous lifecycle return values."""
    return await value if inspect.isawaitable(value) else value


async def _inspect(reference: str) -> dict[str, Any]:
    """Load an explicit integration and close each resource under its owner."""
    from .maf import check_versions, describe, validate_identity

    check_versions()
    module, separator, attribute = reference.partition(":")
    if not separator or not module or not attribute or ":" in attribute:
        raise ValueError("Use an explicit module:target reference")
    integration = getattr(importlib.import_module(module), attribute)
    if not isinstance(integration, Target):
        raise ValueError("Entry point must expose Target or target_factory(...), not an arbitrary callable")
    validate_identity(integration.agent_id)
    agent = await _resolve(integration.build())
    try:
        return describe(agent, integration.agent_id)
    finally:
        try:
            # Never call open(): it opens MCP and client integrations for discovery.
            from agent_framework import Agent
            if type(agent) is Agent:
                await agent.close()
        finally:
            if integration.cleanup is not None:
                await _resolve(integration.cleanup(agent))


def _worker(reference: str, connection: Connection) -> None:
    """Send only JSON metadata or a diagnostic back to the coordinator."""
    # Application stdout must not corrupt the command's JSON output.
    import sys
    try:
        with contextlib.redirect_stdout(sys.stderr):
            report = asyncio.run(_inspect(reference))
        import json
        connection.send_bytes(json.dumps({"report": report}).encode())
    except BaseException as exc:
        import json
        connection.send_bytes(json.dumps({"error": f"{type(exc).__name__}: {exc}"}).encode())
    finally:
        connection.close()


def inspect_target(reference: str, *, timeout: float = 10.0) -> dict[str, Any]:
    """Inspect module:target in a spawned worker within an overall deadline.

    The deadline includes startup, imports, construction, metadata, and cleanup.
    Forced termination cannot guarantee application cleanup or contain side effects.
    Call from a guarded main entry point when using Python on spawn platforms.
    """
    import json
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be a positive finite number")
    context = multiprocessing.get_context("spawn")
    receive, send = context.Pipe(duplex=False)
    process = context.Process(target=_worker, args=(reference, send))
    deadline = time.monotonic() + timeout
    try:
        process.start()
        send.close()
        if not receive.poll(max(0, deadline - time.monotonic())):
            raise InspectionError(f"Inspection deadline exceeded ({timeout}s); cleanup is not guaranteed")
        try:
            message = json.loads(receive.recv_bytes())
        except EOFError as exc:
            raise InspectionError("Inspection worker exited without a result") from exc
        process.join(max(0, deadline - time.monotonic()))
        if process.is_alive():
            raise InspectionError("Inspection worker did not exit before deadline; cleanup is not guaranteed")
        if "error" in message:
            raise InspectionError(message["error"])
        if process.exitcode != 0:
            raise InspectionError(f"Inspection worker exited with code {process.exitcode}")
        return message["report"]
    finally:
        receive.close()
        send.close()
        if process.pid is not None:
            if process.is_alive():
                process.terminate()
                process.join(1)
            if process.is_alive():
                process.kill()
                process.join(1)
            process.close()
