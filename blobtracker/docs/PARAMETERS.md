# Parameter Reference

Every parameter registered in `ParamStore._register_defaults()`, with its
type, default, range, and the UI section where it surfaces.

Keys follow a loose `namespace.field` convention. Some legacy short keys
(without a namespace) exist for historical reasons and are kept for
backward-compat with older presets.

> All values are clamped on `ParamStore.set` according to the `min`/`max`
> columns. Out-of-range writes are silently corrected.

---

## Input

| Key | Type | Default | Range / Options | UI |
| --- | --- | --- | --- | --- |
| `input.source_type` | enum | `webcam` | `webcam`, `file` | Input |
| `input.source_path` | str | `""` | — | Input |
| `input.webcam_index` | int | `0` | 0–8 | Input |
| `input.target_fps` | int | `30` | 1–120 | Input |

## Blob detection

| Key | Type | Default | Range | UI |
| --- | --- | --- | --- | --- |
| `blob.threshold` | int | `90` | 0–255 | Blob |
| `blob.blur_radius` | int | `7` | 1–31 (odd) | Blob |
| `blob.min_area` | float | `120.0` | 1–20000 | Blob |
| `blob.max_area` | float | `50000.0` | 10–400000 | Blob |
| `blob.max_count` | int | `20` | 1–300 | Blob |
| `blob_min_area` | int | `80` | 10–5000 | Detection Mode (alias surface) |
| `blob_max_area` | int | `8000` | 100–50000 | Detection Mode (alias surface) |
| `detector_mode` | enum | `contour` | `contour`, `simple_blob` | Detection Mode |

## Performance

| Key | Type | Default | Range | UI |
| --- | --- | --- | --- | --- |
| `process_scale` | float | `0.5` | 0.25–1.0 | Performance |
| `detect_every_n` | int | `2` | 1–4 | Performance |
| `min_label_area` | int | `200` | 0–2000 | Performance |

## Tracking

| Key | Type | Default | Range | UI |
| --- | --- | --- | --- | --- |
| `tracking.smoothing` | float | `0.35` | 0–1 | Blob / Detection Mode |
| `tracking.max_trail_length` | int | `35` | 1–500 | Tracking / Overlay Style |
| `tracking.id_font_size` | float | `0.5` | 0.2–2.0 | Tracking |
| `tracking.label_offset_x` | int | `10` | -200–200 | Tracking |
| `tracking.label_offset_y` | int | `-10` | -200–200 | Tracking |
| `tracker_max_disappeared` | int | `5` | 1–30 | Detection Mode |
| `tracker_smooth_alpha` | float | `0.4` | 0–1 | Detection Mode (alias) |
| `trail_length` | int | `20` | 0–60 | Overlay Style (alias) |

## Effects (overlays)

| Key | Type | Default | Range / Options | UI |
| --- | --- | --- | --- | --- |
| `effects.bbox_enabled` | bool | `false` | — | Effects |
| `effects.bbox_color` | color | `[240,240,240]` | RGB | Effects |
| `effects.bbox_thickness` | int | `1` | 1–6 | Effects |
| `effects.bbox_corner_style` | enum | `rect` | `rect`, `corner` | Effects / Overlay Style |
| `effects.label_enabled` | bool | `false` | — | Effects |
| `effects.label_color` | color | `[240,240,240]` | RGB | Effects |
| `effects.label_show_coords` | bool | `false` | — | Effects |
| `effects.trail_enabled` | bool | `false` | — | Effects |
| `effects.trail_color` | color | `[0,229,255]` | RGB | Effects |
| `effects.trail_alpha` | float | `0.8` | 0–1 | Effects |
| `effects.trail_thickness` | int | `1` | 1–6 | Effects |
| `effects.zoom_enabled` | bool | `false` | — | Effects / Overlay Style |
| `effects.zoom_blob_id` | int | `0` | 0–99999 | Effects |
| `effects.zoom_factor` | float | `2.0` | 1–6 | Effects |
| `effects.zoom_corner` | enum | `top-right` | 4 corners | Effects |
| `effects.flow_enabled` | bool | `false` | — | Effects |
| `effects.blend_mode` | enum | `normal` | `normal`, `screen`, `overlay`, `multiply` | Effects |

## Frame FX (full-frame look)

| Key | Type | Default | Range | UI |
| --- | --- | --- | --- | --- |
| `frame_desaturate` | float | `0.0` | 0–1 | Frame FX |
| `frame_grain` | float | `0.0` | 0–0.2 | Frame FX |
| `frame_vignette` | float | `0.0` | 0–1 | Frame FX |

## Overlay Style

