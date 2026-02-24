"""Status command."""

import json

from swproj2eq.constants import ExitCode, VIRTUAL_SINK
from swproj2eq.runtime.detect import get_default_sink
from swproj2eq.runtime.routing import sink_exists
from swproj2eq.runtime.service import is_active, is_enabled
from swproj2eq.state.store import load_state


def run(args):
    state = load_state()
    payload = {
        "active_profile_id": state.get("active_profile_id"),
        "default_sink": get_default_sink(),
        "virtual_sink": VIRTUAL_SINK,
        "virtual_sink_exists": sink_exists(VIRTUAL_SINK),
        "service_active": is_active(),
        "service_enabled": is_enabled(),
        "default_sink_switched": state.get("default_sink_switched", False),
        "previous_default_sink": state.get("previous_default_sink"),
    }

    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2))
    else:
        print("swproj2eq status")
        for k, v in payload.items():
            print(f"- {k}: {v}")
    return ExitCode.OK
