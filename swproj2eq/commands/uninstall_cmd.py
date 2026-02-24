"""Uninstall command."""

import shutil

from swproj2eq.constants import ExitCode
from swproj2eq.runtime.routing import unload_virtual_sink
from swproj2eq.runtime.service import daemon_reload, remove_service_file, stop_disable
from swproj2eq.state.locks import state_lock
from swproj2eq.state.paths import config_dir, data_dir, profiles_dir, state_dir
from swproj2eq.state.store import default_state, save_state


def _safe_rmtree(path):
    if path.exists():
        shutil.rmtree(path)


def run(args):
    with state_lock():
        stop_disable()
        unload_virtual_sink()
        remove_service_file()
        daemon_reload()

        # remove only swproj2eq-managed locations
        _safe_rmtree(config_dir())
        if args.purge_profiles:
            _safe_rmtree(profiles_dir())

        # remove runtime state/logs after writing reset state
        save_state(default_state())
        if args.purge_profiles:
            # profiles live under data_dir; keep bin dir if not purge
            _safe_rmtree(data_dir())
        _safe_rmtree(state_dir())

        print("uninstall ok")
        return ExitCode.OK
