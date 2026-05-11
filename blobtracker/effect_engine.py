from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Type

import cv2
import numpy as np

from models import Blob

try:
    from PIL import Image, ImageDraw, ImageFont

    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False
    Image = None
    ImageDraw = None
    ImageFont = None

try:
    from scipy.spatial import cKDTree

    CKDTREE_AVAILABLE = True
except Exception:
    cKDTree = None
    CKDTREE_AVAILABLE = False


def clamp_color(color: Sequence[int]) -> Tuple[int, int, int]:
    return (
        int(max(0, min(255, color[0]))),
        int(max(0, min(255, color[1]))),
        int(max(0, min(255, color[2]))),
    )


def clamp_opacity(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def blend_overlay(base: np.ndarray, overlay: np.ndarray, opacity: float) -> np.ndarray:
    alpha = clamp_opacity(opacity)
    if alpha <= 0.0:
        return base
    if alpha >= 1.0:
        return overlay
    return cv2.addWeighted(overlay, alpha, base, 1.0 - alpha, 0)


class TextRenderer:
    def __init__(self, size_px: int = 10) -> None:
        self.size_px = max(8, int(size_px))
        self.pil_font = self._load_font(self.size_px) if PIL_AVAILABLE else None
        self.cv2_font = cv2.FONT_HERSHEY_SIMPLEX

    @staticmethod
    def _load_font(size_px: int):
        candidates = [
            "JetBrainsMono-Regular.ttf",
            "JetBrains Mono Regular.ttf",
            "C:/Windows/Fonts/JetBrainsMono-Regular.ttf",
            "C:/Windows/Fonts/cour.ttf",
            "C:/Windows/Fonts/consola.ttf",
            "Courier New.ttf",
        ]
        for path in candidates:
            try:
                return ImageFont.truetype(path, size_px)
            except Exception:
                continue
        return None

    def draw_lines(
        self,
        frame: np.ndarray,
        lines: List[Tuple[str, Tuple[int, int]]],
        color: Tuple[int, int, int],
        opacity: float,
        font_scale: float = 0.35,
    ) -> np.ndarray:
        if not lines:
            return frame

        bgr_color = clamp_color(color)
        rgb_color = (bgr_color[2], bgr_color[1], bgr_color[0], 255)

        if self.pil_font is not None and PIL_AVAILABLE:
            rgba = np.zeros((frame.shape[0], frame.shape[1], 4), dtype=np.uint8)
            pil_img = Image.fromarray(rgba, mode="RGBA")
            draw = ImageDraw.Draw(pil_img)
            for text, (x, y) in lines:
                draw.text((int(x), int(y)), text, font=self.pil_font, fill=rgb_color)
            overlay_rgba = np.array(pil_img)
            alpha = overlay_rgba[..., 3:4].astype(np.float32) / 255.0
            rgb = overlay_rgba[..., :3][:, :, ::-1].astype(np.float32)
            base = frame.astype(np.float32)
            composed = base * (1.0 - alpha * clamp_opacity(opacity)) + rgb * (alpha * clamp_opacity(opacity))
            return np.clip(composed, 0, 255).astype(np.uint8)

        out = frame.copy()
        cv_scale = max(0.2, float(font_scale))
        for text, (x, y) in lines:
            cv2.putText(
                out,
                text,
                (int(x), int(y)),
                self.cv2_font,
                cv_scale,
                bgr_color,
                1,
                cv2.LINE_AA,
            )
        return blend_overlay(frame, out, opacity)


class CreativeFilter(ABC):
    name = "BaseFilter"

    @abstractmethod
    def apply(self, frame: np.ndarray) -> np.ndarray:
        raise NotImplementedError


class GrainFilter(CreativeFilter):
    name = "GrainFilter"

    def __init__(self, intensity: float = 0.08, grain_type: str = "gaussian", colored: bool = False) -> None:
        self.intensity = max(0.0, min(0.3, float(intensity)))
        self.grain_type = str(grain_type).lower()
        self.colored = bool(colored)

    def apply(self, frame: np.ndarray) -> np.ndarray:
        intensity = self.intensity
        if intensity <= 0.0:
            return frame
        
        noise_shape = frame.shape if self.colored else (frame.shape[0], frame.shape[1], 1)
        
        if self.grain_type == "uniform":
            noise = np.random.uniform(-255 * intensity, 255 * intensity, noise_shape).astype(np.float32)
        elif self.grain_type == "colored":
            noise = np.random.normal(0, 255 * intensity, frame.shape).astype(np.float32)
        else:  # gaussian
            noise = np.random.normal(0, 255 * intensity, noise_shape).astype(np.float32)
        
        out = frame.astype(np.float32) + noise
        return np.clip(out, 0, 255).astype(np.uint8)


class GlitchFilter(CreativeFilter):
    name = "GlitchFilter"

    def __init__(self, slices: int = 8, max_offset: int = 24, probability: float = 0.5) -> None:
        self.slices = max(1, int(slices))
        self.max_offset = max(1, int(max_offset))
        self.probability = max(0.0, min(1.0, float(probability)))

    def apply(self, frame: np.ndarray) -> np.ndarray:
        if self.probability <= 0.0 or random.random() > self.probability:
            return frame
        
        out = frame.copy()
        h, _ = out.shape[:2]
        slice_height = max(1, h // max(1, self.slices))
        for idx in range(self.slices):
            y0 = idx * slice_height
            y1 = min(h, y0 + slice_height)
            offset = random.randint(-self.max_offset, self.max_offset)
            out[y0:y1] = np.roll(out[y0:y1], offset, axis=1)
        return out


class ThermalFilter(CreativeFilter):
    name = "ThermalFilter"

    def __init__(self, colormap: str = "inferno") -> None:
        self.colormap = str(colormap).lower()
        self._colormap_map = {
            "inferno": cv2.COLORMAP_INFERNO,
            "hot": cv2.COLORMAP_HOT,
            "cool": cv2.COLORMAP_COOL,
            "twilight": cv2.COLORMAP_TWILIGHT,
            "viridis": cv2.COLORMAP_VIRIDIS,
        }

    def apply(self, frame: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        cmap_id = self._colormap_map.get(self.colormap, cv2.COLORMAP_INFERNO)
        return cv2.applyColorMap(gray, cmap_id)


class EdgeFilter(CreativeFilter):
    name = "EdgeFilter"

    def __init__(self, low: int = 80, high: int = 180, alpha: float = 0.7, blur: int = 0) -> None:
        self.low = max(0, int(low))
        self.high = max(0, int(high))
        self.alpha = max(0.0, min(1.0, float(alpha)))
        self.blur = max(0, int(blur))
        if self.blur % 2 == 0:
            self.blur += 1

    def apply(self, frame: np.ndarray) -> np.ndarray:
        working = frame.copy()
        if self.blur > 1:
            working = cv2.GaussianBlur(working, (self.blur, self.blur), 0)
        
        edges = cv2.Canny(working, self.low, self.high)
        edges_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        return cv2.addWeighted(frame, 1.0, edges_bgr, self.alpha, 0)


class ChromaticAberration(CreativeFilter):
    name = "ChromaticAberration"

    def __init__(self, shift_x: int = 3, shift_y: int = 0, randomize: bool = False) -> None:
        self.shift_x = int(shift_x)
        self.shift_y = int(shift_y)
        self.randomize = bool(randomize)

    def apply(self, frame: np.ndarray) -> np.ndarray:
        b, g, r = cv2.split(frame)
        
        sx = self.shift_x
        sy = self.shift_y
        
        if self.randomize:
            sx = random.randint(-abs(self.shift_x), abs(self.shift_x)) if self.shift_x != 0 else 0
            sy = random.randint(-abs(self.shift_y), abs(self.shift_y)) if self.shift_y != 0 else 0
        
        r = np.roll(r, sx, axis=1)
        r = np.roll(r, sy, axis=0)
        b = np.roll(b, -sx, axis=1)
        b = np.roll(b, -sy, axis=0)
        
        return cv2.merge((b, g, r))


class BaseFrameFX:
    def apply(self, frame: np.ndarray, desaturate: float = 0.85, grain: float = 0.03, vignette: float = 0.3) -> np.ndarray:
        out = frame.copy()
        out = self.desaturate(out, desaturate)
        out = self.grain(out, grain)
        out = self.vignette(out, vignette)
        return out

    def desaturate(self, frame: np.ndarray, amount: float) -> np.ndarray:
        amount = clamp_opacity(amount)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        return cv2.addWeighted(frame, 1.0 - amount, gray_bgr, amount, 0)

    def grain(self, frame: np.ndarray, strength: float) -> np.ndarray:
        strength = max(0.0, min(0.2, float(strength)))
        if strength <= 0.0:
            return frame
        noise = np.random.normal(0, 255.0 * strength, frame.shape).astype(np.float32)
        out = frame.astype(np.float32) + noise
        return np.clip(out, 0, 255).astype(np.uint8)

    def vignette(self, frame: np.ndarray, strength: float) -> np.ndarray:
        strength = clamp_opacity(strength)
        if strength <= 0.0:
            return frame
        h, w = frame.shape[:2]
        y = np.linspace(-1.0, 1.0, h)
        x = np.linspace(-1.0, 1.0, w)
        xx, yy = np.meshgrid(x, y)
        dist = np.sqrt(xx * xx + yy * yy)
        mask = 1.0 - strength * np.clip((dist - 0.15) / 1.2, 0.0, 1.0)
        out = frame.astype(np.float32)
        out[..., 0] *= mask
        out[..., 1] *= mask
        out[..., 2] *= mask
        return np.clip(out, 0, 255).astype(np.uint8)


class BoundingBoxFX:
    def __init__(
        self,
        corner_style: str = "ticks",
        color: Tuple[int, int, int] = (255, 255, 255),
        opacity: float = 0.7,
        thickness: int = 1,
        tick_length: int = 10,
    ) -> None:
        self.corner_style = corner_style
        self.color = color
        self.opacity = opacity
        self.thickness = thickness
        self.tick_length = tick_length

    def apply(
        self,
        frame: np.ndarray,
        blobs: Iterable[Blob],
        color: Tuple[int, int, int],
        thickness: int,
        corner_style: str,
        opacity: Optional[float] = None,
        tick_length: Optional[int] = None,
    ) -> np.ndarray:
        overlay = frame.copy()
        draw_color = clamp_color(color if color is not None else self.color)
        draw_thickness = max(1, int(thickness if thickness is not None else self.thickness))
        style = str(corner_style or self.corner_style).strip().lower()
        if style in ("corner", "ticks"):
            style = "ticks"
        else:
            style = "full"
        tick_len = max(4, int(tick_length if tick_length is not None else self.tick_length))

        blob_list = list(blobs)
        if not blob_list:
            return frame
        rects = np.array([b.bbox for b in blob_list], dtype=np.int32)

        for x, y, w, h in rects:
            x2 = x + w
            y2 = y + h
            if style == "ticks":
                t = min(tick_len, max(4, w // 2), max(4, h // 2))
                cv2.line(overlay, (x, y), (x + t, y), draw_color, draw_thickness, cv2.LINE_AA)
                cv2.line(overlay, (x, y), (x, y + t), draw_color, draw_thickness, cv2.LINE_AA)
                cv2.line(overlay, (x2, y), (x2 - t, y), draw_color, draw_thickness, cv2.LINE_AA)
                cv2.line(overlay, (x2, y), (x2, y + t), draw_color, draw_thickness, cv2.LINE_AA)
                cv2.line(overlay, (x, y2), (x + t, y2), draw_color, draw_thickness, cv2.LINE_AA)
                cv2.line(overlay, (x, y2), (x, y2 - t), draw_color, draw_thickness, cv2.LINE_AA)
                cv2.line(overlay, (x2, y2), (x2 - t, y2), draw_color, draw_thickness, cv2.LINE_AA)
                cv2.line(overlay, (x2, y2), (x2, y2 - t), draw_color, draw_thickness, cv2.LINE_AA)
            else:
                cv2.rectangle(overlay, (x, y), (x2, y2), draw_color, draw_thickness, cv2.LINE_AA)

        return blend_overlay(frame, overlay, self.opacity if opacity is None else opacity)


class LeaderLineFX:
    def __init__(
        self,
        line_color: Tuple[int, int, int] = (255, 255, 255),
        opacity: float = 0.7,
        thickness: float = 0.5,
    ) -> None:
        self.line_color = clamp_color(line_color)
        self.opacity = opacity
        self.thickness = thickness

    def apply(
        self,
        frame: np.ndarray,
        leader_segments: List[Tuple[Tuple[int, int], Tuple[int, int]]],
        line_color: Optional[Tuple[int, int, int]] = None,
        opacity: Optional[float] = None,
        thickness: Optional[float] = None,
    ) -> np.ndarray:
        if not leader_segments:
            return frame
        overlay = frame.copy()
        color = clamp_color(line_color if line_color is not None else self.line_color)
        draw_thickness = max(1, int(round(thickness if thickness is not None else self.thickness)))
        for p0, p1 in leader_segments:
            cv2.line(overlay, p0, p1, color, draw_thickness, cv2.LINE_AA)
        return blend_overlay(frame, overlay, self.opacity if opacity is None else opacity)


class CentroidFX:
    def __init__(self, radius: int = 2, color: Tuple[int, int, int] = (255, 255, 255), opacity: float = 0.8) -> None:
        self.radius = radius
        self.color = clamp_color(color)
        self.opacity = opacity

    def apply(
        self,
        frame: np.ndarray,
        blobs: Iterable[Blob],
        radius: Optional[int] = None,
        color: Optional[Tuple[int, int, int]] = None,
        opacity: Optional[float] = None,
    ) -> np.ndarray:
        overlay = frame.copy()
        draw_radius = max(1, int(radius if radius is not None else self.radius))
        draw_color = clamp_color(color if color is not None else self.color)
        for blob in blobs:
            cv2.circle(overlay, tuple(blob.centroid), draw_radius, draw_color, -1, cv2.LINE_AA)
        return blend_overlay(frame, overlay, self.opacity if opacity is None else opacity)


class LabelFX:
    def __init__(
        self,
        font_scale: float = 0.35,
        color: Tuple[int, int, int] = (255, 255, 255),
        show_area: bool = False,
        show_coords: bool = False,
        opacity: float = 0.8,
        line_height: int = 12,
    ) -> None:
        self.font_scale = font_scale
        self.color = clamp_color(color)
        self.show_area = show_area
        self.show_coords = show_coords
        self.opacity = opacity
        self.line_height = line_height
        self.text_renderer = TextRenderer(size_px=10)
        self.leader_fx = LeaderLineFX(line_color=color, opacity=opacity, thickness=0.5)
        self.centroid_fx = CentroidFX(radius=2, color=color, opacity=opacity)

    def apply(
        self,
        frame: np.ndarray,
        blobs: Iterable[Blob],
        font_size: float,
        color: Tuple[int, int, int],
        offset: Tuple[int, int],
        show_coords: bool,
        show_area: Optional[bool] = None,
        min_label_area: int = 200,
        show_label: bool = True,
        show_leader_lines: bool = True,
        show_centroid: bool = True,
        opacity: Optional[float] = None,
    ) -> np.ndarray:
        out = frame.copy()
        draw_color = clamp_color(color if color is not None else self.color)
        fs = max(0.2, float(font_size if font_size is not None else self.font_scale))
        line_h = self.line_height
        lines_to_draw: List[Tuple[str, Tuple[int, int]]] = []
        leader_segments: List[Tuple[Tuple[int, int], Tuple[int, int]]] = []
        min_area = max(0, int(min_label_area))

        for blob in blobs:
            if float(blob.area) < float(min_area):
                continue
            cx, cy = blob.centroid
            base_x = int(cx + offset[0])
            base_y = int(cy + offset[1])

            text_lines: List[str] = []
            if show_label:
                text_lines.append("{:07d}".format(int(blob.id) % 10000000))

            if bool(self.show_area if show_area is None else show_area):
                text_lines.append("A:{}".format(int(blob.area)))

            if bool(show_coords if show_coords is not None else self.show_coords):
                text_lines.append("X:{} Y:{}".format(cx, cy))

            for idx, line in enumerate(text_lines):
                pos = (base_x, base_y + idx * line_h)
                lines_to_draw.append((line, pos))
                if show_leader_lines:
                    target = (base_x - 4, base_y + idx * line_h - 3)
                    leader_segments.append(((cx, cy), target))

        if show_leader_lines:
            out = self.leader_fx.apply(
                out,
                leader_segments,
                line_color=draw_color,
                opacity=self.opacity if opacity is None else opacity,
                thickness=0.5,
            )

        out = self.text_renderer.draw_lines(
            out,
            lines_to_draw,
            color=draw_color,
            opacity=self.opacity if opacity is None else opacity,
            font_scale=fs,
        )

        if show_centroid:
            out = self.centroid_fx.apply(
                out,
                blobs,
                radius=2,
                color=draw_color,
                opacity=self.opacity if opacity is None else opacity,
            )
        return out


class TrailFX:
    def apply(
        self,
        frame: np.ndarray,
        blobs: Iterable[Blob],
        color: Tuple[int, int, int],
        alpha: float,
        thickness: int,
    ) -> np.ndarray:
        out = frame.copy()
        draw_color = clamp_color(color)
        draw_thickness = max(1, int(thickness))
        max_alpha = clamp_opacity(alpha)

        for blob in blobs:
            trail = list(blob.trail)
            if len(trail) < 2:
                continue
            pts = np.array(trail, dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(out, [pts], isClosed=False, color=draw_color, thickness=draw_thickness, lineType=cv2.LINE_AA)

            alphas = np.linspace(0.0, max_alpha, len(trail), dtype=np.float32)
            for i in range(len(trail) - 1):
                p0 = (int(pts[i][0][0]), int(pts[i][0][1]))
                p1 = (int(pts[i + 1][0][0]), int(pts[i + 1][0][1]))
                seg_alpha = float(alphas[i + 1])
                seg_layer = out.copy()
                cv2.line(seg_layer, p0, p1, draw_color, draw_thickness, cv2.LINE_AA)
                out = blend_overlay(out, seg_layer, seg_alpha)
        return out


class ConnectionLineFX:
    def __init__(self, param_store=None) -> None:
        self.param_store = param_store

    def _param(self, key: str, fallback):
        if self.param_store is None:
            return fallback
        if hasattr(self.param_store, "params") and key not in self.param_store.params:
            return fallback
        try:
            return self.param_store.get(key)
        except Exception:
            return fallback

    def apply(self, frame: np.ndarray, blobs: List[Blob]) -> np.ndarray:
        if len(blobs) < 2:
            return frame

        max_dist = float(self._param("connection_max_dist", 200.0))
        color = clamp_color(self._param("connection_color", [255, 255, 255]))
        max_alpha = clamp_opacity(float(self._param("connection_opacity", 0.4)))
        thickness = max(1, int(round(float(self._param("connection_thickness", 0.5)))))
        show_dots = bool(self._param("connection_show_dots", True))
        dot_radius = max(1, int(self._param("connection_dot_radius", 3)))

        if max_dist <= 0.0 or max_alpha <= 0.0:
            return frame

        centroids = np.array([b.centroid for b in blobs], dtype=np.float32)
        n = int(len(centroids))
        overlay = frame.copy()

        if n > 30 and CKDTREE_AVAILABLE and cKDTree is not None:
            tree = cKDTree(centroids)
            pairs = tree.query_pairs(r=max_dist)
            for i, j in pairs:
                delta = centroids[i] - centroids[j]
                dist = float(np.linalg.norm(delta))
                alpha = max_alpha * (1.0 - (dist / max_dist))
                if alpha <= 0.01:
                    continue

                pt1 = (int(centroids[i][0]), int(centroids[i][1]))
                pt2 = (int(centroids[j][0]), int(centroids[j][1]))
                line_overlay = overlay.copy()
                cv2.line(line_overlay, pt1, pt2, color, thickness, lineType=cv2.LINE_AA)
                cv2.addWeighted(line_overlay, alpha, overlay, 1.0 - alpha, 0, overlay)
        else:
            for i in range(n):
                for j in range(i + 1, n):
                    dx = float(centroids[i][0] - centroids[j][0])
                    dy = float(centroids[i][1] - centroids[j][1])
                    dist = float(np.sqrt(dx * dx + dy * dy))
                    if dist > max_dist:
                        continue

                    alpha = max_alpha * (1.0 - (dist / max_dist))
                    if alpha <= 0.01:
                        continue

                    pt1 = (int(centroids[i][0]), int(centroids[i][1]))
                    pt2 = (int(centroids[j][0]), int(centroids[j][1]))
                    line_overlay = overlay.copy()
                    cv2.line(line_overlay, pt1, pt2, color, thickness, lineType=cv2.LINE_AA)
                    cv2.addWeighted(line_overlay, alpha, overlay, 1.0 - alpha, 0, overlay)

        if show_dots:
            for blob in blobs:
                cv2.circle(
                    overlay,
                    (int(blob.centroid[0]), int(blob.centroid[1])),
                    dot_radius,
                    color,
                    -1,
                    lineType=cv2.LINE_AA,
                )

        return overlay


class IntraBlobFX:
    MODES = [
        "none",
        "thermal",
        "edge",
        "pixelate",
        "negative",
        "blur",
        "highlight",
        "desaturate",
    ]

    def __init__(self, param_store=None) -> None:
        self.param_store = param_store

    def _param(self, key: str, fallback):
        if self.param_store is None:
            return fallback
        if hasattr(self.param_store, "params") and key not in self.param_store.params:
            return fallback
        try:
            return self.param_store.get(key)
        except Exception:
            return fallback

    def apply(self, frame: np.ndarray, blobs: List[Blob]) -> np.ndarray:
        if not bool(self._param("intra_blob_enabled", False)):
            return frame
        if not blobs:
            return frame

        mode = str(self._param("intra_blob_mode", "thermal")).lower()
        opacity = clamp_opacity(float(self._param("intra_blob_opacity", 1.0)))
        padding = max(0, int(self._param("intra_blob_padding", 8)))
        feather = bool(self._param("intra_blob_feather", True))

        output = frame.copy()
        h, w = frame.shape[:2]

        for blob in blobs:
            x, y, bw, bh = blob.bbox
            x1 = max(0, int(x) - padding)
            y1 = max(0, int(y) - padding)
            x2 = min(w, int(x + bw) + padding)
            y2 = min(h, int(y + bh) + padding)
            if x2 <= x1 or y2 <= y1:
                continue

            crop = frame[y1:y2, x1:x2].copy()
            processed = self._apply_mode(crop, mode)

            if opacity >= 0.99:
                output[y1:y2, x1:x2] = processed
            else:
                cv2.addWeighted(
                    processed,
                    opacity,
                    output[y1:y2, x1:x2],
                    1.0 - opacity,
                    0,
                    output[y1:y2, x1:x2],
                )

            if feather and min(x2 - x1, y2 - y1) >= 20:
                output = self._feather_edges(output, frame, x1, y1, x2, y2)

        return output

    def _apply_mode(self, crop: np.ndarray, mode: str) -> np.ndarray:
        if mode == "thermal":
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            return cv2.applyColorMap(gray, cv2.COLORMAP_INFERNO)

        if mode == "edge":
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

        if mode == "pixelate":
            size = max(2, int(self._param("intra_blob_pixel_size", 12)))
            rh, rw = crop.shape[:2]
            if rh < size or rw < size:
                return crop
            small = cv2.resize(crop, (max(1, rw // size), max(1, rh // size)), interpolation=cv2.INTER_LINEAR)
            return cv2.resize(small, (rw, rh), interpolation=cv2.INTER_NEAREST)

        if mode == "negative":
            return cv2.bitwise_not(crop)

        if mode == "blur":
            radius = max(3, int(self._param("intra_blob_blur_radius", 21)))
            if radius % 2 == 0:
                radius += 1
            return cv2.GaussianBlur(crop, (radius, radius), 0)

        if mode == "highlight":
            alpha = max(1.0, float(self._param("intra_blob_highlight", 1.4)))
            return cv2.convertScaleAbs(crop, alpha=alpha, beta=0)

        if mode == "desaturate":
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

        return crop

    def _feather_edges(self, output: np.ndarray, original: np.ndarray, x1: int, y1: int, x2: int, y2: int) -> np.ndarray:
        rh, rw = y2 - y1, x2 - x1
        mask = np.zeros((rh, rw), dtype=np.float32)
        fp = max(4, min(rw, rh) // 6)
        if fp * 2 >= rw or fp * 2 >= rh:
            return output
        mask[fp:-fp, fp:-fp] = 1.0
        blur_k = fp * 2 + 1
        mask = cv2.GaussianBlur(mask, (blur_k, blur_k), 0)
        mask3 = np.stack([mask] * 3, axis=2)
        region = output[y1:y2, x1:x2].astype(np.float32)
        orig = original[y1:y2, x1:x2].astype(np.float32)
        blended = region * mask3 + orig * (1.0 - mask3)
        output[y1:y2, x1:x2] = np.clip(blended, 0, 255).astype(np.uint8)
        return output


class ZoomInsetFX:
    def apply(
        self,
        frame: np.ndarray,
        blobs: Sequence[Blob],
        selected_blob_id: int,
        zoom: float,
        inset_size: Tuple[int, int],
        corner: str,
    ) -> np.ndarray:
        if not blobs:
            return frame

        target: Optional[Blob] = None
        if selected_blob_id > 0:
            for blob in blobs:
                if blob.id == selected_blob_id:
                    target = blob
                    break

        if target is None:
            target = max(blobs, key=lambda b: b.area)

        cx, cy = target.centroid
        bx, by, bw, bh = target.bbox
        h, w = frame.shape[:2]

        zoom_scale = max(1.0, float(zoom))
        crop_w = max(20, int(max(8, bw) * zoom_scale))
        crop_h = max(20, int(max(8, bh) * zoom_scale))

        x0 = max(0, int(cx - crop_w // 2))
        y0 = max(0, int(cy - crop_h // 2))
        x1 = min(w, x0 + crop_w)
        y1 = min(h, y0 + crop_h)

        crop = frame[y0:y1, x0:x1]
        if crop.size == 0:
            return frame

        inset = cv2.resize(crop, inset_size, interpolation=cv2.INTER_LINEAR)
        out = frame.copy()

        if corner == "top-left":
            ox, oy = 8, 8
        elif corner == "bottom-left":
            ox, oy = 8, h - inset_size[1] - 8
        elif corner == "bottom-right":
            ox, oy = w - inset_size[0] - 8, h - inset_size[1] - 8
        else:
            ox, oy = w - inset_size[0] - 8, 8

        out[oy : oy + inset_size[1], ox : ox + inset_size[0]] = inset
        cv2.rectangle(out, (ox, oy), (ox + inset_size[0], oy + inset_size[1]), (255, 255, 255), 1)
        return out


class Compositor:
    def __init__(self) -> None:
        self.base_fx = BaseFrameFX()

    @staticmethod
    def blend(base: np.ndarray, layer: np.ndarray, mode: str) -> np.ndarray:
        b = base.astype(np.float32) / 255.0
        l = layer.astype(np.float32) / 255.0

        if mode == "multiply":
            out = b * l
        elif mode == "screen":
            out = 1.0 - (1.0 - b) * (1.0 - l)
        elif mode == "overlay":
            out = np.where(b < 0.5, 2.0 * b * l, 1.0 - 2.0 * (1.0 - b) * (1.0 - l))
        else:
            out = l

        return np.clip(out * 255.0, 0, 255).astype(np.uint8)

    def compose_layers(self, base_frame: np.ndarray, layers: List[Tuple[np.ndarray, float]], mode: str = "normal") -> np.ndarray:
        out = base_frame.copy()
        for layer, opacity in layers:
            alpha = clamp_opacity(opacity)
            if alpha >= 0.99:
                mask = np.any(layer > 0, axis=2)
                out[mask] = layer[mask]
                weighted = out
            else:
                weighted = cv2.addWeighted(layer, alpha, out, 1.0 - alpha, 0)
            out = weighted if mode == "normal" else self.blend(out, weighted, mode)
        return out

    def apply_connection_layer(
        self,
        frame: np.ndarray,
        blobs: List[Blob],
        param_store,
        connection_fx: Optional[ConnectionLineFX] = None,
    ) -> np.ndarray:
        if param_store is None:
            return frame
        if hasattr(param_store, "params") and "connection_enabled" in param_store.params:
            enabled = bool(param_store.get("connection_enabled"))
        else:
            enabled = False
        if not enabled or len(blobs) < 2:
            return frame
        fx = connection_fx if connection_fx is not None else ConnectionLineFX(param_store=param_store)
        return fx.apply(frame, blobs)


class CreativeFX:
    BUILTIN_FILTERS: Dict[str, Type[CreativeFilter]] = {
        GrainFilter.name: GrainFilter,
        GlitchFilter.name: GlitchFilter,
        ThermalFilter.name: ThermalFilter,
        EdgeFilter.name: EdgeFilter,
        ChromaticAberration.name: ChromaticAberration,
    }
    FILTER_ENABLE_KEYS: Dict[str, str] = {
        GrainFilter.name: "fx_grain_enabled",
        GlitchFilter.name: "fx_glitch_enabled",
        ThermalFilter.name: "fx_thermal_enabled",
        EdgeFilter.name: "fx_edge_enabled",
        ChromaticAberration.name: "fx_chroma_enabled",
    }

    def __init__(self) -> None:
        self.registry: Dict[str, Type[CreativeFilter]] = dict(self.BUILTIN_FILTERS)

    def register_filter(self, name: str, filter_cls: Type[CreativeFilter]) -> None:
        self.registry[name] = filter_cls

    def available_filters(self) -> List[str]:
        return sorted(self.registry.keys())

    def sync_params_from_store(self, param_store) -> Dict[str, Dict[str, float]]:
        """Update filter params dict from individual control parameters in param_store"""
        if param_store is None:
            return {}
        
        try:
            params = {
                "GrainFilter": {
                    "intensity": float(param_store.get("creative.grain_intensity")),
                    "grain_type": str(param_store.get("creative.grain_type")),
                    "colored": bool(param_store.get("creative.grain_colored")),
                },
                "GlitchFilter": {
                    "slices": int(param_store.get("creative.glitch_slices")),
                    "max_offset": int(param_store.get("creative.glitch_offset")),
                    "probability": float(param_store.get("creative.glitch_probability")),
                },
                "ThermalFilter": {
                    "colormap": str(param_store.get("creative.thermal_colormap")),
                },
                "EdgeFilter": {
                    "low": int(param_store.get("creative.edge_low_threshold")),
                    "high": int(param_store.get("creative.edge_high_threshold")),
                    "alpha": float(param_store.get("creative.edge_alpha")),
                    "blur": int(param_store.get("creative.edge_blur")),
                },
                "ChromaticAberration": {
                    "shift_x": int(param_store.get("creative.chroma_shift_x")),
                    "shift_y": int(param_store.get("creative.chroma_shift_y")),
                    "randomize": bool(param_store.get("creative.chroma_randomize")),
                },
            }
            return params
        except Exception:
            return {}

    def apply(
        self,
        frame: np.ndarray,
        filter_order: Sequence[str],
        params: Dict[str, Dict[str, float]],
        param_store=None,
    ) -> np.ndarray:
        out = frame.copy()
        for name in filter_order:
            cls = self.registry.get(name)
            if cls is None:
                continue
            enable_key = self.FILTER_ENABLE_KEYS.get(name)
            if enable_key is not None and param_store is not None:
                try:
                    if not bool(param_store.get(enable_key)):
                        continue
                except Exception:
                    pass
            cfg = params.get(name, {})
            try:
                filt = cls(**cfg)
            except TypeError:
                filt = cls()
            out = filt.apply(out)
        return out

    def apply_chain(
        self,
        frame: np.ndarray,
        filter_order: Sequence[str],
        params: Dict[str, Dict[str, float]],
        param_store=None,
    ) -> np.ndarray:
        return self.apply(frame, filter_order, params, param_store=param_store)
