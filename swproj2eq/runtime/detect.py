"""Environment and runtime detection."""

from dataclasses import dataclass
from pathlib import Path

from swproj2eq.runtime.commands import command_exists, run_command, run_user_systemctl


@dataclass
class DetectionResult:
    ok: bool
    message: str
    hints: list[str]


def detect_distro_id():
    os_release = Path("/etc/os-release")
    if not os_release.exists():
        return "unknown"
    for line in os_release.read_text().splitlines():
        if line.startswith("ID="):
            return line.split("=", 1)[1].strip().strip('"')
    return "unknown"


def dependency_hints(dep):
    distro = detect_distro_id()
    if dep == "pipewire":
        if distro in ("ubuntu", "debian"):
            return ["sudo apt install pipewire pipewire-pulse wireplumber"]
        if distro in ("fedora",):
            return ["sudo dnf install pipewire pipewire-pulseaudio wireplumber"]
        if distro in ("arch", "manjaro"):
            return ["sudo pacman -S pipewire pipewire-pulse wireplumber"]
        return ["install PipeWire + pipewire-pulse + wireplumber using your distro package manager"]
    if dep == "camilladsp":
        if distro in ("ubuntu", "debian"):
            return [
                "sudo apt install camilladsp  # if available",
                "or download release binary from https://github.com/HEnquist/camilladsp/releases",
            ]
        if distro in ("fedora",):
            return ["sudo dnf install camilladsp"]
        if distro in ("arch", "manjaro"):
            return ["sudo pacman -S camilladsp"]
        return ["install camilladsp from https://github.com/HEnquist/camilladsp/releases"]
    return []


def detect_pipewire():
    if not command_exists("pactl"):
        return DetectionResult(False, "missing pactl", dependency_hints("pipewire"))
    if not command_exists("pw-cli"):
        return DetectionResult(False, "missing pw-cli", dependency_hints("pipewire"))
    res = run_command(["pactl", "info"])
    if res.code != 0:
        return DetectionResult(False, "pactl info failed", dependency_hints("pipewire"))
    if "pipewire" not in (res.stdout + res.stderr).lower():
        return DetectionResult(False, "PipeWire not detected", ["This MVP supports PipeWire only"])
    return DetectionResult(True, "PipeWire detected", [])


def detect_systemd_user():
    if not command_exists("systemctl"):
        return DetectionResult(False, "missing systemctl", ["systemd user session required for MVP"])
    res = run_user_systemctl(["show-environment"])
    if res.code != 0:
        return DetectionResult(False, "systemd --user not available", ["run inside a systemd user session"])
    return DetectionResult(True, "systemd user session detected", [])


def detect_camilladsp():
    if not command_exists("camilladsp"):
        return DetectionResult(False, "missing camilladsp", dependency_hints("camilladsp"))
    return DetectionResult(True, "camilladsp detected", [])


def get_default_sink():
    if not command_exists("pactl"):
        return None
    res = run_command(["pactl", "get-default-sink"])
    if res.code == 0 and res.stdout.strip():
        return res.stdout.strip()

    info = run_command(["pactl", "info"])
    if info.code != 0:
        return None
    for line in info.stdout.splitlines():
        if line.lower().startswith("default sink:"):
            return line.split(":", 1)[1].strip()
    return None


def list_sinks():
    if not command_exists("pactl"):
        return []
    res = run_command(["pactl", "list", "short", "sinks"])
    if res.code != 0:
        return []
    sinks = []
    for line in res.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            sinks.append(parts[1])
    return sinks


def get_sink_sample_rate(sink_name):
    if not command_exists("pactl"):
        return None
    if not sink_name:
        return None
    res = run_command(["pactl", "list", "sinks"])
    if res.code != 0:
        return None

    current_name = None
    for line in res.stdout.splitlines():
        line = line.strip()
        if line.startswith("Name:"):
            current_name = line.split(":", 1)[1].strip()
        if current_name == sink_name and line.startswith("Sample Specification:"):
            for token in line.split():
                if token.endswith("Hz") and token[:-2].isdigit():
                    return int(token[:-2])
    return None


def is_easyeffects_active():
    if not command_exists("pgrep"):
        return False
    res = run_command(["pgrep", "-x", "easyeffects"])
    return res.code == 0


def is_camilla_active():
    if not command_exists("pgrep"):
        return False
    res = run_command(["pgrep", "-f", "camilladsp"])
    return res.code == 0
