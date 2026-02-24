"""EQ APO (GraphicEQ) exporter."""

from swproj2eq.core.dsp import compute_preamp_db


def export_eqapo(channels, outpath):
    with open(outpath, "w") as f:
        f.write("# Sonarworks SoundID Reference correction curves\n")
        f.write("# Exported from .swproj file\n\n")
        global_preamp = compute_preamp_db(channels)
        for ch in channels:
            f.write(f"# Channel: {ch.name} (delay: {ch.delay_ms:.4f} ms)\n")
            if global_preamp < 0:
                f.write(f"Preamp: {global_preamp:.1f} dB\n")
            points = "; ".join(
                f"{freq:.1f} {corr:.1f}"
                for freq, corr in zip(ch.frequencies, ch.correction_dB)
            )
            f.write(f"GraphicEQ: {points}\n\n")
