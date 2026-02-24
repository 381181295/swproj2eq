"""Disable command."""

from swproj2eq.constants import ExitCode
from swproj2eq.runtime.detect import get_default_sink
from swproj2eq.runtime.routing import set_default_sink
from swproj2eq.runtime.service import is_active, stop_disable
from swproj2eq.state.locks import state_lock
from swproj2eq.state.store import load_state, save_state


def run(args):
    with state_lock():
        state = load_state()

        stop_disable()

        if state.get("default_sink_switched") and state.get("previous_default_sink"):
            current = get_default_sink()
            if current != state["previous_default_sink"]:
                set_default_sink(state["previous_default_sink"])

        state["runtime"]["service_enabled"] = False
        state["runtime"]["service_active"] = is_active()
        state["default_sink_switched"] = False
        save_state(state)
        print("disable ok")
        return ExitCode.OK
