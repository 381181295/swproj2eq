"""Enable command."""

from pathlib import Path

from swproj2eq.commands.common import require_yes
from swproj2eq.constants import ExitCode, VIRTUAL_SINK
from swproj2eq.profile.manager import list_profiles, load_manifest
from swproj2eq.runtime.detect import get_default_sink, is_camilla_active, is_easyeffects_active
from swproj2eq.runtime.routing import ensure_virtual_sink, set_default_sink, sink_exists
from swproj2eq.runtime.service import daemon_reload, enable_start, is_active, is_enabled, write_service_file
from swproj2eq.state.locks import state_lock
from swproj2eq.state.store import load_state, save_state


def run(args):
    with state_lock():
        state = load_state()
        profile_id = args.profile_id or state.get("active_profile_id")
        if not profile_id:
            available = list_profiles()
            print("error: no profile selected")
            if available:
                print("available:")
                for p in available:
                    print(f"  - {p}")
            return ExitCode.USAGE

        manifest = load_manifest(profile_id)
        if not manifest:
            print(f"error: profile manifest not found: {profile_id}")
            return ExitCode.USAGE

        if is_easyeffects_active() and not args.force:
            print("error: EasyEffects appears active; stop it or pass --force")
            return ExitCode.RUNTIME_ERROR
        if is_camilla_active() and not args.force:
            print("error: another camilladsp process appears active; stop it or pass --force")
            return ExitCode.RUNTIME_ERROR

        config_path = manifest["artifacts"]["camilla_config"]
        if not Path(config_path).exists():
            print("error: missing camilla config in profile artifacts; rerun quickstart")
            return ExitCode.RUNTIME_ERROR

        if not ensure_virtual_sink(VIRTUAL_SINK):
            print("error: failed to create virtual sink")
            return ExitCode.RUNTIME_ERROR

        write_service_file(config_path, profile_id)
        if not daemon_reload() or not enable_start():
            print("error: failed to enable/start service")
            return ExitCode.RUNTIME_ERROR
        if not is_active() or not sink_exists(VIRTUAL_SINK):
            print("error: service or sink health check failed")
            return ExitCode.RUNTIME_ERROR

        should_switch = args.set_default
        if not args.set_default and not args.yes:
            should_switch = require_yes(args, f"Set default sink to {VIRTUAL_SINK}?")

        if should_switch:
            prev = get_default_sink()
            if not set_default_sink(VIRTUAL_SINK):
                print("error: failed to switch default sink")
                return ExitCode.RUNTIME_ERROR
            state["previous_default_sink"] = prev
            state["default_sink_switched"] = True

        state["active_profile_id"] = profile_id
        state["runtime"]["service_enabled"] = is_enabled()
        state["runtime"]["service_active"] = True
        save_state(state)
        print(f"enable ok: {profile_id}")
        return ExitCode.OK
