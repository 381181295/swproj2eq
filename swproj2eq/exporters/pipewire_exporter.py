"""PipeWire filter-chain exporter."""

import os

from swproj2eq.core.dsp import compute_preamp_db, freq_response_to_ir_fast, write_wav


def export_pipewire(channels, outdir, sample_rate=48000):
    os.makedirs(outdir, exist_ok=True)

    ir_paths = []
    for ch in channels:
        fname = f"{ch.name.lower()}_correction.wav"
        path = os.path.join(outdir, fname)
        if not os.path.exists(path):
            ir = freq_response_to_ir_fast(ch.frequencies, ch.correction_dB, sample_rate, 4096)
            write_wav(path, ir, sample_rate)
        ir_paths.append(os.path.abspath(path))

    preamp_db = compute_preamp_db(channels)

    lines = [
        "# PipeWire filter-chain config - Sonarworks speaker correction",
        "# Copy to ~/.config/pipewire/filter-chain.conf.d/swproj2eq.conf",
        "# Then: systemctl --user restart pipewire",
        "",
        "context.modules = [",
        "  {",
        "    name = libpipewire-module-filter-chain",
        "    args = {",
        '      node.description = "swproj2eq correction"',
        '      media.name = "swproj2eq correction"',
        "      filter.graph = {",
        "        nodes = [",
    ]

    if preamp_db < 0:
        lines.extend(
            [
                "          {",
                "            type = builtin",
                "            name = preamp",
                "            label = bq_highshelf",
                f'            control = {{ "Freq" = 0 "Q" = 1.0 "Gain" = {preamp_db:.1f} }}',
                "          }",
            ]
        )

    for i, ch in enumerate(channels):
        name = ch.name.lower()
        lines.extend(
            [
                "          {",
                "            type = builtin",
                f"            name = eq_{name}",
                "            label = convolver",
                "            config = {",
                f'              filename = "{ir_paths[i]}"',
                "            }",
                "          }",
            ]
        )

    lines.append("        ]")
    lines.append("        links = [")
    if preamp_db < 0:
        for ch in channels:
            name = ch.name.lower()
            lines.extend(
                [
                    "          {",
                    '            output = "preamp:Out"',
                    f'            input = "eq_{name}:In"',
                    "          }",
                ]
            )
    lines.append("        ]")

    lines.append("        inputs = [")
    if preamp_db < 0:
        lines.append('          "preamp:In"')
    else:
        for ch in channels:
            lines.append(f'          "eq_{ch.name.lower()}:In"')
    lines.append("        ]")

    lines.append("        outputs = [")
    for ch in channels:
        lines.append(f'          "eq_{ch.name.lower()}:Out"')
    lines.append("        ]")

    lines.extend(
        [
            "      }",
            "      capture.props = {",
            "        media.class = Audio/Sink",
            '        node.name = "swproj2eq_eq"',
            '        node.description = "swproj2eq EQ"',
            f"        audio.rate = {sample_rate}",
            "        audio.position = [FL, FR]",
            "      }",
            "      playback.props = {",
            '        node.name = "swproj2eq_eq_output"',
            "        node.passive = true",
            f"        audio.rate = {sample_rate}",
            "        audio.position = [FL, FR]",
            "      }",
            "    }",
            "  }",
            "]",
        ]
    )

    conf_path = os.path.join(outdir, "swproj2eq.conf")
    with open(conf_path, "w") as f:
        f.write("\n".join(lines) + "\n")

    return {"config_path": conf_path, "preamp_db": preamp_db}
