import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from swproj2eq.commands import quickstart_cmd
from swproj2eq.constants import ExitCode


class DummyDetection:
    def __init__(self, ok=True, message="ok", hints=None):
        self.ok = ok
        self.message = message
        self.hints = hints or []


class QuickstartTests(unittest.TestCase):
    def test_quickstart_happy_path(self):
        args = SimpleNamespace(profile=None, set_default=False, yes=True, force=False)
        with tempfile.TemporaryDirectory() as td:
            profile = Path(td) / "test.swproj"
            profile.write_bytes(b"dummy")
            args.profile = str(profile)

            export_result = {
                "profile": SimpleNamespace(channels=[]),
                "outdir": str(Path(td) / "out"),
                "csv_path": str(Path(td) / "out.csv"),
                "eqapo_path": str(Path(td) / "out.txt"),
                "camilla": {"config_path": str(Path(td) / "camilladsp.yml")},
                "pipewire": {"config_path": str(Path(td) / "swproj2eq.conf")},
                "easyeffects": {"ir_path": str(Path(td) / "ir.wav")},
            }

            with (
                patch("swproj2eq.commands.quickstart_cmd.detect_pipewire", return_value=DummyDetection()),
                patch("swproj2eq.commands.quickstart_cmd.detect_systemd_user", return_value=DummyDetection()),
                patch("swproj2eq.commands.quickstart_cmd.detect_camilladsp", return_value=DummyDetection()),
                patch("swproj2eq.commands.quickstart_cmd.is_easyeffects_active", return_value=False),
                patch("swproj2eq.commands.quickstart_cmd.is_camilla_active", return_value=False),
                patch("swproj2eq.commands.quickstart_cmd.get_default_sink", return_value="alsa_output.test"),
                patch("swproj2eq.commands.quickstart_cmd.get_sink_sample_rate", return_value=48000),
                patch("swproj2eq.commands.quickstart_cmd.compute_profile_id", return_value="abc123"),
                patch("swproj2eq.commands.quickstart_cmd.run_export", return_value=export_result),
                patch("swproj2eq.commands.quickstart_cmd.write_manifest", return_value={}),
                patch("swproj2eq.commands.quickstart_cmd.ensure_virtual_sink", return_value=True),
                patch("swproj2eq.commands.quickstart_cmd.write_service_file", return_value="/tmp/service"),
                patch("swproj2eq.commands.quickstart_cmd.daemon_reload", return_value=True),
                patch("swproj2eq.commands.quickstart_cmd.enable_start", return_value=True),
                patch("swproj2eq.commands.quickstart_cmd.is_active", return_value=True),
                patch("swproj2eq.commands.quickstart_cmd.sink_exists", return_value=True),
                patch("swproj2eq.commands.quickstart_cmd.is_enabled", return_value=True),
                patch("swproj2eq.commands.quickstart_cmd.load_state", return_value={
                    "version": 1,
                    "active_profile_id": None,
                    "previous_default_sink": None,
                    "default_sink_switched": False,
                    "runtime": {"service_enabled": False, "service_active": False},
                    "created_files": [],
                }),
                patch("swproj2eq.commands.quickstart_cmd.save_state", return_value={}),
            ):
                code = quickstart_cmd.run(args)
                self.assertEqual(code, ExitCode.OK)


if __name__ == "__main__":
    unittest.main()
