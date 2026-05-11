from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import QObject, pyqtSignal


@dataclass
class ParamDef:
    key: str
    value: Any
    min: Any
    max: Any
    step: Any
    type: str
    options: Optional[List[str]] = None


class ParamStore(QObject):
    _instance: Optional["ParamStore"] = None

    param_changed = pyqtSignal(str, object)
    params_bulk_changed = pyqtSignal()

    def __init__(self, presets_dir: str) -> None:
        super().__init__()
        self.presets_dir = presets_dir
        self.params: Dict[str, ParamDef] = {}
        os.makedirs(self.presets_dir, exist_ok=True)
        self._register_defaults()

    @classmethod
    def instance(cls, presets_dir: str = "presets") -> "ParamStore":
        if cls._instance is None:
            cls._instance = cls(presets_dir=presets_dir)
        return cls._instance

    def register(self, param: ParamDef) -> None:
        self.params[param.key] = param

    def get(self, key: str) -> Any:
        return self.params[key].value

    def set(self, key: str, value: Any, emit: bool = True) -> None:
        if key not in self.params:
            raise KeyError("Unknown parameter: {}".format(key))

        param = self.params[key]
        casted = self._cast_value(param, value)
        if param.value == casted:
            return

        param.value = casted
        self.params[key] = param
        if emit:
            self.param_changed.emit(key, casted)

    def _cast_value(self, param: ParamDef, value: Any) -> Any:
        if param.type == "int":
            value = int(value)
            return max(int(param.min), min(int(param.max), value))
        if param.type == "float":
            value = float(value)
            return max(float(param.min), min(float(param.max), value))
        if param.type == "bool":
            return bool(value)
        if param.type == "enum":
            val = str(value)
            if param.options and val not in param.options:
                return param.options[0]
            return val
        if param.type == "color":
            if isinstance(value, (tuple, list)) and len(value) == 3:
                return [int(value[0]), int(value[1]), int(value[2])]
            return [240, 240, 240]
        if param.type == "str":
            return str(value)
        if param.type == "list":
            return list(value)
        if param.type == "dict":
            return dict(value)
        return value

    def to_dict(self) -> Dict[str, Any]:
        return {key: param.value for key, param in self.params.items()}

    def apply_dict(self, values: Dict[str, Any]) -> None:
        for key, value in values.items():
            if key in self.params:
                self.set(key, value, emit=False)
        self.params_bulk_changed.emit()

    def save_preset(self, name: str) -> str:
        payload = {
            "name": name,
            "params": self.to_dict(),
            "meta": {"version": 1},
        }
        path = os.path.join(self.presets_dir, "{}.json".format(name))
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return path

    def load_preset(self, name: str) -> Dict[str, Any]:
        path = os.path.join(self.presets_dir, "{}.json".format(name))
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        params = payload.get("params", {})
        self.apply_dict(params)
        return params

    def delete_preset(self, name: str) -> None:
        path = os.path.join(self.presets_dir, "{}.json".format(name))
        if os.path.exists(path):
            os.remove(path)

    def list_presets(self) -> List[str]:
        names: List[str] = []
        if not os.path.isdir(self.presets_dir):
            return names
        for filename in os.listdir(self.presets_dir):
            if filename.endswith(".json"):
                names.append(os.path.splitext(filename)[0])
        return sorted(names)

    def export_schema(self) -> Dict[str, Dict[str, Any]]:
        return {k: asdict(v) for k, v in self.params.items()}

    def _register_defaults(self) -> None:
        defaults = [
            ParamDef("input.source_type", "webcam", "", "", "", "enum", ["webcam", "file"]),
            ParamDef("input.source_path", "", "", "", "", "str"),
            ParamDef("input.webcam_index", 0, 0, 8, 1, "int"),
            ParamDef("input.target_fps", 30, 1, 120, 1, "int"),
            ParamDef("blob.threshold", 90, 0, 255, 1, "int"),
            ParamDef("blob.blur_radius", 7, 1, 31, 2, "int"),
            ParamDef("blob.min_area", 120.0, 1.0, 20000.0, 1.0, "float"),
            ParamDef("blob.max_area", 50000.0, 10.0, 400000.0, 1.0, "float"),
            ParamDef("blob.max_count", 20, 1, 300, 1, "int"),
            ParamDef("process_scale", 0.5, 0.25, 1.0, 0.05, "float"),
            ParamDef("detect_every_n", 2, 1, 4, 1, "int"),
            ParamDef("min_label_area", 200, 0, 2000, 1, "int"),
            ParamDef("tracking.smoothing", 0.35, 0.0, 1.0, 0.01, "float"),
            ParamDef("tracking.max_trail_length", 35, 1, 500, 1, "int"),
            ParamDef("tracking.id_font_size", 0.5, 0.2, 2.0, 0.05, "float"),
            ParamDef("tracking.label_offset_x", 10, -200, 200, 1, "int"),
            ParamDef("tracking.label_offset_y", -10, -200, 200, 1, "int"),
            ParamDef("effects.bbox_enabled", False, False, True, 1, "bool"),
            ParamDef("effects.label_enabled", False, False, True, 1, "bool"),
            ParamDef("effects.trail_enabled", False, False, True, 1, "bool"),
            ParamDef("effects.zoom_enabled", False, False, True, 1, "bool"),
            ParamDef("effects.flow_enabled", False, False, True, 1, "bool"),
            ParamDef("effects.bbox_color", [240, 240, 240], 0, 255, 1, "color"),
            ParamDef("effects.bbox_thickness", 1, 1, 6, 1, "int"),
            ParamDef("effects.bbox_corner_style", "rect", "", "", "", "enum", ["rect", "corner"]),
            ParamDef("effects.label_color", [240, 240, 240], 0, 255, 1, "color"),
            ParamDef("effects.label_show_coords", False, False, True, 1, "bool"),
            ParamDef("effects.trail_color", [0, 229, 255], 0, 255, 1, "color"),
            ParamDef("effects.trail_alpha", 0.8, 0.0, 1.0, 0.05, "float"),
            ParamDef("effects.trail_thickness", 1, 1, 6, 1, "int"),
            ParamDef("effects.zoom_blob_id", 0, 0, 99999, 1, "int"),
            ParamDef("effects.zoom_factor", 2.0, 1.0, 6.0, 0.1, "float"),
            ParamDef("effects.zoom_corner", "top-right", "", "", "", "enum", ["top-left", "top-right", "bottom-left", "bottom-right"]),
            ParamDef("effects.blend_mode", "normal", "", "", "", "enum", ["normal", "screen", "overlay", "multiply"]),
            ParamDef("frame_desaturate", 0.0, 0.0, 1.0, 0.01, "float"),
            ParamDef("frame_grain", 0.0, 0.0, 0.2, 0.005, "float"),
            ParamDef("frame_vignette", 0.0, 0.0, 1.0, 0.01, "float"),
            ParamDef("overlay_corner_style", "ticks", "", "", "", "enum", ["full", "ticks"]),
            ParamDef("overlay_tick_length", 10, 4, 30, 1, "int"),
            ParamDef("overlay_box_opacity", 0.7, 0.0, 1.0, 0.01, "float"),
            ParamDef("overlay_show_label", True, False, True, 1, "bool"),
            ParamDef("overlay_show_area", False, False, True, 1, "bool"),
            ParamDef("overlay_show_coords", False, False, True, 1, "bool"),
            ParamDef("overlay_show_leaders", True, False, True, 1, "bool"),
            ParamDef("overlay_show_centroid", True, False, True, 1, "bool"),
            ParamDef("connection_enabled", True, False, True, 1, "bool"),
            ParamDef("connection_max_dist", 200.0, 50.0, 800.0, 1.0, "float"),
            ParamDef("connection_opacity", 0.4, 0.0, 1.0, 0.01, "float"),
            ParamDef("connection_thickness", 0.5, 0.5, 3.0, 0.5, "float"),
            ParamDef("connection_color", [255, 255, 255], 0, 255, 1, "color"),
            ParamDef("connection_show_dots", True, False, True, 1, "bool"),
            ParamDef("connection_dot_radius", 3, 1, 8, 1, "int"),
            ParamDef("trail_length", 20, 0, 60, 1, "int"),
            ParamDef("zoom_inset_enabled", False, False, True, 1, "bool"),
            ParamDef("zoom_inset_scale", 1.8, 1.0, 4.0, 0.1, "float"),
            ParamDef("detector_mode", "contour", "", "", "", "enum", ["contour", "simple_blob"]),
            ParamDef("blob_min_area", 80, 10, 5000, 1, "int"),
            ParamDef("blob_max_area", 8000, 100, 50000, 1, "int"),
            ParamDef("tracker_max_disappeared", 5, 1, 30, 1, "int"),
            ParamDef("tracker_smooth_alpha", 0.4, 0.0, 1.0, 0.01, "float"),
            ParamDef("creative.enabled", False, False, True, 1, "bool"),
            ParamDef("creative.filter_order", [], "", "", "", "list"),
            ParamDef(
                "creative.filter_params",
                {
                    "GrainFilter": {"intensity": 0.08, "grain_type": "gaussian", "colored": False},
                    "GlitchFilter": {"slices": 8, "max_offset": 24, "probability": 0.5},
                    "ThermalFilter": {"colormap": "inferno"},
                    "EdgeFilter": {"low": 80, "high": 180, "alpha": 0.7, "blur": 0},
                    "ChromaticAberration": {"shift_x": 3, "shift_y": 0, "randomize": False},
                },
                "",
                "",
                "",
                "dict",
            ),
            ParamDef("creative.grain_intensity", 0.08, 0.0, 0.3, 0.01, "float"),
            ParamDef("creative.grain_type", "gaussian", "", "", "", "enum", ["gaussian", "uniform", "colored"]),
            ParamDef("creative.grain_colored", False, False, True, 1, "bool"),
            ParamDef("fx_grain_enabled", False, False, True, 1, "bool"),
            ParamDef("fx_glitch_enabled", False, False, True, 1, "bool"),
            ParamDef("fx_thermal_enabled", False, False, True, 1, "bool"),
            ParamDef("fx_edge_enabled", False, False, True, 1, "bool"),
            ParamDef("fx_chroma_enabled", False, False, True, 1, "bool"),
            ParamDef("creative.glitch_slices", 8, 2, 32, 1, "int"),
            ParamDef("creative.glitch_offset", 24, 5, 100, 1, "int"),
            ParamDef("creative.glitch_probability", 0.5, 0.0, 1.0, 0.05, "float"),
            ParamDef("creative.edge_low_threshold", 80, 0, 255, 1, "int"),
            ParamDef("creative.edge_high_threshold", 180, 0, 255, 1, "int"),
            ParamDef("creative.edge_alpha", 0.7, 0.0, 1.0, 0.05, "float"),
            ParamDef("creative.edge_blur", 0, 0, 11, 1, "int"),
            ParamDef("creative.chroma_shift_x", 3, -20, 20, 1, "int"),
            ParamDef("creative.chroma_shift_y", 0, -20, 20, 1, "int"),
            ParamDef("creative.chroma_randomize", False, False, True, 1, "bool"),
            ParamDef("creative.thermal_colormap", "inferno", "", "", "", "enum", ["inferno", "hot", "cool", "twilight", "viridis"]),
            ParamDef("intra_blob_enabled", False, False, True, 1, "bool"),
            ParamDef(
                "intra_blob_mode",
                "thermal",
                "",
                "",
                "",
                "enum",
                ["none", "thermal", "edge", "pixelate", "negative", "blur", "highlight", "desaturate"],
            ),
            ParamDef("intra_blob_opacity", 1.0, 0.0, 1.0, 0.01, "float"),
            ParamDef("intra_blob_padding", 8, 0, 60, 1, "int"),
            ParamDef("intra_blob_feather", True, False, True, 1, "bool"),
            ParamDef("intra_blob_pixel_size", 12, 2, 40, 1, "int"),
            ParamDef("intra_blob_blur_radius", 21, 3, 61, 2, "int"),
            ParamDef("intra_blob_highlight", 1.4, 1.0, 3.0, 0.1, "float"),
            ParamDef("output.export_path", "output.mp4", "", "", "", "str"),
            ParamDef("output.format", "mp4", "", "", "", "enum", ["mp4", "png_seq", "prores"]),
            ParamDef("output.recording", False, False, True, 1, "bool"),
        ]

        for param in defaults:
            self.register(param)
