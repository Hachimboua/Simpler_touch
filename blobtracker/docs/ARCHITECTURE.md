# Architecture

BlobTracker is a single-process PyQt6 desktop app with three primary worker
threads coordinated by Qt signals. This document explains *how* the pieces
talk.

> For a one-line summary of every module, see the top of `README.md`. For the
> full parameter surface, see `PARAMETERS.md`.

---

## 1. Module Map

```
blobtracker/
├── main.py             ← MainWindow, render timer, menus, status bar, glue
├── models.py           ← Blob, FramePacket dataclasses
├── input_layer.py      ← FrameSource, VideoFileSource, WebcamSource,
│                          FrameBuffer (thread-safe queue), CaptureWorker
├── processing_core.py  ← Preprocessor, BlobDetector, Tracker, OpticalFlow,
│                          ProcessorWorker
├── effect_engine.py    ← BaseFrameFX, BoundingBoxFX, LabelFX, TrailFX,
│                          ConnectionLineFX, IntraBlobFX, ZoomInsetFX,
│                          CreativeFX (chain), Compositor, built-in filters
├── output_layer.py     ← PreviewRenderer (QWidget), VideoExporter (writer
│                          thread), ProjectManager
├── renderer.py         ← OfflineRenderer (dedicated full-quality pipeline)
├── param_store.py      ← ParamStore singleton, ParamDef, JSON preset I/O
├── control_panel.py    ← Docked ControlPanel + SectionBox widgets
├── plugin_loader.py    ← PluginLoader — discovery and hot-reload
├── preset_browser.py   ← PresetBrowserDialog
├── hotkeys.py          ← HotkeyManager
├── style.qss           ← Dark theme stylesheet
├── plugins/            ← User CreativeFilter plugins (auto-discovered)
└── presets/            ← Saved JSON presets
```

---

## 2. Threads

| Thread | Owner | Role |
| --- | --- | --- |
| **Qt main thread** | `MainWindow` | UI, rendering of the preview, status updates |
| **CaptureWorker** (`QThread`) | `CaptureWorker` | Pulls frames from the active `FrameSource` and pushes them into the `FrameBuffer` |
| **ProcessorWorker** (`QThread`) | `ProcessorWorker` | Pulls from the `FrameBuffer`, runs detection/tracking, emits `FramePacket` |
| **VideoExporter writer** | `VideoExporter` | Async disk writes for live recording (mp4 / png_seq / prores) |
| **OfflineRenderer worker** | `OfflineRenderer` | Independent end-to-end render pipeline for full-quality file export |

The three worker threads each have a private state machine and only
communicate with the UI thread via Qt signals — there are **no direct calls
across threads**.

---

## 3. Frame Pipeline (live preview)

```
 ┌──────────────────┐    push    ┌──────────────┐   pop     ┌────────────────────┐
 │ CaptureWorker    │──────────▶ │ FrameBuffer  │ ────────▶ │ ProcessorWorker    │
 │  ├ VideoFile     │            │ (thread-safe │           │  ├ Preprocessor    │
 │  └ Webcam        │            │  queue,      │           │  ├ BlobDetector    │
 └──────────────────┘            │  rate-shaped)│           │  ├ Tracker         │
                                 └──────────────┘           │  └ OpticalFlow     │
                                                            └────────┬───────────┘
                                                                     │ emit
                                                                     ▼
                                                      ┌──────────────────────────┐
                                                      │ MainWindow.on_frame_     │
                                                      │ packet  (stores latest)  │
                                                      └────────┬─────────────────┘
                                                               │ render timer tick
                                                               ▼
                                                      ┌──────────────────────────┐
                                                      │ MainWindow.render_       │
                                                      │ latest_packet            │
                                                      │  ├ BaseFrameFX           │
                                                      │  ├ IntraBlobFX           │
                                                      │  ├ ConnectionLineFX      │
                                                      │  ├ BBox / Label / Trail  │
                                                      │  ├ ZoomInsetFX           │
                                                      │  ├ CreativeFX (chain)    │
                                                      │  └ Compositor (blend)    │
                                                      └────────┬─────────────────┘
                                                               │
                                                  ┌────────────┴───────────┐
                                                  ▼                        ▼
                                          PreviewRenderer          VideoExporter
                                          (QLabel + QPixmap)       (if recording)
```

Key design points:

- **Backpressure-free preview.** The `FrameBuffer` drops old frames when the
  consumer can't keep up — we keep latency low at the cost of dropping frames.
