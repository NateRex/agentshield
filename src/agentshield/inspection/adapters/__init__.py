"""Framework implementation selection, loaded only inside inspection workers."""

from ..interfaces import InspectionAdapter


def get_adapter() -> InspectionAdapter:
    """Return the sole supported inspection adapter without importing MAF itself."""
    from . import maf

    return maf