| Key | Type | Default | Range / Options | UI |
| --- | --- | --- | --- | --- |
| `overlay_corner_style` | enum | `ticks` | `full`, `ticks` | Overlay Style |
| `overlay_tick_length` | int | `10` | 4–30 | Overlay Style |
| `overlay_box_opacity` | float | `0.7` | 0–1 | Overlay Style |
| `overlay_show_label` | bool | `true` | — | Overlay Style |
| `overlay_show_area` | bool | `false` | — | Overlay Style |
| `overlay_show_coords` | bool | `false` | — | Overlay Style |
| `overlay_show_leaders` | bool | `true` | — | Overlay Style |
| `overlay_show_centroid` | bool | `true` | — | Overlay Style |
| `zoom_inset_enabled` | bool | `false` | — | Overlay Style (alias) |
| `zoom_inset_scale` | float | `1.8` | 1–4 | (internal) |

## Connection Lines

| Key | Type | Default | Range | UI |
| --- | --- | --- | --- | --- |
| `connection_enabled` | bool | `true` | — | Connection Lines |
| `connection_max_dist` | float | `200.0` | 50–800 | Connection Lines |
| `connection_opacity` | float | `0.4` | 0–1 | Connection Lines |
| `connection_thickness` | float | `0.5` | 0.5–3.0 | Connection Lines |
| `connection_color` | color | `[255,255,255]` | RGB | Connection Lines |
| `connection_show_dots` | bool | `true` | — | Connection Lines |
| `connection_dot_radius` | int | `3` | 1–8 | Connection Lines |

## Blob Interior FX

| Key | Type | Default | Range / Options | UI |
| --- | --- | --- | --- | --- |
| `intra_blob_enabled` | bool | `false` | — | Blob Interior FX |
| `intra_blob_mode` | enum | `thermal` | `none`, `thermal`, `edge`, `pixelate`, `negative`, `blur`, `highlight`, `desaturate` | Blob Interior FX |
| `intra_blob_opacity` | float | `1.0` | 0–1 | Blob Interior FX |
| `intra_blob_padding` | int | `8` | 0–60 | Blob Interior FX |
| `intra_blob_feather` | bool | `true` | — | Blob Interior FX |
| `intra_blob_pixel_size` | int | `12` | 2–40 | Blob Interior FX (pixelate) |
| `intra_blob_blur_radius` | int | `21` | 3–61 (odd) | Blob Interior FX (blur) |
| `intra_blob_highlight` | float | `1.4` | 1–3 | Blob Interior FX (highlight) |

## Creative Filter Chain

| Key | Type | Default | Range / Options | UI |
| --- | --- | --- | --- | --- |
| `creative.enabled` | bool | `false` | — | Creative |
| `creative.filter_order` | list[str] | `[]` | filter class names | Creative (drag-reorder list) |
| `creative.filter_params` | dict | see below | per-filter kwargs | Creative |

### Per-filter enable + parameter keys

| Filter | Enable key | Parameter keys |
| --- | --- | --- |
| Grain | `fx_grain_enabled` | `creative.grain_intensity`, `creative.grain_type`, `creative.grain_colored` |
| Glitch | `fx_glitch_enabled` | `creative.glitch_slices`, `creative.glitch_offset`, `creative.glitch_probability` |
| Thermal | `fx_thermal_enabled` | `creative.thermal_colormap` |
| Edge | `fx_edge_enabled` | `creative.edge_low_threshold`, `creative.edge_high_threshold`, `creative.edge_alpha`, `creative.edge_blur` |
| Chromatic Aberration | `fx_chroma_enabled` | `creative.chroma_shift_x`, `creative.chroma_shift_y`, `creative.chroma_randomize` |

### Default `creative.filter_params` dict

```json
{
  "GrainFilter":         { "intensity": 0.08, "grain_type": "gaussian", "colored": false },
  "GlitchFilter":        { "slices": 8, "max_offset": 24, "probability": 0.5 },
  "ThermalFilter":       { "colormap": "inferno" },
  "EdgeFilter":          { "low": 80, "high": 180, "alpha": 0.7, "blur": 0 },
  "ChromaticAberration": { "shift_x": 3, "shift_y": 0, "randomize": false }
}
```

## Output

| Key | Type | Default | Range / Options | UI |
| --- | --- | --- | --- | --- |
| `output.export_path` | str | `output.mp4` | — | Output / Render to File |
| `output.format` | enum | `mp4` | `mp4`, `png_seq`, `prores` | Output |
| `output.recording` | bool | `false` | — | Output |

---

## Notes on legacy / aliased keys

A handful of fields appear twice under different names (e.g. `tracking.smoothing`
↔ `tracker_smooth_alpha`, `tracking.max_trail_length` ↔ `trail_length`,
`effects.bbox_corner_style` ↔ `overlay_corner_style`). The UI mirrors writes
between them so older presets keep working. Pick whichever name reads better
in your code; both surfaces stay in sync.
