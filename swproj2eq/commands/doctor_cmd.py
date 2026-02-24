"""Doctor command."""

import json

from swproj2eq.constants import ExitCode, VIRTUAL_SINK
from swproj2eq.runtime.detect import (
    detect_camilladsp,
    detect_pipewire,
    detect_systemd_user,
    get_default_sink,
    get_sink_sample_rate,
    is_camilla_active,
    is_easyeffects_active,
)
from swproj2eq.runtime.routing import sink_exists
from swproj2eq.runtime.service import is_active


def run(args):
    checks = {
        "pipewire": detect_pipewire(),
        "systemd_user": detect_systemd_user(),
        "camilladsp": detect_camilladsp(),
    }

    default_sink = get_default_sink()
    payload = {
        "checks": {k: {"ok": v.ok, "message": v.message, "hints": v.hints} for k, v in checks.items()},
        "default_sink": default_sink,
        "default_sink_sample_rate": get_sink_sample_rate(default_sink),
        "virtual_sink_exists": sink_exists(VIRTUAL_SINK),
        "service_active": is_active(),
        "easyeffects_active": is_easyeffects_active(),
        "other_camilladsp_active": is_camilla_active(),
    }
    payload["healthy"] = all(v.ok for v in checks.values())

    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2))
    else:
        print("swproj2eq doctor")
        for name, check in payload["checks"].items():
            print(f"- {name}: {'ok' if check['ok'] else 'fail'} ({check['message']})")
            for hint in check["hints"]:
                print(f"    hint: {hint}")
        print(f"- default_sink: {payload['default_sink']}")
        print(f"- default_sink_sample_rate: {payload['default_sink_sample_rate']}")
        print(f"- virtual_sink_exists: {payload['virtual_sink_exists']}")
        print(f"- service_active: {payload['service_active']}")
        print(f"- easyeffects_active: {payload['easyeffects_active']}")
        print(f"- other_camilladsp_active: {payload['other_camilladsp_active']}")
        print(f"- healthy: {payload['healthy']}")

    return ExitCode.OK if payload["healthy"] else ExitCode.UNHEALTHY
