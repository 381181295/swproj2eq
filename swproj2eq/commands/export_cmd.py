"""Export command."""

from pathlib import Path

from swproj2eq.constants import ExitCode
from swproj2eq.export_pipeline import run_export


def run(args):
    profile = args.profile or args.profile_pos
    if not profile:
        print("error: missing profile path (.swproj)")
        return ExitCode.USAGE

    profile_path = Path(profile).expanduser()
    if not profile_path.exists():
        print(f"error: profile not found: {profile_path}")
        return ExitCode.USAGE

    try:
        run_export(str(profile_path), args.outdir)
    except Exception as exc:
        print(f"error: export failed: {exc}")
        return ExitCode.RUNTIME_ERROR

    return ExitCode.OK
