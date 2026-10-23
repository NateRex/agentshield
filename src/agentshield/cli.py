
"""Command-line inspection without interpreter configuration."""

import argparse
import json
import sys

from .inspection import InspectionError, inspect_target


def main() -> None:
    """Print inspection JSON; exit 2 on construction or compatibility errors."""
    parser = argparse.ArgumentParser(prog="agentshield")
    commands = parser.add_subparsers(dest="command", required=True)
    inspection = commands.add_parser("inspect", help="Inspect registered MAF target metadata")
    inspection.add_argument("target", help="Explicit module:target integration")
    inspection.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()
    print("Warning: application import/construction can have effects; this is not a sandbox. "
          "Termination cannot guarantee cleanup.", file=sys.stderr)
    try:
        report = inspect_target(args.target, timeout=args.timeout)
    except (InspectionError, ValueError) as exc:
        parser.exit(2, f"Inspection failed: {exc}\n")
    print(json.dumps(report, indent=2))
