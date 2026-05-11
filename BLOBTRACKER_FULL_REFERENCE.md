# BlobTracker Full Application Reference

## 1. What This Application Is

BlobTracker is a desktop application built with Python, PyQt6, and OpenCV.
It captures frames from webcam or video files, detects and tracks blobs, applies visual effects, previews output live, and exports processed video.

Core goals:
- Real-time blob detection and tracking.
- Visual overlays (boxes, labels, trails, flow, connection lines, zoom inset).
- Creative filter chain with plugin support.
- Live recording and offline full-frame render.
- Parameter-driven behavior with preset save/load.

## 2. High-Level Architecture

Main modules:
- main.py: Application bootstrap, wiring, live render loop, export controls.
- control_panel.py: All UI controls and parameter bindings.
- param_store.py: Typed parameter registry, defaults, validation, presets.
- input_layer.py: Source abstraction, capture worker, frame buffer.
- processing_core.py: Preprocessing, detection, tracking, optical flow, processing worker.
- effect_engine.py: Overlay effects, creative filters, compositor.
- output_layer.py: Preview widget, threaded exporter, project serializer.
- renderer.py: Offline render pipeline (frame-by-frame high-quality export).
- plugin_loader.py: Dynamic loading of creative filter plugins.
- preset_browser.py: Preset picker dialog.
- hotkeys.py: Keyboard shortcut management.
- models.py: Blob and FramePacket data models.

## 3. Runtime Pipelines

### 3.1 Live Preview Pipeline
1. Source opened by CaptureWorker (webcam or file).
2. Frames pushed into FrameBuffer at target cadence.
3. ProcessorWorker reads frames, preprocesses, detects, tracks, emits FramePacket.
4. MainWindow composes effects on raw frame and blobs.
5. PreviewRenderer shows final frame.
6. If recording is active, final frame is also sent to VideoExporter.

### 3.2 Live Recording Pipeline
1. Start recording from current preview frame size.
2. VideoExporter thread consumes processed frames.
3. Encodes to mp4, png sequence, or ProRes (ffmpeg-based path for ProRes).
4. Stops cleanly and finalizes output.

### 3.3 Offline Render Pipeline
1. OfflineRenderer opens source file and processes every frame.
2. Uses dedicated preprocessor/detector/tracker/effect stack.
3. Writes temporary PNG frames.
4. Assembles to final mp4 using ffmpeg when available, otherwise OpenCV fallback.
5. Reports progress and preview thumbnails back to UI.

## 4. Component Responsibilities

### 4.1 Input Layer
- FrameSource abstract interface standardizes open/read/release/is_opened.
- VideoFileSource supports both videos and image sequences.
- WebcamSource handles camera capture.
- FrameBuffer decouples capture and processing threads.
- CaptureWorker controls start/stop/pause/resume and file-end state.

### 4.2 Processing Core
- Preprocessor: scaling, grayscale, blur, threshold.
- BlobDetector: contour mode or OpenCV simple blob mode.
- Tracker: ID assignment, smoothing, missing-frame handling, trail history.
- OpticalFlow: optional motion visualization overlay.
- ProcessorWorker: threaded orchestrator that emits FramePacket objects.

### 4.3 Effect Engine
- BaseFrameFX: desaturate, grain, vignette.
- BoundingBoxFX: full rectangle or corner-tick style boxes.
- LabelFX: IDs, optional area and coordinates, leader lines, centroid dots.
- TrailFX: polyline trails from tracked history.
- ConnectionLineFX: distance-based link network between blob centroids.
- ZoomInsetFX: magnified inset around selected/largest blob.
- Compositor: blend modes normal/screen/overlay/multiply.
- CreativeFX: ordered chain of built-in and plugin filter classes.

Built-in creative filters:
- GrainFilter
- GlitchFilter
- ThermalFilter
- EdgeFilter
- ChromaticAberration

### 4.4 Output Layer
- PreviewRenderer converts BGR to RGB for Qt display.
- VideoExporter runs asynchronous writing to reduce UI stutter.
- ProjectManager saves/loads project payloads with source path and parameters.

### 4.5 Offline Renderer
- Independent thread and worker.
- Re-runs detection/tracking for deterministic frame-by-frame rendering.
- Applies same major effect stack as live rendering.
- Generates a final encoded video after PNG staging.

### 4.6 Plugin System
- PluginLoader scans plugins directory for Python files.
- Loads subclasses of CreativeFilter dynamically.
- Registered plugin filters become available in creative chain order.

