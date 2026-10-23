"""Stable identity rules shared by workflow and framework implementations."""

import re


def validate_identity(value: str) -> None:
    """Reject ambiguous qualification separators and empty or unstable names."""
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
        raise ValueError(f"Invalid logical identity {value!r}; use letters, digits, _, . or -")
