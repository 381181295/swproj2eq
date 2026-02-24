"""CLI entry and command wiring."""

import argparse
import sys

from swproj2eq.commands import (
    doctor_cmd,
    disable_cmd,
    enable_cmd,
    export_cmd,
    quickstart_cmd,
    rollback_cmd,
    status_cmd,
    tui_cmd,
    uninstall_cmd,
)
from swproj2eq.constants import ExitCode


COMMANDS = {
    "export": export_cmd.run,
    "quickstart": quickstart_cmd.run,
    "enable": enable_cmd.run,
    "disable": disable_cmd.run,
    "status": status_cmd.run,
    "doctor": doctor_cmd.run,
    "rollback": rollback_cmd.run,
    "uninstall": uninstall_cmd.run,
    "tui": tui_cmd.run,
}


def build_parser():
    parser = argparse.ArgumentParser(prog="swproj2eq")
    sub = parser.add_subparsers(dest="command")

    p_export = sub.add_parser("export", help="Export profile to all formats")
    p_export.add_argument("profile_pos", nargs="?", help="Path to .swproj profile")
    p_export.add_argument("--profile", help="Path to .swproj profile")
    p_export.add_argument("--outdir", help="Output directory")

    p_quickstart = sub.add_parser("quickstart", help="Guided setup")
    p_quickstart.add_argument("--profile", help="Path to .swproj profile")
    p_quickstart.add_argument("--set-default", action="store_true")
    p_quickstart.add_argument("--yes", action="store_true")
    p_quickstart.add_argument("--force", action="store_true")

    p_enable = sub.add_parser("enable", help="Enable existing profile")
    p_enable.add_argument("--profile-id")
    p_enable.add_argument("--set-default", action="store_true")
    p_enable.add_argument("--yes", action="store_true")
    p_enable.add_argument("--force", action="store_true")

    p_disable = sub.add_parser("disable", help="Disable swproj2eq runtime")
    p_disable.add_argument("--yes", action="store_true")
    p_disable.add_argument("--force", action="store_true")

    p_status = sub.add_parser("status", help="Show runtime status")
    p_status.add_argument("--json", action="store_true")

    p_doctor = sub.add_parser("doctor", help="Run diagnostics")
    p_doctor.add_argument("--json", action="store_true")

    p_rollback = sub.add_parser("rollback", help="Restore previous sink/runtime")
    p_rollback.add_argument("--yes", action="store_true")
    p_rollback.add_argument("--force", action="store_true")

    p_uninstall = sub.add_parser("uninstall", help="Remove swproj2eq runtime")
    p_uninstall.add_argument("--purge-profiles", action="store_true")
    p_uninstall.add_argument("--yes", action="store_true")
    p_uninstall.add_argument("--force", action="store_true")

    sub.add_parser("tui", help="Launch minimal text UI")

    return parser


def normalize_legacy_args(argv):
    if not argv:
        return argv

    known = set(COMMANDS.keys())
    first = argv[0]
    if first in known or first.startswith("-"):
        return argv

    # Backward compat: `python3 swproj2eq.py path/to/file.swproj --outdir ...`
    return ["export", "--profile", first, *argv[1:]]


def main(argv=None):
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    argv = normalize_legacy_args(raw_argv)
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return ExitCode.USAGE

    return COMMANDS[args.command](args)
