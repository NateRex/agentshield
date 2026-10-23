"""Exercise inspection at the documented command and target seams."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from agentshield import InspectionError, inspect_target


def test_sync_target_inspection_without_a_model():
    """Expose metadata without running the conversation or tool body."""
    result = subprocess.run(
        [sys.executable, "-m", "agentshield", "inspect", "tests.reference_sync:target"],
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


def test_async_target_cleanup_and_reset_ownership(tmp_path, monkeypatch):
    """Async hooks work and inspection runs cleanup without resetting state."""
    marker = tmp_path / "cleanup.txt"
    monkeypatch.setenv("AGENTSHIELD_CLEANUP_MARKER", str(marker))
    report = inspect_target("tests.reference_async:target")
    assert report["agent"]["identity"] == "async-reference"
    assert marker.read_text() == "closed"


@pytest.mark.parametrize(("target", "diagnostic"), [
    ("failure", "construction failed deliberately"),
    ("collision", "identity collision"),
    ("invalid", "Expected a configured MAF Agent"),
    ("ambiguous", "Invalid logical identity"),
    ("crashed", "exited without a result"),
    ("absent", "AttributeError"),
    ("build", "Entry point must expose Target"),
    ("cleanup_error", "application cleanup failed"),
    ("oversized", "metadata exceeds 1048576 bytes"),
])
def test_invalid_targets_fail_with_diagnostics(target, diagnostic):
    """Public inspection rejects ambiguous or failing integrations."""
    with pytest.raises(InspectionError, match=diagnostic):
        inspect_target(f"tests.reference_failures:{target}")


def test_hanging_construction_has_a_bounded_deadline():
    """A blocked factory cannot keep the coordinator waiting indefinitely."""
    with pytest.raises(InspectionError, match="deadline exceeded"):
        inspect_target("tests.reference_failures:timeout", timeout=2)


def test_failed_import_is_reported():
    """Import errors are returned from the worker with useful diagnostics."""
    with pytest.raises(InspectionError, match="ModuleNotFoundError"):
        inspect_target("nonexistent_application:target")


def test_core_imports_and_missing_extra_is_actionable():
    """An isolated core imports without framework packages or site-packages."""
    environment = {**os.environ, "PYTHONPATH": str(Path("src").resolve())}
    result = subprocess.run(
        [sys.executable, "-S", "-c",
         "import agentshield, sys; assert 'agent_framework' not in sys.modules"],
        env=environment, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    result = subprocess.run(
        [sys.executable, "-S", "-m", "agentshield", "inspect", "unused:target"],
        env=environment, capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 2
    assert "pip install 'agentshield[maf]'" in result.stderr


def test_unsupported_version_pair_is_rejected(tmp_path):
    """An installed but unsupported framework version cannot pass inspection."""
    metadata = tmp_path / "agent_framework_core-0.0.1.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: agent-framework-core\nVersion: 0.0.1\n",
        encoding="utf-8",
    )
    environment = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join([str(tmp_path), str(Path("src").resolve())]),
    }
    result = subprocess.run(
        [sys.executable, "-S", "-m", "agentshield", "inspect", "unused:target"],
        env=environment, capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 2
    assert "Unsupported agent-framework-core 0.0.1; expected 1.22.0" in result.stderr


def test_external_integrations_are_not_opened_for_discovery():
    """Unreachable MCP integrations remain metadata-only and unsupported."""
    report = inspect_target("tests.reference_failures:external")
    tools = {tool["identity"]: tool for tool in report["tools"]}
    assert tools["external/external"]["replacement_support"] == "unsupported"
    assert tools["external/declaration"]["observation_support"] == "unsupported"
    assert report["inventory_completeness"] == "partial"


def test_custom_result_parser_is_not_assumed_to_use_default_encoding():
    """A custom parser requires explicit fixture context for future execution."""
    report = inspect_target("tests.reference_failures:custom")
    assert report["tools"][0]["result_encoding"] == "unknown_custom_or_external"


@pytest.mark.parametrize("target", ["target", "collision"])
def test_resource_owners_cleanup_once_even_on_discovery_failure(target, tmp_path, monkeypatch):
    """MAF contexts and application resources are released once by their owners."""
    marker = tmp_path / "lifecycle.txt"
    monkeypatch.setenv("AGENTSHIELD_LIFECYCLE_MARKER", str(marker))
    if target == "collision":
        with pytest.raises(InspectionError, match="identity collision"):
            inspect_target(f"tests.reference_lifecycle:{target}")
    else:
        inspect_target(f"tests.reference_lifecycle:{target}")
    assert marker.read_text() == "framework\napplication\n"


def test_provider_tool_declarations_keep_available_metadata():
    """Dictionary tools retain descriptions and input schemas without support claims."""
    report = inspect_target("tests.reference_failures:dictionary")
    tool = report["tools"][0]
    assert tool["description"] == "Look up a declared resource"
    assert tool["input_schema"]["properties"]["query"] == {"type": "string"}
    assert tool["replacement_support"] == "unsupported"
