"""Systemd user service helpers."""

from pathlib import Path

from swproj2eq.constants import SERVICE_NAME, VIRTUAL_SINK
from swproj2eq.runtime.commands import run_user_systemctl
from swproj2eq.state.paths import runner_script_path, service_file_path


def write_runner_script(camilla_config_path):
    script = runner_script_path()
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"pactl load-module module-null-sink sink_name={VIRTUAL_SINK} object.linger=1 media.class=Audio/Sink channel_map=FL,FR >/dev/null 2>&1 || true\n"
        f"exec camilladsp \"{camilla_config_path}\"\n"
    )
    script.chmod(0o755)
    return script


def write_service_file(camilla_config_path, profile_id):
    unit = service_file_path()
    unit.parent.mkdir(parents=True, exist_ok=True)
    runner = write_runner_script(camilla_config_path)

    content = (
        "[Unit]\n"
        "Description=swproj2eq CamillaDSP runtime\n"
        "After=pipewire.service pipewire-pulse.service wireplumber.service\n\n"
        "[Service]\n"
        "Type=simple\n"
        f"Environment=SWPROJ2EQ_PROFILE_ID={profile_id}\n"
        f"ExecStart={runner}\n"
        "Restart=on-failure\n"
        "RestartSec=2\n\n"
        "[Install]\n"
        "WantedBy=default.target\n"
    )
    unit.write_text(content)
    return unit


def daemon_reload():
    return run_user_systemctl(["daemon-reload"]).code == 0


def enable_start():
    en = run_user_systemctl(["enable", "--now", SERVICE_NAME])
    return en.code == 0


def stop_disable():
    run_user_systemctl(["stop", SERVICE_NAME])
    run_user_systemctl(["disable", SERVICE_NAME])
    return True


def is_active():
    res = run_user_systemctl(["is-active", SERVICE_NAME])
    return res.code == 0 and res.stdout.strip() == "active"


def is_enabled():
    res = run_user_systemctl(["is-enabled", SERVICE_NAME])
    return res.code == 0 and res.stdout.strip() == "enabled"


def remove_service_file():
    sf = service_file_path()
    if sf.exists():
        sf.unlink()
    rs = runner_script_path()
    if rs.exists():
        rs.unlink()
    return True
