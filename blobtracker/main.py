from __future__ import annotations

from collections import deque
import os
import sys
import time
from typing import Dict, List, Optional

import cv2
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from control_panel import ControlPanel
from effect_engine import (
    BaseFrameFX,
    BoundingBoxFX,
    Compositor,
    ConnectionLineFX,
    CreativeFX,
    IntraBlobFX,
    LabelFX,
    TrailFX,
    ZoomInsetFX,
)
from hotkeys import HotkeyManager
from input_layer import CaptureWorker, FrameBuffer, VideoFileSource, WebcamSource
from output_layer import PreviewRenderer, ProjectManager, VideoExporter
from param_store import ParamStore
from plugin_loader import PluginLoader
from preset_browser import PresetBrowserDialog
from processing_core import BlobDetector, OpticalFlow, Preprocessor, ProcessorWorker, Tracker
from renderer import OfflineRenderer


class MainWindow(QMainWindow):
    def __init__(self, app_dir: str) -> None:
        super().__init__()
        self.app_dir = app_dir
        self.setWindowTitle("BlobTracker")
        self.resize(1400, 860)

        presets_dir = os.path.join(self.app_dir, "presets")
        plugins_dir = os.path.join(self.app_dir, "plugins")
        self.param_store = ParamStore.instance(presets_dir=presets_dir)

        self._total_frames: int = 0
        self._current_frame: int = 0
        self._is_playing: bool = False
        self._loop_enabled: bool = False
        self._scrubbing: bool = False

        self.preview = PreviewRenderer()
        center = QWidget(self)
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)
        center_layout.addWidget(self.preview)

        self.playback_bar = QWidget(self)
        self.playback_bar.setObjectName("playback_bar")
        bar_layout = QHBoxLayout(self.playback_bar)
        bar_layout.setContentsMargins(4, 4, 4, 4)
        bar_layout.setSpacing(6)

        self.btn_skip_start = QPushButton("⏮")
        self.btn_play_pause = QPushButton("▶")
        self.btn_skip_end = QPushButton("⏭")
        self.btn_loop = QPushButton("↺")
        for btn in [self.btn_skip_start, self.btn_play_pause, self.btn_skip_end, self.btn_loop]:
            btn.setFlat(True)
            btn.setFixedSize(28, 28)
        self.btn_loop.setCheckable(True)

        self.btn_skip_start.clicked.connect(self._on_skip_start)
        self.btn_play_pause.clicked.connect(self._on_play_pause)
        self.btn_skip_end.clicked.connect(self._on_skip_end)
        self.btn_loop.toggled.connect(self._on_loop_toggle)

        self._timeline = QSlider(Qt.Orientation.Horizontal)
        self._timeline.setObjectName("timeline_slider")
        self._timeline.setMinimum(0)
        self._timeline.setMaximum(0)
        self._timeline.setValue(0)
        self._timeline.setSingleStep(1)
        self._timeline.setPageStep(10)
        self._timeline.sliderPressed.connect(self._on_scrub_start)
        self._timeline.sliderMoved.connect(self._on_scrub_move)
        self._timeline.sliderReleased.connect(self._on_scrub_end)

        self._timecode_label = QLabel("00:00 / 00:00")
        self._timecode_label.setObjectName("timecode_label")
        self._timecode_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._timecode_label.setFixedWidth(90)

        bar_layout.addWidget(self.btn_skip_start)
        bar_layout.addWidget(self.btn_play_pause)
        bar_layout.addWidget(self.btn_skip_end)
        bar_layout.addWidget(self.btn_loop)
        bar_layout.addWidget(self._timeline, 1)
        bar_layout.addWidget(self._timecode_label)

        center_layout.addWidget(self.playback_bar)
        self.setCentralWidget(center)
        self.playback_bar.hide()

        self.control_panel = ControlPanel(self.param_store, self)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.control_panel)

        self.frame_buffer = FrameBuffer(max_size=12, target_fps=float(self.param_store.get("input.target_fps")))
        self.capture_worker = CaptureWorker(self.frame_buffer)
        self.processor_worker = ProcessorWorker(self.frame_buffer, self.param_store)
        self.processor_worker.frame_packet_ready.connect(self.on_frame_packet)
        self._latest_packet = None
        self._render_packet_queue = deque()

        self.bbox_fx = BoundingBoxFX()
        self.label_fx = LabelFX()
        self.trail_fx = TrailFX()
        self.connection_fx = ConnectionLineFX(param_store=self.param_store)
        self.intra_blob_fx = IntraBlobFX(param_store=self.param_store)
        self.zoom_fx = ZoomInsetFX()
        self.base_frame_fx = BaseFrameFX()
        self.optical_flow = OpticalFlow()
        self.compositor = Compositor()
        self.creative_fx = CreativeFX()

        self.plugin_loader = PluginLoader(plugins_dir)
        self.project_manager = ProjectManager()
        self.exporter = VideoExporter()

        # Dedicated offline render pipeline so live preview and worker threads remain independent.
        self.offline_renderer = OfflineRenderer(
            self.param_store,
            Preprocessor(),
            BlobDetector(),
            Tracker(),
            {
                "base_frame_fx": BaseFrameFX(),
                "intra_blob_fx": IntraBlobFX(param_store=self.param_store),
                "optical_flow": OpticalFlow(),
                "connection_fx": ConnectionLineFX(param_store=self.param_store),
                "bbox_fx": BoundingBoxFX(),
                "label_fx": LabelFX(),
                "trail_fx": TrailFX(),
                "zoom_fx": ZoomInsetFX(),
                "creative_fx": self.creative_fx,
            },
            Compositor(),
        )

        self.hotkeys = HotkeyManager(self)
        self.hotkeys.setup_defaults(
            on_play_pause=self._on_play_pause,
            on_record_toggle=self.toggle_record,
            on_preset_browser=self.open_preset_browser,
            on_fullscreen=self.toggle_fullscreen,
        )

        self._last_render_time = time.time()
        self._fps = 0.0
        self._source_running = False
        self._source_paused = False
        self._current_file_source: Optional[VideoFileSource] = None
        self._render_mode_active = False
        self._render_finishing = False
        self._latest_blob_count = 0
        self._output_frame_timestamps = deque(maxlen=120)
        self._render_times = deque(maxlen=30)
        self._offline_render_total_frames = 0
        self._offline_render_active = False

        self._render_timer = QTimer(self)
        self._render_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._render_timer.timeout.connect(self.render_latest_packet)
        self._update_render_timer_interval(int(self.param_store.get("input.target_fps")))
        self._render_timer.start()

        self._build_menus()
        self._build_statusbar()
        self._wire_signals()
        self._load_stylesheet()
        self._load_plugins()

        self.processor_worker.start()

        if "default" in self.param_store.list_presets():
            self.param_store.load_preset("default")
            self._ensure_creative_filter_order()
            self.control_panel.refresh_filter_order()

    def _wire_signals(self) -> None:
        self.control_panel.start_source_requested.connect(self.start_selected_source)
        self.control_panel.stop_source_requested.connect(self.stop_source)
        self.control_panel.play_requested.connect(self.play_video)
        self.control_panel.pause_requested.connect(self.pause_video)
        self.control_panel.render_video_requested.connect(self.render_video)
        self.control_panel.offline_render_requested.connect(self.start_offline_render)
        self.control_panel.offline_render_cancel_requested.connect(self.cancel_offline_render)
        self.control_panel.hot_reload_plugins_requested.connect(self._load_plugins)
        self.param_store.param_changed.connect(self.on_param_changed)

        self.offline_renderer.progress.connect(self._on_offline_render_progress)
        self.offline_renderer.frame_preview.connect(self._update_render_thumb)
        self.offline_renderer.finished.connect(self._on_render_finished)
        self.offline_renderer.error.connect(self._on_render_error)
        self.capture_worker.end_of_file.connect(self._on_end_of_file)

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu("File")
        view_menu = self.menuBar().addMenu("View")
        effects_menu = self.menuBar().addMenu("Effects")
        help_menu = self.menuBar().addMenu("Help")

        open_file_action = QAction("Open Video...", self)
        open_file_action.triggered.connect(self.open_video_dialog)
        file_menu.addAction(open_file_action)

        save_project_action = QAction("Save Project...", self)
        save_project_action.triggered.connect(self.save_project)
        file_menu.addAction(save_project_action)

        load_project_action = QAction("Load Project...", self)
        load_project_action.triggered.connect(self.load_project)
        file_menu.addAction(load_project_action)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        fullscreen_action = QAction("Toggle Fullscreen", self)
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(fullscreen_action)

        preset_browser_action = QAction("Preset Browser", self)
        preset_browser_action.triggered.connect(self.open_preset_browser)
        view_menu.addAction(preset_browser_action)

        reload_plugins_action = QAction("Hot Reload Plugins", self)
        reload_plugins_action.triggered.connect(self._load_plugins)
        effects_menu.addAction(reload_plugins_action)

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def _build_statusbar(self) -> None:
        self.status_fps = QLabel("FPS: 0.0")
        self.status_blobs = QLabel("Blobs: 0")
        self.status_record = QLabel("REC: OFF")
        self.status_source = QLabel("Source: idle")

        self.statusBar().addPermanentWidget(self.status_fps)
        self.statusBar().addPermanentWidget(self.status_blobs)
        self.statusBar().addPermanentWidget(self.status_record)
        self.statusBar().addPermanentWidget(self.status_source)

        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self.refresh_status)
        self._status_timer.start(250)

    def _load_stylesheet(self) -> None:
        qss_path = os.path.join(self.app_dir, "style.qss")
        if os.path.exists(qss_path):
            with open(qss_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def _load_plugins(self) -> None:
        plugin_map = self.plugin_loader.load_plugins()
        for name, cls in plugin_map.items():
            self.creative_fx.register_filter(name, cls)
        offline_creative_fx = self.offline_renderer.effect_engine.get("creative_fx")
        if offline_creative_fx is not None and offline_creative_fx is not self.creative_fx:
            for name, cls in plugin_map.items():
                offline_creative_fx.register_filter(name, cls)

        self._ensure_creative_filter_order()
        self.control_panel.refresh_filter_order()

    def _ensure_creative_filter_order(self) -> None:
        if "creative.filter_order" not in self.param_store.params:
            return
        order = list(self.param_store.get("creative.filter_order"))
        available = self.creative_fx.available_filters()
        if not available:
            return

        merged = [name for name in order if name in available]
        for name in available:
            if name not in merged:
                merged.append(name)

        if merged != order:
            self.param_store.set("creative.filter_order", merged)

    def on_param_changed(self, key: str, value) -> None:
        if key == "input.target_fps":
            self.frame_buffer.set_target_fps(float(value))
            self._update_render_timer_interval(int(value))

        if key == "output.recording":
            if bool(value) and self._offline_render_active:
                self.param_store.set("output.recording", False)
                return
            if bool(value):
                self.start_recording()
            else:
                self.stop_recording()

    def open_video_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Video", "", "Media (*.mp4 *.mov *.avi *.png)")
        if not path:
            return
        self.param_store.set("input.source_type", "file")
        self.param_store.set("input.source_path", path)
        self.control_panel.file_path_edit.setText(path)
        self.control_panel.source_combo.setCurrentText("file")
        self.start_selected_source()

    def start_selected_source(self) -> None:
        source_type = str(self.param_store.get("input.source_type"))
        self.frame_buffer.set_target_fps(float(self.param_store.get("input.target_fps")))

        if source_type == "file":
            path = str(self.param_store.get("input.source_path"))
            if not path:
                QMessageBox.warning(self, "Input", "Select a video or image sequence path first.")
                return
            source = VideoFileSource(path, loop=False)
            self._current_file_source = source
            source_label = os.path.basename(path)
        else:
            index = int(self.param_store.get("input.webcam_index"))
            source = WebcamSource(device_index=index)
            self._current_file_source = None
            source_label = "webcam:{}".format(index)
            self.playback_bar.hide()
            self._total_frames = 0
            self._current_frame = 0

        ok = self.capture_worker.start(source)
        if not ok:
            QMessageBox.critical(self, "Input", "Unable to open source.")
            self._source_running = False
            self.status_source.setText("Source: failed")
            self.control_panel.update_playback_state("stopped")
            return

        self._source_running = True
        self._source_paused = False
        self._is_playing = True
        self.btn_play_pause.setText("⏸")

        if source_type == "file" and self._current_file_source is not None:
            self._total_frames = max(0, int(self._current_file_source.get_total_frames()))
            self._current_frame = 0
            self._timeline.setMaximum(max(0, self._total_frames - 1))
            self._timeline.setValue(0)
            self._update_timecode(0)
            self.playback_bar.show()

        self.control_panel.update_playback_state("playing")
        self.status_source.setText("Source: {}".format(source_label))

    def stop_source(self) -> None:
        self.capture_worker.stop()
        self._source_running = False
        self._source_paused = False
        self._is_playing = False
        self._current_file_source = None
        self._latest_packet = None
        self._render_packet_queue.clear()
        self._current_frame = 0
        self._timeline.blockSignals(True)
        self._timeline.setValue(0)
        self._timeline.blockSignals(False)
        self._update_timecode(0)
        self.btn_play_pause.setText("▶")
        if self._render_mode_active:
            self._render_mode_active = False
            self.exporter.stop()
        self.control_panel.update_playback_state("stopped")
        self.status_source.setText("Source: idle")

    def on_frame_packet(self, packet) -> None:
        if self._render_mode_active or self._render_finishing:
            self._render_packet_queue.append(packet)
            return
        self._latest_packet = packet

    def play_video(self) -> None:
        """Start playback or resume from pause."""
        if self._source_paused:
            self.capture_worker.resume()
            self._source_paused = False
            self._source_running = True
            self._is_playing = True
            self.btn_play_pause.setText("⏸")
            self.control_panel.update_playback_state("playing")
            self.status_source.setText("Source: playing")
        else:
            self.start_selected_source()

    def pause_video(self) -> None:
        """Pause playback (file sources only)."""
        if not self._source_running:
            return
        self.capture_worker.pause()
        self._source_paused = True
        self._source_running = False
        self._is_playing = False
        self.btn_play_pause.setText("▶")
        self.control_panel.update_playback_state("paused")
        self.status_source.setText("Source: paused")

    def _on_play_pause(self) -> None:
        if self._current_file_source is None:
            self.toggle_play_pause()
            return
        if self._is_playing:
            self._is_playing = False
            self.btn_play_pause.setText("▶")
            self._current_file_source.pause()
            self.capture_worker.pause()
            self._source_paused = True
            self._source_running = False
        else:
            self._is_playing = True
            self.btn_play_pause.setText("⏸")
            self._current_file_source.resume()
            self.capture_worker.resume()
            self._source_paused = False
            self._source_running = True

    def _on_skip_start(self) -> None:
        if self._current_file_source is None:
            return
        self._current_file_source.pause()
        self.capture_worker.pause()
        self._current_file_source.seek(0)
        self._current_frame = 0
        self._timeline.blockSignals(True)
        self._timeline.setValue(0)
        self._timeline.blockSignals(False)
        self._render_single_frame()

    def _on_skip_end(self) -> None:
        if self._current_file_source is None or self._total_frames <= 0:
            return
        self._current_file_source.pause()
        self.capture_worker.pause()
        last = max(0, self._total_frames - 1)
        self._current_file_source.seek(last)
        self._current_frame = last
        self._timeline.blockSignals(True)
        self._timeline.setValue(last)
        self._timeline.blockSignals(False)
        self._render_single_frame()

    def _on_loop_toggle(self, checked: bool) -> None:
        self._loop_enabled = bool(checked)
        if self._current_file_source is not None:
            self._current_file_source.set_loop(bool(checked))

    def _on_scrub_start(self) -> None:
        if self._current_file_source is None:
            return
        self._scrubbing = True
        self._current_file_source.pause()
        self.capture_worker.pause()

    def _on_scrub_move(self, value: int) -> None:
        if self._current_file_source is None:
            return
        self._current_frame = int(value)
        self._current_file_source.seek(self._current_frame)
        self._render_single_frame()
        self._update_timecode(self._current_frame)

    def _on_scrub_end(self) -> None:
        self._scrubbing = False
        if self._current_file_source is None:
            return
        if self._is_playing:
            self._current_file_source.resume()
            self.capture_worker.resume()

    def _render_single_frame(self) -> None:
        if self._current_file_source is None:
            return

        self.frame_buffer.clear()
        self._render_packet_queue.clear()
        self._latest_packet = None

        ok, frame = self._current_file_source.read()
        if not ok or frame is None:
            return

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

        binary, used_scale = self.processor_worker.preprocessor.run(
            frame,
            threshold=threshold,
            blur_radius=blur,
            scale=process_scale,
        )
        detections = self.processor_worker.detector.run(
            binary,
            scale=used_scale,
            min_area=min_area,
            max_area=max_area,
            max_count=max_count,
            mode=detector_mode,
            min_circularity=min_circularity,
            simple_min_threshold=simple_min_threshold,
            simple_max_threshold=simple_max_threshold,
        )
        blobs = self.processor_worker.tracker.update(
            detections,
            max_distance=max(10.0, 100.0 * (1.0 - min(0.95, smoothing))),
            trail_length=trail_length,
            max_missing=max_disappeared,
            smoothing_alpha=smooth_alpha,
        )

        from models import FramePacket

        packet = FramePacket(
            raw_frame=frame,
            blobs=blobs,
            timestamp=time.perf_counter(),
            frame_index=max(1, self._current_frame),
        )
        self._process_packet(packet)
        self._update_timecode(self._current_frame)

    def _update_timecode(self, frame_index: int) -> None:
        if self._current_file_source is not None:
            fps = float(self._current_file_source.get_fps() or 24.0)
        else:
            fps = 24.0

        def _fmt(fi: int) -> str:
            secs = int(float(max(0, fi)) / max(0.001, fps))
            mins, sec = divmod(secs, 60)
            return "{:02d}:{:02d}".format(mins, sec)

        self._timecode_label.setText("{} / {}".format(_fmt(frame_index), _fmt(self._total_frames)))

    def _on_end_of_file(self) -> None:
        self._is_playing = False
        self._source_running = False
        self._source_paused = False
        self.btn_play_pause.setText("▶")
        last = max(0, self._total_frames - 1)
        self._timeline.blockSignals(True)
        self._timeline.setValue(last)
        self._timeline.blockSignals(False)
        self._update_timecode(last)

    def _set_playback_controls_enabled(self, enabled: bool) -> None:
        state = bool(enabled)
        self.btn_skip_start.setEnabled(state)
        self.btn_play_pause.setEnabled(state)
        self.btn_skip_end.setEnabled(state)
        self.btn_loop.setEnabled(state)
        self._timeline.setEnabled(state)

    def render_video(self) -> None:
        """Play the entire file from start to finish and write every processed frame to the export path."""
        source_type = str(self.param_store.get("input.source_type"))
        if source_type != "file":
            QMessageBox.warning(self, "Render", "Render is only available for file sources.")
            return

        source_path = str(self.param_store.get("input.source_path"))
        if not source_path:
            QMessageBox.warning(self, "Render", "No file selected.")
            return

        export_path = str(self.param_store.get("output.export_path"))
        if not export_path:
            QMessageBox.warning(self, "Render", "No export path set.")
            return

        # Peek at the video to obtain native dimensions/fps before starting
        size: tuple = (0, 0)
        fps = float(self.param_store.get("input.target_fps"))
        try:
            cap = cv2.VideoCapture(source_path)
            if cap.isOpened():
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                native_fps = cap.get(cv2.CAP_PROP_FPS)
                if w > 0 and h > 0:
                    size = (w, h)
                if native_fps > 0:
                    fps = native_fps
            cap.release()
        except Exception:
            pass

        if size == (0, 0):
            QMessageBox.warning(self, "Render", "Cannot read video dimensions.")
            return

        # Stop any current playback cleanly
        if self._source_running or self._source_paused:
            self.capture_worker.stop()
            self._source_running = False
            self._source_paused = False

        # Open the file source in non-loop mode so the thread exits naturally at end
        source = VideoFileSource(source_path, loop=False)
        self._current_file_source = source
        self.frame_buffer.set_target_fps(fps)
        self._latest_packet = None
        self._render_packet_queue.clear()
        ok = self.capture_worker.start(source)
        if not ok:
            QMessageBox.critical(self, "Render", "Cannot open video file.")
            return

        # Build the output file path
        fmt = str(self.param_store.get("output.format"))
        if fmt == "png_seq":
            target = export_path
        elif fmt == "prores":
            target = export_path if export_path.lower().endswith(".mov") else "{}.mov".format(export_path)
        else:
            target = export_path if export_path.lower().endswith(".mp4") else "{}.mp4".format(export_path)

        self.exporter.stop()  # ensure clean state
        self.exporter.start(target, fps=fps, size=size, fmt=fmt)

        self._source_running = True
        self._source_paused = False
        self._is_playing = True
        self._render_mode_active = True
        self._render_finishing = False
        self._set_playback_controls_enabled(False)
        self.control_panel.update_playback_state("playing")
        self.status_source.setText("Source: rendering → {}".format(os.path.basename(target)))

    def _finish_render(self) -> None:
        if not self._render_mode_active:
            return  # already finished or cancelled
        self._render_mode_active = False
        self._render_finishing = False
        self.exporter.stop()
        self.capture_worker.stop()
        self._source_running = False
        self._source_paused = False
        self._is_playing = False
        self._current_file_source = None
        self._set_playback_controls_enabled(True)
        self.control_panel.update_playback_state("stopped")
        self.status_source.setText("Source: idle")
        QMessageBox.information(self, "Render Complete", "Video rendered successfully.")

    def _update_render_timer_interval(self, fps: int) -> None:
        fps = max(1, int(fps))
        interval_ms = max(1, int(1000 / fps))
        self._render_timer.setInterval(interval_ms)

    def render_latest_packet(self) -> None:
        if self._render_mode_active or self._render_finishing:
            processed_any = False
            while self._render_packet_queue:
                packet = self._render_packet_queue.popleft()
                self._process_packet(packet)
                processed_any = True

            if not processed_any:
                # Detect render-mode completion only after queued packets are drained.
                if (
                    self._render_mode_active
                    and not self._render_finishing
                    and self.capture_worker.video_ended
                    and (
                        self.capture_worker._thread is None
                        or not self.capture_worker._thread.is_alive()
                    )
                ):
                    self._render_finishing = True
                    QTimer.singleShot(2000, self._finish_render)
            return

        packet = self._latest_packet
        if packet is None:
            return
        self._latest_packet = None
        self._process_packet(packet)

    def _process_packet(self, packet) -> None:
        if packet is None:
            return

        frame = packet.raw_frame.copy()
        frame = self.base_frame_fx.apply(
            frame,
            desaturate=float(self.param_store.get("frame_desaturate")),
            grain=float(self.param_store.get("frame_grain")),
            vignette=float(self.param_store.get("frame_vignette")),
        )
        blobs = packet.blobs
        self._latest_blob_count = len(blobs)

        frame = self.intra_blob_fx.apply(frame, blobs)

        if bool(self.param_store.get("effects.flow_enabled")):
            frame = self.optical_flow.overlay(frame, enabled=True)
        else:
            frame = self.optical_flow.overlay(frame, enabled=False)

        layer = frame.copy()
        if bool(self.param_store.get("connection_enabled")) and len(blobs) >= 2:
            layer = self.connection_fx.apply(layer, blobs)

        if bool(self.param_store.get("effects.trail_enabled")):
            layer = self.trail_fx.apply(
                layer,
                blobs,
                tuple(self.param_store.get("effects.trail_color")),
                float(self.param_store.get("effects.trail_alpha")),
                int(self.param_store.get("effects.trail_thickness")),
            )

        if bool(self.param_store.get("effects.bbox_enabled")):
            layer = self.bbox_fx.apply(
                layer,
                blobs,
                tuple(self.param_store.get("effects.bbox_color")),
                int(self.param_store.get("effects.bbox_thickness")),
                str(self.param_store.get("effects.bbox_corner_style")),
            )

        if bool(self.param_store.get("effects.label_enabled")):
            layer = self.label_fx.apply(
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

        if bool(self.param_store.get("effects.zoom_enabled")):
            layer = self.zoom_fx.apply(
                layer,
                blobs,
                int(self.param_store.get("effects.zoom_blob_id")),
                float(self.param_store.get("effects.zoom_factor")),
                (220, 160),
                str(self.param_store.get("effects.zoom_corner")),
            )

        if bool(self.param_store.get("creative.enabled")):
            self._ensure_creative_filter_order()
            filter_order: List[str] = list(self.param_store.get("creative.filter_order"))
            # Sync individual param store controls to unified filter_params dict
            filter_params: Dict[str, Dict[str, float]] = self.creative_fx.sync_params_from_store(self.param_store)
            if not filter_params:
                filter_params = dict(self.param_store.get("creative.filter_params"))
            layer = self.creative_fx.apply_chain(layer, filter_order, filter_params, param_store=self.param_store)

        blend_mode = str(self.param_store.get("effects.blend_mode"))
        if blend_mode == "normal":
            final_frame = layer
        else:
            final_frame = self.compositor.blend(frame, layer, blend_mode)

        now = time.time()
        self._output_frame_timestamps.append(now)
        dt = now - self._last_render_time
        if dt > 0:
            self._fps = 0.85 * self._fps + 0.15 * (1.0 / dt)
        self._last_render_time = now
        self._render_times.append(time.perf_counter())

        self.preview.update_frame(final_frame)

        if self._current_file_source is not None and not self._scrubbing:
            self._current_frame = int(self._current_file_source.get_current_frame())
            self._timeline.blockSignals(True)
            self._timeline.setValue(max(0, min(self._timeline.maximum(), self._current_frame)))
            self._timeline.blockSignals(False)
            self._update_timecode(self._current_frame)

        if self.exporter.recording:
            self.exporter.push_frame(final_frame.copy())

    def _measured_output_fps(self) -> float:
        if len(self._output_frame_timestamps) < 2:
            return 0.0
        first = float(self._output_frame_timestamps[0])
        last = float(self._output_frame_timestamps[-1])
        if last <= first:
            return 0.0
        frame_count = len(self._output_frame_timestamps) - 1
        return float(frame_count / (last - first))

    def refresh_status(self) -> None:
        if (
            self.exporter.recording
            and not self._render_mode_active
            and not self._render_finishing
            and str(self.param_store.get("input.source_type")) == "file"
            and self.capture_worker.video_ended
        ):
            self.stop_recording()
            self.param_store.set("output.recording", False)
            self.status_source.setText("Source: file ended")

        rec_indicator = "REC: ON" if self.exporter.is_recording else "REC: OFF"
        rec_dot = "● REC" if self.exporter.recording else "○"
        if len(self._render_times) >= 2 and self._render_times[-1] > self._render_times[0]:
            fps = (len(self._render_times) - 1) / (self._render_times[-1] - self._render_times[0])
        else:
            fps = 0.0
        self._fps = float(fps)

        scale = float(self.param_store.get("process_scale")) if "process_scale" in self.param_store.params else 1.0
        self.statusBar().showMessage(
            "FPS: {:.1f}  |  Blobs: {}  |  Scale: {:.2f}  |  {}".format(
                self._fps,
                self._latest_blob_count,
                scale,
                rec_dot,
            )
        )
        self.status_fps.setText(
            "FPS: {:.1f} | Blobs: {} | {}".format(self._fps, self._latest_blob_count, rec_indicator)
        )
        self.status_blobs.setText("Blobs: {}".format(self._latest_blob_count))
        self.status_record.setText(rec_indicator)
        if hasattr(self.control_panel, "set_performance_fps"):
            self.control_panel.set_performance_fps(self._fps)
        if self.exporter.is_recording:
            self.status_record.setStyleSheet("color: #00e5ff;")
        else:
            self.status_record.setStyleSheet("color: #f0f0f0;")

    def start_recording(self) -> None:
        if self.exporter.is_recording:
            return

        path = str(self.param_store.get("output.export_path"))
        if not path:
            QMessageBox.warning(self, "Output", "Set an export path first.")
            self.param_store.set("output.recording", False)
            return

        fmt = str(self.param_store.get("output.format"))
        if fmt == "png_seq":
            target = path
        elif fmt == "prores":
            target = path if path.lower().endswith(".mov") else "{}.mov".format(path)
        else:
            target = path if path.lower().endswith(".mp4") else "{}.mp4".format(path)

        if self.preview._last_frame is None:
            QMessageBox.warning(self, "Output", "No frames available for export yet.")
            self.param_store.set("output.recording", False)
            return

        h, w = self.preview._last_frame.shape[:2]
        source_fps = 0.0
        source = self.capture_worker.source
        if source is not None and hasattr(source, "get_fps"):
            source_fps = float(getattr(source, "get_fps")())

        source_type = str(self.param_store.get("input.source_type"))
        measured_fps = self._measured_output_fps()
        if source_type == "file":
            export_fps = source_fps if source_fps > 0 else 25.0
        else:
            export_fps = measured_fps if measured_fps > 0 else 25.0

        self.exporter.start_recording(target, fps=export_fps, width=w, height=h, fmt=fmt)
        self._set_playback_controls_enabled(False)

    def stop_recording(self) -> None:
        self.exporter.stop()
        if not self._offline_render_active:
            self._set_playback_controls_enabled(True)

    def start_offline_render(self, output_path: str) -> None:
        if self._offline_render_active:
            return

        source_type = str(self.param_store.get("input.source_type"))
        if source_type != "file":
            QMessageBox.warning(self, "Render to File", "Render requires a video file source.")
            return

        source_path = str(self.param_store.get("input.source_path"))
        if not source_path or not os.path.exists(source_path):
            QMessageBox.warning(self, "Render to File", "Select a valid source video file first.")
            return

        if self.exporter.recording:
            QMessageBox.warning(self, "Render to File", "Stop live recording before starting offline render.")
            return

        output_path = output_path.strip()
        if not output_path:
            QMessageBox.warning(self, "Render to File", "Set an output path first.")
            return
        if not output_path.lower().endswith(".mp4"):
            output_path = "{}.mp4".format(output_path)

        cap = cv2.VideoCapture(source_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) if cap.isOpened() else 0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) if cap.isOpened() else 0
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) if cap.isOpened() else 0
        cap.release()

        estimated_gb = 0.0
        if total_frames > 0 and width > 0 and height > 0:
            estimated_gb = (float(total_frames) * float(width) * float(height) * 3.0) / float(1024**3)
        if estimated_gb > 2.0:
            answer = QMessageBox.question(
                self,
                "Render to File",
                "Estimated temp space: {:.1f} GB. Continue?".format(estimated_gb),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        self._offline_render_total_frames = total_frames
        self._offline_render_active = True
        self._set_playback_controls_enabled(False)
        self.control_panel.set_offline_render_running(True)
        self.control_panel.set_offline_render_progress(0, "Frame 0 / {}".format(max(0, total_frames)))
        self.control_panel.set_offline_render_status("Starting...")
        self.control_panel.record_btn.setEnabled(False)
        self.status_source.setText("Source: offline rendering")

        self.offline_renderer.start_render(source_path, output_path)

    def cancel_offline_render(self) -> None:
        if not self._offline_render_active:
            return
        self.offline_renderer.cancel()
        self.control_panel.set_offline_render_status("Cancelling...")

    def _on_offline_render_progress(self, percent: int) -> None:
        total = max(1, int(self._offline_render_total_frames))
        frame_num = int(round((max(0, min(100, int(percent))) / 100.0) * float(total)))
        self.control_panel.set_offline_render_progress(percent, "Frame {} / {}".format(frame_num, total))

    def _update_render_thumb(self, frame) -> None:
        self.control_panel.update_render_thumbnail(frame)

    def _on_render_finished(self, path: str) -> None:
        self._offline_render_active = False
        self.control_panel.set_offline_render_running(False)
        self.control_panel.set_offline_render_progress(100)
        self.control_panel.set_offline_render_status("Done: {}".format(os.path.basename(path)))
        self.control_panel.record_btn.setEnabled(True)
        if not self.exporter.recording:
            self._set_playback_controls_enabled(True)
        self.status_source.setText("Source: idle")
        QMessageBox.information(self, "Render to File", "Render complete. Saved to: {}".format(path))

    def _on_render_error(self, msg: str) -> None:
        self._offline_render_active = False
        self.control_panel.set_offline_render_running(False)
        if str(msg).strip().lower() == "render cancelled":
            self.control_panel.set_offline_render_status("Cancelled")
        else:
            self.control_panel.set_offline_render_status("Error")
        self.control_panel.record_btn.setEnabled(True)
        if not self.exporter.recording:
            self._set_playback_controls_enabled(True)
        self.status_source.setText("Source: idle")
        QMessageBox.warning(self, "Render to File", str(msg))

    def save_project(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save Project", "project.btrack", "BlobTracker Project (*.btrack)")
        if not path:
            return
        if not path.endswith(".btrack"):
            path += ".btrack"

        self.project_manager.save_project(
            path=path,
            source_path=str(self.param_store.get("input.source_path")),
            params=self.param_store.to_dict(),
            filter_chain=list(self.param_store.get("creative.filter_order")),
        )

    def load_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load Project", "", "BlobTracker Project (*.btrack)")
        if not path:
            return

        payload = self.project_manager.load_project(path)
        params = payload.get("params", {})
        self.param_store.apply_dict(params)
        self._ensure_creative_filter_order()
        self.control_panel.refresh_filter_order()
        self.control_panel.refresh_presets_list()

    def open_preset_browser(self) -> None:
        dialog = PresetBrowserDialog(self.param_store, self)
        if dialog.exec() and dialog.selected:
            self.param_store.load_preset(dialog.selected)
            self._ensure_creative_filter_order()
            self.control_panel.refresh_filter_order()
            self.control_panel.refresh_presets_list()

    def toggle_record(self) -> None:
        state = bool(self.param_store.get("output.recording"))
        self.param_store.set("output.recording", not state)
        self.control_panel.record_btn.setText("Stop Record" if not state else "Start Record")

    def toggle_play_pause(self) -> None:
        self._on_play_pause()

    def toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def show_about(self) -> None:
        QMessageBox.information(
            self,
            "About",
            "BlobTracker\nReal-time blob tracking and creative overlays.",
        )

    def closeEvent(self, event) -> None:
        if self._offline_render_active:
            self.offline_renderer.cancel()
        self.stop_source()
        self.stop_recording()
        self.processor_worker.stop()
        super().closeEvent(event)


def main() -> None:
    app = QApplication(sys.argv)
    app_dir = os.path.dirname(os.path.abspath(__file__))
    window = MainWindow(app_dir=app_dir)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
