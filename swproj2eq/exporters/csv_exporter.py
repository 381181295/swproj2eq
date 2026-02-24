"""CSV exporter."""

import csv


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
