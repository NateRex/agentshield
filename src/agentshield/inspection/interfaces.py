"""Framework-independent interface for construction-time metadata inspection."""

from typing import Any, Protocol


class InspectionAdapter(Protocol):
    """Describe and release a constructed agent without opening integrations.

    Implementations validate their dependencies before application import, return
    JSON-serializable metadata with explicit discovery limits, and close only
    framework-owned resources. They never invoke conversations or application
    cleanup. An adapter may be a module satisfying these operations.
    """

    def check_versions(self) -> None:
        """Raise an actionable error for missing or unsupported dependencies."""
        ...

    def describe(self, agent: Any, agent_id: str) -> dict[str, Any]:
        """Return metadata or reject an unsupported agent or ambiguous identity."""
        ...

    async def close(self, agent: Any) -> None:
        """Release framework-owned contexts without opening new integrations."""
        ...
