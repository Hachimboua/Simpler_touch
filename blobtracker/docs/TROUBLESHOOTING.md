# Troubleshooting

Common issues and fixes, in roughly the order users hit them.

---

## Launch

### `ModuleNotFoundError: No module named 'PyQt6'`
You're using the wrong Python interpreter. Activate the virtualenv and re-install:

```bash
.venv\Scripts\activate
pip install -r requirements.txt
```

### `qt.qpa.plugin: Could not find the Qt platform plugin "windows"`
Reinstall the PyQt6 binary wheels (don't trust system-installed Qt):

```bash
pip install --force-reinstall --no-cache-dir PyQt6 PyQt6-Qt6 PyQt6-sip
```

### Black window or instant crash on launch
Update graphics drivers and try `QT_OPENGL=software` in the environment. On
laptops with hybrid graphics, force the app to use the discrete GPU.

---

## Source / Capture

### Webcam not opening
- Check **Webcam Index** — the OS-assigned index is rarely `0` on multi-camera
  setups. Try `1`, `2`, etc.
- Close anything else using the camera (Teams, browser).
- On Windows, allow desktop apps in *Privacy → Camera*.

### Video file doesn't open
- Confirm the file plays in VLC. If VLC can play it but BlobTracker can't,
  re-encode to H.264 MP4 (`ffmpeg -i in.mov -c:v libx264 -crf 18 out.mp4`).
- OpenCV's bundled codecs are limited — exotic formats (HEVC variants,
  ProRes, RAW DNG sequences) often fail without a system codec.

### Image sequence not advancing
The `VideoFileSource` treats single PNGs as one-frame inputs. For a numbered
sequence, point at the first file (`frame_0001.png`) — OpenCV picks up the
pattern automatically when the filename matches `printf`-style padding.

---

## Detection / Tracking

### Nothing is detected
- Watch the **Threshold** slider — if the scene is bright on bright (or dark
  on dark), the binarisation produces no contours.
- Increase **Blur Radius** to merge speckle.
- Check **Min Area** — small blobs may be filtered out by area alone.
- Try switching **Detector Mode → Simple Blob** which uses
  `cv2.SimpleBlobDetector` with brightness/circularity heuristics instead of
  pure contour detection.

### Blob IDs flicker / re-assign on every frame
- Increase **Disappeared Frames** to keep IDs alive across short occlusions.
- Reduce **Centroid Smoothing Alpha** if smoothing is masking real motion and
  making the assignment confused.
- Drop **Detect Every N** to `1` — skipping detection frames combined with
  fast motion can break ID continuity.

### Tracker is laggy / sluggish
- That's smoothing. Reduce `tracking.smoothing` (Blob section) toward `0.1`.

---

## Performance

### Low FPS
1. Lower **Process Scale** to `0.5` (Performance section).
2. Set **Detect Every N** to `2` or `3`.
3. Turn off **Optical Flow** if not needed — it's the most expensive overlay.
4. Disable the **Creative** chain when iterating on detection — creative
   filters run on the full-res output frame.
5. Reduce **Max Blob Count** if the scene is genuinely crowded.

### CPU spikes when recording
The `VideoExporter` shares the host CPU with the live pipeline. For high-res
recordings, prefer **Render to File** (offline mode) which is throughput-
optimised and not bound to live FPS.

---

## Recording / Export

### Recorded file is empty / 0 bytes
- Set the **Export Path** before pressing Start Record.
- Make sure the source is actually playing — recording only writes frames it
  receives.
- Codec mismatch: try `png_seq` first to confirm the pipeline works, then
  switch back to `mp4`.

### `prores` produces nothing
The `prores` format shells out to `ffmpeg`. Confirm:

```bash
ffmpeg -version
```

If `ffmpeg` isn't on `PATH`, install it and restart the app (PATH is read at
process start).

### Offline render says "ffmpeg not found, falling back to OpenCV"
This is informational, not an error — output will still be written via
`cv2.VideoWriter`, but with a more limited codec set. Install `ffmpeg` for
best results.

---

## UI

### Control panel cut off / scrolling oddly
Resize the dock wider (drag the right edge) or undock it (drag its title bar
out of the window).

### Section won't expand
The little checkbox in each section title is the expand/collapse toggle. Make
sure it's checked.

### Color picker shows wrong colour on the swatch button
Save and reload the preset — this resyncs the UI state from `ParamStore`.

---

## Plugins

### My plugin isn't showing up
- File must be in `plugins/` and end with `.py`.
- File name must not start with `_`.
- Class must inherit from `effect_engine.CreativeFilter` and define a `name`
  class attribute.
- Click **Hot Reload Plugins** after editing.
- Check the console — import errors are printed but don't crash the app.

### Plugin loads but its parameters are ignored
Plugin constructor kwargs come from `creative.filter_params["<ClassName>"]`.
Either add an entry there in a preset, or rely on the constructor defaults.

---

## Presets

### Preset file exists but doesn't show in the list
- Must end with `.json`.
- Must live directly under `presets/` (no nesting).
- Restart the app or click **Save** on a dummy preset to refresh the list.

### Loading an old preset complains about unknown keys
That's a warning, not a failure — unknown keys are dropped. Re-save the
preset under the same name to migrate it.

---

## Still stuck?

Open an issue with:

1. OS + Python version (`python --version`)
2. `pip freeze` output
3. The exact preset and source file (or "webcam")
4. Steps to reproduce
5. A screenshot or short screen recording if it's a UI bug
