"""Quickstart command."""

from swproj2eq.commands.common import ensure_existing_file, require_yes, resolve_profile_arg
from swproj2eq.constants import ExitCode, VIRTUAL_SINK
from swproj2eq.export_pipeline import run_export
from swproj2eq.profile.manager import compute_profile_id, profile_dir, write_manifest
from swproj2eq.runtime.detect import (
    detect_camilladsp,
    detect_pipewire,
    detect_systemd_user,
    get_default_sink,
    get_sink_sample_rate,
    is_camilla_active,
    is_easyeffects_active,
)
from swproj2eq.runtime.routing import ensure_virtual_sink, set_default_sink, sink_exists, unload_virtual_sink
from swproj2eq.runtime.service import (
    daemon_reload,
    enable_start,
    is_active,
    is_enabled,
    stop_disable,
    write_service_file,
)
from swproj2eq.state.locks import state_lock
from swproj2eq.state.paths import ensure_dirs
from swproj2eq.state.store import load_state, save_state


def _print_detection_failure(result):
    print(f"error: {result.message}")
    for hint in result.hints:
        print(f"  - {hint}")


def run(args):
    with state_lock():
        ensure_dirs()
        previous_sink_for_rollback = None
        switched_default = False

        def fail_with_rollback(message):
            if switched_default and previous_sink_for_rollback:
                set_default_sink(previous_sink_for_rollback)
            stop_disable()
            unload_virtual_sink(VIRTUAL_SINK)
            print(message)
            return ExitCode.RUNTIME_ERROR

        for check in (detect_pipewire(), detect_systemd_user(), detect_camilladsp()):
            if not check.ok:
                _print_detection_failure(check)
                return ExitCode.RUNTIME_ERROR

        if is_easyeffects_active() and not args.force:
            print("error: EasyEffects appears active; stop it or pass --force")
            return ExitCode.RUNTIME_ERROR
        if is_camilla_active() and not args.force:
            print("error: another camilladsp process appears active; stop it or pass --force")
            return ExitCode.RUNTIME_ERROR

        profile_arg = resolve_profile_arg(args)
        profile_path = ensure_existing_file(profile_arg)
        if not profile_path:
            print("error: missing/invalid .swproj path")
            return ExitCode.USAGE

        default_sink = get_default_sink()
        if not default_sink:
            print("error: unable to determine current default sink")
            return ExitCode.RUNTIME_ERROR

        # Persist checkpoint before any routing/service changes.
        state = load_state()
        if not state.get("previous_default_sink"):
            state["previous_default_sink"] = default_sink
            save_state(state)

        sample_rate = get_sink_sample_rate(default_sink) or 48000
        profile_id = compute_profile_id(profile_path)
        outdir = profile_dir(profile_id) / "exports"

        try:
            result = run_export(
                str(profile_path),
                str(outdir),
                sample_rate=sample_rate,
                camilla_capture_device=f"{VIRTUAL_SINK}.monitor",
                camilla_playback_device=default_sink,
            )
        except Exception as exc:
            print(f"error: export failed: {exc}")
            return ExitCode.RUNTIME_ERROR

        write_manifest(profile_id, profile_path, result)

        if not ensure_virtual_sink(VIRTUAL_SINK):
            print("error: failed to create virtual sink")
            return ExitCode.RUNTIME_ERROR

        service_path = write_service_file(result["camilla"]["config_path"], profile_id)
        if not daemon_reload():
            return fail_with_rollback("error: systemd --user daemon-reload failed")
        if not enable_start():
            return fail_with_rollback("error: failed to enable/start swproj2eq service")

        if not is_active() or not sink_exists(VIRTUAL_SINK):
            return fail_with_rollback("error: service or sink health check failed")

        state["active_profile_id"] = profile_id
        state["runtime"]["service_enabled"] = is_enabled()
        state["runtime"]["service_active"] = True
        state["created_files"] = [str(service_path), str(outdir)]

        should_switch = args.set_default
        if not args.set_default and not args.yes:
            should_switch = require_yes(args, f"Set default sink to {VIRTUAL_SINK}?")

        if should_switch:
            previous_sink_for_rollback = get_default_sink()
            state["previous_default_sink"] = previous_sink_for_rollback
            if not set_default_sink(VIRTUAL_SINK):
                return fail_with_rollback("error: failed to switch default sink")
            switched_default = True
            if get_default_sink() != VIRTUAL_SINK:
                return fail_with_rollback("error: default sink switch did not stick")
            state["default_sink_switched"] = True
        else:
            state["default_sink_switched"] = False
            if state.get("previous_default_sink") is None:
                state["previous_default_sink"] = default_sink

        save_state(state)
        print(f"quickstart ok: profile {profile_id} active")
        if not should_switch:
            print(f"note: default sink unchanged (use --set-default to route all apps)")
        return ExitCode.OK
