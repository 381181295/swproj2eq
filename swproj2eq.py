#!/usr/bin/env python3
"""
Sonarworks .swproj file parser.

Extracts speaker calibration curves from SoundID Reference project files
and exports them to formats usable on Linux (CamillaDSP, PipeWire, EasyEffects).

File format (reverse-engineered):
  1. XML header (<ProjectHeader>) with version and part info
  2. Binary PEQb data containing per-channel blocks:
     - 2-float blocks (freq_hz, correction_dB) x 355 points = correction curve
     - 3-float blocks (freq_hz, measurement_dB, extra) x 355 points = raw measurement
  3. Metadata per channel: name, group, index, delay_ms, frequency range
  4. Remaining bytes after EQ data: encrypted/compressed project state (ignored)
"""

import struct
import re
import sys
import json
import csv
import os
import math
import wave
import array
from dataclasses import dataclass


@dataclass
class ChannelData:
    name: str
    index: int
    group: str
    delay_ms: float
    frequencies: list[float]
    correction_dB: list[float]
    measurement_dB: list[float]


def parse_swproj(filepath: str) -> list[ChannelData]:
    with open(filepath, "rb") as f:
        data = f.read()

    xml_end = data.find(b"</ProjectHeader>")
    if xml_end == -1:
        raise ValueError("Not a valid .swproj file (no ProjectHeader)")
    xml_end += len(b"</ProjectHeader>")

    # Find data headers: 355 points (0x163) + type 7
    DATA_HEADER = b"\x63\x01\x00\x00\x07\x00\x00\x00"
    data_headers = []
    pos = 0
    while True:
        idx = data.find(DATA_HEADER, pos)
        if idx == -1:
            break
        data_headers.append(idx)
        pos = idx + 1

    delay_positions = [m.start() for m in re.finditer(b"ChannelDelayMs", data)]
    all_boundaries = sorted(data_headers + delay_positions)

    def parse_metadata(start_pos):
        meta = {}
        pos = start_pos
        end = min((b for b in all_boundaries if b > start_pos), default=len(data))
        while pos < end:
            null_pos = data.find(b"\x00", pos, pos + 100)
            if null_pos == -1 or null_pos - pos > 50:
                pos += 1
                continue
            key = data[pos:null_pos].decode("ascii", errors="replace")
            if not key.isprintable() or len(key) < 2:
                pos += 1
                continue
            val_len_pos = null_pos + 1
            if val_len_pos + 4 > len(data):
                break
            val_len = struct.unpack_from("<I", data, val_len_pos)[0]
            if val_len > 200:
                pos += 1
                continue
            val = data[val_len_pos + 4 : val_len_pos + 4 + val_len].decode(
                "ascii", errors="replace"
            )
            meta[key] = val
            pos = val_len_pos + 4 + val_len
        return meta

    blocks = []
    for dh in data_headers:
        float_start = dh + 8
        next_boundary = min(
            (b for b in all_boundaries + [len(data)] if b > float_start),
            default=len(data),
        )
        block_bytes = next_boundary - float_start
        fpp = round((block_bytes // 4) / 355)
        freqs, values = [], []
        for j in range(355):
            offset = float_start + j * fpp * 4
            freq = struct.unpack_from("<f", data, offset)[0]
            val = struct.unpack_from("<f", data, offset + 4)[0]
            freqs.append(freq)
            values.append(val)
        blocks.append({"fpp": fpp, "freqs": freqs, "values": values})

    channels = {}
    meta_blocks = [parse_metadata(dp) for dp in delay_positions]

    for i, meta in enumerate(meta_blocks):
        ch_name = meta.get("ChannelName", f"Channel_{i}")
        ch_idx = int(meta.get("ChannelIndex", i))
        key = (ch_name, ch_idx)
        if key not in channels:
            channels[key] = ChannelData(
                name=ch_name, index=ch_idx,
                group=meta.get("ChannelGroup", ""),
                delay_ms=0.0, frequencies=[], correction_dB=[], measurement_dB=[],
            )
        delay_str = meta.get("ChannelDelayMs", "0")
        delay_val = float(delay_str) if delay_str not in ("-0", "0") else 0.0
        if delay_val != 0:
            channels[key].delay_ms = abs(delay_val)

    channel_list = sorted(channels.values(), key=lambda c: c.index)
    for ch_i, ch in enumerate(channel_list):
        corr_idx = ch_i * 2
        meas_idx = ch_i * 2 + 1
        if corr_idx < len(blocks):
            ch.frequencies = blocks[corr_idx]["freqs"]
            ch.correction_dB = blocks[corr_idx]["values"]
        if meas_idx < len(blocks):
            ch.measurement_dB = blocks[meas_idx]["values"]

    return channel_list


# ---------------------------------------------------------------------------
# FIR impulse response generation from frequency response curve
# ---------------------------------------------------------------------------

def freq_response_to_ir(freqs, gains_dB, sample_rate=48000, ir_length=4096):
    """Convert a frequency/gain curve to a minimum-phase FIR impulse response."""
    n_fft = ir_length
    half = n_fft // 2 + 1

    # Interpolate the correction curve onto linear frequency bins
    bin_freqs = [i * sample_rate / n_fft for i in range(half)]
    interp_gains_dB = []
    for bf in bin_freqs:
        if bf <= freqs[0]:
            interp_gains_dB.append(gains_dB[0])
        elif bf >= freqs[-1]:
            interp_gains_dB.append(gains_dB[-1])
        else:
            # Binary search for bracketing indices
            lo, hi = 0, len(freqs) - 1
            while hi - lo > 1:
                mid = (lo + hi) // 2
                if freqs[mid] <= bf:
                    lo = mid
                else:
                    hi = mid
            # Linear interpolation in log-freq domain
            if freqs[hi] != freqs[lo]:
                t = (math.log(bf) - math.log(freqs[lo])) / (
                    math.log(freqs[hi]) - math.log(freqs[lo])
                )
            else:
                t = 0
            interp_gains_dB.append(gains_dB[lo] + t * (gains_dB[hi] - gains_dB[lo]))

    # Convert dB to linear magnitude
    magnitudes = [10 ** (g / 20.0) for g in interp_gains_dB]

    # Build minimum-phase: use log-magnitude -> Hilbert transform -> phase
    log_mag = [math.log(max(m, 1e-10)) for m in magnitudes]

    # Mirror for full FFT spectrum
    full_log_mag = log_mag + log_mag[-2:0:-1]

    # IFFT of log magnitude to get cepstrum
    n = len(full_log_mag)
    cepstrum_real = [0.0] * n
    cepstrum_imag = [0.0] * n
    for k in range(n):
        for j in range(n):
            angle = 2 * math.pi * k * j / n
            cepstrum_real[k] += full_log_mag[j] * math.cos(angle) / n
            cepstrum_imag[k] += full_log_mag[j] * (-math.sin(angle)) / n

    # Apply minimum-phase window to cepstrum
    # Keep DC, double causal, zero anti-causal
    mp_cepstrum_real = [0.0] * n
    mp_cepstrum_imag = [0.0] * n
    mp_cepstrum_real[0] = cepstrum_real[0]
    for k in range(1, n // 2):
        mp_cepstrum_real[k] = 2 * cepstrum_real[k]
        mp_cepstrum_imag[k] = 2 * cepstrum_imag[k]
    if n % 2 == 0:
        mp_cepstrum_real[n // 2] = cepstrum_real[n // 2]

    # FFT of modified cepstrum to get complex log spectrum
    spec_real = [0.0] * n
    spec_imag = [0.0] * n
    for k in range(n):
        for j in range(n):
            angle = 2 * math.pi * k * j / n
            spec_real[k] += mp_cepstrum_real[j] * math.cos(angle) - mp_cepstrum_imag[j] * (-math.sin(angle))
            spec_imag[k] += mp_cepstrum_real[j] * (-math.sin(angle)) + mp_cepstrum_imag[j] * math.cos(angle)

    # Exponentiate to get minimum-phase spectrum
    mp_spec_real = [0.0] * n
    mp_spec_imag = [0.0] * n
    for k in range(n):
        e_real = math.exp(spec_real[k])
        mp_spec_real[k] = e_real * math.cos(spec_imag[k])
        mp_spec_imag[k] = e_real * math.sin(spec_imag[k])

    # IFFT to get impulse response
    ir = [0.0] * n
    for k in range(n):
        for j in range(n):
            angle = 2 * math.pi * k * j / n
            ir[k] += mp_spec_real[j] * math.cos(angle) - mp_spec_imag[j] * (-math.sin(angle))
        ir[k] /= n

    return ir[:ir_length]


def freq_response_to_ir_fast(freqs, gains_dB, sample_rate=48000, ir_length=4096):
    """Same as above but using numpy/scipy if available (much faster)."""
    try:
        import numpy as np
        from scipy import signal as sig

        n_fft = ir_length
        half = n_fft // 2 + 1
        bin_freqs = np.linspace(0, sample_rate / 2, half)

        # Log-frequency interpolation
        interp_gains = np.interp(
            np.log(np.clip(bin_freqs, freqs[0], freqs[-1])),
            np.log(freqs),
            gains_dB,
        )
        # Edges
        interp_gains[bin_freqs < freqs[0]] = gains_dB[0]
        interp_gains[bin_freqs > freqs[-1]] = gains_dB[-1]

        magnitudes = 10 ** (interp_gains / 20.0)

        # Minimum-phase via cepstral method
        log_mag = np.log(np.clip(magnitudes, 1e-10, None))
        full_log_mag = np.concatenate([log_mag, log_mag[-2:0:-1]])
        cepstrum = np.fft.ifft(full_log_mag).real
        n = len(cepstrum)
        window = np.zeros(n)
        window[0] = 1
        window[1 : n // 2] = 2
        if n % 2 == 0:
            window[n // 2] = 1
        mp_cepstrum = cepstrum * window
        min_phase_spec = np.exp(np.fft.fft(mp_cepstrum))
        ir = np.fft.ifft(min_phase_spec).real
        return ir[:ir_length].tolist()

    except ImportError:
        return freq_response_to_ir(freqs, gains_dB, sample_rate, ir_length)


def write_wav(filepath, samples, sample_rate=48000):
    """Write mono float samples to a 32-bit float WAV file."""
    # Normalize peak to 0.95
    peak = max(abs(s) for s in samples) or 1.0
    scale = 0.95 / peak
    int_samples = [max(-32767, min(32767, int(s * scale * 32767))) for s in samples]
    with wave.open(filepath, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)  # 16-bit
        w.setframerate(sample_rate)
        w.writeframes(array.array("h", int_samples).tobytes())


# ---------------------------------------------------------------------------
# Export functions
# ---------------------------------------------------------------------------

def export_csv(channels, outpath):
    with open(outpath, "w", newline="") as f:
        writer = csv.writer(f)
        header = ["frequency_hz"] + [f"{ch.name}_correction_dB" for ch in channels]
        writer.writerow(header)
        for i in range(len(channels[0].frequencies)):
            row = [f"{channels[0].frequencies[i]:.2f}"]
            for ch in channels:
                row.append(f"{ch.correction_dB[i]:.4f}")
            writer.writerow(row)
    print(f"  CSV: {outpath}")


def export_eqapo(channels, outpath):
    with open(outpath, "w") as f:
        f.write("# Sonarworks SoundID Reference correction curves\n")
        f.write("# Exported from .swproj file\n\n")
        for ch in channels:
            f.write(f"# Channel: {ch.name} (delay: {ch.delay_ms:.4f} ms)\n")
            max_gain = max(ch.correction_dB)
            if max_gain > 0:
                f.write(f"Preamp: {-max_gain:.1f} dB\n")
            points = "; ".join(
                f"{freq:.1f} {corr:.1f}"
                for freq, corr in zip(ch.frequencies, ch.correction_dB)
            )
            f.write(f"GraphicEQ: {points}\n\n")
    print(f"  EQ APO: {outpath}")


def export_camilladsp(channels, outdir, sample_rate=48000):
    """Generate CamillaDSP YAML config + impulse response WAV files."""
    os.makedirs(outdir, exist_ok=True)

    ir_files = []
    for ch in channels:
        print(f"  Generating IR for {ch.name}...", end=" ", flush=True)
        ir = freq_response_to_ir_fast(
            ch.frequencies, ch.correction_dB, sample_rate, 4096
        )
        fname = f"{ch.name.lower()}_correction.wav"
        fpath = os.path.join(outdir, fname)
        write_wav(fpath, ir, sample_rate)
        ir_files.append(fname)
        print(f"-> {fname}")

    # Also write raw freq/dB text files (useful for plotting/verification)
    for ch in channels:
        txt_path = os.path.join(outdir, f"{ch.name.lower()}_correction.txt")
        with open(txt_path, "w") as f:
            for freq, corr in zip(ch.frequencies, ch.correction_dB):
                f.write(f"{freq:.2f} {corr:.4f}\n")

    # Generate YAML config
    yaml_lines = []
    yaml_lines.append("# CamillaDSP config - Sonarworks speaker correction")
    yaml_lines.append("# Generated by swproj_parser.py")
    yaml_lines.append("")
    yaml_lines.append("devices:")
    yaml_lines.append(f"  samplerate: {sample_rate}")
    yaml_lines.append("  chunksize: 4096")
    yaml_lines.append("  capture:")
    yaml_lines.append('    type: Pulse   # change to Alsa if not using PulseAudio/PipeWire')
    yaml_lines.append("    channels: 2")
    yaml_lines.append('    device: "CamillaDSP.monitor"  # adjust to your setup')
    yaml_lines.append('    format: S32LE')
    yaml_lines.append("  playback:")
    yaml_lines.append('    type: Pulse   # change to Alsa if not using PulseAudio/PipeWire')
    yaml_lines.append("    channels: 2")
    yaml_lines.append('    device: "alsa_output.your_device"  # adjust to your setup')
    yaml_lines.append('    format: S32LE')
    yaml_lines.append("")

    # Filters
    yaml_lines.append("filters:")
    for i, ch in enumerate(channels):
        name = ch.name.lower()
        yaml_lines.append(f"  {name}_eq:")
        yaml_lines.append("    type: Conv")
        yaml_lines.append("    parameters:")
        yaml_lines.append(f'      filename: "{ir_files[i]}"')
        yaml_lines.append("      type: Wav")
        yaml_lines.append(f"      channel: 0")
        if ch.delay_ms > 0:
            yaml_lines.append(f"  {name}_delay:")
            yaml_lines.append("    type: Delay")
            yaml_lines.append("    parameters:")
            yaml_lines.append(f"      delay: {ch.delay_ms}")
            yaml_lines.append("      unit: ms")

    # Preamp (negative of max gain to prevent clipping)
    all_max = max(max(ch.correction_dB) for ch in channels)
    if all_max > 0:
        yaml_lines.append("  preamp:")
        yaml_lines.append("    type: Gain")
        yaml_lines.append("    parameters:")
        yaml_lines.append(f"      gain: {-all_max - 1:.1f}")

    yaml_lines.append("")
    yaml_lines.append("pipeline:")

    if all_max > 0:
        yaml_lines.append("  - type: Filter")
        yaml_lines.append(f"    channel: 0")
        yaml_lines.append("    names:")
        yaml_lines.append("      - preamp")
        yaml_lines.append("  - type: Filter")
        yaml_lines.append(f"    channel: 1")
        yaml_lines.append("    names:")
        yaml_lines.append("      - preamp")

    for i, ch in enumerate(channels):
        name = ch.name.lower()
        names = [f"{name}_eq"]
        if ch.delay_ms > 0:
            names.append(f"{name}_delay")
        yaml_lines.append("  - type: Filter")
        yaml_lines.append(f"    channel: {i}")
        yaml_lines.append("    names:")
        for n in names:
            yaml_lines.append(f"      - {n}")

    yaml_path = os.path.join(outdir, "camilladsp.yml")
    with open(yaml_path, "w") as f:
        f.write("\n".join(yaml_lines) + "\n")
    print(f"  CamillaDSP config: {yaml_path}")

    # Summary JSON
    summary = {"source": "Sonarworks SoundID Reference (.swproj)", "channels": []}
    for ch in channels:
        summary["channels"].append({
            "name": ch.name, "index": ch.index, "group": ch.group,
            "delay_ms": ch.delay_ms,
            "freq_range": [round(ch.frequencies[0], 2), round(ch.frequencies[-1], 2)],
            "correction_range_dB": [round(min(ch.correction_dB), 2), round(max(ch.correction_dB), 2)],
        })
    with open(os.path.join(outdir, "profile_info.json"), "w") as f:
        json.dump(summary, f, indent=2)


def export_pipewire(channels, outdir, sample_rate=48000):
    """Generate PipeWire filter-chain config using convolver with the IR WAVs."""
    os.makedirs(outdir, exist_ok=True)

    # Reuse or generate IR WAVs
    ir_files = []
    for ch in channels:
        fname = f"{ch.name.lower()}_correction.wav"
        fpath = os.path.join(outdir, fname)
        if not os.path.exists(fpath):
            print(f"  Generating IR for {ch.name}...", end=" ", flush=True)
            ir = freq_response_to_ir_fast(
                ch.frequencies, ch.correction_dB, sample_rate, 4096
            )
            write_wav(fpath, ir, sample_rate)
            print(f"-> {fname}")
        ir_files.append(os.path.abspath(fpath))

    # Preamp
    all_max = max(max(ch.correction_dB) for ch in channels)
    preamp_dB = -(all_max + 1) if all_max > 0 else 0

    conf_lines = []
    conf_lines.append("# PipeWire filter-chain config - Sonarworks speaker correction")
    conf_lines.append("# Copy to ~/.config/pipewire/filter-chain.conf.d/sonarworks.conf")
    conf_lines.append("# Then: systemctl --user restart pipewire")
    conf_lines.append("")
    conf_lines.append("context.modules = [")
    conf_lines.append("  {")
    conf_lines.append("    name = libpipewire-module-filter-chain")
    conf_lines.append("    args = {")
    conf_lines.append('      node.description = "Sonarworks Speaker Correction"')
    conf_lines.append('      media.name = "Sonarworks Speaker Correction"')
    conf_lines.append("      filter.graph = {")
    conf_lines.append("        nodes = [")

    # Preamp node
    if preamp_dB != 0:
        conf_lines.append("          {")
        conf_lines.append("            type = builtin")
        conf_lines.append("            name = preamp")
        conf_lines.append("            label = bq_highshelf")
        conf_lines.append(f'            control = {{ "Freq" = 0 "Q" = 1.0 "Gain" = {preamp_dB:.1f} }}')
        conf_lines.append("          }")

    # Convolver nodes (one per channel)
    for i, ch in enumerate(channels):
        name = ch.name.lower()
        conf_lines.append("          {")
        conf_lines.append("            type = builtin")
        conf_lines.append(f"            name = eq_{name}")
        conf_lines.append("            label = convolver")
        conf_lines.append("            config = {")
        conf_lines.append(f'              filename = "{ir_files[i]}"')
        conf_lines.append("            }")
        conf_lines.append("          }")

    conf_lines.append("        ]")

    # Links
    conf_lines.append("        links = [")
    if preamp_dB != 0:
        for i, ch in enumerate(channels):
            name = ch.name.lower()
            conf_lines.append("          {")
            conf_lines.append(f'            output = "preamp:Out"')
            conf_lines.append(f'            input = "eq_{name}:In"')
            conf_lines.append("          }")
    conf_lines.append("        ]")

    # Inputs/outputs
    ch_map = ["FL", "FR", "FC", "LFE", "RL", "RR", "SL", "SR"]
    conf_lines.append("        inputs = [")
    if preamp_dB != 0:
        conf_lines.append(f'          "preamp:In"')
    else:
        for i, ch in enumerate(channels):
            conf_lines.append(f'          "eq_{ch.name.lower()}:In"')
    conf_lines.append("        ]")
    conf_lines.append("        outputs = [")
    for i, ch in enumerate(channels):
        conf_lines.append(f'          "eq_{ch.name.lower()}:Out"')
    conf_lines.append("        ]")

    conf_lines.append("      }")  # filter.graph

    conf_lines.append("      capture.props = {")
    conf_lines.append('        media.class = Audio/Sink')
    conf_lines.append('        node.name = "sonarworks_eq"')
    conf_lines.append('        node.description = "Sonarworks Speaker Correction"')
    conf_lines.append('        audio.rate = ' + str(sample_rate))
    position = ", ".join(ch_map[i] for i in range(len(channels)))
    conf_lines.append(f'        audio.position = [{position}]')
    conf_lines.append("      }")
    conf_lines.append("      playback.props = {")
    conf_lines.append('        node.name = "sonarworks_eq_output"')
    conf_lines.append('        node.passive = true')
    conf_lines.append('        audio.rate = ' + str(sample_rate))
    conf_lines.append(f'        audio.position = [{position}]')
    conf_lines.append("      }")

    conf_lines.append("    }")  # args
    conf_lines.append("  }")
    conf_lines.append("]")

    conf_path = os.path.join(outdir, "sonarworks.conf")
    with open(conf_path, "w") as f:
        f.write("\n".join(conf_lines) + "\n")
    print(f"  PipeWire config: {conf_path}")


def export_easyeffects(channels, outdir, sample_rate=48000):
    """Generate EasyEffects convolver preset using the IR WAVs."""
    os.makedirs(outdir, exist_ok=True)

    # Reuse or generate IR WAVs -- EasyEffects needs a stereo WAV
    print("  Generating stereo IR for EasyEffects...", end=" ", flush=True)
    irs = []
    for ch in channels:
        ir = freq_response_to_ir_fast(
            ch.frequencies, ch.correction_dB, sample_rate, 4096
        )
        irs.append(ir)

    # Write stereo WAV
    stereo_path = os.path.join(outdir, "sonarworks_correction_stereo.wav")
    peak = max(max(abs(s) for s in ir) for ir in irs) or 1.0
    scale = 0.95 / peak
    interleaved = []
    for j in range(len(irs[0])):
        for ir in irs:
            interleaved.append(max(-32767, min(32767, int(ir[j] * scale * 32767))))
    with wave.open(stereo_path, "w") as w:
        w.setnchannels(len(channels))
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(array.array("h", interleaved).tobytes())
    print(f"-> {stereo_path}")

    # Write instructions
    instructions_path = os.path.join(outdir, "EASYEFFECTS_INSTRUCTIONS.txt")
    all_max = max(max(ch.correction_dB) for ch in channels)
    preamp = -(all_max + 1) if all_max > 0 else 0
    with open(instructions_path, "w") as f:
        f.write("EasyEffects Setup Instructions\n")
        f.write("=" * 40 + "\n\n")
        f.write("1. Open EasyEffects\n")
        f.write("2. Go to the Output tab (speakers icon)\n")
        f.write("3. Add a 'Convolver' effect\n")
        f.write(f"4. Load the IR file: {os.path.abspath(stereo_path)}\n")
        f.write(f"5. Set input gain to {preamp:.1f} dB to prevent clipping\n")
        f.write("6. Enable the effect and save as preset\n")
    print(f"  EasyEffects instructions: {instructions_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: swproj_parser.py <file.swproj> [--outdir dir]")
        print("\nExports Sonarworks speaker calibration profiles for Linux.")
        print("Generates: CSV, EQ APO, CamillaDSP, PipeWire, EasyEffects")
        sys.exit(1)

    filepath = sys.argv[1]
    channels = parse_swproj(filepath)

    print(f"\nParsed {len(channels)} channels:")
    for ch in channels:
        print(f"  {ch.name} (index={ch.index}, group={ch.group})")
        print(f"    Delay: {ch.delay_ms:.4f} ms")
        print(f"    Freq range: {ch.frequencies[0]:.0f} - {ch.frequencies[-1]:.0f} Hz")
        print(f"    Correction: {min(ch.correction_dB):.1f} to {max(ch.correction_dB):.1f} dB")

    base = os.path.splitext(os.path.basename(filepath))[0]
    if "--outdir" in sys.argv:
        outdir = sys.argv[sys.argv.index("--outdir") + 1]
    else:
        outdir = os.path.join(os.path.dirname(filepath) or ".", f"{base}_export")
    os.makedirs(outdir, exist_ok=True)

    print(f"\nExporting to {outdir}/\n")
    export_csv(channels, os.path.join(outdir, f"{base}.csv"))
    export_eqapo(channels, os.path.join(outdir, f"{base}_eqapo.txt"))
    export_camilladsp(channels, os.path.join(outdir, "camilladsp"))
    export_pipewire(channels, os.path.join(outdir, "pipewire"))
    export_easyeffects(channels, os.path.join(outdir, "easyeffects"))
    print("\nDone! See each subdirectory for format-specific files.")


if __name__ == "__main__":
    main()
