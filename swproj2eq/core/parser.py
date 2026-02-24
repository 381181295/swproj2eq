"""Sonarworks .swproj parser."""

import re
import struct

from swproj2eq.core.models import ChannelData, Profile


POINTS_PER_CURVE = 355
DATA_HEADER = b"\x63\x01\x00\x00\x07\x00\x00\x00"


def _parse_metadata(data, start_pos, boundaries):
    meta = {}
    pos = start_pos
    end = min((b for b in boundaries if b > start_pos), default=len(data))
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


def _parse_blocks(data, data_headers, boundaries):
    blocks = []
    for header in data_headers:
        float_start = header + 8
        next_boundary = min(
            (b for b in boundaries + [len(data)] if b > float_start),
            default=len(data),
        )
        block_bytes = next_boundary - float_start
        fpp = round((block_bytes // 4) / POINTS_PER_CURVE)
        freqs, values = [], []

        for i in range(POINTS_PER_CURVE):
            offset = float_start + i * fpp * 4
            freq = struct.unpack_from("<f", data, offset)[0]
            val = struct.unpack_from("<f", data, offset + 4)[0]
            freqs.append(freq)
            values.append(val)

        blocks.append({"fpp": fpp, "freqs": freqs, "values": values})
    return blocks


def parse_swproj(path, require_stereo=True):
    with open(path, "rb") as f:
        data = f.read()

    xml_end = data.find(b"</ProjectHeader>")
    if xml_end == -1:
        raise ValueError("not a valid .swproj file (no ProjectHeader)")

    data_headers = []
    pos = 0
    while True:
        idx = data.find(DATA_HEADER, pos)
        if idx == -1:
            break
        data_headers.append(idx)
        pos = idx + 1

    if not data_headers:
        raise ValueError("could not find PEQ data blocks")

    delay_positions = [m.start() for m in re.finditer(b"ChannelDelayMs", data)]
    boundaries = sorted(data_headers + delay_positions)
    blocks = _parse_blocks(data, data_headers, boundaries)

    channels = {}
    for i, meta_start in enumerate(delay_positions):
        meta = _parse_metadata(data, meta_start, boundaries)
        ch_name = meta.get("ChannelName", f"Channel_{i}")
        ch_idx = int(meta.get("ChannelIndex", i))
        key = (ch_name, ch_idx)
        if key not in channels:
            channels[key] = ChannelData(
                name=ch_name,
                index=ch_idx,
                group=meta.get("ChannelGroup", ""),
                delay_ms=0.0,
                frequencies=[],
                correction_dB=[],
                measurement_dB=[],
            )
        delay_str = meta.get("ChannelDelayMs", "0")
        delay_val = float(delay_str) if delay_str not in ("-0", "0") else 0.0
        if delay_val != 0:
            channels[key].delay_ms = abs(delay_val)

    channel_list = sorted(channels.values(), key=lambda c: c.index)
    for i, ch in enumerate(channel_list):
        corr_idx = i * 2
        meas_idx = i * 2 + 1
        if corr_idx < len(blocks):
            ch.frequencies = blocks[corr_idx]["freqs"]
            ch.correction_dB = blocks[corr_idx]["values"]
        if meas_idx < len(blocks):
            ch.measurement_dB = blocks[meas_idx]["values"]

    if require_stereo and len(channel_list) != 2:
        raise ValueError(f"only stereo profiles are supported; got {len(channel_list)} channels")

    return Profile(source_path=str(path), channels=channel_list)