### 4.7 Presets and Project Files
- Presets are JSON snapshots of all parameters.
- Project save/load stores source path plus parameter dictionary and filter chain.

## 5. Data Models

- Blob:
  - id: tracker ID.
  - centroid: current center point.
  - bbox: bounding rectangle.
  - area: measured blob area.
  - trail: centroid history list.

- FramePacket:
  - raw_frame: captured frame.
  - blobs: tracked blob list.
  - timestamp: processing timestamp.
  - frame_index: sequential frame count.

## 6. Hotkeys

Default shortcuts:
- Space: play/pause.
- R: toggle recording.
- P: open preset browser.
- F: toggle fullscreen.

## 7. Parameter System

Parameters are defined in param_store.py as ParamDef entries with:
- key
- value (default)
- min/max/step (for numeric controls)
- type
- options (for enums)

Behavior notes:
- ParamStore.set validates and clamps by declared type.
- Param changes drive runtime behavior immediately through UI bindings and MainWindow handlers.
- params_bulk_changed is emitted when loading preset/project payloads.

## 8. Full Parameter Reference (All 66 Parameters)

Legend:
- Scope: where parameter is primarily used.
- Status:
  - Active: directly affects processing/render output.
  - Alias: mirrors or syncs with another key.
  - UI-state: mostly used for control state or planned style behavior.

### 8.1 Input Parameters

| Key | Type | Default | Range/Options | Scope | Status | Use |
|---|---|---:|---|---|---|---|
| input.source_type | enum | webcam | webcam, file | MainWindow, ControlPanel | Active | Selects capture source mode. |
| input.source_path | str | (empty) | any path | Input, MainWindow | Active | File path for video/image-sequence input. |
| input.webcam_index | int | 0 | 0..8 | Input, MainWindow | Active | Camera device index for webcam source. |
| input.target_fps | int | 30 | 1..120 | Capture timing, UI timer | Active | Target frame cadence for buffer capture and render timer interval. |

### 8.2 Blob Detection and Performance

| Key | Type | Default | Range/Options | Scope | Status | Use |
|---|---|---:|---|---|---|---|
| blob.threshold | int | 90 | 0..255 | Preprocessor, detector | Active | Binary threshold value after blur. |
| blob.blur_radius | int | 7 | 1..31 | Preprocessor | Active | Gaussian blur kernel size before thresholding. |
| blob.min_area | float | 120.0 | 1..20000 | Detector | Active | Minimum allowed blob area for contour path. |
| blob.max_area | float | 50000.0 | 10..400000 | Detector | Active | Maximum allowed blob area for contour path. |
| blob.max_count | int | 20 | 1..300 | Detector | Active | Max number of blobs retained per frame. |
| process_scale | float | 0.5 | 0.25..1.0 | Preprocessor | Active | Downscale factor for faster detection. |
| detect_every_n | int | 2 | 1..4 | ProcessorWorker | Active | Run full detection every N frames; interpolate trails on skipped frames. |
| min_label_area | int | 200 | 0..2000 | LabelFX invocation | Active | Suppresses labels on tiny blobs. |

### 8.3 Tracking

| Key | Type | Default | Range/Options | Scope | Status | Use |
|---|---|---:|---|---|---|---|
| tracking.smoothing | float | 0.35 | 0..1 | Tracker | Active | Smoothing factor for centroid updates and distance tolerance shaping. |
| tracking.max_trail_length | int | 35 | 1..500 | Tracker/UI | Alias | Historical trail length; primary runtime key is trail_length when present. |
| tracking.id_font_size | float | 0.5 | 0.2..2.0 | LabelFX | Active | Font scale for blob labels. |
| tracking.label_offset_x | int | 10 | -200..200 | LabelFX | Active | Horizontal label offset from centroid. |
| tracking.label_offset_y | int | -10 | -200..200 | LabelFX | Active | Vertical label offset from centroid. |

### 8.4 Core Effects

