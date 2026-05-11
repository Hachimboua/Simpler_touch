# Enhanced Effect Parameters - User Guide

You now have **fine-grained control** over all creative effects in BlobTracker. Each effect has been expanded with multiple tunable parameters accessible through the Creative FX section in the control panel.

## Effects Overview

### 1. **GrainFilter** - Add texture and noise
- **intensity** (0.0 - 0.3): How strong the grain effect is
- **grain_type** (gaussian | uniform | colored): 
  - `gaussian`: Natural film-like grain (default)
  - `uniform`: Flat random noise
  - `colored`: RGB channel-specific noise
- **colored** (toggle): Enable multi-channel grain instead of grayscale

**Use Cases:** Film grain effect, texture enhancement, noise simulation

---

### 2. **GlitchFilter** - Digital glitch effect
- **slices** (2 - 32): Number of horizontal bands to glitch
- **max_offset** (5 - 100): Maximum pixel shift distance per slice
- **probability** (0.0 - 1.0): How often the glitch appears (0=never, 1=always)

**Use Cases:** Sci-fi, digital breakdown, visual stuttering effects

---

### 3. **EdgeFilter** - Edge detection overlay
- **low_threshold** (0 - 255): Lower edge detection boundary (Canny)
- **high_threshold** (0 - 255): Upper edge detection boundary (Canny)
- **alpha** (0.0 - 1.0): Blend strength of edges into frame
- **blur** (0 - 20): Pre-processing Gaussian blur (0 = disabled)

**Tips:** 
- Higher thresholds = fewer edges detected
- Blur helps reduce noise in edge detection
- Alpha=0.5 gives 50% blend with original frame

**Use Cases:** Contour highlighting, edge enhancement, artistic processing

---

### 4. **ChromaticAberration** - RGB channel displacement
- **shift_x** (-20 to 20): Horizontal pixel offset for R/B channels
- **shift_y** (-20 to 20): Vertical pixel offset for R/B channels
- **randomize** (toggle): Randomize shifts each frame for animation

**Use Cases:** VHS/analog effect, lens distortion, RGB separation

---

### 5. **ThermalFilter** - Thermal/heat map visualization
- **colormap** (inferno | hot | cool | twilight | viridis): Color scheme
  - `inferno`: Yellow/white on dark (default thermal-like)
  - `hot`: Red/white on black
  - `cool`: Blue/cyan gradient
  - `twilight`: Purple/pink cycle
  - `viridis`: Green/yellow perceptual

**Use Cases:** Thermal visualization, mood lighting, artistic coloring

---

## Parameter Synchronization

Parameters work in **two ways**:

### Method 1: Individual Controls (Recommended)
Use the spinboxes and dropdowns in the "Creative" section of the control panel. These directly control effect parameters in real-time:
- Located in Control Panel → Creative FX section
- Changes apply immediately to live preview
- Values sync automatically to filter chain

### Method 2: Filter Params Dict (Advanced)
For preset saving, all individual controls are also stored in the unified `creative.filter_params` dictionary. This is automatically synchronized by:
- `CreativeFX.sync_params_from_store()` converts individual params → filter dict
- Applied in `main.py` and `renderer.py` effect chains
- Ensures offline renders use same settings as live preview

## Workflow Example

### Creating a Film Look
1. Enable Creative FX checkbox
2. Add **GrainFilter** to filter chain
3. Set grain intensity to 0.12
4. Set grain_type to "gaussian"
5. Add **EdgeFilter** if desired for contour
6. Save as preset for reuse

### Creating a Digital Glitch Effect
1. Add **GlitchFilter** and **ChromaticAberration** 
2. Set glitch probability to 0.3 (30% of time)
3. Glitch slices: 12
4. Max offset: 40px
5. Chroma shift X: ±5, Y: 0
6. Enable randomize for animation

## Parameter Ranges Reference

| Effect | Parameter | Min | Max | Type | Default |
|--------|-----------|-----|-----|------|---------|
| Grain | intensity | 0.0 | 0.3 | float | 0.08 |
| Grain | grain_type | - | - | enum | gaussian |
| Glitch | slices | 2 | 32 | int | 8 |
| Glitch | max_offset | 5 | 100 | int | 24 |
| Glitch | probability | 0.0 | 1.0 | float | 0.5 |
| Edge | low_threshold | 0 | 255 | int | 80 |
| Edge | high_threshold | 0 | 255 | int | 180 |
| Edge | alpha | 0.0 | 1.0 | float | 0.7 |
| Edge | blur | 0 | 20 | int | 0 |
| Chroma | shift_x | -20 | 20 | int | 3 |
| Chroma | shift_y | -20 | 20 | int | 0 |
| Thermal | colormap | - | - | enum | inferno |

## Implementation Details

### New ParamDef Entries Added
```
creative.grain_intensity (float)
creative.grain_type (enum)
creative.grain_colored (bool)
creative.glitch_slices (int)
creative.glitch_offset (int)
creative.glitch_probability (float)
creative.edge_low_threshold (int)
creative.edge_high_threshold (int)
creative.edge_alpha (float)
creative.edge_blur (int)
creative.chroma_shift_x (int)
creative.chroma_shift_y (int)
creative.chroma_randomize (bool)
creative.thermal_colormap (enum)
```

### Updated Classes
- **GrainFilter**: Added grain_type and colored parameters
- **GlitchFilter**: Added probability for frame-by-frame control
- **EdgeFilter**: Added blur preprocessing
- **ChromaticAberration**: Split shift into X/Y with randomization
- **ThermalFilter**: Added colormap selection support
- **CreativeFX**: Added `sync_params_from_store()` method for parameter synchronization

### UI Changes
Control Panel "Creative" section now includes:
- Separate controls for each filter's parameters
- Dropdowns for enum selections (grain_type, colormap)
- Spinboxes for numeric ranges
- Checkboxes for boolean toggles
- Auto-sync between UI and parameter store

## Tips for Best Results

1. **Start with low values** - Effects compound when stacked
2. **Use probability instead of always-on** - Glitch at 50% is less jarring than 100%
3. **Combine complementary effects** - Grain + thermal = cinematic
4. **Test in offline render** - Preview may differ from final export
5. **Save presets** - Once you like a combo, save it for reuse
6. **Use blur on edge detection** - Reduces noise and artifacts

## Troubleshooting

**Q: Effects not appearing in live preview?**
- Ensure "Enable Creative FX" is checked
- Verify filter is in the filter chain (drag to reorder if needed)
- Check parameter values aren't at 0 or minimal values

**Q: Offline render differs from live preview?**
- The sync_params_from_store() method ensures parity
- Close and reopen application if values seem stale
- Try disabling/re-enabling creative FX

**Q: Too much effect, can't dial down?**
- Use probability for glitch (0.1-0.3 is subtle)
- Use alpha for edge (<0.5 is gentle overlay)
- Use intensity for grain (0.05-0.1 is taste)
