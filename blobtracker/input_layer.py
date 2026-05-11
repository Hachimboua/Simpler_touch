from __future__ import annotations

import glob
import os
import threading
import time
from abc import ABC, abstractmethod
from queue import Empty, Full, Queue
from typing import List, Optional, Tuple

import cv2
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal


class FrameSource(ABC):
    @abstractmethod
    def open(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        raise NotImplementedError

    @abstractmethod
    def release(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def is_opened(self) -> bool:
        raise NotImplementedError


class VideoFileSource(FrameSource):
    def __init__(self, path: str, loop: bool = True) -> None:
        self.path = path
        self.loop = loop
        self.capture: Optional[cv2.VideoCapture] = None
        self.sequence_files: List[str] = []
        self.sequence_index = 0
        self._is_sequence = False
        self._paused = False
        self._current_frame = 0

    def _load_sequence(self) -> bool:
        if os.path.isdir(self.path):
            candidates = sorted(
                glob.glob(os.path.join(self.path, "*.png"))
                + glob.glob(os.path.join(self.path, "*.jpg"))
                + glob.glob(os.path.join(self.path, "*.jpeg"))
            )
        elif self.path.lower().endswith(".png"):
            base_dir = os.path.dirname(self.path) or "."
            candidates = sorted(glob.glob(os.path.join(base_dir, "*.png")))
        else:
            candidates = []

        if not candidates:
            return False

        self.sequence_files = candidates
        self.sequence_index = 0
        self._is_sequence = True
        return True

    def open(self) -> bool:
        if self._load_sequence():
            return True

        self.capture = cv2.VideoCapture(self.path)
        self._is_sequence = False
        return bool(self.capture and self.capture.isOpened())

    def seek_to_start(self) -> None:
        if self._is_sequence:
            self.sequence_index = 0
            self._current_frame = 0
        elif self.capture:
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self._current_frame = 0

    def seek(self, frame_index: int) -> None:
        fi = max(0, int(frame_index))
        if self._is_sequence:
            if self.sequence_files:
                self.sequence_index = min(len(self.sequence_files) - 1, fi)
            else:
                self.sequence_index = 0
            self._current_frame = self.sequence_index
            return
        if self.capture:
            self.capture.set(cv2.CAP_PROP_POS_FRAMES, float(fi))
            self._current_frame = fi

    def get_total_frames(self) -> int:
        if self._is_sequence:
            return len(self.sequence_files)
        if self.capture:
            return int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
        return 0

    def get_current_frame(self) -> int:
        if self._is_sequence:
            return int(self._current_frame)
        if self.capture:
            return int(self.capture.get(cv2.CAP_PROP_POS_FRAMES))
        return int(self._current_frame)

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def set_loop(self, enabled: bool):
        self.loop = bool(enabled)

    def get_fps(self) -> float:
        if self._is_sequence:
            return 25.0
        if self.capture:
            fps = self.capture.get(cv2.CAP_PROP_FPS)
            return float(fps) if fps > 0 else 25.0
        return 25.0

    def get_size(self) -> Tuple[int, int]:
        """Return (width, height), or (0, 0) if unavailable."""
        if self._is_sequence:
            if self.sequence_files:
                img = cv2.imread(self.sequence_files[0])
                if img is not None:
                    return img.shape[1], img.shape[0]
            return 0, 0
        if self.capture:
            w = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            return w, h
        return 0, 0

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        if self._paused:
            return False, None

        if self._is_sequence:
            if self.sequence_index >= len(self.sequence_files):
                if self.loop:
                    self.sequence_index = 0
                    self._current_frame = 0
                else:
                    return False, None
            frame_path = self.sequence_files[self.sequence_index]
            self.sequence_index += 1
            self._current_frame = self.sequence_index
            frame = cv2.imread(frame_path)
            return frame is not None, frame

        if not self.capture:
            return False, None
        ok, frame = self.capture.read()
        if not ok:
            if self.loop:
                self.capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self._current_frame = 0
                ok, frame = self.capture.read()
            else:
                return False, None
        if ok:
            self._current_frame = int(self.capture.get(cv2.CAP_PROP_POS_FRAMES))
        return ok, frame

    def release(self) -> None:
        if self.capture is not None:
            self.capture.release()
            self.capture = None

    def is_opened(self) -> bool:
        if self._is_sequence:
            return bool(self.sequence_files)
        return bool(self.capture and self.capture.isOpened())


class WebcamSource(FrameSource):
    def __init__(self, device_index: int = 0) -> None:
        self.device_index = device_index
        self.capture: Optional[cv2.VideoCapture] = None

    def open(self) -> bool:
        self.capture = cv2.VideoCapture(self.device_index)
        return bool(self.capture and self.capture.isOpened())

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        if not self.capture:
            return False, None
        return self.capture.read()

    def release(self) -> None:
        if self.capture is not None:
            self.capture.release()
            self.capture = None

    def is_opened(self) -> bool:
        return bool(self.capture and self.capture.isOpened())

    def get_fps(self) -> float:
        if self.capture:
            measured = self.capture.get(cv2.CAP_PROP_FPS)
            return float(measured) if measured > 0 else 25.0
        return 25.0

    def seek(self, frame_index: int):
        return

    def get_total_frames(self) -> int:
        return 0

    def get_current_frame(self) -> int:
        return 0

    def pause(self):
        return

    def resume(self):
        return

    def set_loop(self, enabled: bool):
        return


class FrameBuffer:
    def __init__(self, max_size: int = 8, target_fps: float = 30.0) -> None:
        self.queue: "Queue[np.ndarray]" = Queue(maxsize=max_size)
        self.target_fps = target_fps
        self._lock = threading.Lock()

    def set_target_fps(self, fps: float) -> None:
        with self._lock:
            self.target_fps = max(1.0, fps)

    def put(self, frame: np.ndarray, timeout: float = 0.01) -> bool:
        try:
            self.queue.put(frame, timeout=timeout)
            return True
        except Full:
            return False

    def get(self, timeout: float = 0.05) -> Optional[np.ndarray]:
        try:
            return self.queue.get(timeout=timeout)
        except Empty:
            return None

    def clear(self) -> None:
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except Empty:
                break

    def frame_interval(self) -> float:
        with self._lock:
            return 1.0 / max(1.0, self.target_fps)


class CaptureWorker(QObject):
    end_of_file = pyqtSignal()

    def __init__(self, buffer: FrameBuffer) -> None:
        super().__init__()
        self.buffer = buffer
        self.source: Optional[FrameSource] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # not paused by default
        self._paused = False
        self._is_playing = False
        self.video_ended: bool = False

    def start(self, source: FrameSource) -> bool:
        self.stop()
        self.source = source
        self.buffer.clear()
        self.video_ended = False

        if not self.source.open():
            self.source = None
            return False

        self._stop_event.clear()
        self._pause_event.set()  # always start unpaused
        self._paused = False
        self._is_playing = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return True

    def pause(self) -> None:
        self._pause_event.clear()
        self._paused = True
        self._is_playing = False
        if self.source and hasattr(self.source, "pause"):
            self.source.pause()

    def resume(self) -> None:
        self._pause_event.set()
        self._paused = False
        self._is_playing = True
        if self.source and hasattr(self.source, "resume"):
            self.source.resume()

    def _run(self) -> None:
        while not self._stop_event.is_set():
            if self._paused:
                time.sleep(0.01)
                continue

            # Pause support: block here while paused, re-check stop every 100 ms
            if not self._pause_event.wait(timeout=0.1):
                continue

            if not self.source or not self.source.is_opened():
                break

            ok, frame = self.source.read()
            if not ok or frame is None:
                self.video_ended = True
                self._is_playing = False
                self.end_of_file.emit()
                break

            pushed = self.buffer.put(frame)
            if not pushed:
                time.sleep(0.001)

            time.sleep(self.buffer.frame_interval())

    def stop(self) -> None:
        self._stop_event.set()
        self._pause_event.set()  # unblock any waiting pause so thread can exit
        self._paused = False
        self._is_playing = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)
        if self.source:
            self.source.release()
        self.source = None
