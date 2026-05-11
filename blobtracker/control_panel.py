from __future__ import annotations

import cv2
import numpy as np
from typing import Any, Dict, List

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDockWidget,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from param_store import ParamStore


class SectionBox(QGroupBox):
    def __init__(self, title: str, icon: str = "") -> None:
        display_title = f"{icon} {title}" if icon else title
        super().__init__(display_title)
        self.setCheckable(True)
        self.setChecked(True)
        self.content = QWidget()
        self.layout_root = QVBoxLayout(self)
        self.layout_root.setContentsMargins(10, 15, 10, 10)
        self.layout_root.setSpacing(8)
        self.layout_root.addWidget(self.content)
        self.inner_layout = QFormLayout(self.content)
        self.inner_layout.setContentsMargins(0, 0, 0, 0)
        self.inner_layout.setSpacing(10)
        self.inner_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.toggled.connect(self.content.setVisible)
        self.toggled.connect(self._on_toggled)

    def _on_toggled(self, on: bool) -> None:
        if on:
            self.setStyleSheet("QGroupBox { background: #1e1e1e; }")
        else:
            self.setStyleSheet("QGroupBox { background: #181818; }")


class ControlPanel(QDockWidget):
    start_source_requested = pyqtSignal()
    stop_source_requested = pyqtSignal()
    hot_reload_plugins_requested = pyqtSignal()
    play_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    render_video_requested = pyqtSignal()
    offline_render_requested = pyqtSignal(str)
    offline_render_cancel_requested = pyqtSignal()

    def __init__(self, param_store: ParamStore, parent=None) -> None:
        super().__init__("Control Panel", parent)
        self.param_store = param_store
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self._offline_render_busy = False

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        self.input_section = self._build_input_section()
        self.blob_section = self._build_blob_section()
        self.tracking_section = self._build_tracking_section()
        self.effects_section = self._build_effects_section()
        self.frame_fx_section = self._build_frame_fx_section()
        self.overlay_style_section = self._build_overlay_style_section()
        self.connection_lines_section = self._build_connection_lines_section()
        self.blob_interior_fx_section = self._build_blob_interior_fx_section()
        self.detection_mode_section = self._build_detection_mode_section()
        self.creative_section = self._build_creative_section()
        self.output_section = self._build_output_section()
        self.presets_section = self._build_presets_section()
        self.performance_section = self._build_performance_section()
        self.render_to_file_section = self._build_render_to_file_section()

        layout.addWidget(self.input_section)
        layout.addWidget(self.blob_section)
        layout.addWidget(self.tracking_section)
        layout.addWidget(self.effects_section)
        layout.addWidget(self.frame_fx_section)
        layout.addWidget(self.overlay_style_section)
        layout.addWidget(self.connection_lines_section)
        layout.addWidget(self.blob_interior_fx_section)
        layout.addWidget(self.detection_mode_section)
        layout.addWidget(self.creative_section)
        layout.addWidget(self.output_section)
        layout.addWidget(self.presets_section)
        layout.addWidget(self.performance_section)
        layout.addWidget(self.render_to_file_section)
        layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(root)

        self.setWidget(scroll)
        self.setMinimumWidth(300)
        self.param_store.params_bulk_changed.connect(self.sync_all_from_store)
        self.refresh_presets_list()
        self.refresh_filter_order()
        self.sync_all_from_store()

    def _bind_spin(self, spin: Any, key: str) -> None:
        if isinstance(spin, QSpinBox):
            spin.setValue(int(self.param_store.get(key)))
            spin.valueChanged.connect(lambda v: self.param_store.set(key, int(v)))
        else:
            spin.setValue(float(self.param_store.get(key)))
            spin.valueChanged.connect(lambda v: self.param_store.set(key, float(v)))

    def _bind_checkbox(self, checkbox: QCheckBox, key: str) -> None:
        checkbox.setChecked(bool(self.param_store.get(key)))
        checkbox.toggled.connect(lambda v: self.param_store.set(key, bool(v)))

    def _bind_check(self, checkbox: QCheckBox, key: str) -> None:
        self._bind_checkbox(checkbox, key)

    def _bind_slider(self, slider: QSlider, key: str, scale: float = 1.0) -> None:
        value = float(self.param_store.get(key))
        slider.setValue(int(round(value * scale)))
        slider.valueChanged.connect(lambda v: self.param_store.set(key, float(v) / scale))

    def _bind_combo(self, combo: QComboBox, key: str) -> None:
        value = str(self.param_store.get(key))
        idx = combo.findText(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        combo.currentTextChanged.connect(lambda t: self.param_store.set(key, t))

    def _build_input_section(self) -> SectionBox:
        section = SectionBox("Input", "📥")

        self.source_combo = QComboBox()
        self.source_combo.addItems(["webcam", "file"])
        self._bind_combo(self.source_combo, "input.source_type")
        self.source_combo.currentTextChanged.connect(lambda t: self.set_offline_render_available(t == "file"))

        self.file_path_edit = QLineEdit(str(self.param_store.get("input.source_path")))
        self.file_path_edit.setPlaceholderText("Path to video file...")
        browse_btn = QPushButton("📁 Browse")
        browse_btn.clicked.connect(self._pick_file)

        file_row = QWidget()
        file_row_layout = QHBoxLayout(file_row)
        file_row_layout.setContentsMargins(0, 0, 0, 0)
        file_row_layout.addWidget(self.file_path_edit)
        file_row_layout.addWidget(browse_btn)

        self.webcam_spin = QSpinBox()
        self.webcam_spin.setRange(0, 16)
        self._bind_spin(self.webcam_spin, "input.webcam_index")

        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 120)
        self._bind_spin(self.fps_spin, "input.target_fps")

        self.play_btn = QPushButton("▶  Play")
        self.pause_btn = QPushButton("⏸  Pause")
        self.stop_btn = QPushButton("⏹  Stop")
        self.play_btn.clicked.connect(self._play_requested)
        self.pause_btn.clicked.connect(self.pause_requested.emit)
        self.stop_btn.clicked.connect(self.stop_source_requested.emit)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)

        run_row = QWidget()
        run_layout = QHBoxLayout(run_row)
        run_layout.setContentsMargins(0, 0, 0, 0)
        run_layout.addWidget(self.play_btn)
        run_layout.addWidget(self.pause_btn)
        run_layout.addWidget(self.stop_btn)

        section.inner_layout.addRow("Source", self.source_combo)
        section.inner_layout.addRow("File", file_row)
        section.inner_layout.addRow("Webcam Index", self.webcam_spin)
        section.inner_layout.addRow("Target FPS", self.fps_spin)
        section.inner_layout.addRow(run_row)
        return section

    def _build_blob_section(self) -> SectionBox:
        section = SectionBox("Blob", "🫧")

        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(0, 255)
        self._bind_spin(self.threshold_spin, "blob.threshold")

        self.blur_spin = QSpinBox()
        self.blur_spin.setRange(1, 31)
        self.blur_spin.setSingleStep(2)
        self._bind_spin(self.blur_spin, "blob.blur_radius")

        self.min_area_spin = QDoubleSpinBox()
        self.min_area_spin.setRange(1.0, 200000.0)
        self.min_area_spin.setSingleStep(10.0)
        self._bind_spin(self.min_area_spin, "blob.min_area")

        self.max_area_spin = QDoubleSpinBox()
        self.max_area_spin.setRange(1.0, 500000.0)
        self.max_area_spin.setSingleStep(50.0)
        self._bind_spin(self.max_area_spin, "blob.max_area")

        self.max_count_spin = QSpinBox()
        self.max_count_spin.setRange(1, 300)
        self._bind_spin(self.max_count_spin, "blob.max_count")

        self.smoothing_spin = QDoubleSpinBox()
        self.smoothing_spin.setRange(0.0, 1.0)
        self.smoothing_spin.setSingleStep(0.01)
        self._bind_spin(self.smoothing_spin, "tracking.smoothing")

        section.inner_layout.addRow("Threshold", self.threshold_spin)
        section.inner_layout.addRow("Blur Radius", self.blur_spin)
        section.inner_layout.addRow("Min Area", self.min_area_spin)
        section.inner_layout.addRow("Max Area", self.max_area_spin)
        section.inner_layout.addRow("Max Blob Count", self.max_count_spin)
        section.inner_layout.addRow("Smoothing", self.smoothing_spin)
        return section

    def _build_tracking_section(self) -> SectionBox:
        section = SectionBox("Tracking", "🎯")

        self.trail_len_spin = QSpinBox()
        self.trail_len_spin.setRange(1, 500)
        self._bind_spin(self.trail_len_spin, "tracking.max_trail_length")

        self.font_spin = QDoubleSpinBox()
        self.font_spin.setRange(0.2, 2.0)
        self.font_spin.setSingleStep(0.05)
        self._bind_spin(self.font_spin, "tracking.id_font_size")

        self.offset_x = QSpinBox()
        self.offset_x.setRange(-200, 200)
        self._bind_spin(self.offset_x, "tracking.label_offset_x")

        self.offset_y = QSpinBox()
        self.offset_y.setRange(-200, 200)
        self._bind_spin(self.offset_y, "tracking.label_offset_y")

        section.inner_layout.addRow("Max Trail Length", self.trail_len_spin)
        section.inner_layout.addRow("ID Font Size", self.font_spin)
        section.inner_layout.addRow("Label Offset X", self.offset_x)
        section.inner_layout.addRow("Label Offset Y", self.offset_y)
        return section

    def _make_color_button(self, key: str) -> QPushButton:
        btn = QPushButton()
        btn.setFixedWidth(60)
        btn.setFixedHeight(24)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)

        def update_button() -> None:
            c = self.param_store.get(key)
            # Use border-radius and border for a nice swatch look
            btn.setStyleSheet(
                f"background-color: rgb({c[0]}, {c[1]}, {c[2]}); "
                "border: 2px solid #333333; "
                "border-radius: 4px;"
            )

        def pick() -> None:
            current = self.param_store.get(key)
            color = QColorDialog.getColor(QColor(current[0], current[1], current[2]), self)
            if color.isValid():
                self.param_store.set(key, [color.red(), color.green(), color.blue()])
                update_button()

        btn.clicked.connect(pick)
        update_button()
        return btn

    def _build_effects_section(self) -> SectionBox:
        section = SectionBox("Effects", "✨")

        self.bbox_enabled = QCheckBox("Bounding Box")
        self._bind_checkbox(self.bbox_enabled, "effects.bbox_enabled")

        self.label_enabled = QCheckBox("Labels")
        self._bind_checkbox(self.label_enabled, "effects.label_enabled")

        self.trail_enabled = QCheckBox("Trail")
        self._bind_checkbox(self.trail_enabled, "effects.trail_enabled")

        self.zoom_enabled = QCheckBox("Zoom Inset")
        self._bind_checkbox(self.zoom_enabled, "effects.zoom_enabled")

        self.flow_enabled = QCheckBox("Optical Flow")
        self._bind_checkbox(self.flow_enabled, "effects.flow_enabled")

        self.label_coords = QCheckBox("Show Coordinates")
        self._bind_checkbox(self.label_coords, "effects.label_show_coords")

        self.bbox_color_btn = self._make_color_button("effects.bbox_color")
        self.label_color_btn = self._make_color_button("effects.label_color")
        self.trail_color_btn = self._make_color_button("effects.trail_color")

        self.bbox_thickness = QSpinBox()
        self.bbox_thickness.setRange(1, 6)
        self._bind_spin(self.bbox_thickness, "effects.bbox_thickness")

        self.trail_alpha = QDoubleSpinBox()
        self.trail_alpha.setRange(0.0, 1.0)
        self.trail_alpha.setSingleStep(0.05)
        self._bind_spin(self.trail_alpha, "effects.trail_alpha")

        self.trail_thickness = QSpinBox()
        self.trail_thickness.setRange(1, 6)
        self._bind_spin(self.trail_thickness, "effects.trail_thickness")

        self.zoom_blob_id = QSpinBox()
        self.zoom_blob_id.setRange(0, 99999)
        self._bind_spin(self.zoom_blob_id, "effects.zoom_blob_id")

        self.zoom_factor = QDoubleSpinBox()
        self.zoom_factor.setRange(1.0, 6.0)
        self.zoom_factor.setSingleStep(0.1)
        self._bind_spin(self.zoom_factor, "effects.zoom_factor")

        self.zoom_corner = QComboBox()
        self.zoom_corner.addItems(["top-left", "top-right", "bottom-left", "bottom-right"])
        self._bind_combo(self.zoom_corner, "effects.zoom_corner")

        self.bbox_corner = QComboBox()
        self.bbox_corner.addItems(["rect", "corner"])
        self._bind_combo(self.bbox_corner, "effects.bbox_corner_style")

        self.blend_mode = QComboBox()
        self.blend_mode.addItems(["normal", "screen", "overlay", "multiply"])
        self._bind_combo(self.blend_mode, "effects.blend_mode")

        section.inner_layout.addRow(self.bbox_enabled)
        section.inner_layout.addRow(self.label_enabled)
        section.inner_layout.addRow(self.trail_enabled)
        section.inner_layout.addRow(self.zoom_enabled)
        section.inner_layout.addRow(self.flow_enabled)
        section.inner_layout.addRow(self.label_coords)
        section.inner_layout.addRow("BBox Color", self.bbox_color_btn)
        section.inner_layout.addRow("Label Color", self.label_color_btn)
        section.inner_layout.addRow("Trail Color", self.trail_color_btn)
        section.inner_layout.addRow("BBox Thickness", self.bbox_thickness)
        section.inner_layout.addRow("BBox Corner", self.bbox_corner)
        section.inner_layout.addRow("Trail Alpha", self.trail_alpha)
        section.inner_layout.addRow("Trail Thickness", self.trail_thickness)
        section.inner_layout.addRow("Zoom Blob ID", self.zoom_blob_id)
        section.inner_layout.addRow("Zoom Factor", self.zoom_factor)
        section.inner_layout.addRow("Zoom Corner", self.zoom_corner)
        section.inner_layout.addRow("Blend Mode", self.blend_mode)
        return section

    def _build_creative_section(self) -> SectionBox:
        section = SectionBox("Creative", "🎨")

        self.creative_enabled = QCheckBox("Enable Creative FX")
        self._bind_checkbox(self.creative_enabled, "creative.enabled")

        self.filter_list = QListWidget()
        self.filter_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.filter_list.model().rowsMoved.connect(lambda *args: self._on_filter_order_changed())

        reload_btn = QPushButton("Hot Reload Plugins")
        reload_btn.clicked.connect(self.hot_reload_plugins_requested.emit)

        # Grain filter block
        grain_group = QGroupBox("GrainFilter")
        grain_layout = QFormLayout(grain_group)
        self.fx_grain_enabled_cb = QCheckBox("Enable")
        self._bind_check(self.fx_grain_enabled_cb, "fx_grain_enabled")
        self.grain_intensity = QDoubleSpinBox()
        self.grain_intensity.setRange(0.0, 0.3)
        self.grain_intensity.setSingleStep(0.01)
        self.grain_type = QComboBox()
        self.grain_type.addItems(["gaussian", "uniform", "colored"])
        self._bind_combo(self.grain_type, "creative.grain_type")
        self.grain_colored = QCheckBox("Colored")
        self._bind_checkbox(self.grain_colored, "creative.grain_colored")
        self._grain_filter_widgets = [self.grain_intensity, self.grain_type, self.grain_colored]
        self.fx_grain_enabled_cb.stateChanged.connect(
            lambda v: [w.setEnabled(bool(v)) for w in self._grain_filter_widgets]
        )
        grain_layout.addRow(self.fx_grain_enabled_cb)
        grain_layout.addRow("Intensity", self.grain_intensity)
        grain_layout.addRow("Type", self.grain_type)
        grain_layout.addRow(self.grain_colored)

        # Glitch filter block
        glitch_group = QGroupBox("GlitchFilter")
        glitch_layout = QFormLayout(glitch_group)
        self.fx_glitch_enabled_cb = QCheckBox("Enable")
        self._bind_check(self.fx_glitch_enabled_cb, "fx_glitch_enabled")
        self.glitch_slices = QSpinBox()
        self.glitch_slices.setRange(2, 32)
        self.glitch_offset = QSpinBox()
        self.glitch_offset.setRange(5, 100)
        self.glitch_probability = QDoubleSpinBox()
        self.glitch_probability.setRange(0.0, 1.0)
        self.glitch_probability.setSingleStep(0.05)
        self._glitch_filter_widgets = [self.glitch_slices, self.glitch_offset, self.glitch_probability]
        self.fx_glitch_enabled_cb.stateChanged.connect(
            lambda v: [w.setEnabled(bool(v)) for w in self._glitch_filter_widgets]
        )
        glitch_layout.addRow(self.fx_glitch_enabled_cb)
        glitch_layout.addRow("Slices", self.glitch_slices)
        glitch_layout.addRow("Max Offset", self.glitch_offset)
        glitch_layout.addRow("Probability", self.glitch_probability)

        # Thermal filter block
        thermal_group = QGroupBox("ThermalFilter")
        thermal_layout = QFormLayout(thermal_group)
        self.fx_thermal_enabled_cb = QCheckBox("Enable")
        self._bind_check(self.fx_thermal_enabled_cb, "fx_thermal_enabled")
        self.thermal_colormap = QComboBox()
        self.thermal_colormap.addItems(["inferno", "hot", "cool", "twilight", "viridis"])
        self._bind_combo(self.thermal_colormap, "creative.thermal_colormap")
        self._thermal_filter_widgets = [self.thermal_colormap]
        self.fx_thermal_enabled_cb.stateChanged.connect(
            lambda v: [w.setEnabled(bool(v)) for w in self._thermal_filter_widgets]
        )
        thermal_layout.addRow(self.fx_thermal_enabled_cb)
        thermal_layout.addRow("Colormap", self.thermal_colormap)

        # Edge filter block
        edge_group = QGroupBox("EdgeFilter")
        edge_layout = QFormLayout(edge_group)
        self.fx_edge_enabled_cb = QCheckBox("Enable")
        self._bind_check(self.fx_edge_enabled_cb, "fx_edge_enabled")
        self.edge_low = QSpinBox()
        self.edge_low.setRange(0, 255)
        self.edge_high = QSpinBox()
        self.edge_high.setRange(0, 255)
        self.edge_alpha = QDoubleSpinBox()
        self.edge_alpha.setRange(0.0, 1.0)
        self.edge_alpha.setSingleStep(0.05)
        self.edge_blur = QSpinBox()
        self.edge_blur.setRange(0, 11)
        self._edge_filter_widgets = [self.edge_low, self.edge_high, self.edge_alpha, self.edge_blur]
        self.fx_edge_enabled_cb.stateChanged.connect(
            lambda v: [w.setEnabled(bool(v)) for w in self._edge_filter_widgets]
        )
        edge_layout.addRow(self.fx_edge_enabled_cb)
        edge_layout.addRow("Low Threshold", self.edge_low)
        edge_layout.addRow("High Threshold", self.edge_high)
        edge_layout.addRow("Alpha", self.edge_alpha)
        edge_layout.addRow("Blur", self.edge_blur)

        # Chromatic filter block
        chroma_group = QGroupBox("ChromaticAberration")
        chroma_layout = QFormLayout(chroma_group)
        self.fx_chroma_enabled_cb = QCheckBox("Enable")
        self._bind_check(self.fx_chroma_enabled_cb, "fx_chroma_enabled")
        self.chrom_shift_x = QSpinBox()
        self.chrom_shift_x.setRange(-20, 20)
        self.chrom_shift_y = QSpinBox()
        self.chrom_shift_y.setRange(-20, 20)
        self.chrom_randomize = QCheckBox("Randomize Shift")
        self._bind_checkbox(self.chrom_randomize, "creative.chroma_randomize")
        self._chroma_filter_widgets = [self.chrom_shift_x, self.chrom_shift_y, self.chrom_randomize]
        self.fx_chroma_enabled_cb.stateChanged.connect(
            lambda v: [w.setEnabled(bool(v)) for w in self._chroma_filter_widgets]
        )
        chroma_layout.addRow(self.fx_chroma_enabled_cb)
        chroma_layout.addRow("Shift X", self.chrom_shift_x)
        chroma_layout.addRow("Shift Y", self.chrom_shift_y)
        chroma_layout.addRow(self.chrom_randomize)

        self._sync_filter_param_widgets()

        for widget, cb in [
            (self.grain_intensity, self._sync_filter_params_from_widgets),
            (self.grain_type, self._sync_filter_params_from_widgets),
            (self.grain_colored, self._sync_filter_params_from_widgets),
            (self.fx_grain_enabled_cb, self._sync_filter_params_from_widgets),
            (self.glitch_slices, self._sync_filter_params_from_widgets),
            (self.glitch_offset, self._sync_filter_params_from_widgets),
            (self.glitch_probability, self._sync_filter_params_from_widgets),
            (self.fx_glitch_enabled_cb, self._sync_filter_params_from_widgets),
            (self.fx_thermal_enabled_cb, self._sync_filter_params_from_widgets),
            (self.edge_low, self._sync_filter_params_from_widgets),
            (self.edge_high, self._sync_filter_params_from_widgets),
            (self.edge_alpha, self._sync_filter_params_from_widgets),
            (self.edge_blur, self._sync_filter_params_from_widgets),
            (self.fx_edge_enabled_cb, self._sync_filter_params_from_widgets),
            (self.chrom_shift_x, self._sync_filter_params_from_widgets),
            (self.chrom_shift_y, self._sync_filter_params_from_widgets),
            (self.chrom_randomize, self._sync_filter_params_from_widgets),
            (self.fx_chroma_enabled_cb, self._sync_filter_params_from_widgets),
            (self.thermal_colormap, self._sync_filter_params_from_widgets),
        ]:
            if isinstance(widget, QCheckBox):
                widget.stateChanged.connect(cb)
            elif isinstance(widget, QComboBox):
                widget.currentTextChanged.connect(cb)
            else:
                widget.valueChanged.connect(cb)

        section.inner_layout.addRow(self.creative_enabled)
        section.inner_layout.addRow(QLabel("Filter Chain (drag to reorder)"))
        section.inner_layout.addRow(self.filter_list)
        section.inner_layout.addRow(reload_btn)

        section.inner_layout.addRow(grain_group)
        section.inner_layout.addRow(glitch_group)
        section.inner_layout.addRow(thermal_group)
        section.inner_layout.addRow(edge_group)
        section.inner_layout.addRow(chroma_group)
        return section

    def _build_frame_fx_section(self) -> SectionBox:
        section = SectionBox("Frame FX", "🎞️")

        self.frame_desaturate_spin = QDoubleSpinBox()
        self.frame_desaturate_spin.setRange(0.0, 1.0)
        self.frame_desaturate_spin.setSingleStep(0.01)
        self._bind_spin(self.frame_desaturate_spin, "frame_desaturate")

        self.frame_grain_spin = QDoubleSpinBox()
        self.frame_grain_spin.setRange(0.0, 0.2)
        self.frame_grain_spin.setSingleStep(0.005)
        self._bind_spin(self.frame_grain_spin, "frame_grain")

        self.frame_vignette_spin = QDoubleSpinBox()
        self.frame_vignette_spin.setRange(0.0, 1.0)
        self.frame_vignette_spin.setSingleStep(0.01)
        self._bind_spin(self.frame_vignette_spin, "frame_vignette")

        section.inner_layout.addRow("Desaturate Amount", self.frame_desaturate_spin)
        section.inner_layout.addRow("Grain Strength", self.frame_grain_spin)
        section.inner_layout.addRow("Vignette Strength", self.frame_vignette_spin)
        return section

    def _build_overlay_style_section(self) -> SectionBox:
        section = SectionBox("Overlay Style", "🖼️")

        self.overlay_corner_style_combo = QComboBox()
        self.overlay_corner_style_combo.addItem("full rect", "full")
        self.overlay_corner_style_combo.addItem("corner ticks", "ticks")
        style_value = str(self.param_store.get("overlay_corner_style"))
        for idx in range(self.overlay_corner_style_combo.count()):
            if self.overlay_corner_style_combo.itemData(idx) == style_value:
                self.overlay_corner_style_combo.setCurrentIndex(idx)
                break
        self.overlay_corner_style_combo.currentIndexChanged.connect(
            lambda idx: self.param_store.set("overlay_corner_style", self.overlay_corner_style_combo.itemData(idx))
        )
        self.overlay_corner_style_combo.currentIndexChanged.connect(
            lambda idx: self.param_store.set(
                "effects.bbox_corner_style",
                "corner" if self.overlay_corner_style_combo.itemData(idx) == "ticks" else "rect",
            )
        )

        self.overlay_tick_length_spin = QSpinBox()
        self.overlay_tick_length_spin.setRange(4, 30)
        self._bind_spin(self.overlay_tick_length_spin, "overlay_tick_length")

        self.overlay_box_opacity_spin = QDoubleSpinBox()
        self.overlay_box_opacity_spin.setRange(0.0, 1.0)
        self.overlay_box_opacity_spin.setSingleStep(0.01)
        self._bind_spin(self.overlay_box_opacity_spin, "overlay_box_opacity")

        self.overlay_show_label_cb = QCheckBox("Show ID Label")
        self._bind_checkbox(self.overlay_show_label_cb, "overlay_show_label")
        self.overlay_show_label_cb.toggled.connect(lambda v: self.param_store.set("effects.label_enabled", bool(v)))

        self.overlay_show_area_cb = QCheckBox("Show Area Readout")
        self._bind_checkbox(self.overlay_show_area_cb, "overlay_show_area")

        self.overlay_show_coords_cb = QCheckBox("Show Coord Readout")
        self._bind_checkbox(self.overlay_show_coords_cb, "overlay_show_coords")
        self.overlay_show_coords_cb.toggled.connect(lambda v: self.param_store.set("effects.label_show_coords", bool(v)))

        self.overlay_show_leaders_cb = QCheckBox("Show Leader Lines")
        self._bind_checkbox(self.overlay_show_leaders_cb, "overlay_show_leaders")

        self.overlay_show_centroid_cb = QCheckBox("Show Centroid Dot")
        self._bind_checkbox(self.overlay_show_centroid_cb, "overlay_show_centroid")

        self.trail_length_spin = QSpinBox()
        self.trail_length_spin.setRange(0, 60)
        self._bind_spin(self.trail_length_spin, "trail_length")
        self.trail_length_spin.valueChanged.connect(lambda v: self.param_store.set("tracking.max_trail_length", max(1, int(v))))

        self.zoom_inset_enabled_cb = QCheckBox("Show Zoom Inset")
        self._bind_checkbox(self.zoom_inset_enabled_cb, "zoom_inset_enabled")
        self.zoom_inset_enabled_cb.toggled.connect(lambda v: self.param_store.set("effects.zoom_enabled", bool(v)))

        section.inner_layout.addRow("Corner Style", self.overlay_corner_style_combo)
        section.inner_layout.addRow("Tick Length", self.overlay_tick_length_spin)
        section.inner_layout.addRow("Box Opacity", self.overlay_box_opacity_spin)
        section.inner_layout.addRow(self.overlay_show_label_cb)
        section.inner_layout.addRow(self.overlay_show_area_cb)
        section.inner_layout.addRow(self.overlay_show_coords_cb)
        section.inner_layout.addRow(self.overlay_show_leaders_cb)
        section.inner_layout.addRow(self.overlay_show_centroid_cb)
        section.inner_layout.addRow("Trail Length", self.trail_length_spin)
        section.inner_layout.addRow(self.zoom_inset_enabled_cb)
        return section

    def _build_connection_lines_section(self) -> SectionBox:
        section = SectionBox("Connection Lines", "🔗")
        section.setChecked(False)

        self.connection_enabled_cb = QCheckBox("Enable Connections")
        self._bind_checkbox(self.connection_enabled_cb, "connection_enabled")

        self.connection_max_dist_slider = QSlider(Qt.Orientation.Horizontal)
        self.connection_max_dist_slider.setRange(50, 800)
        self.connection_max_dist_slider.setSingleStep(1)
        self.connection_max_dist_slider.setValue(int(round(float(self.param_store.get("connection_max_dist")))))
        self.connection_max_dist_label = QLabel("{} px".format(int(round(float(self.param_store.get("connection_max_dist"))))))

        max_dist_row = QWidget()
        max_dist_layout = QHBoxLayout(max_dist_row)
        max_dist_layout.setContentsMargins(0, 0, 0, 0)
        max_dist_layout.addWidget(self.connection_max_dist_slider)
        max_dist_layout.addWidget(self.connection_max_dist_label)

        def on_connection_max_dist(v: int) -> None:
            dist = float(v)
            self.connection_max_dist_label.setText("{} px".format(int(v)))
            self.param_store.set("connection_max_dist", dist)

        self.connection_max_dist_slider.valueChanged.connect(on_connection_max_dist)

        self.connection_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.connection_opacity_slider.setRange(0, 100)
        self.connection_opacity_slider.setSingleStep(1)
        self.connection_opacity_slider.setValue(int(round(float(self.param_store.get("connection_opacity")) * 100.0)))
        self.connection_opacity_label = QLabel("{:.2f}".format(float(self.param_store.get("connection_opacity"))))

        opacity_row = QWidget()
        opacity_layout = QHBoxLayout(opacity_row)
        opacity_layout.setContentsMargins(0, 0, 0, 0)
        opacity_layout.addWidget(self.connection_opacity_slider)
        opacity_layout.addWidget(self.connection_opacity_label)

        def on_connection_opacity(v: int) -> None:
            alpha = float(v) / 100.0
            self.connection_opacity_label.setText("{:.2f}".format(alpha))
            self.param_store.set("connection_opacity", alpha)

        self.connection_opacity_slider.valueChanged.connect(on_connection_opacity)

        self.connection_thickness_slider = QSlider(Qt.Orientation.Horizontal)
        self.connection_thickness_slider.setRange(1, 6)
        self.connection_thickness_slider.setSingleStep(1)
        self.connection_thickness_slider.setValue(int(round(float(self.param_store.get("connection_thickness")) * 2.0)))
        self.connection_thickness_label = QLabel("{:.1f}".format(float(self.param_store.get("connection_thickness"))))

        thickness_row = QWidget()
        thickness_layout = QHBoxLayout(thickness_row)
        thickness_layout.setContentsMargins(0, 0, 0, 0)
        thickness_layout.addWidget(self.connection_thickness_slider)
        thickness_layout.addWidget(self.connection_thickness_label)

        def on_connection_thickness(v: int) -> None:
            thickness = float(v) / 2.0
            self.connection_thickness_label.setText("{:.1f}".format(thickness))
            self.param_store.set("connection_thickness", thickness)

        self.connection_thickness_slider.valueChanged.connect(on_connection_thickness)

        self.connection_show_dots_cb = QCheckBox("Show Junction Dots")
        self._bind_checkbox(self.connection_show_dots_cb, "connection_show_dots")

        self.connection_dot_radius_spin = QSpinBox()
        self.connection_dot_radius_spin.setRange(1, 8)
        self._bind_spin(self.connection_dot_radius_spin, "connection_dot_radius")

        self.connection_color_btn = self._make_color_button("connection_color")

        section.inner_layout.addRow(self.connection_enabled_cb)
        section.inner_layout.addRow("Max Distance", max_dist_row)
        section.inner_layout.addRow("Line Opacity", opacity_row)
        section.inner_layout.addRow("Line Thickness", thickness_row)
        section.inner_layout.addRow(self.connection_show_dots_cb)
        section.inner_layout.addRow("Dot Radius", self.connection_dot_radius_spin)
        section.inner_layout.addRow("Color", self.connection_color_btn)
        return section

    def _build_blob_interior_fx_section(self) -> SectionBox:
        section = SectionBox("Blob Interior FX", "💎")
        section.setChecked(False)

        self.intra_blob_enabled_cb = QCheckBox("Enable blob interior FX")
        self._bind_check(self.intra_blob_enabled_cb, "intra_blob_enabled")

        self.intra_blob_mode_combo = QComboBox()
        self.intra_blob_mode_combo.addItems(
            ["none", "thermal", "edge", "pixelate", "negative", "blur", "highlight", "desaturate"]
        )
        self._bind_combo(self.intra_blob_mode_combo, "intra_blob_mode")

        self.intra_blob_opacity_spin = QDoubleSpinBox()
        self.intra_blob_opacity_spin.setRange(0.0, 1.0)
        self.intra_blob_opacity_spin.setSingleStep(0.01)
        self._bind_spin(self.intra_blob_opacity_spin, "intra_blob_opacity")

        self.intra_blob_padding_spin = QSpinBox()
        self.intra_blob_padding_spin.setRange(0, 60)
        self._bind_spin(self.intra_blob_padding_spin, "intra_blob_padding")

        self.intra_blob_feather_cb = QCheckBox("Feather edges")
        self._bind_check(self.intra_blob_feather_cb, "intra_blob_feather")

        self.intra_blob_pixel_size_spin = QSpinBox()
        self.intra_blob_pixel_size_spin.setRange(2, 40)
        self._bind_spin(self.intra_blob_pixel_size_spin, "intra_blob_pixel_size")

        self.intra_blob_blur_radius_spin = QSpinBox()
        self.intra_blob_blur_radius_spin.setRange(3, 61)
        self.intra_blob_blur_radius_spin.setSingleStep(2)
        self._bind_spin(self.intra_blob_blur_radius_spin, "intra_blob_blur_radius")

        self.intra_blob_highlight_spin = QDoubleSpinBox()
        self.intra_blob_highlight_spin.setRange(1.0, 3.0)
        self.intra_blob_highlight_spin.setSingleStep(0.1)
        self._bind_spin(self.intra_blob_highlight_spin, "intra_blob_highlight")

        self._intra_blob_pixel_label = QLabel("Pixel size")
        self._intra_blob_blur_label = QLabel("Blur radius")
        self._intra_blob_highlight_label = QLabel("Brightness")

        section.inner_layout.addRow(self.intra_blob_enabled_cb)
        section.inner_layout.addRow("Mode", self.intra_blob_mode_combo)
        section.inner_layout.addRow("Opacity", self.intra_blob_opacity_spin)
        section.inner_layout.addRow("Padding", self.intra_blob_padding_spin)
        section.inner_layout.addRow(self.intra_blob_feather_cb)
        section.inner_layout.addRow(self._intra_blob_pixel_label, self.intra_blob_pixel_size_spin)
        section.inner_layout.addRow(self._intra_blob_blur_label, self.intra_blob_blur_radius_spin)
        section.inner_layout.addRow(self._intra_blob_highlight_label, self.intra_blob_highlight_spin)

        self.intra_blob_mode_combo.currentIndexChanged.connect(self._update_intra_blob_visibility)
        self._update_intra_blob_visibility()
        return section

    def _update_intra_blob_visibility(self) -> None:
        mode = str(self.intra_blob_mode_combo.currentText()).lower()
        is_pixelate = mode == "pixelate"
        is_blur = mode == "blur"
        is_highlight = mode == "highlight"

        self._intra_blob_pixel_label.setVisible(is_pixelate)
        self.intra_blob_pixel_size_spin.setVisible(is_pixelate)
        self._intra_blob_blur_label.setVisible(is_blur)
        self.intra_blob_blur_radius_spin.setVisible(is_blur)
        self._intra_blob_highlight_label.setVisible(is_highlight)
        self.intra_blob_highlight_spin.setVisible(is_highlight)

    def _build_detection_mode_section(self) -> SectionBox:
        section = SectionBox("Detection Mode", "🔍")

        self.detector_mode_combo = QComboBox()
        self.detector_mode_combo.addItem("Contour", "contour")
        self.detector_mode_combo.addItem("Simple Blob", "simple_blob")
        mode_value = str(self.param_store.get("detector_mode"))
        for idx in range(self.detector_mode_combo.count()):
            if self.detector_mode_combo.itemData(idx) == mode_value:
                self.detector_mode_combo.setCurrentIndex(idx)
                break
        self.detector_mode_combo.currentIndexChanged.connect(
            lambda idx: self.param_store.set("detector_mode", self.detector_mode_combo.itemData(idx))
        )

        self.blob_min_area_spin = QSpinBox()
        self.blob_min_area_spin.setRange(10, 5000)
        self._bind_spin(self.blob_min_area_spin, "blob_min_area")
        self.blob_min_area_spin.valueChanged.connect(lambda v: self.param_store.set("blob.min_area", float(v)))

        self.blob_max_area_spin = QSpinBox()
        self.blob_max_area_spin.setRange(100, 50000)
        self._bind_spin(self.blob_max_area_spin, "blob_max_area")
        self.blob_max_area_spin.valueChanged.connect(lambda v: self.param_store.set("blob.max_area", float(v)))

        self.disappeared_frames_spin = QSpinBox()
        self.disappeared_frames_spin.setRange(1, 30)
        self._bind_spin(self.disappeared_frames_spin, "tracker_max_disappeared")

        self.centroid_smoothing_alpha_spin = QDoubleSpinBox()
        self.centroid_smoothing_alpha_spin.setRange(0.0, 1.0)
        self.centroid_smoothing_alpha_spin.setSingleStep(0.01)
        self._bind_spin(self.centroid_smoothing_alpha_spin, "tracker_smooth_alpha")
        self.centroid_smoothing_alpha_spin.valueChanged.connect(lambda v: self.param_store.set("tracking.smoothing", float(v)))

        section.inner_layout.addRow("Detector Mode", self.detector_mode_combo)
        section.inner_layout.addRow("Min Area", self.blob_min_area_spin)
        section.inner_layout.addRow("Max Area", self.blob_max_area_spin)
        section.inner_layout.addRow("Disappeared Frames", self.disappeared_frames_spin)
        section.inner_layout.addRow("Centroid Smoothing Alpha", self.centroid_smoothing_alpha_spin)
        return section

    def _build_output_section(self) -> SectionBox:
        section = SectionBox("Output", "📤")

        self.export_path_edit = QLineEdit(str(self.param_store.get("output.export_path")))
        pick_btn = QPushButton("Browse")
        pick_btn.clicked.connect(self._pick_export)

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(self.export_path_edit)
        row_layout.addWidget(pick_btn)

        self.output_format = QComboBox()
        self.output_format.addItems(["mp4", "png_seq", "prores"])
        self._bind_combo(self.output_format, "output.format")

        self.record_btn = QPushButton("Start Record")
        self.record_btn.clicked.connect(self._toggle_record)

        self.render_btn = QPushButton("⏺  Render Video")
        self.render_btn.clicked.connect(self.render_video_requested.emit)
        self.render_btn.setToolTip("Play the entire video from start to finish and save the processed result")

        rec_row = QWidget()
        rec_layout = QHBoxLayout(rec_row)
        rec_layout.setContentsMargins(0, 0, 0, 0)
        rec_layout.addWidget(self.record_btn)
        rec_layout.addWidget(self.render_btn)

        section.inner_layout.addRow("Export Path", row)
        section.inner_layout.addRow("Format", self.output_format)
        section.inner_layout.addRow(rec_row)
        return section

    def _build_presets_section(self) -> SectionBox:
        section = SectionBox("Presets", "💾")

        self.preset_name_edit = QLineEdit("default")
        self.preset_list = QListWidget()

        save_btn = QPushButton("Save")
        load_btn = QPushButton("Load")
        delete_btn = QPushButton("Delete")

        save_btn.clicked.connect(self._save_preset)
        load_btn.clicked.connect(self._load_selected_preset)
        delete_btn.clicked.connect(self._delete_selected_preset)

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(save_btn)
        row_layout.addWidget(load_btn)
        row_layout.addWidget(delete_btn)

        section.inner_layout.addRow("Preset Name", self.preset_name_edit)
        section.inner_layout.addRow(self.preset_list)
        section.inner_layout.addRow(row)
        return section

    def _build_performance_section(self) -> SectionBox:
        section = SectionBox("Performance", "⚡")

        self.process_scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.process_scale_slider.setRange(25, 100)
        self.process_scale_slider.setSingleStep(5)
        self.process_scale_slider.setPageStep(5)
        self.process_scale_slider.setValue(int(round(float(self.param_store.get("process_scale")) * 100)))
        self.process_scale_value = QLabel("{:.2f}".format(float(self.param_store.get("process_scale"))))
        self.process_scale_hint = QLabel("0.5 = half res (recommended)")

        scale_row = QWidget()
        scale_layout = QHBoxLayout(scale_row)
        scale_layout.setContentsMargins(0, 0, 0, 0)
        scale_layout.addWidget(self.process_scale_slider)
        scale_layout.addWidget(self.process_scale_value)

        def on_scale_changed(v: int) -> None:
            snapped = max(25, min(100, int(round(v / 5.0) * 5)))
            scale = float(snapped / 100.0)
            self.process_scale_value.setText("{:.2f}".format(scale))
            self.param_store.set("process_scale", scale)

        self.process_scale_slider.valueChanged.connect(on_scale_changed)

        self.detect_every_spin = QSpinBox()
        self.detect_every_spin.setRange(1, 4)
        self._bind_spin(self.detect_every_spin, "detect_every_n")
        self.detect_every_hint = QLabel("1 = every frame, 2 = skip 1 (recommended)")

        self.min_label_area_spin = QSpinBox()
        self.min_label_area_spin.setRange(0, 2000)
        self._bind_spin(self.min_label_area_spin, "min_label_area")
        self.min_label_hint = QLabel("skip labels on small blobs")

        self.performance_fps_label = QLabel("FPS: 0.0")

        section.inner_layout.addRow("Process Scale", scale_row)
        section.inner_layout.addRow(self.process_scale_hint)
        section.inner_layout.addRow("Detect Every N", self.detect_every_spin)
        section.inner_layout.addRow(self.detect_every_hint)
        section.inner_layout.addRow("Min Label Area", self.min_label_area_spin)
        section.inner_layout.addRow(self.min_label_hint)
        section.inner_layout.addRow("FPS Display", self.performance_fps_label)
        return section

    def set_performance_fps(self, fps: float) -> None:
        self.performance_fps_label.setText("FPS: {:.1f}".format(float(fps)))

    def _build_render_to_file_section(self) -> SectionBox:
        section = SectionBox("Render to File", "🎬")

        info = QLabel("Offline render - processes every frame at full quality")

        self.render_output_edit = QLineEdit(str(self.param_store.get("output.export_path")))
        self.render_output_browse = QPushButton("Browse")
        self.render_output_browse.clicked.connect(self._pick_render_output)

        output_row = QWidget()
        output_layout = QHBoxLayout(output_row)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_layout.addWidget(self.render_output_edit)
        output_layout.addWidget(self.render_output_browse)

        self.render_to_file_btn = QPushButton("Render to File")
        self.render_to_file_btn.clicked.connect(self._start_offline_render)
        self.render_to_file_btn.setToolTip("Render requires a video file")

        self.cancel_render_btn = QPushButton("Cancel")
        self.cancel_render_btn.clicked.connect(self.offline_render_cancel_requested.emit)
        self.cancel_render_btn.setVisible(False)

        action_row = QWidget()
        action_layout = QHBoxLayout(action_row)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.addWidget(self.render_to_file_btn)
        action_layout.addWidget(self.cancel_render_btn)

        self.render_progress = QProgressBar()
        self.render_progress.setRange(0, 100)
        self.render_progress.setValue(0)
        self.render_progress.setVisible(False)

        self.render_status_label = QLabel("Idle")

        self.render_thumb = QLabel()
        self.render_thumb.setFixedSize(120, 68)
        self.render_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.render_thumb.setStyleSheet("background: #141414; border: 1px solid #2c2c2c;")
        self.render_thumb.setText("No preview")

        section.inner_layout.addRow(info)
        section.inner_layout.addRow("Output Path", output_row)
        section.inner_layout.addRow(action_row)
        section.inner_layout.addRow(self.render_progress)
        section.inner_layout.addRow("Status", self.render_status_label)
        section.inner_layout.addRow("Thumbnail", self.render_thumb)
        return section

    def _pick_render_output(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Render to File Output", "render_output.mp4", "Video (*.mp4 *.mov *.avi)")
        if path:
            self.render_output_edit.setText(path)

    def _start_offline_render(self) -> None:
        output_path = self.render_output_edit.text().strip()
        if not output_path:
            return
        self.offline_render_requested.emit(output_path)

    def set_offline_render_available(self, is_file_source: bool) -> None:
        if self._offline_render_busy:
            return
        self.render_to_file_btn.setEnabled(bool(is_file_source))
        if is_file_source:
            self.render_to_file_btn.setToolTip("")
        else:
            self.render_to_file_btn.setToolTip("Render requires a video file")

    def set_offline_render_running(self, running: bool) -> None:
        self._offline_render_busy = bool(running)
        self.cancel_render_btn.setVisible(bool(running))
        self.render_progress.setVisible(bool(running))
        self.render_output_edit.setEnabled(not running)
        self.render_output_browse.setEnabled(not running)
        self.render_to_file_btn.setEnabled(not running and str(self.param_store.get("input.source_type")) == "file")

    def set_offline_render_progress(self, percent: int, frame_text: str = "") -> None:
        self.render_progress.setValue(max(0, min(100, int(percent))))
        if frame_text:
            self.render_status_label.setText(frame_text)

    def set_offline_render_status(self, text: str) -> None:
        self.render_status_label.setText(str(text))

    def update_render_thumbnail(self, frame_bgr: np.ndarray) -> None:
        if frame_bgr is None or not hasattr(frame_bgr, "shape"):
            return
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w, c = rgb.shape
        image = QImage(rgb.data, w, h, c * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(image)
        self.render_thumb.setPixmap(
            pixmap.scaled(
                self.render_thumb.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _pick_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Video", "", "Media (*.mp4 *.mov *.avi *.png)")
        if path:
            self.file_path_edit.setText(path)
            self.param_store.set("input.source_path", path)

    def _pick_export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export Path", "output.mp4", "Video (*.mp4)")
        if path:
            self.export_path_edit.setText(path)
            self.param_store.set("output.export_path", path)

    def _start_requested(self) -> None:
        self.param_store.set("input.source_type", self.source_combo.currentText())
        self.param_store.set("input.source_path", self.file_path_edit.text().strip())
        self.param_store.set("input.webcam_index", self.webcam_spin.value())
        self.param_store.set("input.target_fps", self.fps_spin.value())
        self.start_source_requested.emit()

    def _play_requested(self) -> None:
        self.param_store.set("input.source_type", self.source_combo.currentText())
        self.param_store.set("input.source_path", self.file_path_edit.text().strip())
        self.param_store.set("input.webcam_index", self.webcam_spin.value())
        self.param_store.set("input.target_fps", self.fps_spin.value())
        self.play_requested.emit()

    def update_playback_state(self, state: str) -> None:
        """Update button states. state: 'stopped', 'playing', 'paused'."""
        self.play_btn.setEnabled(state != "playing")
        self.pause_btn.setEnabled(state == "playing")
        self.stop_btn.setEnabled(state != "stopped")
        self.render_btn.setEnabled(state == "stopped")

    def _toggle_record(self) -> None:
        recording = bool(self.param_store.get("output.recording"))
        new_state = not recording
        self.param_store.set("output.export_path", self.export_path_edit.text().strip())
        self.param_store.set("output.recording", new_state)
        self.record_btn.setText("Stop Record" if new_state else "Start Record")

    def _save_preset(self) -> None:
        name = self.preset_name_edit.text().strip()
        if not name:
            return
        self.param_store.save_preset(name)
        self.refresh_presets_list()

    def _load_selected_preset(self) -> None:
        item = self.preset_list.currentItem()
        if not item:
            return
        self.param_store.load_preset(item.text())
        self.refresh_filter_order()
        self._sync_filter_param_widgets()

    def _delete_selected_preset(self) -> None:
        item = self.preset_list.currentItem()
        if not item:
            return
        self.param_store.delete_preset(item.text())
        self.refresh_presets_list()

    def refresh_presets_list(self) -> None:
        self.preset_list.clear()
        for preset in self.param_store.list_presets():
            self.preset_list.addItem(QListWidgetItem(preset))

    def refresh_filter_order(self) -> None:
        self.filter_list.clear()
        for name in list(self.param_store.get("creative.filter_order")):
            self.filter_list.addItem(QListWidgetItem(name))

    def _on_filter_order_changed(self) -> None:
        order = [self.filter_list.item(i).text() for i in range(self.filter_list.count())]
        self.param_store.set("creative.filter_order", order)

    def _sync_filter_param_widgets(self) -> None:
        """Sync widget values from param_store"""
        params: Dict[str, Dict[str, Any]] = dict(self.param_store.get("creative.filter_params"))
        grain = params.get("GrainFilter", {})
        glitch = params.get("GlitchFilter", {})
        edge = params.get("EdgeFilter", {})
        chrom = params.get("ChromaticAberration", {})
        thermal = params.get("ThermalFilter", {})

        # Grain
        self.grain_intensity.setValue(float(grain.get("intensity", 0.08)))
        self.grain_type.setCurrentText(str(grain.get("grain_type", "gaussian")))
        self.grain_colored.setChecked(bool(grain.get("colored", False)))

        # Glitch
        self.glitch_slices.setValue(int(glitch.get("slices", 8)))
        self.glitch_offset.setValue(int(glitch.get("max_offset", 24)))
        self.glitch_probability.setValue(float(glitch.get("probability", 0.5)))

        # Edge
        self.edge_low.setValue(int(edge.get("low", 80)))
        self.edge_high.setValue(int(edge.get("high", 180)))
        self.edge_alpha.setValue(float(edge.get("alpha", 0.7)))
        self.edge_blur.setValue(int(edge.get("blur", 0)))

        # Chromatic
        self.chrom_shift_x.setValue(int(chrom.get("shift_x", 3)))
        self.chrom_shift_y.setValue(int(chrom.get("shift_y", 0)))
        self.chrom_randomize.setChecked(bool(chrom.get("randomize", False)))

        # Thermal
        self.thermal_colormap.setCurrentText(str(thermal.get("colormap", "inferno")))

        self.fx_grain_enabled_cb.setChecked(bool(self.param_store.get("fx_grain_enabled")))
        self.fx_glitch_enabled_cb.setChecked(bool(self.param_store.get("fx_glitch_enabled")))
        self.fx_thermal_enabled_cb.setChecked(bool(self.param_store.get("fx_thermal_enabled")))
        self.fx_edge_enabled_cb.setChecked(bool(self.param_store.get("fx_edge_enabled")))
        self.fx_chroma_enabled_cb.setChecked(bool(self.param_store.get("fx_chroma_enabled")))

        for w in self._grain_filter_widgets:
            w.setEnabled(self.fx_grain_enabled_cb.isChecked())
        for w in self._glitch_filter_widgets:
            w.setEnabled(self.fx_glitch_enabled_cb.isChecked())
        for w in self._thermal_filter_widgets:
            w.setEnabled(self.fx_thermal_enabled_cb.isChecked())
        for w in self._edge_filter_widgets:
            w.setEnabled(self.fx_edge_enabled_cb.isChecked())
        for w in self._chroma_filter_widgets:
            w.setEnabled(self.fx_chroma_enabled_cb.isChecked())

        # Also sync from individual param_store entries
        self.param_store.set("creative.grain_intensity", self.grain_intensity.value(), emit=False)
        self.param_store.set("creative.grain_type", self.grain_type.currentText(), emit=False)
        self.param_store.set("creative.grain_colored", self.grain_colored.isChecked(), emit=False)
        self.param_store.set("creative.glitch_slices", self.glitch_slices.value(), emit=False)
        self.param_store.set("creative.glitch_offset", self.glitch_offset.value(), emit=False)
        self.param_store.set("creative.glitch_probability", self.glitch_probability.value(), emit=False)
        self.param_store.set("creative.edge_low_threshold", self.edge_low.value(), emit=False)
        self.param_store.set("creative.edge_high_threshold", self.edge_high.value(), emit=False)
        self.param_store.set("creative.edge_alpha", self.edge_alpha.value(), emit=False)
        self.param_store.set("creative.edge_blur", self.edge_blur.value(), emit=False)
        self.param_store.set("creative.chroma_shift_x", self.chrom_shift_x.value(), emit=False)
        self.param_store.set("creative.chroma_shift_y", self.chrom_shift_y.value(), emit=False)
        self.param_store.set("creative.chroma_randomize", self.chrom_randomize.isChecked(), emit=False)
        self.param_store.set("creative.thermal_colormap", self.thermal_colormap.currentText(), emit=False)

    def _sync_filter_params_from_widgets(self) -> None:
        """Sync param_store from widget values"""
        # Update individual control parameters
        self.param_store.set("creative.grain_intensity", float(self.grain_intensity.value()), emit=False)
        self.param_store.set("creative.grain_type", str(self.grain_type.currentText()), emit=False)
        self.param_store.set("creative.grain_colored", bool(self.grain_colored.isChecked()), emit=False)
        self.param_store.set("creative.glitch_slices", int(self.glitch_slices.value()), emit=False)
        self.param_store.set("creative.glitch_offset", int(self.glitch_offset.value()), emit=False)
        self.param_store.set("creative.glitch_probability", float(self.glitch_probability.value()), emit=False)
        self.param_store.set("creative.edge_low_threshold", int(self.edge_low.value()), emit=False)
        self.param_store.set("creative.edge_high_threshold", int(self.edge_high.value()), emit=False)
        self.param_store.set("creative.edge_alpha", float(self.edge_alpha.value()), emit=False)
        self.param_store.set("creative.edge_blur", int(self.edge_blur.value()), emit=False)
        self.param_store.set("creative.chroma_shift_x", int(self.chrom_shift_x.value()), emit=False)
        self.param_store.set("creative.chroma_shift_y", int(self.chrom_shift_y.value()), emit=False)
        self.param_store.set("creative.chroma_randomize", bool(self.chrom_randomize.isChecked()), emit=False)
        self.param_store.set("creative.thermal_colormap", str(self.thermal_colormap.currentText()), emit=False)
        
        # Also update the unified filter_params dict for backward compatibility
        params: Dict[str, Dict[str, Any]] = dict(self.param_store.get("creative.filter_params"))
        params.setdefault("GrainFilter", {})["intensity"] = float(self.grain_intensity.value())
        params["GrainFilter"]["grain_type"] = str(self.grain_type.currentText())
        params["GrainFilter"]["colored"] = bool(self.grain_colored.isChecked())
        
        params.setdefault("GlitchFilter", {})["slices"] = int(self.glitch_slices.value())
        params["GlitchFilter"]["max_offset"] = int(self.glitch_offset.value())
        params["GlitchFilter"]["probability"] = float(self.glitch_probability.value())
        
        params.setdefault("EdgeFilter", {})["low"] = int(self.edge_low.value())
        params["EdgeFilter"]["high"] = int(self.edge_high.value())
        params["EdgeFilter"]["alpha"] = float(self.edge_alpha.value())
        params["EdgeFilter"]["blur"] = int(self.edge_blur.value())
        
        params.setdefault("ChromaticAberration", {})["shift_x"] = int(self.chrom_shift_x.value())
        params["ChromaticAberration"]["shift_y"] = int(self.chrom_shift_y.value())
        params["ChromaticAberration"]["randomize"] = bool(self.chrom_randomize.isChecked())
        
        params.setdefault("ThermalFilter", {})["colormap"] = str(self.thermal_colormap.currentText())

        self.param_store.set("creative.filter_params", params)

    def sync_all_from_store(self) -> None:
        self.source_combo.setCurrentText(str(self.param_store.get("input.source_type")))
        self.file_path_edit.setText(str(self.param_store.get("input.source_path")))
        self.webcam_spin.setValue(int(self.param_store.get("input.webcam_index")))
        self.fps_spin.setValue(int(self.param_store.get("input.target_fps")))

        self.threshold_spin.setValue(int(self.param_store.get("blob.threshold")))
        self.blur_spin.setValue(int(self.param_store.get("blob.blur_radius")))
        self.min_area_spin.setValue(float(self.param_store.get("blob.min_area")))
        self.max_area_spin.setValue(float(self.param_store.get("blob.max_area")))
        self.max_count_spin.setValue(int(self.param_store.get("blob.max_count")))
        self.process_scale_slider.setValue(int(round(float(self.param_store.get("process_scale")) * 100)))
        self.process_scale_value.setText("{:.2f}".format(float(self.param_store.get("process_scale"))))
        self.detect_every_spin.setValue(int(self.param_store.get("detect_every_n")))
        self.min_label_area_spin.setValue(int(self.param_store.get("min_label_area")))
        self.smoothing_spin.setValue(float(self.param_store.get("tracking.smoothing")))

        self.trail_len_spin.setValue(int(self.param_store.get("tracking.max_trail_length")))
        self.font_spin.setValue(float(self.param_store.get("tracking.id_font_size")))
        self.offset_x.setValue(int(self.param_store.get("tracking.label_offset_x")))
        self.offset_y.setValue(int(self.param_store.get("tracking.label_offset_y")))

        self.bbox_enabled.setChecked(bool(self.param_store.get("effects.bbox_enabled")))
        self.label_enabled.setChecked(bool(self.param_store.get("effects.label_enabled")))
        self.trail_enabled.setChecked(bool(self.param_store.get("effects.trail_enabled")))
        self.zoom_enabled.setChecked(bool(self.param_store.get("effects.zoom_enabled")))
        self.flow_enabled.setChecked(bool(self.param_store.get("effects.flow_enabled")))
        self.label_coords.setChecked(bool(self.param_store.get("effects.label_show_coords")))
        self.bbox_thickness.setValue(int(self.param_store.get("effects.bbox_thickness")))
        self.trail_alpha.setValue(float(self.param_store.get("effects.trail_alpha")))
        self.trail_thickness.setValue(int(self.param_store.get("effects.trail_thickness")))
        self.zoom_blob_id.setValue(int(self.param_store.get("effects.zoom_blob_id")))
        self.zoom_factor.setValue(float(self.param_store.get("effects.zoom_factor")))
        self.zoom_corner.setCurrentText(str(self.param_store.get("effects.zoom_corner")))
        self.bbox_corner.setCurrentText(str(self.param_store.get("effects.bbox_corner_style")))
        self.blend_mode.setCurrentText(str(self.param_store.get("effects.blend_mode")))

        self.frame_desaturate_spin.setValue(float(self.param_store.get("frame_desaturate")))
        self.frame_grain_spin.setValue(float(self.param_store.get("frame_grain")))
        self.frame_vignette_spin.setValue(float(self.param_store.get("frame_vignette")))

        overlay_corner = str(self.param_store.get("overlay_corner_style"))
        for idx in range(self.overlay_corner_style_combo.count()):
            if self.overlay_corner_style_combo.itemData(idx) == overlay_corner:
                self.overlay_corner_style_combo.setCurrentIndex(idx)
                break
        self.overlay_tick_length_spin.setValue(int(self.param_store.get("overlay_tick_length")))
        self.overlay_box_opacity_spin.setValue(float(self.param_store.get("overlay_box_opacity")))
        self.overlay_show_label_cb.setChecked(bool(self.param_store.get("overlay_show_label")))
        self.overlay_show_area_cb.setChecked(bool(self.param_store.get("overlay_show_area")))
        self.overlay_show_coords_cb.setChecked(bool(self.param_store.get("overlay_show_coords")))
        self.overlay_show_leaders_cb.setChecked(bool(self.param_store.get("overlay_show_leaders")))
        self.overlay_show_centroid_cb.setChecked(bool(self.param_store.get("overlay_show_centroid")))

        self.connection_enabled_cb.setChecked(bool(self.param_store.get("connection_enabled")))
        self.connection_max_dist_slider.setValue(int(round(float(self.param_store.get("connection_max_dist")))))
        self.connection_max_dist_label.setText("{} px".format(int(round(float(self.param_store.get("connection_max_dist"))))))
        self.connection_opacity_slider.setValue(int(round(float(self.param_store.get("connection_opacity")) * 100.0)))
        self.connection_opacity_label.setText("{:.2f}".format(float(self.param_store.get("connection_opacity"))))
        self.connection_thickness_slider.setValue(int(round(float(self.param_store.get("connection_thickness")) * 2.0)))
        self.connection_thickness_label.setText("{:.1f}".format(float(self.param_store.get("connection_thickness"))))
        self.connection_show_dots_cb.setChecked(bool(self.param_store.get("connection_show_dots")))
        self.connection_dot_radius_spin.setValue(int(self.param_store.get("connection_dot_radius")))

        self.intra_blob_enabled_cb.setChecked(bool(self.param_store.get("intra_blob_enabled")))
        self.intra_blob_mode_combo.setCurrentText(str(self.param_store.get("intra_blob_mode")))
        self.intra_blob_opacity_spin.setValue(float(self.param_store.get("intra_blob_opacity")))
        self.intra_blob_padding_spin.setValue(int(self.param_store.get("intra_blob_padding")))
        self.intra_blob_feather_cb.setChecked(bool(self.param_store.get("intra_blob_feather")))
        self.intra_blob_pixel_size_spin.setValue(int(self.param_store.get("intra_blob_pixel_size")))
        self.intra_blob_blur_radius_spin.setValue(int(self.param_store.get("intra_blob_blur_radius")))
        self.intra_blob_highlight_spin.setValue(float(self.param_store.get("intra_blob_highlight")))
        self._update_intra_blob_visibility()

        self.trail_length_spin.setValue(int(self.param_store.get("trail_length")))
        self.zoom_inset_enabled_cb.setChecked(bool(self.param_store.get("zoom_inset_enabled")))

        detector_mode = str(self.param_store.get("detector_mode"))
        for idx in range(self.detector_mode_combo.count()):
            if self.detector_mode_combo.itemData(idx) == detector_mode:
                self.detector_mode_combo.setCurrentIndex(idx)
                break
        self.blob_min_area_spin.setValue(int(self.param_store.get("blob_min_area")))
        self.blob_max_area_spin.setValue(int(self.param_store.get("blob_max_area")))
        self.disappeared_frames_spin.setValue(int(self.param_store.get("tracker_max_disappeared")))
        self.centroid_smoothing_alpha_spin.setValue(float(self.param_store.get("tracker_smooth_alpha")))

        self.creative_enabled.setChecked(bool(self.param_store.get("creative.enabled")))
        self.refresh_filter_order()
        self._sync_filter_param_widgets()

        self.export_path_edit.setText(str(self.param_store.get("output.export_path")))
        self.output_format.setCurrentText(str(self.param_store.get("output.format")))
        recording = bool(self.param_store.get("output.recording"))
        self.record_btn.setText("Stop Record" if recording else "Start Record")
        self.render_output_edit.setText(str(self.param_store.get("output.export_path")))
        self.set_offline_render_available(str(self.param_store.get("input.source_type")) == "file")

        self.refresh_presets_list()
