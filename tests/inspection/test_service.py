"""Public behavior checks matching the corresponding source module."""

import pytest

from agentshield.inspection import InspectionError, inspect_target


def test_async_target_cleanup_and_reset_ownership(tmp_path, monkeypatch):
    """Async hooks work and inspection runs cleanup without resetting state."""
    marker = tmp_path / "cleanup.txt"
    monkeypatch.setenv("AGENTSHIELD_CLEANUP_MARKER", str(marker))
    report = inspect_target("tests.inspection.adapters.maf.reference_async:target")
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
        inspect_target(f"tests.inspection.adapters.maf.reference_failures:{target}")



def test_hanging_construction_has_a_bounded_deadline():
    """A blocked factory cannot keep the coordinator waiting indefinitely."""
    with pytest.raises(InspectionError, match="deadline exceeded"):
        inspect_target("tests.inspection.adapters.maf.reference_failures:timeout", timeout=2)



def test_failed_import_is_reported():
    """Import errors are returned from the worker with useful diagnostics."""
    with pytest.raises(InspectionError, match="ModuleNotFoundError"):
        inspect_target("nonexistent_application:target")
