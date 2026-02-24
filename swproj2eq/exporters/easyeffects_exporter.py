"""EasyEffects convolver exporter."""

import array
import os
import wave

from swproj2eq.core.dsp import compute_preamp_db, freq_response_to_ir_fast


def export_easyeffects(channels, outdir, sample_rate=48000):
    os.makedirs(outdir, exist_ok=True)

    irs = []
    for ch in channels:
        ir = freq_response_to_ir_fast(ch.frequencies, ch.correction_dB, sample_rate, 4096)
        irs.append(ir)

    stereo_path = os.path.join(outdir, "swproj2eq_correction_stereo.wav")
    peak = max(max(abs(s) for s in ir) for ir in irs) or 1.0
    scale = 0.95 / peak
    interleaved = []
    for i in range(len(irs[0])):
        for ir in irs:
            interleaved.append(max(-32767, min(32767, int(ir[i] * scale * 32767))))

    with wave.open(stereo_path, "w") as w:
        w.setnchannels(len(channels))
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(array.array("h", interleaved).tobytes())

    preamp_db = compute_preamp_db(channels)
    instructions_path = os.path.join(outdir, "EASYEFFECTS_INSTRUCTIONS.txt")
    with open(instructions_path, "w") as f:
        f.write("EasyEffects Setup Instructions\n")
        f.write("=" * 40 + "\n\n")
        f.write("1. Open EasyEffects\n")
        f.write("2. Go to Output tab\n")
        f.write("3. Add Convolver effect\n")
        f.write(f"4. Load IR file: {os.path.abspath(stereo_path)}\n")
        f.write(f"5. Set input gain to {preamp_db:.1f} dB\n")

    return {
        "ir_path": stereo_path,
        "instructions_path": instructions_path,
        "preamp_db": preamp_db,
    }
