# BlobTracker

BlobTracker is a native desktop application (Python + PyQt6 + OpenCV) for real-time blob tracking with cinematic overlays: stable IDs, bounding boxes, centroid dots, trail lines, zoom insets, optical flow, and stackable creative filters.

> **Looking for the full docs?** See [`docs/README.md`](docs/README.md) for the user guide, architecture, parameter reference, development guide, and troubleshooting.

## Setup

1. Create and activate a Python 3.8 environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run:

```bash
python main.py
```

## Project Structure

- `main.py` - app entrypoint and full pipeline wiring
- `models.py` - `Blob` and `FramePacket` dataclasses
- `input_layer.py` - file/webcam sources, frame buffer, capture worker
- `processing_core.py` - preprocessing, contour detection, tracking, optical flow
- `effect_engine.py` - overlay FX, creative filters, compositor
- `param_store.py` - singleton typed parameter store + JSON presets
- `control_panel.py` - docked control panel with live bindings
- `output_layer.py` - preview renderer, exporter, project manager
- `plugin_loader.py` - plugin discovery and hot reload
- `preset_browser.py` - visual preset browser dialog
- `hotkeys.py` - keyboard shortcut bindings
- `style.qss` - dark UI theme

## Hotkeys

- `Space` - Play / Pause source capture
- `R` - Start / Stop recording
- `P` - Open preset browser
- `F` - Toggle fullscreen preview

## Adding a Plugin Filter

1. Create a `.py` file inside `plugins/`.
2. Implement a class that inherits from `CreativeFilter` from `effect_engine.py`.
3. Add a `name` class attribute and an `apply(frame)` method.
4. Click **Hot Reload Plugins** in the Creative section.

Use `plugins/example_filter.py` as a template.

## Presets

- Presets are JSON files in `presets/`.
- Use the **Presets** section in the Control Panel:
  - Enter a name and click **Save**
  - Select and click **Load**
  - Select and click **Delete**
- `presets/default.json` is loaded on startup if present.

## Export

- `Output` section supports:
  - `mp4` via OpenCV `VideoWriter`
  - `png_seq` as numbered frame sequence
  - `prores` via optional `ffmpeg` subprocess (writes `.mov`)
- Recording runs in a separate writer thread to avoid stalling preview rendering.