| Key | Type | Default | Range/Options | Scope | Status | Use |
|---|---|---:|---|---|---|---|
| effects.bbox_enabled | bool | false | false/true | Render composition | Active | Enables bounding box overlay. |
| effects.label_enabled | bool | false | false/true | Render composition | Active | Enables labels overlay. |
| effects.trail_enabled | bool | false | false/true | Render composition | Active | Enables trail rendering. |
| effects.zoom_enabled | bool | false | false/true | Render composition | Active | Enables zoom inset overlay. |
| effects.flow_enabled | bool | false | false/true | Render composition | Active | Enables optical-flow motion overlay. |
| effects.bbox_color | color | [240,240,240] | RGB 0..255 | BoundingBoxFX | Active | Bounding box color. |
| effects.bbox_thickness | int | 1 | 1..6 | BoundingBoxFX | Active | Bounding box line thickness. |
| effects.bbox_corner_style | enum | rect | rect, corner | BoundingBoxFX | Active | Box style: full rectangle or corner ticks. |
| effects.label_color | color | [240,240,240] | RGB 0..255 | LabelFX | Active | Label, leader, and centroid color. |
| effects.label_show_coords | bool | false | false/true | LabelFX | Active | Appends centroid coordinates to text label. |
| effects.trail_color | color | [0,229,255] | RGB 0..255 | TrailFX | Active | Trail line color. |
| effects.trail_alpha | float | 0.8 | 0..1 | TrailFX | Active | Trail opacity envelope. |
| effects.trail_thickness | int | 1 | 1..6 | TrailFX | Active | Trail line thickness. |
| effects.zoom_blob_id | int | 0 | 0..99999 | ZoomInsetFX | Active | Target blob ID for zoom inset; 0 means auto-select largest blob. |
| effects.zoom_factor | float | 2.0 | 1..6 | ZoomInsetFX | Active | Zoom crop multiplier around target blob. |
| effects.zoom_corner | enum | top-right | top-left, top-right, bottom-left, bottom-right | ZoomInsetFX | Active | Corner placement of inset window. |
| effects.blend_mode | enum | normal | normal, screen, overlay, multiply | Compositor | Active | Blend mode between base and overlay layers. |

### 8.5 Frame Stylization

| Key | Type | Default | Range/Options | Scope | Status | Use |
|---|---|---:|---|---|---|---|
| frame_desaturate | float | 0.0 | 0..1 | BaseFrameFX | Active | Amount of grayscale mix into frame. |
| frame_grain | float | 0.0 | 0..0.2 | BaseFrameFX | Active | Procedural noise intensity. |
| frame_vignette | float | 0.0 | 0..1 | BaseFrameFX | Active | Edge darkening strength. |

### 8.6 Overlay Style and Legacy Overlay Controls

| Key | Type | Default | Range/Options | Scope | Status | Use |
|---|---|---:|---|---|---|---|
| overlay_corner_style | enum | ticks | full, ticks | ControlPanel | Alias/UI-state | UI style selector that also syncs effects.bbox_corner_style. |
| overlay_tick_length | int | 10 | 4..30 | ControlPanel | UI-state | Stored tick-length preference; not currently passed into BoundingBoxFX call path. |
| overlay_box_opacity | float | 0.7 | 0..1 | ControlPanel | UI-state | Stored box opacity preference; not currently passed into BoundingBoxFX call path. |
| overlay_show_label | bool | true | false/true | ControlPanel | Alias | Toggles effects.label_enabled through UI linkage. |
| overlay_show_area | bool | false | false/true | ControlPanel | UI-state | Stored area-readout preference; not currently wired into LabelFX call path. |
| overlay_show_coords | bool | false | false/true | ControlPanel | Alias | Toggles effects.label_show_coords through UI linkage. |
| overlay_show_leaders | bool | true | false/true | ControlPanel | UI-state | Stored leader-lines preference; currently not wired into LabelFX call parameters. |
| overlay_show_centroid | bool | true | false/true | ControlPanel | UI-state | Stored centroid-dot preference; currently not wired into LabelFX call parameters. |

### 8.7 Connection Line Network

| Key | Type | Default | Range/Options | Scope | Status | Use |
|---|---|---:|---|---|---|---|
| connection_enabled | bool | true | false/true | MainWindow, OfflineRenderer | Active | Enables centroid connection graph overlay. |
| connection_max_dist | float | 200.0 | 50..800 | ConnectionLineFX | Active | Max centroid distance to draw connection. |
| connection_opacity | float | 0.4 | 0..1 | ConnectionLineFX | Active | Maximum connection line opacity. |
| connection_thickness | float | 0.5 | 0.5..3.0 | ConnectionLineFX | Active | Connection line thickness. |
| connection_color | color | [255,255,255] | RGB 0..255 | ConnectionLineFX | Active | Connection and dot color. |
| connection_show_dots | bool | true | false/true | ConnectionLineFX | Active | Draw dot at each centroid when connected layer is on. |
| connection_dot_radius | int | 3 | 1..8 | ConnectionLineFX | Active | Dot radius for centroid markers. |

### 8.8 Compatibility and Alternate Tracking/Detection Controls

