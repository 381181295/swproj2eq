"""TUI command wrapper."""

from swproj2eq.constants import ExitCode
from swproj2eq.tui.app import run_tui


def run(args):
    return run_tui()
