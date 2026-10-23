"""Framework-independent target integration and bounded metadata inspection."""

from .inspection import InspectionError, inspect_target
from .core import Target, target_factory

__all__ = ["Target", "target_factory", "inspect_target", "InspectionError"]
