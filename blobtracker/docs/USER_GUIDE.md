# User Guide

This guide walks through every section of the BlobTracker UI, top to bottom.

---

## 1. Window Layout

```
┌─────────────────────────────────────────────────────────────┐
│ File   View   Effects   Help                                │  ← Menu bar
├──────────────┬──────────────────────────────────────────────┤
│              │                                              │
│ CONTROL      │              VIDEO PREVIEW                   │
│ PANEL        │                                              │
│ (dockable)   │                                              │
│              │                                              │
│              ├──────────────────────────────────────────────┤
│              │  ⏮  ▶  ⏭  ⟳   ────●──────────  00:12 / 02:30 │  ← Playback bar
├──────────────┴──────────────────────────────────────────────┤
│ ▸ playing │ ◉ 12 blobs │ ⚡ 29.4 fps │ ○ idle               │  ← Status bar
└─────────────────────────────────────────────────────────────┘
```

- The **Control Panel** can be undocked, moved to the right side, or hidden via
  the View menu.
- The **Playback Bar** only appears for file sources.
- The **Status Bar** updates four times per second.

---

## 2. Hotkeys

| Key | Action |
| --- | --- |
| `Space` | Play / pause the current source |
| `R` | Toggle live recording |
| `P` | Open the visual preset browser |
| `F` | Toggle fullscreen preview |

---

## 3. Menu Bar

### File
- **Open Video…** — pick a media file and start playback immediately.
- **Save Project / Load Project** — persist the current source + parameters.
- **Quit**.

### View
- **Toggle Control Panel** — hide/show the dock.
- **Fullscreen Preview**.

### Effects
- **Hot Reload Plugins** — re-scans `plugins/*.py` (see DEVELOPMENT.md).

### Help
- **About**.

---

## 4. Control Panel Sections

The sidebar is divided into collapsible sections. Click a section header (or
its checkbox) to expand/collapse.

### ▶ Input
Choose where frames come from.

| Field | Notes |
| --- | --- |
| **Source** | `webcam` or `file` |
| **File** | Browse to an `.mp4 / .mov / .avi / .png` |
| **Webcam Index** | OS camera index, usually `0` |
| **Target FPS** | Capture/playback rate target |
| **▶ Play / ⏸ Pause / ⏹ Stop** | Source transport |

> Picking `file` enables the **Render to File** action lower down.

### ◉ Blob
Core detection knobs (applied to the preprocessed frame).

| Field | Effect |
| --- | --- |
| **Threshold** | Binarisation cut-off after grayscale + blur |
| **Blur Radius** | Gaussian blur kernel (odd values) |
| **Min Area / Max Area** | Filters out blobs outside this contour-area band |
| **Max Blob Count** | Hard cap to keep performance stable |
| **Smoothing** | Centroid smoothing alpha (0 = no smoothing, 1 = freeze) |

### ⟳ Tracking
Trail and label geometry.

| Field | Effect |
| --- | --- |
| **Max Trail Length** | Frames of history kept per blob |
| **ID Font Size** | OpenCV font scale for IDs |
| **Label Offset X/Y** | Offset of the ID label from the centroid (px) |

### ✦ Effects
Overlay toggles + colours.

- **Checkbox toggles** — bounding box, labels, trail, zoom inset, optical
  flow, show coords.
- **Colour pickers** — bbox / label / trail colour (swatch button shows the
  current colour and hex).
- **BBox Thickness / Trail Alpha / Trail Thickness** — line styling.
- **Zoom Blob ID / Zoom Factor / Zoom Corner** — magnify a specific tracked
  blob into one corner of the frame.
- **BBox Corner** — `rect` (full rectangle) or `corner` (corner ticks only).
- **Blend Mode** — how the effect layer composites on the base frame
  (`normal / screen / overlay / multiply`).

### ⬡ Frame FX
Whole-frame look passes applied first in the pipeline.

| Field | Range | Effect |
| --- | --- | --- |
| **Desaturate Amount** | 0–1 | Mix toward grayscale |
| **Grain Strength** | 0–0.2 | Additive noise |
| **Vignette Strength** | 0–1 | Darken the corners |

### ⊡ Overlay Style
Visual style for overlay text/markers (works alongside the Effects section).

- **Corner Style** — `full rect` or `corner ticks`.
- **Tick Length** — length of corner ticks in px.
- **Box Opacity** — overlay alpha.
- **Show ID Label / Show Area Readout / Show Coord Readout / Show Leader Lines / Show Centroid Dot** — toggles for individual overlay components.
- **Trail Length** — short alias for `tracking.max_trail_length`.
- **Show Zoom Inset** — alias toggle.

### ⌖ Connection Lines
Draw lines between blobs whose centroids are within a distance threshold —
great for crowd / cluster visualisation.

