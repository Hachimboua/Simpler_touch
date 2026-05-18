# Development Guide

Everything you need to hack on BlobTracker: dev setup, conventions, plugin
authoring, preset format, and pointers for common extensions.

---

## 1. Dev Setup

```bash
# clone, then:
cd blobtracker
python -m venv .venv
.venv\Scripts\activate            # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Recommended tooling:

- **Python 3.10+** (the codebase declares 3.8 minimum, but PyQt6 + modern
  type hints work best on 3.10+).
- **ruff** for linting (no config bundled; project follows PEP 8).
- **mypy** for optional typing — most modules use `from __future__ import
  annotations` and PEP 604 unions.

### Optional: ffmpeg

Required only for the `prores` output format and as the preferred encoder for
`OfflineRenderer`. If `ffmpeg` is not on `PATH`, the offline renderer falls
back to OpenCV's `VideoWriter`.

---

## 2. Repo Conventions

- **No global state outside `ParamStore`.** Treat every tunable as a parameter
  and register it in `ParamStore._register_defaults()`.
- **Effects are stateless functions.** If you need history (e.g. trails),
  store it on the `Blob` dataclass via the `Tracker`, not on the effect.
- **Threading discipline.** All inter-thread communication goes through Qt
  signals. Never call UI methods from worker threads.
- **Imports.** Use absolute imports within the `blobtracker/` package.
- **Type-cast at the boundary.** `ParamStore.set` already casts, but when
  reading values, convert with `int()`/`float()`/`bool()` at the read site to
  keep linters quiet.

### File layout cheat-sheet

| Want to change… | Edit… |
| --- | --- |
| Detection algorithm | `processing_core.BlobDetector` |
| Tracking algorithm | `processing_core.Tracker` |
| An overlay effect | `effect_engine.<EffectName>` |
| A new built-in creative filter | `effect_engine.*Filter` + register in `CreativeFX` |
| UI layout / a new section | `control_panel.ControlPanel._build_<section>_section` |
| A new parameter | `param_store.ParamStore._register_defaults` |
| Theme | `style.qss` |
| Offline render order | `renderer.OfflineRenderer._render_frame` |

---

## 3. Writing a Plugin (Creative Filter)

Plugins are auto-discovered from `plugins/*.py`. They must subclass
`CreativeFilter` from `effect_engine`.

### Minimal example

```python
# plugins/my_filter.py
from __future__ import annotations
import cv2
import numpy as np
from effect_engine import CreativeFilter


class VignettePulseFilter(CreativeFilter):
    name = "VignettePulseFilter"

    def __init__(self, strength: float = 0.5, falloff: float = 1.5) -> None:
        self.strength = float(strength)
        self.falloff = float(falloff)

    def apply(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        y, x = np.indices((h, w), dtype=np.float32)
        cx, cy = w / 2.0, h / 2.0
        d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        mask = 1.0 - self.strength * (d / d.max()) ** self.falloff
        mask = np.clip(mask, 0.0, 1.0)[..., None]
        return (frame.astype(np.float32) * mask).astype(np.uint8)
```

### Required contract

| Member | Type | Notes |
| --- | --- | --- |
| `name` | `str` class attribute | Used as the filter's identity in `creative.filter_order` and `creative.filter_params` |
| `__init__(**kwargs)` | constructor | Any kwargs must have sensible defaults; missing keys fall back to defaults |
| `apply(frame: np.ndarray) -> np.ndarray` | method | Input is BGR `uint8`. Return BGR `uint8` of the same shape |

### Wiring constructor kwargs from the UI

If your filter takes constructor parameters, add an entry to
`creative.filter_params` so users can configure them via JSON presets:

```json
"creative.filter_params": {
  "VignettePulseFilter": { "strength": 0.55, "falloff": 1.8 }
}
```

The `CreativeFX` chain reads this dict when instantiating the filter. Missing
keys fall back to the constructor defaults.

### Hot reload

After dropping a new file into `plugins/`, click **Hot Reload Plugins** in the
Creative section (or `Effects → Hot Reload Plugins` in the menu bar). No app
restart needed. The loader:

1. Re-scans `plugins/*.py`.
2. Re-imports each module with `importlib.util`.
3. Re-registers all `CreativeFilter` subclasses.

> The old class objects are *not* unloaded from `sys.modules` — they are
> shadowed by the new ones. If you observe stale behaviour after a reload,
> restart the app.

### Where filters run in the pipeline

Creative filters run **after** all overlay effects (bbox, label, trail, etc.)
and **after** the `Compositor` blend mode is applied. They see the final
composited frame just before it reaches the preview / exporter.

The order of execution within the filter chain is exactly the order shown in
the **Filter Chain (drag to reorder)** list.

---

## 4. Preset Format

Presets live in `presets/<name>.json`. The schema is intentionally minimal:

```json
{
  "name": "surveillance",
  "params": {
    "input.source_type": "file",
    "blob.threshold": 110,
    "effects.bbox_enabled": true,
    "effects.bbox_color": [0, 229, 255],
    "creative.enabled": true,
    "creative.filter_order": ["EdgeFilter", "GrainFilter"],
    "creative.filter_params": {
      "EdgeFilter": { "low": 60, "high": 160, "alpha": 0.6, "blur": 0 }
    }
  },
  "meta": { "version": 1 }
}
```

- Keys missing from `params` fall back to whatever is currently registered in
  `ParamStore` — partial presets are valid.
- Unknown keys are silently ignored — old presets stay forward-compatible.
- Colors are `[R, G, B]` with 0–255 ints.

Use `ParamStore.export_schema()` to dump the full registered surface
(including types, ranges, and enum options) for tooling.

---

## 5. Adding a New Parameter

1. Add a `ParamDef(...)` row to `ParamStore._register_defaults()` with the
   right `type`, `min`, `max`, `step`, and (for enums) `options`.
2. Create a Qt control in the appropriate `control_panel._build_*_section`
   method and bind it with one of the helpers:
   - `_bind_spin(spinbox, "your.key")`
   - `_bind_slider(slider, "your.key", scale=…)`
   - `_bind_checkbox(checkbox, "your.key")`
   - `_bind_combo(combo, "your.key")`
   - `_make_color_button("your.key")` for colours.
3. Add an entry to `ControlPanel.sync_all_from_store` so presets re-sync the
   widget on load.
4. Read the value in your effect via `param_store.get("your.key")`.
5. Update `docs/PARAMETERS.md`.

---

## 6. Adding a New Overlay Effect

1. Create a class in `effect_engine.py`:

   ```python
   class MyOverlayFX:
       def apply(self, frame: np.ndarray, blobs: list[Blob]) -> np.ndarray:
           # mutate or return a copy
           return frame
   ```

2. Instantiate it in `MainWindow.__init__` and wire it into
   `MainWindow.render_latest_packet` between the existing overlay calls.
3. (If it's expensive) add an `enabled` parameter so users can toggle it.
4. Also wire it into `OfflineRenderer` if you want it in offline renders.

---

## 7. Style / Theme

All visual styling is in `style.qss`. The file is loaded by
`MainWindow._load_stylesheet` at startup.

- The accent colour is `#00c8f0` — search and replace to re-skin.
- Per-section title colours live at the bottom under `#section_<name>` rules.
- Avoid inline `setStyleSheet()` in Python; prefer adding a rule to
  `style.qss` and tagging the widget with `setObjectName(...)`.

---

## 8. Testing & Debugging

There is no formal test suite (yet). For ad-hoc debugging:

- **Disable detection** to isolate a UI bug: set `blob.max_count` to `0` or
  toggle off every effect.
- **Force a slower frame rate** with `input.target_fps = 5` to see overlays
  draw step-by-step.
- **Check threading** by adding `QThread.currentThread().objectName()` traces
  if you suspect cross-thread UI writes — those will throw at runtime under
  PyQt6.

For reproducible bugs, save the preset and the source path, then attach both
to your report.