- **Decoupled detection rate.** `detect_every_n` and `process_scale` let
  detection run on a coarser cadence than display; tracker carries forward
  the last known blobs in between.
- **Render timer is the heartbeat.** A `QTimer` (precise type) in
  `MainWindow` fires at the target FPS and pulls the most recent
  `FramePacket`. This is what drives effect composition and the on-screen
  pixmap update — *not* the capture rate.
- **Effects are stateless except `TrailFX` and `IntraBlobFX`.** Trail history
  lives on the `Tracker`'s blob entries.

---

## 4. Offline Render Pipeline

`OfflineRenderer` (`renderer.py`) is an entirely separate pipeline so live
preview and export can coexist without interfering.

1. Open the source file with a fresh `VideoFileSource`.
2. For each frame: `Preprocessor → BlobDetector → Tracker → Effects → Compositor`.
3. Write the result as a numbered PNG to a temp directory.
4. After all frames are processed, assemble the PNGs with `ffmpeg` (preferred)
   or fall back to OpenCV `VideoWriter`.
5. Emit `progress`, `frame_preview`, `finished` / `error` signals back to
   `MainWindow`, which updates the **Render to File** section.

Because this runs on its own thread with its own detector/tracker instances,
output is **deterministic** for a given source + parameter set, regardless of
host load.

---

## 5. Parameter System (`ParamStore`)

`ParamStore` is a singleton QObject that holds every tunable parameter as a
typed `ParamDef`:

```python
@dataclass
class ParamDef:
    key: str
    value: Any
    min: Any
    max: Any
    step: Any
    type: str                     # "int" | "float" | "bool" | "enum" |
                                  # "color" | "str" | "list" | "dict"
    options: Optional[List[str]]  # for "enum"
```

- `ParamStore.set(key, value)` casts and clamps the value, then emits
  `param_changed(key, value)`.
- `ParamStore.apply_dict({...})` does a bulk update and emits a single
  `params_bulk_changed()` so the UI can resync efficiently.
- `save_preset(name)` / `load_preset(name)` round-trip the full state through
  `presets/<name>.json`.

The `ControlPanel` widget binds each Qt control (spinbox, slider, checkbox,
combo, color button) directly to a `ParamStore` key via small helper methods
(`_bind_spin`, `_bind_checkbox`, `_bind_slider`, `_bind_combo`). All effect
modules subscribe to either the `ParamStore` directly or read the values
during their `apply()` call.

See **PARAMETERS.md** for the complete inventory.

---

## 6. Signals & Wiring

Important Qt signals (not exhaustive):

| Signal | Emitter | Connected to |
| --- | --- | --- |
| `param_changed(key, value)` | `ParamStore` | `MainWindow.on_param_changed` |
| `params_bulk_changed()` | `ParamStore` | `ControlPanel.sync_all_from_store` |
| `frame_packet_ready(packet)` | `ProcessorWorker` | `MainWindow.on_frame_packet` |
| `start_source_requested / stop_source_requested / play_requested / pause_requested` | `ControlPanel` | `MainWindow` transport handlers |
| `render_video_requested` | `ControlPanel` | `MainWindow.start_live_render` |
| `offline_render_requested(path)` | `ControlPanel` | `MainWindow.start_offline_render` |
| `offline_render.progress / frame_preview / finished / error` | `OfflineRenderer` | `MainWindow._on_offline_render_*` |
| `end_of_file` | `CaptureWorker` | `MainWindow._on_end_of_file` |

All signals are routed through `MainWindow._wire_signals` for easy auditing.

---

## 7. Plugin System

`PluginLoader` scans `plugins/*.py`, dynamically imports each file with
`importlib.util`, and registers every subclass of `effect_engine.CreativeFilter`
it finds.

- Plugins are stateless from the loader's perspective — re-running
  `load_plugins()` swaps in fresh classes.
- The `CreativeFX` chain instantiates filters lazily, passing constructor
  kwargs from `creative.filter_params[<ClassName>]`.

See **DEVELOPMENT.md → Writing a Plugin** for an end-to-end example.

---

## 8. UI Theming

All styling is centralised in `style.qss`. The theme uses:

- **Base palette:** `#0c0e10` background, `#101316` panels.
- **Accent:** `#00c8f0` (soft cyan).
- **Per-section title colours:** assigned via `#section_<name> QGroupBox::title`
  rules at the bottom of the QSS.

`MainWindow._load_stylesheet` loads the file at startup; you can edit and
relaunch to iterate.
