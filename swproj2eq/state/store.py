"""Persistent runtime state."""

import json
from datetime import datetime, UTC

from swproj2eq.state.paths import ensure_dirs, state_file


def _now_iso():
    return datetime.now(UTC).isoformat()


def default_state():
    return {
        "version": 1,
        "active_profile_id": None,
        "previous_default_sink": None,
        "default_sink_switched": False,
        "runtime": {
            "service_enabled": False,
            "service_active": False,
        },
        "created_files": [],
        "updated_at": _now_iso(),
    }


def load_state():
    ensure_dirs()
    sf = state_file()
    if not sf.exists():
        return default_state()
    try:
        with sf.open("r") as f:
            data = json.load(f)
        base = default_state()
        base.update(data)
        return base
    except Exception:
        return default_state()


def _atomic_write_json(path, payload):
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(payload, f, indent=2)
    tmp.replace(path)


def save_state(state):
    ensure_dirs()
    state = dict(state)
    state["updated_at"] = _now_iso()
    _atomic_write_json(state_file(), state)
    return state


def update_state(**kwargs):
    state = load_state()
    state.update(kwargs)
    return save_state(state)
