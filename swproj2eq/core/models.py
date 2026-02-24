"""Shared data models."""

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


@dataclass
class Profile:
    source_path: str
    channels: list[ChannelData]
