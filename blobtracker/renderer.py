from __future__ import annotations

import glob
import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PyQt6.QtCore import QObject, QThread, pyqtSignal


class _RenderWorker(QObject):
    progress = pyqtSignal(int)
    frame_preview = pyqtSignal(object)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(
        self,
        param_store,
        preprocessor,
        detector,
        tracker,
        effect_engine: Dict[str, Any],
        compositor,
        source_path: str,
        output_path: str,
        render_dir: str,
    ) -> None:
        super().__init__()
        self.param_store = param_store
        self.preprocessor = preprocessor
        self.detector = detector
        self.tracker = tracker
        self.effect_engine = effect_engine
        self.compositor = compositor
        self.source_path = source_path
        self.output_path = output_path
        self.render_dir = render_dir
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def _cleanup_pngs(self) -> None:
        pattern = os.path.join(self.render_dir, "frame_*.png")
        for path in glob.glob(pattern):
            try:
                os.remove(path)
            except OSError:
                pass

    def _assemble_with_opencv(self, fps: float) -> None:
        frame_paths = sorted(glob.glob(os.path.join(self.render_dir, "frame_*.png")))
        if not frame_paths:
            raise RuntimeError("No rendered frames were found for video assembly.")

        first = cv2.imread(frame_paths[0])
        if first is None:
            raise RuntimeError("Unable to read first rendered frame for assembly.")
        h, w = first.shape[:2]

        output_path = self.output_path
        if not output_path.lower().endswith(".mp4"):
            output_path = "{}.mp4".format(output_path)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(output_path, fourcc, float(max(1.0, fps)), (w, h))
        if not writer.isOpened():
            raise RuntimeError("OpenCV fallback writer could not be opened.")

        for path in frame_paths:
            frame = cv2.imread(path)
            if frame is None:
                continue
            writer.write(frame)
        writer.release()
        self.output_path = output_path

    def _reset_tracker_state(self) -> None:
        # Prefer tracker.reset() if available; otherwise reset known fields safely.
        if hasattr(self.tracker, "reset") and callable(getattr(self.tracker, "reset")):
            self.tracker.reset()
            return

        if hasattr(self.tracker, "next_id"):
            self.tracker.next_id = 1
        if hasattr(self.tracker, "active"):
            self.tracker.active = {}
        if hasattr(self.tracker, "missing_count"):
            self.tracker.missing_count = {}
        if hasattr(self.tracker, "trails"):
            self.tracker.trails = {}

    def _apply_effects(self, raw_frame: np.ndarray, blobs: List[Any]) -> np.ndarray:
        frame = raw_frame.copy()

        base_frame_fx = self.effect_engine.get("base_frame_fx")
        intra_blob_fx = self.effect_engine.get("intra_blob_fx")
        optical_flow = self.effect_engine.get("optical_flow")
        connection_fx = self.effect_engine.get("connection_fx")
        bbox_fx = self.effect_engine.get("bbox_fx")
        label_fx = self.effect_engine.get("label_fx")
        trail_fx = self.effect_engine.get("trail_fx")
        zoom_fx = self.effect_engine.get("zoom_fx")
        creative_fx = self.effect_engine.get("creative_fx")

        if base_frame_fx is not None:
            frame = base_frame_fx.apply(
                frame,
                desaturate=float(self.param_store.get("frame_desaturate")),
                grain=float(self.param_store.get("frame_grain")),
                vignette=float(self.param_store.get("frame_vignette")),
            )

        if intra_blob_fx is not None:
            frame = intra_blob_fx.apply(frame, blobs)

        if optical_flow is not None:
            if bool(self.param_store.get("effects.flow_enabled")):
                frame = optical_flow.overlay(frame, enabled=True)
            else:
                frame = optical_flow.overlay(frame, enabled=False)

        layer = frame.copy()

        if (
            connection_fx is not None
            and bool(self.param_store.get("connection_enabled"))
            and len(blobs) >= 2
        ):
            layer = connection_fx.apply(layer, blobs)

        if trail_fx is not None and bool(self.param_store.get("effects.trail_enabled")):
            layer = trail_fx.apply(
                layer,
                blobs,
                tuple(self.param_store.get("effects.trail_color")),
                float(self.param_store.get("effects.trail_alpha")),
                int(self.param_store.get("effects.trail_thickness")),
            )

        if bbox_fx is not None and bool(self.param_store.get("effects.bbox_enabled")):
            layer = bbox_fx.apply(
                layer,
                blobs,
                tuple(self.param_store.get("effects.bbox_color")),
                int(self.param_store.get("effects.bbox_thickness")),
                str(self.param_store.get("effects.bbox_corner_style")),
            )

        if label_fx is not None and bool(self.param_store.get("effects.label_enabled")):
            layer = label_fx.apply(
                layer,
                blobs,
                float(self.param_store.get("tracking.id_font_size")),
                tuple(self.param_store.get("effects.label_color")),
                (
                    int(self.param_store.get("tracking.label_offset_x")),
                    int(self.param_store.get("tracking.label_offset_y")),
                ),
                bool(self.param_store.get("effects.label_show_coords")),
                min_label_area=int(self.param_store.get("min_label_area")) if "min_label_area" in self.param_store.params else 200,
            )

        if zoom_fx is not None and bool(self.param_store.get("effects.zoom_enabled")):
            layer = zoom_fx.apply(
                layer,
                blobs,
                int(self.param_store.get("effects.zoom_blob_id")),
                float(self.param_store.get("effects.zoom_factor")),
                (220, 160),
                str(self.param_store.get("effects.zoom_corner")),
            )

        if creative_fx is not None and bool(self.param_store.get("creative.enabled")):
            filter_order = list(self.param_store.get("creative.filter_order"))
            # Sync individual param store controls to unified filter_params dict
            filter_params = creative_fx.sync_params_from_store(self.param_store)
            if not filter_params:
                filter_params = dict(self.param_store.get("creative.filter_params"))
            layer = creative_fx.apply_chain(layer, filter_order, filter_params, param_store=self.param_store)

        blend_mode = str(self.param_store.get("effects.blend_mode"))
        if blend_mode == "normal":
            return layer
        return self.compositor.blend(frame, layer, blend_mode)

    def run(self) -> None:
        cap = cv2.VideoCapture(self.source_path)
        if not cap.isOpened():
            self.error.emit("Unable to open source video file.")
            return

        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        if fps <= 0:
            fps = 25.0

        os.makedirs(self.render_dir, exist_ok=True)
        self._cleanup_pngs()
        self._reset_tracker_state()

        try:
            frame_index = 0
            while True:
                if self._cancel:
                    self._cleanup_pngs()
                    self.error.emit("Render cancelled")
                    cap.release()
                    return

                ret, raw_frame = cap.read()
                if not ret or raw_frame is None:
                    break

                threshold = int(self.param_store.get("blob.threshold"))
                blur = int(self.param_store.get("blob.blur_radius"))
                process_scale = float(self.param_store.get("process_scale")) if "process_scale" in self.param_store.params else 1.0

                min_area = float(self.param_store.get("blob_min_area")) if "blob_min_area" in self.param_store.params else float(self.param_store.get("blob.min_area"))
                max_area = float(self.param_store.get("blob_max_area")) if "blob_max_area" in self.param_store.params else float(self.param_store.get("blob.max_area"))
                max_count = int(self.param_store.get("blob.max_count"))
                detector_mode = str(self.param_store.get("detector_mode")) if "detector_mode" in self.param_store.params else "contour"
                min_circularity = float(self.param_store.get("blob.min_circularity")) if "blob.min_circularity" in self.param_store.params else 0.0
                simple_min_threshold = float(self.param_store.get("blob.threshold"))
                simple_max_threshold = 255.0

                trail_length = int(self.param_store.get("trail_length")) if "trail_length" in self.param_store.params else int(self.param_store.get("tracking.max_trail_length"))
                smoothing = float(self.param_store.get("tracking.smoothing"))
                max_disappeared = int(self.param_store.get("tracker_max_disappeared")) if "tracker_max_disappeared" in self.param_store.params else 10
                smooth_alpha = float(self.param_store.get("tracker_smooth_alpha")) if "tracker_smooth_alpha" in self.param_store.params else smoothing

                thresh, used_scale = self.preprocessor.run(
                    raw_frame,
                    threshold=threshold,
                    blur_radius=blur,
                    scale=process_scale,
                )
                detections = self.detector.run(
                    thresh,
                    scale=used_scale,
                    min_area=min_area,
                    max_area=max_area,
                    max_count=max_count,
                    mode=detector_mode,
                    min_circularity=min_circularity,
                    simple_min_threshold=simple_min_threshold,
                    simple_max_threshold=simple_max_threshold,
                )
                blobs = self.tracker.update(
                    detections,
                    max_distance=max(10.0, 100.0 * (1.0 - min(0.95, smoothing))),
                    trail_length=trail_length,
                    max_missing=max_disappeared,
                    smoothing_alpha=smooth_alpha,
                )

                composited = self._apply_effects(raw_frame, blobs)
                filename = os.path.join(self.render_dir, "frame_{:06d}.png".format(frame_index))
                cv2.imwrite(filename, composited)

                if frame_index % 10 == 0:
                    self.frame_preview.emit(composited)

                if total > 0:
                    percent = int(((frame_index + 1) / float(total)) * 100.0)
                    self.progress.emit(max(0, min(100, percent)))

                frame_index += 1

            cap.release()

            if self._cancel:
                self._cleanup_pngs()
                self.error.emit("Render cancelled")
                return

            ffmpeg_path = shutil.which("ffmpeg")
            if ffmpeg_path:
                ffmpeg_cmd = [
                    ffmpeg_path,
                    "-y",
                    "-r",
                    str(float(fps)),
                    "-i",
                    os.path.join(self.render_dir, "frame_%06d.png"),
                    "-i",
                    self.source_path,
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0?",
                    "-c:v",
                    "libx264",
                    "-crf",
                    "18",
                    "-preset",
                    "slow",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-shortest",
                ]
                ffmpeg_cmd.append(self.output_path)
                try:
                    subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)
                except subprocess.CalledProcessError as exc:
                    stderr = (exc.stderr or "").strip()
                    if stderr:
                        raise RuntimeError("FFmpeg failed: {}".format(stderr[-1200:])) from exc
                    raise
            else:
                self._assemble_with_opencv(fps)

            self._cleanup_pngs()
            self.progress.emit(100)
            self.finished.emit(self.output_path)
        except Exception as exc:
            cap.release()
            if isinstance(exc, FileNotFoundError):
                self.error.emit("FFmpeg executable not found. Install ffmpeg or use the built-in OpenCV fallback.")
            else:
                self.error.emit(str(exc))


