"""Managed path layout."""

from pathlib import Path


def config_dir():
    return Path.home() / ".config" / "swproj2eq"


def data_dir():
    return Path.home() / ".local" / "share" / "swproj2eq"


def state_dir():
    return Path.home() / ".local" / "state" / "swproj2eq"


def logs_dir():
    return state_dir() / "logs"


def profiles_dir():
    return data_dir() / "profiles"


def profile_dir(profile_id):
    return profiles_dir() / profile_id


def state_file():
    return state_dir() / "state.json"


def lock_file():
    return state_dir() / "lock"


def runner_script_path():
    return data_dir() / "bin" / "swproj2eq-run.sh"


def service_file_path():
    return Path.home() / ".config" / "systemd" / "user" / "swproj2eq-camilla.service"


def ensure_dirs():
    for p in [config_dir(), data_dir(), state_dir(), logs_dir(), profiles_dir(), runner_script_path().parent, service_file_path().parent]:
        p.mkdir(parents=True, exist_ok=True)
