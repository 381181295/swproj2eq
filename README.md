# swproj2eq

Convert [Sonarworks SoundID Reference](https://www.sonarworks.com/soundid-reference) speaker calibration profiles (`.swproj`) to EQ configs for Linux audio tools.

Parses the binary `.swproj` format (reverse-engineered, not actually encrypted despite what the header claims) and exports correction curves as FIR impulse responses and EQ configs.

`swproj2eq` is a compatibility tool. It is not affiliated with or endorsed by Sonarworks.

## Usage

```
python3 swproj2eq.py export path/to/profile.swproj
```

Outputs all formats to a `_export/` directory. Optionally:

```
python3 swproj2eq.py export profile.swproj --outdir ~/my-eq
```

Backward-compatible shortcut still works:

```bash
python3 swproj2eq.py profile.swproj --outdir ~/my-eq
```

## Quickstart runtime (PipeWire, stereo)

Set up CamillaDSP passthrough and optional default sink switch:

```bash
python3 swproj2eq.py quickstart --profile path/to/profile.swproj
python3 swproj2eq.py quickstart --profile path/to/profile.swproj --set-default
```

Other runtime commands:

```bash
python3 swproj2eq.py status
python3 swproj2eq.py doctor
python3 swproj2eq.py enable --profile-id <id>
python3 swproj2eq.py disable
python3 swproj2eq.py rollback
python3 swproj2eq.py uninstall
python3 swproj2eq.py tui
```

No dependencies required. Uses numpy/scipy if available for faster IR generation, pure Python fallback otherwise.

Quickstart requirements:

- PipeWire stack (`pactl` available)
- systemd user session
- `camilladsp` binary installed

If dependencies are missing, `doctor` prints install hints for Ubuntu/Fedora/Arch.

## Exports

| Format | Tool | Notes |
|--------|------|-------|
| CamillaDSP | [CamillaDSP](https://github.com/HEnquist/camilladsp) | YAML config + FIR impulse response WAVs, per-channel delay |
| PipeWire | PipeWire filter-chain | Drop-in `.conf` file + convolver IRs |
| EasyEffects | [EasyEffects](https://github.com/wwmm/easyeffects) | Stereo convolver IR WAV |
| EQ APO | GraphicEQ format | 355-point correction curve |
| CSV | Any | Raw frequency/dB data |

## .swproj file format

The `.swproj` format (reverse-engineered):

```
+---------------------------+
| XML ProjectHeader         |  version, parts list
+---------------------------+
| PEQb binary header        |  magic bytes, counts
+---------------------------+
| Correction curve (2 fpp)  |  355 x (freq_hz, correction_dB) per channel
+---------------------------+
| Measurement data (3 fpp)  |  355 x (freq_hz, level_dB, extra) per channel
+---------------------------+
| Channel metadata          |  name, group, index, delay_ms
+---------------------------+
| Encrypted project state   |  (ignored, not needed for EQ)
+---------------------------+
```

- 355 log-spaced frequency points, 20 Hz -- 22 kHz
- IEEE 754 float32, little-endian
- Per-channel delay compensation in milliseconds
- Cross-platform (macOS/Windows), not encrypted despite XML header claim

## Linux setup

### PipeWire (no extra software)

```bash
mkdir -p ~/.config/pipewire/filter-chain.conf.d/
cp pipewire/swproj2eq.conf ~/.config/pipewire/filter-chain.conf.d/
cp pipewire/*.wav ~/.config/pipewire/filter-chain.conf.d/
# edit swproj2eq.conf to fix WAV paths
systemctl --user restart pipewire
pactl set-default-sink swproj2eq_eq
```

### CamillaDSP

1. Install from [releases](https://github.com/HEnquist/camilladsp/releases)
2. Edit `camilladsp/camilladsp.yml` -- set capture/playback device names (if using export-only mode)
3. `camilladsp camilladsp.yml`
4. `pactl set-default-sink CamillaDSP`

### EasyEffects

1. Add a Convolver effect to the output chain
2. Load `easyeffects/sonarworks_correction_stereo.wav`
3. Set input gain per the instructions file

## License

MIT

## What files swproj2eq creates

Only swproj2eq-managed paths are touched:

- `~/.local/share/swproj2eq/profiles/<profile-id>/...`
- `~/.local/share/swproj2eq/bin/swproj2eq-run.sh`
- `~/.local/state/swproj2eq/state.json`
- `~/.config/systemd/user/swproj2eq-camilla.service`

No `/etc` writes in MVP.

## Conflict policy

- If EasyEffects is active, quickstart/enable blocks unless `--force`.
- If another CamillaDSP process is active, quickstart/enable blocks unless `--force`.
