# swproj2eq

Convert [Sonarworks SoundID Reference](https://www.sonarworks.com/soundid-reference) speaker calibration profiles (`.swproj`) to EQ configs for Linux audio tools.

Parses the binary `.swproj` format (reverse-engineered, not actually encrypted despite what the header claims) and exports correction curves as FIR impulse responses and EQ configs.

## Usage

```
python3 swproj2eq.py path/to/profile.swproj
```

Outputs all formats to a `_export/` directory. Optionally:

```
python3 swproj2eq.py profile.swproj --outdir ~/my-eq
```

No dependencies required. Uses numpy/scipy if available for faster IR generation, pure Python fallback otherwise.

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
cp pipewire/sonarworks.conf ~/.config/pipewire/filter-chain.conf.d/
cp pipewire/*.wav ~/.config/pipewire/filter-chain.conf.d/
# edit sonarworks.conf to fix WAV paths
systemctl --user restart pipewire
pactl set-default-sink sonarworks_eq
```

### CamillaDSP

1. Install from [releases](https://github.com/HEnquist/camilladsp/releases)
2. Edit `camilladsp/camilladsp.yml` -- set capture/playback device names
3. `camilladsp camilladsp.yml`
4. `pactl set-default-sink CamillaDSP`

### EasyEffects

1. Add a Convolver effect to the output chain
2. Load `easyeffects/sonarworks_correction_stereo.wav`
3. Set input gain per the instructions file

## License

MIT
