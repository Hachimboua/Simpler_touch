# BlobTracker — Documentation

Welcome. This folder contains the full documentation for **BlobTracker**, a
PyQt6 + OpenCV desktop application for real-time blob tracking with cinematic
overlays and stackable creative filters.

## Documentation Map

| Document | Audience | Contents |
| --- | --- | --- |
| [USER_GUIDE.md](USER_GUIDE.md) | End users | Walkthrough of every UI section, playback, recording, presets, export |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Developers | Module layout, threading model, frame pipeline, signal flow |
| [PARAMETERS.md](PARAMETERS.md) | Power users / devs | Full reference of every parameter, default, range, and where it appears |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Contributors | Dev setup, code conventions, writing plugins, preset format, extending the app |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Everyone | Common errors, performance tuning, ffmpeg/codec notes |

## Quick Start

```bash
# 1. Install Python 3.8+ and create a virtualenv
python -m venv .venv
.venv\Scripts\activate           # Windows
# source .venv/bin/activate      # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
python main.py
```

The window opens with the control panel docked on the left and a video preview
in the centre. Pick a source (webcam or file), press **Play**, and tweak the
sections below to taste.

## At a Glance

- **Real-time blob detection** — threshold/contour or `SimpleBlobDetector`.
- **Stable ID tracking** — Hungarian assignment + centroid smoothing + trail
  history.
- **Live overlay FX** — bounding boxes, IDs, coords, trails, connection lines,
  optical flow vectors, blob-interior effects, zoom inset.
- **Creative filter chain** — grain, glitch, thermal, edge, chromatic
  aberration; drag to reorder; hot-reload custom plugins.
- **Presets** — save and load full parameter sets as JSON.
- **Export** — record live to `mp4` / `png_seq` / `prores`, or do a full-quality
  offline render of a source file.

See **USER_GUIDE.md** for the full tour.
