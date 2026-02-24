"""High-level export orchestration."""

import os

from swproj2eq.core.parser import parse_swproj
from swproj2eq.exporters.camilla_exporter import export_camilladsp
from swproj2eq.exporters.csv_exporter import export_csv
from swproj2eq.exporters.easyeffects_exporter import export_easyeffects
from swproj2eq.exporters.eqapo_exporter import export_eqapo
from swproj2eq.exporters.pipewire_exporter import export_pipewire


def run_export(
    filepath,
    outdir=None,
    sample_rate=48000,
    camilla_capture_device="swproj2eq_in.monitor",
    camilla_playback_device="",
):
    profile = parse_swproj(filepath, require_stereo=True)
    channels = profile.channels

    print(f"\nParsed {len(channels)} channels:")
    for ch in channels:
        print(f"  {ch.name} (index={ch.index}, group={ch.group})")
        print(f"    Delay: {ch.delay_ms:.4f} ms")
        print(f"    Freq range: {ch.frequencies[0]:.0f} - {ch.frequencies[-1]:.0f} Hz")
        print(f"    Correction: {min(ch.correction_dB):.1f} to {max(ch.correction_dB):.1f} dB")

    base = os.path.splitext(os.path.basename(filepath))[0]
    if outdir is None:
        outdir = os.path.join(os.path.dirname(filepath) or ".", f"{base}_export")
    os.makedirs(outdir, exist_ok=True)

    print(f"\nExporting to {outdir}/\n")
    csv_path = os.path.join(outdir, f"{base}.csv")
    eqapo_path = os.path.join(outdir, f"{base}_eqapo.txt")
    camilla_dir = os.path.join(outdir, "camilladsp")
    pipewire_dir = os.path.join(outdir, "pipewire")
    easyeffects_dir = os.path.join(outdir, "easyeffects")

    export_csv(channels, csv_path)
    print(f"  CSV: {csv_path}")

    export_eqapo(channels, eqapo_path)
    print(f"  EQ APO: {eqapo_path}")

    camilla_result = export_camilladsp(
        channels,
        camilla_dir,
        sample_rate=sample_rate,
        capture_device=camilla_capture_device,
        playback_device=camilla_playback_device,
    )
    print(f"  CamillaDSP config: {camilla_result['config_path']}")

    pipewire_result = export_pipewire(channels, pipewire_dir, sample_rate=sample_rate)
    print(f"  PipeWire config: {pipewire_result['config_path']}")

    easyeffects_result = export_easyeffects(channels, easyeffects_dir, sample_rate=sample_rate)
    print(f"  EasyEffects IR: {easyeffects_result['ir_path']}")

    print("\nDone! See each subdirectory for format-specific files.")
    return {
        "profile": profile,
        "outdir": outdir,
        "csv_path": csv_path,
        "eqapo_path": eqapo_path,
        "camilla": camilla_result,
        "pipewire": pipewire_result,
        "easyeffects": easyeffects_result,
    }