| Key | Type | Default | Range/Options | Scope | Status | Use |
|---|---|---:|---|---|---|---|
| trail_length | int | 20 | 0..60 | Tracker | Active | Preferred runtime trail length used in processing/offline render. |
| zoom_inset_enabled | bool | false | false/true | ControlPanel | Alias | Mirrors/toggles effects.zoom_enabled from overlay style section. |
| zoom_inset_scale | float | 1.8 | 1..4 | ControlPanel | UI-state | Stored zoom scale preference; current zoom rendering uses effects.zoom_factor. |
| detector_mode | enum | contour | contour, simple_blob | Detector | Active | Select detection algorithm. |
| blob_min_area | int | 80 | 10..5000 | Detector | Active | Runtime min area used by current detection path; UI syncs blob.min_area too. |
| blob_max_area | int | 8000 | 100..50000 | Detector | Active | Runtime max area used by current detection path; UI syncs blob.max_area too. |
| tracker_max_disappeared | int | 5 | 1..30 | Tracker | Active | Max consecutive missed frames before track removal. |
| tracker_smooth_alpha | float | 0.4 | 0..1 | Tracker | Active | Explicit centroid smoothing alpha; UI also syncs tracking.smoothing. |

### 8.9 Creative Filter Chain

| Key | Type | Default | Range/Options | Scope | Status | Use |
|---|---|---:|---|---|---|---|
| creative.enabled | bool | false | false/true | MainWindow, OfflineRenderer | Active | Enables creative filter chain processing. |
| creative.filter_order | list | [] | dynamic list | CreativeFX | Active | Ordered list of filter names; controls chain execution sequence. |
| creative.filter_params | dict | built-in config map | dynamic map | CreativeFX | Active | Per-filter constructor parameters. Defaults include GrainFilter, GlitchFilter, ThermalFilter, EdgeFilter, ChromaticAberration configs. |

### 8.10 Output and Recording

| Key | Type | Default | Range/Options | Scope | Status | Use |
|---|---|---:|---|---|---|---|
| output.export_path | str | output.mp4 | path | Exporter, render dialogs | Active | Target path for recording and offline render output. |
| output.format | enum | mp4 | mp4, png_seq, prores | Exporter | Active | Chooses export backend format. |
| output.recording | bool | false | false/true | MainWindow, ControlPanel | Active | Recording state flag; toggled to start/stop threaded exporter. |

## 9. Parameter Interactions and Aliases

Important key interactions:
- overlay_show_label toggles effects.label_enabled.
- overlay_show_coords toggles effects.label_show_coords.
- overlay_corner_style toggles effects.bbox_corner_style mapping ticks to corner and full to rect.
- trail_length and tracking.max_trail_length are kept aligned from UI, but runtime prefers trail_length where available.
- blob_min_area and blob_max_area are synchronized from detection mode controls to blob.min_area and blob.max_area.
- tracker_smooth_alpha is synchronized to tracking.smoothing from detection mode controls.
- zoom_inset_enabled toggles effects.zoom_enabled.

## 10. Notes on Current Behavior

- Base frame stylization is always applied in render pipeline, but with current neutral defaults it does not alter color until changed.
- Some overlay-style keys are currently stored and shown in UI but not fully threaded into effect invocation parameters (overlay_tick_length, overlay_box_opacity, overlay_show_area, overlay_show_leaders, overlay_show_centroid, zoom_inset_scale).
- Offline render uses PNG staging plus final assembly, which can require large temporary disk space for long/high-resolution videos.

## 11. Typical Workflows

### 11.1 Live Tracking Session
1. Choose webcam or file source.
2. Start playback.
3. Tune blob and tracking parameters.
4. Enable desired effects and blend mode.
5. Optionally enable creative chain.

### 11.2 Live Recording
1. Set output path and format.
2. Start source.
3. Toggle recording.
4. Stop recording to finalize file.

### 11.3 Offline High-Quality Render
1. Select file source and output path.
2. Tune parameters and effects.
3. Click Render to File.
4. Monitor progress and thumbnail.

## 12. Extending the Application

### 12.1 Add Creative Plugins
- Add Python file in plugins directory.
- Implement class inheriting CreativeFilter with name and apply(frame).
- Use Hot Reload Plugins to register without restarting.

### 12.2 Add New Parameters
1. Add ParamDef in param_store defaults.
2. Bind UI control in control_panel.
3. Consume parameter in processing/effect/export code.
4. Optionally include in presets/project behavior (already automatic when in ParamStore).

---

This document reflects the current codebase behavior as of March 18, 2026.
