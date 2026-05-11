from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

import numpy as np


@dataclass
class Blob:
    id: int
    centroid: Tuple[int, int]
    bbox: Tuple[int, int, int, int]
    area: float
    trail: List[Tuple[int, int]] = field(default_factory=list)


@dataclass
class FramePacket:
    raw_frame: np.ndarray
    blobs: List[Blob]
    timestamp: float
    frame_index: int
