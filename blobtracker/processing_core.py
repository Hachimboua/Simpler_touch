from __future__ import annotations

import math
import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal

from models import Blob, FramePacket

PROCESS_SCALE: float = 0.5

try:
    from scipy.optimize import linear_sum_assignment
    from scipy.spatial.distance import cdist

    SCIPY_AVAILABLE = True
except Exception:
    SCIPY_AVAILABLE = False
    linear_sum_assignment = None
    cdist = None


class Preprocessor:
    def run(self, frame: np.ndarray, threshold: int, blur_radius: int, scale: float) -> Tuple[np.ndarray, float]:
        scale = max(0.25, min(1.0, float(scale)))
        h, w = frame.shape[:2]
        small_w = max(1, int(w * scale))
        small_h = max(1, int(h * scale))
        small = cv2.resize(frame, (small_w, small_h), interpolation=cv2.INTER_LINEAR)

        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

        if blur_radius % 2 == 0:
            blur_radius += 1
        blur_radius = max(1, blur_radius)

        blurred = cv2.GaussianBlur(gray, (blur_radius, blur_radius), 0)
        _, binary = cv2.threshold(blurred, threshold, 255, cv2.THRESH_BINARY)
        return binary, scale

    def process(self, frame: np.ndarray, threshold: int, blur_radius: int, scale: float) -> Tuple[np.ndarray, float]:
        return self.run(frame, threshold, blur_radius, scale)


