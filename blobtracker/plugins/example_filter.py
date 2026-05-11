"""Example plugin filter for BlobTracker.

Plugin API
==========
1. Place a Python file in the plugins directory.
2. Define one or more classes that inherit from effect_engine.CreativeFilter.
3. Implement:
      - class attribute: name (str)
      - method: apply(frame: np.ndarray) -> np.ndarray
4. The app scans plugins/*.py and automatically registers subclasses of CreativeFilter.
5. Use the Hot Reload Plugins button in the Creative section to reload without restart.

Constructor parameters
======================
If your filter constructor takes keyword arguments, they can be provided through
ParamStore under creative.filter_params with this shape:

{
  "YourFilterName": {
    "param1": 1.0,
    "param2": 5
  }
}

Any missing parameter falls back to your class defaults.
"""

from __future__ import annotations

import cv2
import numpy as np

from effect_engine import CreativeFilter


class ScanlinePulseFilter(CreativeFilter):
    name = "ScanlinePulseFilter"

    def __init__(self, spacing: int = 4, intensity: float = 0.22) -> None:
        self.spacing = max(1, int(spacing))
        self.intensity = max(0.0, min(1.0, float(intensity)))

    def apply(self, frame: np.ndarray) -> np.ndarray:
        out = frame.copy().astype(np.float32)
        out[:: self.spacing, :, :] *= 1.0 - self.intensity
        return cv2.convertScaleAbs(out)
