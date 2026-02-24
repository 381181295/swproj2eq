"""Profile storage and manifest utilities."""

from datetime import datetime, UTC
import hashlib
import json
from pathlib import Path

from swproj2eq.state.paths import profile_dir, profiles_dir


def compute_profile_id(profile_path):
    p = Path(profile_path)
    h = hashlib.sha256()
    with p.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()[:12]


def manifest_path(profile_id):
    return profile_dir(profile_id) / "manifest.json"


def write_manifest(profile_id, source_path, export_result):
    pdir = profile_dir(profile_id)
    pdir.mkdir(parents=True, exist_ok=True)
    payload = {
        "profile_id": profile_id,
        "created_at": datetime.now(UTC).isoformat(),
        "source_path": str(source_path),
        "channels": [
            {
                "name": ch.name,
                "index": ch.index,
                "group": ch.group,
                "delay_ms": ch.delay_ms,
            }
            for ch in export_result["profile"].channels
        ],
        "artifacts": {
            "outdir": export_result["outdir"],
            "camilla_config": export_result["camilla"]["config_path"],
            "pipewire_config": export_result["pipewire"]["config_path"],
            "eqapo": export_result["eqapo_path"],
            "csv": export_result["csv_path"],
            "easyeffects_ir": export_result["easyeffects"]["ir_path"],
        },
    }
    with manifest_path(profile_id).open("w") as f:
        json.dump(payload, f, indent=2)
    return payload


def load_manifest(profile_id):
    mp = manifest_path(profile_id)
    if not mp.exists():
        return None
    with mp.open("r") as f:
        return json.load(f)


def list_profiles():
    root = profiles_dir()
    if not root.exists():
        return []
    result = []
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        mp = d / "manifest.json"
        if mp.exists():
            result.append(d.name)
    return result