| Field | Effect |
| --- | --- |
| **Enable Connections** | Master toggle |
| **Max Distance** | Pixels — pairs farther apart get no line |
| **Line Opacity / Thickness** | Self-explanatory |
| **Show Junction Dots** | Draws a dot at each blob endpoint |
| **Dot Radius / Color** | Junction dot styling |

### ⬔ Blob Interior FX
Apply a per-blob effect *inside* the blob's bounding rect, leaving the rest of
the frame alone.

- **Mode** — `none / thermal / edge / pixelate / negative / blur / highlight /
  desaturate`.
- **Opacity** — blend strength.
- **Padding** — grow the bounding box before applying.
- **Feather edges** — soft alpha on the mask edge.
- Mode-specific options appear when relevant: `Pixel size` (pixelate),
  `Blur radius` (blur), `Brightness` (highlight).

### ◈ Detection Mode
Switch between detector backends and tracker behaviour.

| Field | Effect |
| --- | --- |
| **Detector Mode** | `Contour` (default) or `Simple Blob` (OpenCV SimpleBlobDetector) |
| **Min / Max Area** | Mirror of the Blob section, scoped to this mode |
| **Disappeared Frames** | How many missing frames before a tracked ID is dropped |
| **Centroid Smoothing Alpha** | Alias of `tracking.smoothing` |

### ✺ Creative
Stackable creative filter chain.

- **Enable Creative FX** — master toggle.
- **Filter Chain (drag to reorder)** — drag rows in the list to change the
  apply order.
- **Hot Reload Plugins** — re-scans `plugins/` and rebuilds the filter
  registry without restarting the app.
- Per-filter blocks (each with its own enable checkbox + params):
  - **GrainFilter** — intensity, type (`gaussian / uniform / colored`), colored.
  - **GlitchFilter** — slices, max offset, probability.
  - **ThermalFilter** — colormap (`inferno / hot / cool / twilight / viridis`).
  - **EdgeFilter** — low/high Canny thresholds, alpha, blur.
  - **ChromaticAberration** — shift X/Y, randomize.

### ⏺ Output (live record)
Real-time export while playing.

| Field | Effect |
| --- | --- |
| **Export Path** | Output file/folder |
| **Format** | `mp4` (OpenCV), `png_seq` (numbered PNGs), `prores` (ffmpeg → `.mov`) |
| **Start Record / Stop Record** | Toggles live capture to disk |
| **⏺ Render Video** | Plays the file from start to end, saving the processed result (live preview rate) |

> Recording runs on a dedicated writer thread so the UI doesn't stall.

### ☰ Presets
Save the entire parameter set as JSON.

- **Preset Name** + **Save** — writes `presets/<name>.json`.
- **Load** — applies the selected preset.
- **Delete** — removes the JSON file.

`presets/default.json` is auto-loaded on startup if present.

### ⚡ Performance
Trade quality for speed.

| Field | Effect |
| --- | --- |
| **Process Scale** | 0.25–1.0 — detection runs on a downscaled copy (`0.5` recommended) |
| **Detect Every N** | 1 = every frame, 2 = skip 1, etc. (recommended `2`) |
| **Min Label Area** | Skip drawing labels on blobs smaller than this |
| **FPS Display** | Live read-out |

### ⬇ Render to File
**Offline, full-quality** render of a video file — re-runs detection and
tracking deterministically frame by frame, independent of the live preview
rate.

| Field | Effect |
| --- | --- |
| **Output Path** | Final video destination |
| **Render to File** | Starts the offline pipeline |
| **Cancel** | Aborts the in-progress render |
| **Progress / Status / Thumbnail** | Live updates from the render worker |

> Only enabled when the source is `file`.

---

## 5. Playback Bar (file source only)

| Button | Action |
| --- | --- |
| ⏮ | Skip to start |
| ▶ / ⏸ | Play / pause |
| ⏭ | Skip to end |
| ⟳ | Toggle loop (highlighted green when active) |
| Timeline | Click or drag to scrub |
| Timecode | `MM:SS / MM:SS` |

---

## 6. Status Bar

Four monospace segments, refreshed every 250 ms:

- `▸ <source>` — current source state (idle / playing / paused / end of file / render).
- `◉ <n> blobs` — count of currently tracked blobs.
- `⚡ <fps> fps` — measured render FPS.
- `○ idle` — recording indicator (turns to **`● REC`** in red when recording).

---

## 7. Tips

- For webcam work, start with **Process Scale = 0.5** and **Detect Every N = 2**.
- The **Connection Lines** + **Blob Interior FX** combo is the fastest way to
  get a striking "surveillance / thermal" look.
- Save your favourite parameter sets as presets early — undo is not yet
  supported.
- Use **Render to File** for the final deliverable: offline rendering is
  deterministic and ignores frame drops.