class BlobDetector:
    def run(
        self,
        binary_frame: np.ndarray,
        scale: float,
        min_area: float,
        max_area: float,
        max_count: int,
        mode: str = "contour",
        min_circularity: float = 0.0,
        simple_min_threshold: float = 10.0,
        simple_max_threshold: float = 220.0,
    ) -> List[Tuple[Tuple[int, int], Tuple[int, int, int, int], float]]:
        scale = max(0.25, min(1.0, float(scale)))
        if str(mode).lower() == "simple_blob":
            return self._detect_simple_blob(
                binary_frame,
                scale=scale,
                min_area=min_area,
                max_area=max_area,
                max_count=max_count,
                min_threshold=simple_min_threshold,
                max_threshold=simple_max_threshold,
                min_circularity=min_circularity,
            )
        return self._detect_contours(binary_frame, scale, min_area, max_area, max_count, min_circularity)

    def detect(
        self,
        binary_frame: np.ndarray,
        scale: float,
        min_area: float,
        max_area: float,
        max_count: int,
        mode: str = "contour",
        min_circularity: float = 0.0,
        simple_min_threshold: float = 10.0,
        simple_max_threshold: float = 220.0,
    ) -> List[Tuple[Tuple[int, int], Tuple[int, int, int, int], float]]:
        return self.run(
            binary_frame,
            scale,
            min_area,
            max_area,
            max_count,
            mode,
            min_circularity,
            simple_min_threshold,
            simple_max_threshold,
        )

    def _detect_contours(
        self,
        binary_frame: np.ndarray,
        scale: float,
        min_area: float,
        max_area: float,
        max_count: int,
        min_circularity: float,
    ) -> List[Tuple[Tuple[int, int], Tuple[int, int, int, int], float]]:
        contours, _ = cv2.findContours(binary_frame, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        blobs: List[Tuple[Tuple[int, int], Tuple[int, int, int, int], float]] = []

        for contour in contours:
            raw_area = cv2.contourArea(contour)
            area = float(raw_area / (scale * scale))
            if area < min_area or area > max_area:
                continue

            if min_circularity > 0.0:
                perimeter = cv2.arcLength(contour, True)
                if perimeter <= 0.0:
                    continue
                circularity = 4.0 * math.pi * raw_area / (perimeter * perimeter)
                if circularity < min_circularity:
                    continue

            raw_x, raw_y, raw_w, raw_h = cv2.boundingRect(contour)
            moments = cv2.moments(contour)
            if moments["m00"] == 0:
                raw_cx = raw_x + (raw_w // 2)
                raw_cy = raw_y + (raw_h // 2)
            else:
                raw_cx = int(moments["m10"] / moments["m00"])
                raw_cy = int(moments["m01"] / moments["m00"])

            centroid = (int(raw_cx / scale), int(raw_cy / scale))
            bbox = (
                int(raw_x / scale),
                int(raw_y / scale),
                max(1, int(raw_w / scale)),
                max(1, int(raw_h / scale)),
            )

            blobs.append((centroid, bbox, area))

        blobs.sort(key=lambda item: item[2], reverse=True)
        return blobs[: max(1, max_count)]

    def _detect_simple_blob(
        self,
        binary_frame: np.ndarray,
        scale: float,
        min_area: float,
        max_area: float,
        max_count: int,
        min_threshold: float,
        max_threshold: float,
        min_circularity: float,
    ) -> List[Tuple[Tuple[int, int], Tuple[int, int, int, int], float]]:
        params = cv2.SimpleBlobDetector_Params()
        params.minThreshold = float(min_threshold)
        params.maxThreshold = float(max_threshold)
        params.thresholdStep = 10.0
        params.filterByArea = True
        params.minArea = float(min_area)
        params.maxArea = float(max_area)
        params.filterByCircularity = bool(min_circularity > 0.0)
        params.minCircularity = float(max(0.01, min_circularity)) if min_circularity > 0.0 else 0.0
        params.filterByConvexity = False
        params.filterByInertia = False
        params.filterByColor = False

        detector = cv2.SimpleBlobDetector_create(params)
        keypoints = detector.detect(binary_frame)
        blobs: List[Tuple[Tuple[int, int], Tuple[int, int, int, int], float]] = []
        h, w = binary_frame.shape[:2]

        for keypoint in keypoints:
            raw_cx = int(round(keypoint.pt[0]))
            raw_cy = int(round(keypoint.pt[1]))
            raw_radius = max(2, int(round(keypoint.size * 0.5)))
            raw_x0 = max(0, raw_cx - raw_radius)
            raw_y0 = max(0, raw_cy - raw_radius)
            raw_x1 = min(w - 1, raw_cx + raw_radius)
            raw_y1 = min(h - 1, raw_cy + raw_radius)
            area = float((math.pi * raw_radius * raw_radius) / (scale * scale))
            if area < min_area or area > max_area:
                continue

            centroid = (int(raw_cx / scale), int(raw_cy / scale))
            bbox = (
                int(raw_x0 / scale),
                int(raw_y0 / scale),
                max(1, int((raw_x1 - raw_x0) / scale)),
                max(1, int((raw_y1 - raw_y0) / scale)),
            )
            blobs.append((centroid, bbox, area))

        blobs.sort(key=lambda item: item[2], reverse=True)
        return blobs[: max(1, max_count)]


class Tracker:
    def __init__(self) -> None:
        self.next_id = 1
        self.active: Dict[int, Tuple[int, int]] = {}
        self.missing_count: Dict[int, int] = defaultdict(int)
        self.trails: Dict[int, Deque[Tuple[int, int]]] = defaultdict(lambda: deque(maxlen=30))

    @staticmethod
    def _distance(p1: Tuple[int, int], p2: Tuple[int, int]) -> float:
        return math.hypot(float(p1[0] - p2[0]), float(p1[1] - p2[1]))

    def update(
        self,
        detections: List[Tuple[Tuple[int, int], Tuple[int, int, int, int], float]],
        max_distance: float,
        trail_length: int,
        max_missing: int = 10,
        smoothing_alpha: float = 0.4,
    ) -> List[Blob]:
        target_len = max(1, trail_length)
        smoothing_alpha = max(0.0, min(1.0, float(smoothing_alpha)))
        for track_id, trail in list(self.trails.items()):
            if trail.maxlen != target_len:
                self.trails[track_id] = deque(trail, maxlen=target_len)

        assigned = self._assign_tracks(detections, max_distance=max_distance)

        updated_active: Dict[int, Tuple[int, int]] = {}
        seen_ids = set()
        output: List[Blob] = []

        for idx, (centroid, bbox, area) in enumerate(detections):
            if idx in assigned:
                blob_id = assigned[idx]
                prev_centroid = self.active.get(blob_id, centroid)
                smoothed = (
                    int(round((1.0 - smoothing_alpha) * prev_centroid[0] + smoothing_alpha * centroid[0])),
                    int(round((1.0 - smoothing_alpha) * prev_centroid[1] + smoothing_alpha * centroid[1])),
                )
            else:
                blob_id = self.next_id
                self.next_id += 1
                smoothed = centroid

            updated_active[blob_id] = smoothed
            seen_ids.add(blob_id)
            self.missing_count[blob_id] = 0

            existing = self.trails.get(blob_id)
            if existing is None or existing.maxlen != target_len:
                existing = deque(existing or [], maxlen=target_len)
            existing.append(smoothed)
            self.trails[blob_id] = existing

            output.append(
                Blob(
                    id=blob_id,
                    centroid=smoothed,
                    bbox=bbox,
                    area=area,
                    trail=list(existing),
                )
            )

        for track_id, prev_centroid in self.active.items():
            if track_id in seen_ids:
                continue
            self.missing_count[track_id] += 1
            if self.missing_count[track_id] <= max_missing:
                updated_active[track_id] = prev_centroid
            else:
                self.missing_count.pop(track_id, None)
                self.trails.pop(track_id, None)

        self.active = updated_active
        return output

    def update_trails_only(self, blobs: List[Blob], trail_length: int) -> List[Blob]:
        target_len = max(1, int(trail_length))
        output: List[Blob] = []

        for blob in blobs:
            existing = self.trails.get(blob.id)
            if existing is None or existing.maxlen != target_len:
                existing = deque(existing or blob.trail or [], maxlen=target_len)
            existing.append((int(blob.centroid[0]), int(blob.centroid[1])))
            self.trails[blob.id] = existing
            self.active[blob.id] = (int(blob.centroid[0]), int(blob.centroid[1]))

            output.append(
                Blob(
                    id=blob.id,
                    centroid=(int(blob.centroid[0]), int(blob.centroid[1])),
                    bbox=(int(blob.bbox[0]), int(blob.bbox[1]), int(blob.bbox[2]), int(blob.bbox[3])),
                    area=float(blob.area),
                    trail=list(existing),
                )
            )

        return output

    def _assign_tracks(
        self,
        detections: List[Tuple[Tuple[int, int], Tuple[int, int, int, int], float]],
        max_distance: float,
    ) -> Dict[int, int]:
        if not detections or not self.active:
            return {}

        track_ids = list(self.active.keys())
        track_centroids = np.array([self.active[tid] for tid in track_ids], dtype=np.float32)
        det_centroids = np.array([det[0] for det in detections], dtype=np.float32)

        assignment: Dict[int, int] = {}
        if SCIPY_AVAILABLE and cdist is not None and linear_sum_assignment is not None:
            dist_matrix = cdist(track_centroids, det_centroids)
            row_idx, col_idx = linear_sum_assignment(dist_matrix)
            for r, c in zip(row_idx.tolist(), col_idx.tolist()):
                if float(dist_matrix[r, c]) <= float(max_distance):
                    assignment[int(c)] = track_ids[int(r)]
            return assignment

        used_tracks = set()
        for det_idx, det_center in enumerate(det_centroids):
            best_track = None
            best_dist = float("inf")
            for row_idx, track_id in enumerate(track_ids):
                if track_id in used_tracks:
                    continue
                dist = float(np.linalg.norm(track_centroids[row_idx] - det_center))
                if dist <= max_distance and dist < best_dist:
                    best_dist = dist
                    best_track = track_id
            if best_track is not None:
                assignment[det_idx] = best_track
                used_tracks.add(best_track)
        return assignment


class OpticalFlow:
    def __init__(self) -> None:
        self.prev_gray: Optional[np.ndarray] = None

    def reset(self) -> None:
        self.prev_gray = None

    def overlay(self, frame: np.ndarray, enabled: bool, alpha: float = 0.4) -> np.ndarray:
        if not enabled:
            self.prev_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            return frame

        current_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if self.prev_gray is None:
            self.prev_gray = current_gray
            return frame

        flow = cv2.calcOpticalFlowFarneback(
            self.prev_gray,
            current_gray,
            None,
            0.5,
            3,
            15,
            3,
            5,
            1.2,
            0,
        )
        mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        hsv = np.zeros_like(frame)
        hsv[..., 1] = 255
        hsv[..., 0] = ang * 90 / np.pi
        hsv[..., 2] = np.minimum(mag * 8, 255).astype(np.uint8)
        flow_bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        self.prev_gray = current_gray
        return cv2.addWeighted(frame, 1.0 - alpha, flow_bgr, alpha, 0)


class ProcessorWorker(QObject):
    frame_packet_ready = pyqtSignal(object)

    def __init__(self, frame_buffer, param_store) -> None:
        super().__init__()
        self.frame_buffer = frame_buffer
        self.param_store = param_store
        self.preprocessor = Preprocessor()
        self.detector = BlobDetector()
        self.tracker = Tracker()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._frame_counter: int = 0
        self._last_blobs: List[Blob] = []

    def start(self) -> None:
        self.stop()
        self._frame_counter = 0
        self._last_blobs = []
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop_event.is_set():
            frame = self.frame_buffer.get(timeout=0.1)
            if frame is None:
                continue

            threshold = int(self.param_store.get("blob.threshold"))
            blur = int(self.param_store.get("blob.blur_radius"))
            min_area = float(self.param_store.get("blob.min_area"))
            max_area = float(self.param_store.get("blob.max_area"))
            max_count = int(self.param_store.get("blob.max_count"))
            smoothing = float(self.param_store.get("tracking.smoothing"))
            trail_length = int(self.param_store.get("trail_length")) if "trail_length" in self.param_store.params else int(self.param_store.get("tracking.max_trail_length"))
            process_scale = float(self.param_store.get("process_scale")) if "process_scale" in self.param_store.params else PROCESS_SCALE
            detect_every_n = int(self.param_store.get("detect_every_n")) if "detect_every_n" in self.param_store.params else 1
            detect_every_n = max(1, min(4, detect_every_n))

            detector_mode = str(self.param_store.get("detector_mode")) if "detector_mode" in self.param_store.params else "contour"
            blob_min_area = float(self.param_store.get("blob_min_area")) if "blob_min_area" in self.param_store.params else min_area
            blob_max_area = float(self.param_store.get("blob_max_area")) if "blob_max_area" in self.param_store.params else max_area
            max_disappeared = int(self.param_store.get("tracker_max_disappeared")) if "tracker_max_disappeared" in self.param_store.params else 10
            smooth_alpha = float(self.param_store.get("tracker_smooth_alpha")) if "tracker_smooth_alpha" in self.param_store.params else smoothing
            min_circularity = float(self.param_store.get("blob.min_circularity")) if "blob.min_circularity" in self.param_store.params else 0.0

            simple_min_threshold = float(self.param_store.get("blob.threshold"))
            simple_max_threshold = 255.0

            self._frame_counter += 1

            if self._frame_counter % detect_every_n == 0 or not self._last_blobs:
                binary, used_scale = self.preprocessor.run(
                    frame,
                    threshold=threshold,
                    blur_radius=blur,
                    scale=process_scale,
                )
                detections = self.detector.run(
                    binary,
                    scale=used_scale,
                    min_area=blob_min_area,
                    max_area=blob_max_area,
                    max_count=max_count,
                    mode=detector_mode,
                    min_circularity=min_circularity,
                    simple_min_threshold=simple_min_threshold,
                    simple_max_threshold=simple_max_threshold,
                )

                self._last_blobs = self.tracker.update(
                    detections,
                    max_distance=max(10.0, 100.0 * (1.0 - min(0.95, smoothing))),
                    trail_length=trail_length,
                    max_missing=max_disappeared,
                    smoothing_alpha=smooth_alpha,
                )
            else:
                self._last_blobs = self.tracker.update_trails_only(self._last_blobs, trail_length=trail_length)

            packet = FramePacket(
                raw_frame=frame,
                blobs=self._last_blobs,
                timestamp=time.perf_counter(),
                frame_index=self._frame_counter,
            )
            self.frame_packet_ready.emit(packet)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)