class OfflineRenderer(QObject):
    progress = pyqtSignal(int)
    frame_preview = pyqtSignal(object)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(
        self,
        param_store,
        preprocessor,
        detector,
        tracker,
        effect_engine,
        compositor,
    ) -> None:
        super().__init__()
        self.param_store = param_store
        self.preprocessor = preprocessor
        self.detector = detector
        self.tracker = tracker
        self.effect_engine = effect_engine
        self.compositor = compositor

        self._cancel = False
        self._thread: Optional[QThread] = None
        self._worker: Optional[_RenderWorker] = None
        self.source_path: str = ""
        self.output_path: str = ""
        self.total_frames: int = 0

    def _get_render_dir(self) -> str:
        out_dir = os.path.dirname(self.output_path) or os.getcwd()
        render_dir = os.path.join(out_dir, "blobtracker_render_tmp")
        os.makedirs(render_dir, exist_ok=True)
        return render_dir

    def start_render(self, source_path: str, output_path: str) -> None:
        if self._thread is not None and self._thread.isRunning():
            self.error.emit("Render already in progress")
            return

        self._cancel = False
        self.source_path = source_path
        self.output_path = output_path

        cap = cv2.VideoCapture(self.source_path)
        if cap.isOpened():
            self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        else:
            self.total_frames = 0
        cap.release()

        render_dir = self._get_render_dir()

        self._thread = QThread()
        self._worker = _RenderWorker(
            param_store=self.param_store,
            preprocessor=self.preprocessor,
            detector=self.detector,
            tracker=self.tracker,
            effect_engine=self.effect_engine,
            compositor=self.compositor,
            source_path=self.source_path,
            output_path=self.output_path,
            render_dir=render_dir,
        )
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.progress.emit)
        self._worker.frame_preview.connect(self.frame_preview.emit)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.error.connect(self._on_worker_error)

        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def cancel(self) -> None:
        self._cancel = True
        if self._worker is not None:
            self._worker.cancel()

    def _on_worker_finished(self, path: str) -> None:
        self.finished.emit(path)
        self._worker = None
        self._thread = None

    def _on_worker_error(self, msg: str) -> None:
        self.error.emit(msg)
        self._worker = None
        self._thread = None
