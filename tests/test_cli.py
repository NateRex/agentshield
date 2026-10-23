"""Public behavior checks matching the corresponding source module."""

import json
import os
from pathlib import Path
import subprocess
import sys


def test_sync_target_inspection_without_a_model():
    """Expose metadata without running the conversation or tool body."""
    result = subprocess.run(
        [sys.executable, "-m", "agentshield", "inspect", "tests.inspection.adapters.maf.reference_sync:target"],
        capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["agent"]["identity"] == "reference"
    assert report["inventory_completeness"] == "partial"
    tool = report["tools"][0]
    assert tool["identity"] == "reference/lookup"
    assert tool["input_schema"]["properties"]["query"]["type"] == "string"
    assert "synthetic document" in tool["docstring"]



def test_missing_extra_is_actionable():
    """Missing optional framework packages produce installation guidance."""
    environment = {**os.environ, "PYTHONPATH": str(Path("src").resolve())}
    result = subprocess.run(
        [sys.executable, "-S", "-m", "agentshield", "inspect", "unused:target"],
        env=environment, capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 2
    assert "pip install 'agentshield[maf]'" in result.stderr
