"""Public behavior checks matching the corresponding source module."""

import os
from pathlib import Path
import subprocess
import sys

import pytest

from agentshield.inspection import InspectionError, inspect_target


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
    report = inspect_target("tests.inspection.adapters.maf.reference_failures:external")
    tools = {tool["identity"]: tool for tool in report["tools"]}
    assert tools["external/external"]["replacement_support"] == "unsupported"
    assert tools["external/declaration"]["observation_support"] == "unsupported"
    assert report["inventory_completeness"] == "partial"



def test_custom_result_parser_is_not_assumed_to_use_default_encoding():
    """A custom parser requires explicit fixture context for future execution."""
    report = inspect_target("tests.inspection.adapters.maf.reference_failures:custom")
    assert report["tools"][0]["result_encoding"] == "unknown_custom_or_external"



@pytest.mark.parametrize("target", ["target", "collision"])
def test_resource_owners_cleanup_once_even_on_discovery_failure(target, tmp_path, monkeypatch):
    """MAF contexts and application resources are released once by their owners."""
    marker = tmp_path / "lifecycle.txt"
    monkeypatch.setenv("AGENTSHIELD_LIFECYCLE_MARKER", str(marker))
    if target == "collision":
        with pytest.raises(InspectionError, match="identity collision"):
            inspect_target(f"tests.inspection.adapters.maf.reference_lifecycle:{target}")
    else:
        inspect_target(f"tests.inspection.adapters.maf.reference_lifecycle:{target}")
    assert marker.read_text() == "framework\napplication\n"



def test_provider_tool_declarations_keep_available_metadata():
    """Dictionary tools retain descriptions and input schemas without support claims."""
    report = inspect_target("tests.inspection.adapters.maf.reference_failures:dictionary")
    tool = report["tools"][0]
    assert tool["description"] == "Look up a declared resource"
    assert tool["input_schema"]["properties"]["query"] == {"type": "string"}
    assert tool["replacement_support"] == "unsupported"
