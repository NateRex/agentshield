"""Inspect configured targets through bounded workers and framework adapters."""

from .service import InspectionError, inspect_target

__all__ = ["InspectionError", "inspect_target"]
