from __future__ import annotations

import json
import os
import platform
import subprocess
import threading
import time
from queue import Empty, Queue
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout


class PreviewRenderer(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet("background: #060708;")
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setMinimumSize(640, 360)
        self.label.setText("NO SOURCE")
        self.label.setStyleSheet(
            "QLabel { background: transparent; color: #1a2535;"
            " font-family: 'JetBrains Mono','Courier New',monospace;"
            " font-size: 13px; letter-spacing: 4px; }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        self._last_frame: Optional[np.ndarray] = None
        self._has_content = False

    def update_frame(self, frame_bgr: np.ndarray) -> None:
        self._last_frame = frame_bgr
        if not self._has_content:
            self._has_content = True
            self.label.setStyleSheet("QLabel { background: transparent; }")
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w, c = rgb.shape
        image = QImage(rgb.data, w, h, c * w, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(image)
        scaled = pix.scaled(
            self.label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        self.label.setPixmap(scaled)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._last_frame is not None:
            self.update_frame(self._last_frame)


class VideoExporter:
    def __init__(self) -> None:
        self.writer: Optional[cv2.VideoWriter] = None
        self.export_queue: "Queue[np.ndarray]" = Queue()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.recording: bool = False
        self._png_seq = False
        self._prores = False
        self._seq_dir = ""
        self._seq_index = 0
        self._ffmpeg_proc: Optional[subprocess.Popen] = None
        self._active_output_path: Optional[str] = None
        self._pending_start: bool = False
        self._pending_path: str = ""
        self._pending_size: Tuple[int, int] = (0, 0)
        self._pending_fmt: str = "mp4"
        self._init_fps: float = 25.0
        self._frame_times: list[float] = []
        self._measured_fps: float = 0.0
        self._fps_window: int = 30
        self._startup_warmup_frames: int = 30
        self._startup_buffer: list[np.ndarray] = []

    def _reset_queue(self) -> None:
        while not self.export_queue.empty():
            try:
                self.export_queue.get_nowait()
            except Empty:
                break

    def _measure_fps(self) -> float:
        now = time.perf_counter()
        self._frame_times.append(now)
        max_len = self._fps_window + 1
        if len(self._frame_times) > max_len:
            self._frame_times = self._frame_times[-max_len:]

        if len(self._frame_times) < 8:
            self._measured_fps = float(max(1.0, self._init_fps))
            return self._measured_fps

        intervals = np.diff(np.array(self._frame_times, dtype=np.float64))
        valid = intervals[(intervals > 0.0) & (intervals < 1.0)]
        if valid.size == 0:
            self._measured_fps = float(max(1.0, self._init_fps))
            return self._measured_fps

        mean_interval = float(valid.mean())
        if mean_interval <= 0.0:
            self._measured_fps = float(max(1.0, self._init_fps))
            return self._measured_fps

        measured = float(1.0 / mean_interval)
        self._measured_fps = measured if measured > 2.0 else float(max(2.0, self._init_fps))
        return self._measured_fps

    def _get_fourcc_and_ext(self, requested_path: str) -> Tuple[int, str]:
        if platform.system() == "Windows":
            return cv2.VideoWriter_fourcc(*"mp4v"), os.path.splitext(requested_path)[0] + ".mp4"

        fourcc = cv2.VideoWriter_fourcc(*"avc1")
        path = os.path.splitext(requested_path)[0] + ".mp4"
        test = cv2.VideoWriter(path, fourcc, 24, (64, 64))
        if test.isOpened():
            test.release()
            try:
                os.remove(path)
            except Exception:
                pass
            return fourcc, path

        test.release()
        return cv2.VideoWriter_fourcc(*"XVID"), os.path.splitext(requested_path)[0] + ".avi"

    def _open_pending_writer(self) -> None:
        if self._png_seq:
            self._seq_dir = self._pending_path
            os.makedirs(self._seq_dir, exist_ok=True)
            self._pending_start = False
            print("[VideoExporter] codec=png_seq path={}".format(self._seq_dir))
            return

        if self._prores:
            cmd = [
                "ffmpeg",
                "-y",
                "-f",
                "rawvideo",
                "-pixel_format",
                "bgr24",
                "-video_size",
                "{}x{}".format(self._pending_size[0], self._pending_size[1]),
                "-framerate",
                str(float(max(1.0, self._measured_fps))),
                "-i",
                "-",
                "-c:v",
                "prores_ks",
                "-profile:v",
                "3",
                self._pending_path,
            ]
            try:
                self._ffmpeg_proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
                self._active_output_path = self._pending_path
                print("[VideoExporter] codec=prores_ks fps={:.2f} path={}".format(self._measured_fps, self._pending_path))
                self._pending_start = False
                return
            except FileNotFoundError:
                self._prores = False

        fourcc, final_path = self._get_fourcc_and_ext(self._pending_path)
        self._active_output_path = final_path
        self.writer = cv2.VideoWriter(
            final_path,
            fourcc,
            float(max(1.0, self._measured_fps)),
            self._pending_size,
        )
        print("[VideoExporter] fps={:.2f} path={}".format(self._measured_fps, final_path))
        self._pending_start = False

    def start_recording(self, output_path: str, fps: float, width: int, height: int, fmt: str = "mp4") -> None:
        self.stop_recording()
        self._pending_size = (int(width), int(height))
        self._pending_path = output_path
        self._pending_fmt = fmt
        self._png_seq = fmt == "png_seq"
        self._prores = fmt == "prores"
        self._pending_start = True
        self._init_fps = float(max(1.0, fps))
        self._measured_fps = self._init_fps
        self._frame_times = []
        self._startup_buffer = []
        self._seq_index = 0
        self._active_output_path = None
        self._reset_queue()

        self._stop_event.clear()
        self.recording = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def push_frame(self, frame: np.ndarray) -> None:
        if not self.recording:
            return
        try:
            self.export_queue.put(frame)
        except Exception:
            return

    def _run(self) -> None:
        while not self._stop_event.is_set() or not self.export_queue.empty():
            try:
                frame = self.export_queue.get(timeout=0.1)
            except Empty:
                continue

            self._measure_fps()

            if self._pending_start:
                self._startup_buffer.append(frame)
                if len(self._startup_buffer) < self._startup_warmup_frames:
                    continue

                self._open_pending_writer()
                for buffered_frame in self._startup_buffer:
                    if self._png_seq:
                        filename = os.path.join(self._seq_dir, "frame_{:06d}.png".format(self._seq_index))
                        self._seq_index += 1
                        cv2.imwrite(filename, buffered_frame)
                    elif self._prores and self._ffmpeg_proc and self._ffmpeg_proc.stdin:
                        self._ffmpeg_proc.stdin.write(buffered_frame.tobytes())
                    elif self.writer is not None:
                        self.writer.write(buffered_frame)
                self._startup_buffer = []
                continue

            if self._png_seq:
                filename = os.path.join(self._seq_dir, "frame_{:06d}.png".format(self._seq_index))
                self._seq_index += 1
                cv2.imwrite(filename, frame)
            elif self._prores and self._ffmpeg_proc and self._ffmpeg_proc.stdin:
                self._ffmpeg_proc.stdin.write(frame.tobytes())
            elif self.writer is not None:
                self.writer.write(frame)

        if self._pending_start and self._startup_buffer:
            self._open_pending_writer()
            for buffered_frame in self._startup_buffer:
                if self._png_seq:
                    filename = os.path.join(self._seq_dir, "frame_{:06d}.png".format(self._seq_index))
                    self._seq_index += 1
                    cv2.imwrite(filename, buffered_frame)
                elif self._prores and self._ffmpeg_proc and self._ffmpeg_proc.stdin:
                    self._ffmpeg_proc.stdin.write(buffered_frame.tobytes())
                elif self.writer is not None:
                    self.writer.write(buffered_frame)
            self._startup_buffer = []

    def stop_recording(self) -> None:
        self.recording = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=30)
        if self._startup_buffer and not self._pending_start:
            for buffered_frame in self._startup_buffer:
                if self._png_seq:
                    filename = os.path.join(self._seq_dir, "frame_{:06d}.png".format(self._seq_index))
                    self._seq_index += 1
                    cv2.imwrite(filename, buffered_frame)
                elif self._prores and self._ffmpeg_proc and self._ffmpeg_proc.stdin:
                    self._ffmpeg_proc.stdin.write(buffered_frame.tobytes())
                elif self.writer is not None:
                    self.writer.write(buffered_frame)
        if self.writer is not None:
            self.writer.release()
            self.writer = None
        if self._ffmpeg_proc is not None:
            if self._ffmpeg_proc.stdin:
                self._ffmpeg_proc.stdin.close()
            try:
                self._ffmpeg_proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._ffmpeg_proc.kill()
            self._ffmpeg_proc = None
        self._startup_buffer = []
        self._pending_start = False
        self._thread = None
        self._stop_event.clear()

    # Backward-compatible wrappers for existing callers.
    def start(self, path: str, fps: float, size: Tuple[int, int], fmt: str = "mp4") -> None:
        self.start_recording(output_path=path, fps=fps, width=size[0], height=size[1], fmt=fmt)

    def write(self, frame: np.ndarray) -> None:
        self.push_frame(frame)

    def stop(self) -> None:
        self.stop_recording()

    @property
    def is_recording(self) -> bool:
        return self.recording


class ProjectManager:
    def save_project(self, path: str, source_path: str, params: Dict[str, Any], filter_chain) -> None:
        payload = {
            "source_path": source_path,
            "params": params,
            "filter_chain": list(filter_chain),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def load_project(self, path: str) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
