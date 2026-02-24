"""Shared command helpers."""

from pathlib import Path


def resolve_profile_arg(args):
    profile = getattr(args, "profile", None) or getattr(args, "profile_pos", None)
    if profile:
        return profile
    try:
        value = input("Path to .swproj profile: ").strip()
    except EOFError:
        return None
    return value or None


def require_yes(args, action_text):
    if getattr(args, "yes", False):
        return True
    try:
        reply = input(f"{action_text} [y/N]: ").strip().lower()
    except EOFError:
        return False
    return reply in ("y", "yes")


def ensure_existing_file(path_text):
    if not path_text:
        return None
    p = Path(path_text).expanduser()
    if not p.exists() or not p.is_file():
        return None
    return p
