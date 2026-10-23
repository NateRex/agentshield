"""Shared target contracts remain available without framework dependencies."""

import os
from pathlib import Path
import subprocess
import sys


def test_public_packages_import_without_framework_dependencies():
    """Root exports and workflow packages remain usable in a core-only install."""
    result = subprocess.run(
        [sys.executable, "-S", "-c", """
import sys
import agentshield
import agentshield.core
import agentshield.inspection
import agentshield.planning
import agentshield.execution
assert agentshield.Target is agentshield.core.Target
assert agentshield.target_factory is agentshield.core.target_factory
assert agentshield.inspect_target is agentshield.inspection.inspect_target
assert agentshield.InspectionError is agentshield.inspection.InspectionError
assert 'agent_framework' not in sys.modules
assert 'agentshield.inspection.adapters.maf' not in sys.modules
"""],
        env={**os.environ, "PYTHONPATH": str(Path("src").resolve())},
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
