"""Spawn-based inspection coordinator; no live agent crosses process boundaries."""

import asyncio
import contextlib
import importlib
import inspect
import math
import multiprocessing
import queue
import threading
import time
from multiprocessing.connection import Connection
from typing import Any

from agentshield.core import Target
from agentshield.core.identity import validate_identity

MAX_REPORT_BYTES = 1_048_576


class InspectionError(RuntimeError):
    """Target import, construction, inspection, cleanup, or worker failure."""


async def _resolve(value: Any) -> Any:
    """Normalize synchronous and asynchronous lifecycle return values."""
    return await value if inspect.isawaitable(value) else value


async def _inspect(reference: str) -> dict[str, Any]:
    """Load an explicit integration and close each resource under its owner."""
    from .adapters import get_adapter

    adapter = get_adapter()
    adapter.check_versions()
    module, separator, attribute = reference.partition(":")
    if not separator or not module or not attribute or ":" in attribute:
        raise ValueError("Use an explicit module:target reference")
    integration = getattr(importlib.import_module(module), attribute)
    if not isinstance(integration, Target):
        raise ValueError("Entry point must expose Target or target_factory(...), not an arbitrary callable")
    validate_identity(integration.agent_id)
    agent = await _resolve(integration.build())
    try:
        return adapter.describe(agent, integration.agent_id)
    finally:
        try:
            # Never call open(): it opens MCP and client integrations for discovery.
            await adapter.close(agent)
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
        payload = json.dumps({"report": report}).encode()
        if len(payload) > MAX_REPORT_BYTES:
            raise ValueError(f"Inspection metadata exceeds {MAX_REPORT_BYTES} bytes; reduce tool metadata")
        connection.send_bytes(payload)
    except BaseException as exc:
        import json
        connection.send_bytes(json.dumps({"error": f"{type(exc).__name__}: {exc}"}).encode())
    finally:
        connection.close()


def _receive(connection: Connection, messages: queue.Queue) -> None:
    """Decode bounded worker transport off the coordinator's deadline thread."""
    import json
    try:
        messages.put(json.loads(connection.recv_bytes(MAX_REPORT_BYTES)))
    except EOFError:
        messages.put({"error": "Inspection worker exited without a result"})
    except (OSError, ValueError) as exc:
        messages.put({"error": f"Invalid inspection worker result: {exc}"})


def inspect_target(reference: str, *, timeout: float = 10.0) -> dict[str, Any]:
    """Inspect module:target in a spawned worker within an overall deadline.

    The deadline includes startup, imports, construction, metadata, and cleanup.
    Forced termination cannot guarantee application cleanup or contain side effects.
    Call from a guarded main entry point when using Python on spawn platforms.
    """
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be a positive finite number")
    context = multiprocessing.get_context("spawn")
    receive, send = context.Pipe(duplex=False)
    process = context.Process(target=_worker, args=(reference, send))
    deadline = time.monotonic() + timeout
    reader: threading.Thread | None = None
    try:
        process.start()
        send.close()
        messages: queue.Queue = queue.Queue(maxsize=1)
        reader = threading.Thread(target=_receive, args=(receive, messages), daemon=True)
        reader.start()
        try:
            message = messages.get(timeout=max(0, deadline - time.monotonic()))
        except queue.Empty as exc:
            raise InspectionError(
                f"Inspection deadline exceeded ({timeout}s); cleanup is not guaranteed"
            ) from exc
        process.join(max(0, deadline - time.monotonic()))
        if process.is_alive():
            raise InspectionError("Inspection worker did not exit before deadline; cleanup is not guaranteed")
        if "error" in message:
            raise InspectionError(message["error"])
        if process.exitcode != 0:
            raise InspectionError(f"Inspection worker exited with code {process.exitcode}")
        return message["report"]
    except OSError as exc:
        raise InspectionError(f"Could not run inspection worker: {exc}") from exc
    finally:
        send.close()
        if process.pid is not None:
            if process.is_alive():
                process.terminate()
                process.join(1)
            if process.is_alive():
                process.kill()
                process.join(1)
            process.close()
        if reader is not None:
            reader.join(1)
        receive.close()
