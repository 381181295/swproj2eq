"""PipeWire routing helpers."""

from swproj2eq.constants import VIRTUAL_SINK
from swproj2eq.runtime.commands import run_command
from swproj2eq.runtime.detect import list_sinks


def sink_exists(name=VIRTUAL_SINK):
    return name in list_sinks()


def ensure_virtual_sink(name=VIRTUAL_SINK):
    if sink_exists(name):
        return True
    res = run_command(
        [
            "pactl",
            "load-module",
            "module-null-sink",
            f"sink_name={name}",
            "object.linger=1",
            "media.class=Audio/Sink",
            "channel_map=FL,FR",
        ]
    )
    if res.code != 0:
        return sink_exists(name)
    return True


def unload_virtual_sink(name=VIRTUAL_SINK):
    modules = run_command(["pactl", "list", "short", "modules"])
    if modules.code != 0:
        return False
    ok = True
    for line in modules.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        mod_id, mod_name, mod_args = parts[0], parts[1], parts[2]
        if mod_name == "module-null-sink" and f"sink_name={name}" in mod_args:
            res = run_command(["pactl", "unload-module", mod_id])
            if res.code != 0:
                ok = False
    return ok


def set_default_sink(name):
    res = run_command(["pactl", "set-default-sink", name])
    return res.code == 0
