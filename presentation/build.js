// =====================================================================
//  BlobTracker — Academic Presentation
//  Authors: Hachim Boubdillah & Baqua Abdellah
// =====================================================================

const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";         // 13.3" x 7.5"
pres.title  = "BlobTracker — Real-time Blob Tracking and Creative Overlays";
pres.author = "Hachim Boubdillah and Baqua Abdellah";
pres.subject = "Computer Vision · PyQt6 Desktop Application";

// ---- Palette (matches the app theme) --------------------------------
const C = {
    bg:        "0C0E10",
    bgPanel:   "141820",
    bgCard:    "1A2030",
    accent:    "00C8F0",
    accentDk:  "006E96",
    rule:      "2A3344",
    text:      "E8ECF0",
    textDim:   "7A8A9A",
    textFaint: "4A5A6A",
    secInput:  "5A9ACC",
    secBlob:   "CC8844",
    secTrack:  "7ACC7A",
    secFx:     "CC7ACC",
    secCre:    "F06090",
    secPerf:   "00C8F0",
};

const W = 13.3;
const H = 7.5;

// ---- Shadow factory (skill warns against reuse) ---------------------
const softShadow = () => ({ type: "outer", color: "000000", blur: 12, offset: 4, angle: 90, opacity: 0.35 });

// ---- Shared chrome --------------------------------------------------
function chrome(slide, num, total, sectionLabel, sectionColor) {
    // background
    slide.background = { color: C.bg };

    // top-left number badge
    slide.addShape("rect", {
        x: 0.55, y: 0.55, w: 0.05, h: 0.55, fill: { color: sectionColor || C.accent }, line: { color: sectionColor || C.accent }
    });
    slide.addText(String(num).padStart(2, "0"), {
        x: 0.7, y: 0.45, w: 0.7, h: 0.4,
        fontFace: "Consolas", fontSize: 12, color: C.textDim, bold: true, charSpacing: 4, margin: 0
    });
    slide.addText("/ " + String(total).padStart(2, "0"), {
        x: 0.7, y: 0.75, w: 0.8, h: 0.32,
        fontFace: "Consolas", fontSize: 10, color: C.textFaint, margin: 0
    });

    // top-right section label
    if (sectionLabel) {
        slide.addText(sectionLabel, {
            x: W - 4.5, y: 0.5, w: 4.0, h: 0.4,
            fontFace: "Consolas", fontSize: 10, color: sectionColor || C.accent,
            bold: true, charSpacing: 5, align: "right", margin: 0
        });
    }

    // footer rule + brand
    slide.addShape("line", {
        x: 0.55, y: H - 0.55, w: W - 1.1, h: 0,
        line: { color: C.rule, width: 0.5 }
    });
    slide.addText("BLOBTRACKER", {
        x: 0.55, y: H - 0.45, w: 4, h: 0.3,
        fontFace: "Consolas", fontSize: 9, color: C.textFaint,
        bold: true, charSpacing: 4, margin: 0
    });
    slide.addText("Hachim Boubdillah  ·  Baqua Abdellah", {
        x: W - 6.1, y: H - 0.45, w: 5.5, h: 0.3,
        fontFace: "Calibri", fontSize: 9, color: C.textFaint, align: "right", margin: 0
    });
}

function slideTitle(slide, title, subtitle, color) {
    slide.addText(title, {
        x: 0.55, y: 1.25, w: W - 1.1, h: 0.7,
        fontFace: "Calibri", fontSize: 32, color: C.text, bold: true, margin: 0
    });
    if (subtitle) {
        slide.addText(subtitle, {
            x: 0.55, y: 1.95, w: W - 1.1, h: 0.4,
            fontFace: "Calibri", fontSize: 14, color: color || C.accent, italic: true, margin: 0
        });
    }
    // tiny accent square next to the title
    slide.addShape("rect", {
        x: 0.55, y: 1.4, w: 0.0, h: 0.0, fill: { color: color || C.accent }
    });
}

// =====================================================================
//  SLIDE 1 — TITLE
// =====================================================================
{
    const s = pres.addSlide();
    s.background = { color: C.bg };

    // faint geometric pattern: stacked thin lines top-right
    for (let i = 0; i < 9; i++) {
        s.addShape("rect", {
            x: W - 3.5 + i * 0.05, y: 0.6 + i * 0.08, w: 3.0, h: 0.03,
            fill: { color: C.accent, transparency: 80 - i * 7 },
            line: { color: C.accent, width: 0 }
        });
    }

    // bottom-left grid of dots
    for (let r = 0; r < 5; r++) {
        for (let c = 0; c < 5; c++) {
            s.addShape("ellipse", {
                x: 0.6 + c * 0.18, y: H - 1.7 + r * 0.18, w: 0.04, h: 0.04,
                fill: { color: C.accent, transparency: 60 + r * 6 },
                line: { color: C.accent, width: 0 }
            });
        }
    }

    // accent vertical bar
    s.addShape("rect", {
        x: 1.5, y: 2.4, w: 0.08, h: 2.4, fill: { color: C.accent }, line: { color: C.accent }
    });

    // overline label
    s.addText("ACADEMIC PROJECT  ·  COMPUTER VISION  ·  PyQt6", {
        x: 1.75, y: 2.45, w: 10, h: 0.35,
        fontFace: "Consolas", fontSize: 11, color: C.textDim,
        bold: true, charSpacing: 6, margin: 0
    });

    // main title
    s.addText("BLOBTRACKER", {
        x: 1.75, y: 2.85, w: 11, h: 1.0,
        fontFace: "Calibri", fontSize: 66, color: C.accent, bold: true, charSpacing: 10, margin: 0
    });

    // subtitle
    s.addText("Real-time Blob Detection, Tracking,\nand Creative Overlay Engine", {
        x: 1.75, y: 4.0, w: 10, h: 1.0,
        fontFace: "Calibri", fontSize: 22, color: C.text, margin: 0
    });

    // separator
    s.addShape("line", {
        x: 1.75, y: 5.4, w: 6.5, h: 0,
        line: { color: C.rule, width: 1 }
    });

    // authors block
    s.addText("AUTHORS", {
        x: 1.75, y: 5.55, w: 4, h: 0.3,
        fontFace: "Consolas", fontSize: 10, color: C.textFaint, bold: true, charSpacing: 4, margin: 0
    });
    s.addText("Hachim Boubdillah", {
        x: 1.75, y: 5.85, w: 5, h: 0.35,
        fontFace: "Calibri", fontSize: 16, color: C.text, bold: true, margin: 0
    });
    s.addText("Baqua Abdellah", {
        x: 1.75, y: 6.2, w: 5, h: 0.35,
        fontFace: "Calibri", fontSize: 16, color: C.text, bold: true, margin: 0
    });

    // date / stack
    s.addText("STACK", {
        x: 8.0, y: 5.55, w: 4, h: 0.3,
        fontFace: "Consolas", fontSize: 10, color: C.textFaint, bold: true, charSpacing: 4, margin: 0
    });
    s.addText("Python  ·  PyQt6  ·  OpenCV\nNumPy  ·  SciPy  ·  Pillow", {
        x: 8.0, y: 5.85, w: 5, h: 0.7,
        fontFace: "Calibri", fontSize: 14, color: C.textDim, margin: 0
    });

    // bottom footer
    s.addShape("rect", {
        x: 0, y: H - 0.25, w: W, h: 0.25, fill: { color: C.accentDk }, line: { color: C.accentDk }
    });
}

const TOTAL = 15;

// =====================================================================
//  SLIDE 2 — OUTLINE
// =====================================================================
{
    const s = pres.addSlide();
    chrome(s, 2, TOTAL, "OUTLINE");
    slideTitle(s, "Presentation Outline", "Roadmap of the talk");

    const items = [
        ["01", "Introduction & Motivation"],
        ["02", "Problem Statement & Objectives"],
        ["03", "Technology Stack"],
        ["04", "System Architecture"],
        ["05", "Detection Pipeline"],
        ["06", "Tracking Algorithm"],
        ["07", "Effects & Compositing Engine"],
        ["08", "User Interface Design"],
        ["09", "Plugin Architecture"],
        ["10", "Performance Analysis"],
        ["11", "Use Cases & Results"],
        ["12", "Conclusion & Future Work"],
    ];

    const colW = 5.5;
    const rowH = 0.45;
    const startX = 0.9;
    const startY = 2.7;

    items.forEach((it, i) => {
        const col = Math.floor(i / 6);
        const row = i % 6;
        const x = startX + col * (colW + 0.6);
        const y = startY + row * (rowH + 0.15);

        s.addText(it[0], {
            x: x, y: y, w: 0.55, h: rowH,
            fontFace: "Consolas", fontSize: 18, color: C.accentDk, bold: true, margin: 0, valign: "middle"
        });
        s.addShape("line", {
            x: x + 0.55, y: y + rowH / 2, w: 0.25, h: 0,
            line: { color: C.rule, width: 0.75 }
        });
        s.addText(it[1], {
            x: x + 0.9, y: y, w: colW - 0.9, h: rowH,
            fontFace: "Calibri", fontSize: 15, color: C.text, margin: 0, valign: "middle"
        });
    });
}

// =====================================================================
//  SLIDE 3 — INTRODUCTION & MOTIVATION
// =====================================================================
{
    const s = pres.addSlide();
    chrome(s, 3, TOTAL, "01  INTRODUCTION");
    slideTitle(s, "What is BlobTracker?", "A native desktop tool for real-time computer vision");

    // Left column: prose
    s.addText([
        { text: "Real-time blob detection and tracking", options: { bold: true, color: C.accent, breakLine: true } },
        { text: "on webcam or video file input, with stable ", options: { color: C.text, breakLine: true } },
        { text: "IDs and a stackable overlay/effects pipeline.", options: { color: C.text, breakLine: true } },
        { text: " ", options: { breakLine: true } },
        { text: "Bridges three worlds:", options: { color: C.textDim, italic: true, breakLine: true } },
        { text: " ", options: { breakLine: true } },
        { text: "·  ", options: { color: C.accent } },
        { text: "Computer vision research prototypes", options: { color: C.text, breakLine: true } },
        { text: "·  ", options: { color: C.accent } },
        { text: "Live surveillance and monitoring tools", options: { color: C.text, breakLine: true } },
        { text: "·  ", options: { color: C.accent } },
        { text: "Creative-coding and visual installations", options: { color: C.text } },
    ], {
        x: 0.9, y: 2.7, w: 6.3, h: 3.5,
        fontFace: "Calibri", fontSize: 15, paraSpaceAfter: 4, margin: 0
    });

    // Right column: stat callouts (3 cards)
    const cards = [
        { n: "13+",    l: "control panel sections" },
        { n: "60+",    l: "tunable parameters" },
        { n: "5",      l: "built-in creative filters" },
    ];
    cards.forEach((c, i) => {
        const x = 7.6, y = 2.65 + i * 1.25;
        s.addShape("rect", {
            x: x, y: y, w: 5.0, h: 1.1,
            fill: { color: C.bgCard }, line: { color: C.rule, width: 0.5 }
        });
        s.addShape("rect", {
            x: x, y: y, w: 0.08, h: 1.1,
            fill: { color: C.accent }, line: { color: C.accent }
        });
        s.addText(c.n, {
            x: x + 0.3, y: y + 0.1, w: 2, h: 0.9,
            fontFace: "Calibri", fontSize: 40, color: C.accent, bold: true, margin: 0, valign: "middle"
        });
        s.addText(c.l, {
            x: x + 2.3, y: y + 0.1, w: 2.6, h: 0.9,
            fontFace: "Calibri", fontSize: 13, color: C.textDim, margin: 0, valign: "middle"
        });
    });
}

// =====================================================================
//  SLIDE 4 — PROBLEM STATEMENT & OBJECTIVES
// =====================================================================
{
    const s = pres.addSlide();
    chrome(s, 4, TOTAL, "02  OBJECTIVES");
    slideTitle(s, "Problem Statement & Objectives", "What we set out to build, and why");

    // problem block
    s.addShape("rect", {
        x: 0.9, y: 2.75, w: W - 1.8, h: 1.05,
        fill: { color: C.bgPanel }, line: { color: C.rule, width: 0.5 }
    });
    s.addShape("rect", {
        x: 0.9, y: 2.75, w: 0.08, h: 1.05,
        fill: { color: C.secBlob }, line: { color: C.secBlob }
    });
    s.addText("PROBLEM", {
        x: 1.15, y: 2.85, w: 2, h: 0.3,
        fontFace: "Consolas", fontSize: 10, color: C.secBlob, bold: true, charSpacing: 4, margin: 0
    });
    s.addText("Existing CV tools are either powerful but headless (OpenCV scripts) or polished but inflexible (commercial trackers). Researchers and creators need a tool that combines live, tweakable detection with a reproducible offline render path — in a single native app.", {
        x: 1.15, y: 3.15, w: W - 2.3, h: 0.6,
        fontFace: "Calibri", fontSize: 13, color: C.text, margin: 0
    });

    // 4 objective cards (2x2)
    const objs = [
        { c: C.secInput,  t: "Real-time pipeline", d: "Decoupled capture, processing, and render threads driven by a precision Qt timer." },
        { c: C.secTrack,  t: "Stable identity tracking", d: "Hungarian assignment + centroid smoothing + configurable disappearance window." },
        { c: C.secFx,     t: "Creative overlay layer", d: "Stackable, drag-reorderable effect chain with hot-reloadable Python plugins." },
        { c: C.secPerf,   t: "Deterministic export", d: "Independent offline render path produces reproducible output regardless of host load." },
    ];
    objs.forEach((o, i) => {
        const col = i % 2, row = Math.floor(i / 2);
        const x = 0.9 + col * 5.85, y = 4.05 + row * 1.45;
        s.addShape("rect", {
            x: x, y: y, w: 5.55, h: 1.3,
            fill: { color: C.bgCard }, line: { color: C.rule, width: 0.5 }
        });
        s.addShape("rect", {
            x: x, y: y, w: 0.08, h: 1.3,
            fill: { color: o.c }, line: { color: o.c }
        });
        s.addText(o.t, {
            x: x + 0.25, y: y + 0.15, w: 5.2, h: 0.4,
            fontFace: "Calibri", fontSize: 15, color: o.c, bold: true, margin: 0
        });
        s.addText(o.d, {
            x: x + 0.25, y: y + 0.55, w: 5.2, h: 0.7,
            fontFace: "Calibri", fontSize: 12, color: C.textDim, margin: 0
        });
    });
}

// =====================================================================
//  SLIDE 5 — TECHNOLOGY STACK
// =====================================================================
{
    const s = pres.addSlide();
    chrome(s, 5, TOTAL, "03  STACK");
    slideTitle(s, "Technology Stack", "Open-source libraries used and why");

    const stack = [
        { tag: "RUNTIME",  name: "Python 3.8+",      desc: "Cross-platform dynamic language with mature scientific tooling." },
        { tag: "UI",       name: "PyQt6 / Qt 6",     desc: "Native widgets, dock layouts, signals/slots, QThread workers." },
        { tag: "VISION",   name: "OpenCV 4.8+",      desc: "Image processing, blob detection, optical flow, video I/O." },
        { tag: "NUMERIC",  name: "NumPy 2.x",        desc: "Vectorised pixel ops, frame buffers, mask compositing." },
        { tag: "MATCHING", name: "SciPy 1.14+",      desc: "linear_sum_assignment (Hungarian) for ID-blob matching." },
        { tag: "TEXT",     name: "Pillow 10.4+",     desc: "TrueType label rendering with anti-aliased glyphs." },
    ];

    const cols = 3, rows = 2;
    const cardW = 4.1, cardH = 1.65, gapX = 0.2, gapY = 0.25;
    const startX = (W - (cols * cardW + (cols - 1) * gapX)) / 2;
    const startY = 2.85;

    stack.forEach((it, i) => {
        const col = i % cols, row = Math.floor(i / cols);
        const x = startX + col * (cardW + gapX);
        const y = startY + row * (cardH + gapY);

        s.addShape("rect", {
            x: x, y: y, w: cardW, h: cardH,
            fill: { color: C.bgCard }, line: { color: C.rule, width: 0.5 }
        });
        s.addText(it.tag, {
            x: x + 0.25, y: y + 0.18, w: cardW - 0.5, h: 0.3,
            fontFace: "Consolas", fontSize: 9, color: C.accent, bold: true, charSpacing: 4, margin: 0
        });
        s.addText(it.name, {
            x: x + 0.25, y: y + 0.5, w: cardW - 0.5, h: 0.4,
            fontFace: "Calibri", fontSize: 18, color: C.text, bold: true, margin: 0
        });
        s.addText(it.desc, {
            x: x + 0.25, y: y + 0.95, w: cardW - 0.5, h: cardH - 1.05,
            fontFace: "Calibri", fontSize: 12, color: C.textDim, margin: 0
        });
    });
}

// =====================================================================
//  SLIDE 6 — SYSTEM ARCHITECTURE
// =====================================================================
{
    const s = pres.addSlide();
    chrome(s, 6, TOTAL, "04  ARCHITECTURE");
    slideTitle(s, "System Architecture", "Three worker threads coordinated by Qt signals");

    // Stage boxes
    const stages = [
        { x: 0.9,  c: C.secInput,  t: "CAPTURE",   sub: "CaptureWorker",   d: "Webcam / file source\nthread-safe FrameBuffer" },
        { x: 4.7,  c: C.secBlob,   t: "PROCESS",   sub: "ProcessorWorker", d: "Preprocessor\nDetector + Tracker" },
        { x: 8.5,  c: C.secFx,     t: "RENDER",    sub: "Qt main thread",  d: "Effects + Compositor\nPreviewRenderer" },
    ];
    stages.forEach(st => {
        s.addShape("rect", {
            x: st.x, y: 3.1, w: 3.4, h: 2.0,
            fill: { color: C.bgCard }, line: { color: st.c, width: 1 }
        });
        s.addText(st.t, {
            x: st.x + 0.2, y: 3.25, w: 3.0, h: 0.35,
            fontFace: "Consolas", fontSize: 11, color: st.c, bold: true, charSpacing: 5, margin: 0
        });
        s.addText(st.sub, {
            x: st.x + 0.2, y: 3.6, w: 3.0, h: 0.4,
            fontFace: "Calibri", fontSize: 16, color: C.text, bold: true, margin: 0
        });
        s.addShape("line", {
            x: st.x + 0.2, y: 4.05, w: 3.0, h: 0,
            line: { color: C.rule, width: 0.5 }
        });
        s.addText(st.d, {
            x: st.x + 0.2, y: 4.15, w: 3.0, h: 0.85,
            fontFace: "Calibri", fontSize: 12, color: C.textDim, margin: 0
        });
    });

    // Arrows between stages
    [4.3, 8.1].forEach(x => {
        s.addShape("line", {
            x: x, y: 4.1, w: 0.4, h: 0,
            line: { color: C.accent, width: 2, endArrowType: "triangle" }
        });
    });

    // Side outputs
    s.addShape("line", {
        x: 10.2, y: 5.1, w: 0, h: 0.55,
        line: { color: C.accent, width: 2, endArrowType: "triangle" }
    });
    s.addShape("rect", {
        x: 8.5, y: 5.75, w: 3.4, h: 0.7,
        fill: { color: C.bgPanel }, line: { color: C.rule, width: 0.5 }
    });
    s.addText("VideoExporter  /  OfflineRenderer", {
        x: 8.5, y: 5.75, w: 3.4, h: 0.7,
        fontFace: "Calibri", fontSize: 13, color: C.text, align: "center", valign: "middle", margin: 0
    });

    // Key points below
    s.addText("Key design properties", {
        x: 0.9, y: 5.5, w: 7, h: 0.3,
        fontFace: "Consolas", fontSize: 10, color: C.textFaint, bold: true, charSpacing: 4, margin: 0
    });
    s.addText([
        { text: "·  ", options: { color: C.accent } },
        { text: "Backpressure-free preview — old frames dropped to keep latency low",
          options: { color: C.text, breakLine: true } },
        { text: "·  ", options: { color: C.accent } },
        { text: "Inter-thread communication only via Qt signals (no shared mutables)",
          options: { color: C.text, breakLine: true } },
        { text: "·  ", options: { color: C.accent } },
        { text: "Render timer is the heartbeat — decouples display from capture rate",
          options: { color: C.text } },
    ], {
        x: 0.9, y: 5.8, w: 7.4, h: 1.0,
        fontFace: "Calibri", fontSize: 12, paraSpaceAfter: 2, margin: 0
    });
}

// =====================================================================
//  SLIDE 7 — DETECTION PIPELINE
// =====================================================================
{
    const s = pres.addSlide();
    chrome(s, 7, TOTAL, "05  DETECTION", C.secBlob);
    slideTitle(s, "Detection Pipeline", "From raw pixels to clean blob candidates", C.secBlob);

    // 5-step horizontal pipeline
    const steps = [
        { t: "GRAYSCALE", d: "BGR → single channel" },
        { t: "BLUR",      d: "Gaussian, odd kernel" },
        { t: "THRESHOLD", d: "Binarisation 0–255" },
        { t: "CONTOURS",  d: "External or simple-blob" },
        { t: "FILTER",    d: "Area + count bounds" },
    ];
    const stepW = 2.3, stepH = 1.2;
    const gap = 0.15;
    const startX = (W - (steps.length * stepW + (steps.length - 1) * gap)) / 2;
    const y = 3.0;

    steps.forEach((st, i) => {
        const x = startX + i * (stepW + gap);

        s.addShape("rect", {
            x: x, y: y, w: stepW, h: stepH,
            fill: { color: C.bgCard }, line: { color: C.rule, width: 0.5 }
        });
        s.addText(String(i + 1).padStart(2, "0"), {
            x: x, y: y + 0.1, w: stepW, h: 0.3,
            fontFace: "Consolas", fontSize: 10, color: C.secBlob, bold: true, align: "center", margin: 0
        });
        s.addText(st.t, {
            x: x, y: y + 0.4, w: stepW, h: 0.35,
            fontFace: "Calibri", fontSize: 14, color: C.text, bold: true, align: "center", margin: 0
        });
        s.addText(st.d, {
            x: x + 0.1, y: y + 0.75, w: stepW - 0.2, h: 0.4,
            fontFace: "Calibri", fontSize: 11, color: C.textDim, align: "center", margin: 0
        });

        // arrow between
        if (i < steps.length - 1) {
            s.addShape("line", {
                x: x + stepW, y: y + stepH / 2, w: gap, h: 0,
                line: { color: C.secBlob, width: 2, endArrowType: "triangle" }
            });
        }
    });

    // Implementation block
    s.addText("IMPLEMENTATION  ·  processing_core.py", {
        x: 0.9, y: 4.6, w: 6, h: 0.3,
        fontFace: "Consolas", fontSize: 10, color: C.textFaint, bold: true, charSpacing: 4, margin: 0
    });
    s.addShape("rect", {
        x: 0.9, y: 4.95, w: W - 1.8, h: 1.5,
        fill: { color: C.bgPanel }, line: { color: C.rule, width: 0.5 }
    });
    s.addText([
        { text: "gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)", options: { color: C.text, breakLine: true } },
        { text: "blur  = cv2.GaussianBlur(gray, (k, k), 0)",        options: { color: C.text, breakLine: true } },
        { text: "_, bin = cv2.threshold(blur, thr, 255, cv2.THRESH_BINARY)", options: { color: C.text, breakLine: true } },
        { text: "cnts, _ = cv2.findContours(bin, RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)", options: { color: C.text, breakLine: true } },
        { text: "blobs = [b for b in cnts if min_area <= cv2.contourArea(b) <= max_area]", options: { color: C.accent } },
    ], {
        x: 1.1, y: 5.05, w: W - 2.2, h: 1.4,
        fontFace: "Consolas", fontSize: 12, paraSpaceAfter: 2, margin: 0
    });
}

// =====================================================================
//  SLIDE 8 — TRACKING ALGORITHM
// =====================================================================
{
    const s = pres.addSlide();
    chrome(s, 8, TOTAL, "06  TRACKING", C.secTrack);
    slideTitle(s, "Tracking Algorithm", "Assigning stable IDs across frames", C.secTrack);

    // Left: theory
    s.addText("ASSIGNMENT", {
        x: 0.9, y: 2.75, w: 4, h: 0.3,
        fontFace: "Consolas", fontSize: 10, color: C.textFaint, bold: true, charSpacing: 4, margin: 0
    });
    s.addText("Hungarian algorithm", {
        x: 0.9, y: 3.05, w: 6, h: 0.4,
        fontFace: "Calibri", fontSize: 18, color: C.secTrack, bold: true, margin: 0
    });
    s.addText("Builds a cost matrix of Euclidean distances between previous blob centroids and current detections. SciPy's linear_sum_assignment solves the optimal one-to-one matching in O(n³).", {
        x: 0.9, y: 3.5, w: 6.3, h: 1.0,
        fontFace: "Calibri", fontSize: 12, color: C.text, margin: 0
    });

    s.addText("SMOOTHING", {
        x: 0.9, y: 4.55, w: 4, h: 0.3,
        fontFace: "Consolas", fontSize: 10, color: C.textFaint, bold: true, charSpacing: 4, margin: 0
    });
    s.addText("Exponential moving average", {
        x: 0.9, y: 4.85, w: 6, h: 0.4,
        fontFace: "Calibri", fontSize: 18, color: C.secTrack, bold: true, margin: 0
    });
    s.addShape("rect", {
        x: 0.9, y: 5.3, w: 6.3, h: 0.85,
        fill: { color: C.bgPanel }, line: { color: C.rule, width: 0.5 }
    });
    s.addText("c[t] = α · c[t-1] + (1 - α) · c_measured",
    {
        x: 1.05, y: 5.4, w: 6.0, h: 0.65,
        fontFace: "Consolas", fontSize: 16, color: C.text, valign: "middle", margin: 0
    });

    // Right: properties
    const props = [
        { t: "Trail history",     d: "Each Blob carries a deque of past centroids (configurable length)." },
        { t: "Disappearance window", d: "Blobs are kept alive for N missing frames before their ID is freed." },
        { t: "Backwards-compatible", d: "Aliased keys ensure older presets keep working across UI revisions." },
    ];
    props.forEach((p, i) => {
        const y = 2.75 + i * 1.15;
        s.addShape("rect", {
            x: 7.6, y: y, w: 5.0, h: 1.0,
            fill: { color: C.bgCard }, line: { color: C.rule, width: 0.5 }
        });
        s.addShape("rect", {
            x: 7.6, y: y, w: 0.08, h: 1.0,
            fill: { color: C.secTrack }, line: { color: C.secTrack }
        });
        s.addText(p.t, {
            x: 7.85, y: y + 0.12, w: 4.7, h: 0.35,
            fontFace: "Calibri", fontSize: 14, color: C.secTrack, bold: true, margin: 0
        });
        s.addText(p.d, {
            x: 7.85, y: y + 0.5, w: 4.7, h: 0.5,
            fontFace: "Calibri", fontSize: 12, color: C.textDim, margin: 0
        });
    });
}

// =====================================================================
//  SLIDE 9 — EFFECTS ENGINE
// =====================================================================
{
    const s = pres.addSlide();
    chrome(s, 9, TOTAL, "07  EFFECTS", C.secFx);
    slideTitle(s, "Effects & Compositing Engine", "Composable layers, blend modes, and creative filters", C.secFx);

    // Effect grid
    const fx = [
        { t: "BoundingBoxFX",    d: "Rectangles or corner ticks" },
        { t: "LabelFX",          d: "IDs, coords, leader lines" },
        { t: "TrailFX",          d: "Polyline trails from history" },
        { t: "ConnectionLineFX", d: "Distance-based blob links" },
        { t: "IntraBlobFX",      d: "Per-blob interior treatment" },
        { t: "ZoomInsetFX",      d: "Magnified inset of target blob" },
        { t: "BaseFrameFX",      d: "Desaturate · grain · vignette" },
        { t: "CreativeFX (chain)", d: "Stackable plugin filters" },
    ];

    const cw = 2.95, ch = 1.0;
    const cols = 4;
    fx.forEach((f, i) => {
        const col = i % cols, row = Math.floor(i / cols);
        const x = 0.9 + col * (cw + 0.15);
        const y = 2.85 + row * (ch + 0.15);
        s.addShape("rect", {
            x: x, y: y, w: cw, h: ch,
            fill: { color: C.bgCard }, line: { color: C.rule, width: 0.5 }
        });
        s.addShape("rect", {
            x: x, y: y, w: cw, h: 0.05,
            fill: { color: C.secFx }, line: { color: C.secFx }
        });
        s.addText(f.t, {
            x: x + 0.2, y: y + 0.15, w: cw - 0.4, h: 0.3,
            fontFace: "Consolas", fontSize: 12, color: C.text, bold: true, margin: 0
        });
        s.addText(f.d, {
            x: x + 0.2, y: y + 0.48, w: cw - 0.4, h: 0.45,
            fontFace: "Calibri", fontSize: 11, color: C.textDim, margin: 0
        });
    });

    // Blend modes strip
    s.addText("COMPOSITOR  ·  BLEND MODES", {
        x: 0.9, y: 5.35, w: 6, h: 0.3,
        fontFace: "Consolas", fontSize: 10, color: C.textFaint, bold: true, charSpacing: 4, margin: 0
    });
    const blends = ["normal", "screen", "overlay", "multiply"];
    blends.forEach((b, i) => {
        const x = 0.9 + i * 3.05;
        s.addShape("rect", {
            x: x, y: 5.7, w: 2.9, h: 0.6,
            fill: { color: C.bgPanel }, line: { color: C.secFx, width: 0.5 }
        });
        s.addText(b, {
            x: x, y: 5.7, w: 2.9, h: 0.6,
            fontFace: "Consolas", fontSize: 14, color: C.text, align: "center", valign: "middle", bold: true, margin: 0
        });
    });
}

// =====================================================================
//  SLIDE 10 — UI DESIGN
// =====================================================================
{
    const s = pres.addSlide();
    chrome(s, 10, TOTAL, "08  UI DESIGN");
    slideTitle(s, "User Interface Design", "Dark theme, dockable controls, signature cyan");

    // Mock window layout on the left
    const winX = 0.9, winY = 2.8, winW = 6.5, winH = 3.6;
    s.addShape("rect", {
        x: winX, y: winY, w: winW, h: winH,
        fill: { color: C.bg }, line: { color: C.rule, width: 1 }
    });
    // Title bar
    s.addShape("rect", {
        x: winX, y: winY, w: winW, h: 0.3,
        fill: { color: "060708" }, line: { color: "060708" }
    });
    s.addText("BLOBTRACKER  ·  Real-time Blob Tracking", {
        x: winX + 0.15, y: winY, w: winW, h: 0.3,
        fontFace: "Consolas", fontSize: 9, color: C.textDim, valign: "middle", margin: 0
    });
    // Control panel
    s.addShape("rect", {
        x: winX, y: winY + 0.3, w: 2.0, h: winH - 0.6,
        fill: { color: C.bgPanel }, line: { color: C.bgPanel }
    });
    // Section bars within control panel
    ["INPUT", "BLOB", "TRACKING", "EFFECTS", "CREATIVE"].forEach((lbl, i) => {
        const colors = [C.secInput, C.secBlob, C.secTrack, C.secFx, C.secCre];
        s.addText(lbl, {
            x: winX + 0.15, y: winY + 0.5 + i * 0.45, w: 1.8, h: 0.3,
            fontFace: "Consolas", fontSize: 8, color: colors[i], bold: true, charSpacing: 2, margin: 0
        });
        s.addShape("rect", {
            x: winX + 0.15, y: winY + 0.78 + i * 0.45, w: 1.7, h: 0.08,
            fill: { color: C.bgCard }, line: { color: C.bgCard }
        });
        s.addShape("rect", {
            x: winX + 0.15 + Math.random() * 0.6, y: winY + 0.78 + i * 0.45, w: 0.5, h: 0.08,
            fill: { color: colors[i] }, line: { color: colors[i] }
        });
    });
    // Preview area
    s.addShape("rect", {
        x: winX + 2.05, y: winY + 0.3, w: winW - 2.05, h: winH - 0.9,
        fill: { color: "060708" }, line: { color: "060708" }
    });
    s.addText("NO  SOURCE", {
        x: winX + 2.05, y: winY + 0.3, w: winW - 2.05, h: winH - 0.9,
        fontFace: "Consolas", fontSize: 11, color: "1A2535",
        align: "center", valign: "middle", charSpacing: 6, margin: 0
    });
    // Status bar
    s.addShape("rect", {
        x: winX, y: winY + winH - 0.3, w: winW, h: 0.3,
        fill: { color: "090B0D" }, line: { color: "090B0D" }
    });
    s.addText("▸ playing   ◉ 12 blobs   ⚡ 29.4 fps   ○ idle", {
        x: winX + 0.15, y: winY + winH - 0.3, w: winW - 0.3, h: 0.3,
        fontFace: "Consolas", fontSize: 9, color: C.textFaint, valign: "middle", margin: 0
    });

    // Right column: design principles
    s.addText("DESIGN PRINCIPLES", {
        x: 7.7, y: 2.85, w: 5, h: 0.3,
        fontFace: "Consolas", fontSize: 10, color: C.textFaint, bold: true, charSpacing: 4, margin: 0
    });
    const principles = [
        { t: "Dark-first palette",   d: "Reduces eye strain during long sessions; #0C0E10 base, #00C8F0 accent." },
        { t: "Section colour-coding", d: "Each control group has its own title hue for fast visual scanning." },
        { t: "Monospace where it counts", d: "All numeric read-outs use JetBrains Mono for stable column widths." },
        { t: "Dockable panel", d: "Control panel can be undocked, moved right, or hidden entirely." },
    ];
    principles.forEach((p, i) => {
        const y = 3.25 + i * 0.78;
        s.addText("·", {
            x: 7.7, y: y, w: 0.2, h: 0.3,
            fontFace: "Calibri", fontSize: 18, color: C.accent, bold: true, margin: 0
        });
        s.addText(p.t, {
            x: 7.95, y: y, w: 4.6, h: 0.3,
            fontFace: "Calibri", fontSize: 14, color: C.text, bold: true, margin: 0
        });
        s.addText(p.d, {
            x: 7.95, y: y + 0.3, w: 4.6, h: 0.4,
            fontFace: "Calibri", fontSize: 11, color: C.textDim, margin: 0
        });
    });
}

// =====================================================================
//  SLIDE 11 — PLUGIN ARCHITECTURE
// =====================================================================
{
    const s = pres.addSlide();
    chrome(s, 11, TOTAL, "09  PLUGINS", C.secCre);
    slideTitle(s, "Plugin Architecture", "Extending the creative chain without recompiling", C.secCre);

    // Steps
    const steps = [
        { n: "1", t: "Drop file in plugins/", d: "Any .py file is auto-discovered on scan." },
        { n: "2", t: "Subclass CreativeFilter", d: "Define name attribute + apply(frame) method." },
        { n: "3", t: "Hot reload",          d: "Click reload — no app restart, importlib re-binds the class." },
    ];
    steps.forEach((st, i) => {
        const x = 0.9 + i * 4.15;
        s.addShape("rect", {
            x: x, y: 2.85, w: 3.9, h: 1.5,
            fill: { color: C.bgCard }, line: { color: C.rule, width: 0.5 }
        });
        s.addShape("ellipse", {
            x: x + 0.25, y: 3.0, w: 0.55, h: 0.55,
            fill: { color: C.secCre }, line: { color: C.secCre }
        });
        s.addText(st.n, {
            x: x + 0.25, y: 3.0, w: 0.55, h: 0.55,
            fontFace: "Calibri", fontSize: 18, color: C.bg, bold: true,
            align: "center", valign: "middle", margin: 0
        });
        s.addText(st.t, {
            x: x + 0.95, y: 3.0, w: 2.85, h: 0.4,
            fontFace: "Calibri", fontSize: 14, color: C.text, bold: true, margin: 0
        });
        s.addText(st.d, {
            x: x + 0.95, y: 3.45, w: 2.85, h: 0.85,
            fontFace: "Calibri", fontSize: 11, color: C.textDim, margin: 0
        });
    });

    // Code block
    s.addText("EXAMPLE  ·  plugins/vignette_pulse.py", {
        x: 0.9, y: 4.6, w: 8, h: 0.3,
        fontFace: "Consolas", fontSize: 10, color: C.textFaint, bold: true, charSpacing: 4, margin: 0
    });
    s.addShape("rect", {
        x: 0.9, y: 4.95, w: W - 1.8, h: 1.55,
        fill: { color: C.bgPanel }, line: { color: C.rule, width: 0.5 }
    });
    s.addText([
        { text: "from ", options: { color: C.textDim } },
        { text: "effect_engine ", options: { color: C.text } },
        { text: "import ", options: { color: C.textDim } },
        { text: "CreativeFilter", options: { color: C.accent, breakLine: true } },
        { text: " ", options: { breakLine: true } },
        { text: "class ", options: { color: C.secCre } },
        { text: "VignettePulseFilter", options: { color: C.text, bold: true } },
        { text: "(CreativeFilter):", options: { color: C.text, breakLine: true } },
        { text: "    name = ", options: { color: C.text } },
        { text: "\"VignettePulseFilter\"", options: { color: C.accent, breakLine: true } },
        { text: " ", options: { breakLine: true } },
        { text: "    def ", options: { color: C.secCre } },
        { text: "apply", options: { color: C.text, bold: true } },
        { text: "(self, frame):", options: { color: C.text, breakLine: true } },
        { text: "        ", options: { color: C.text } },
        { text: "# darken corners proportional to radial distance", options: { color: C.textFaint, italic: true, breakLine: true } },
        { text: "        return ", options: { color: C.secCre } },
        { text: "(frame * radial_mask).astype(np.uint8)", options: { color: C.text } },
    ], {
        x: 1.1, y: 5.1, w: W - 2.2, h: 1.4,
        fontFace: "Consolas", fontSize: 12, paraSpaceAfter: 0, margin: 0
    });
}

// =====================================================================
//  SLIDE 12 — PERFORMANCE
// =====================================================================
{
    const s = pres.addSlide();
    chrome(s, 12, TOTAL, "10  PERFORMANCE");
    slideTitle(s, "Performance Analysis", "FPS scaling with process_scale and detect_every_n");

    // Chart: FPS vs process_scale at three detect_every_n values
    s.addChart(pres.charts.LINE, [
        { name: "detect_every_n = 1", labels: ["0.25", "0.40", "0.50", "0.65", "0.80", "1.00"], values: [60, 52, 44, 33, 22, 14] },
        { name: "detect_every_n = 2", labels: ["0.25", "0.40", "0.50", "0.65", "0.80", "1.00"], values: [60, 60, 58, 48, 35, 24] },
        { name: "detect_every_n = 3", labels: ["0.25", "0.40", "0.50", "0.65", "0.80", "1.00"], values: [60, 60, 60, 58, 47, 33] },
    ], {
        x: 0.9, y: 2.8, w: 7.5, h: 3.8,
        chartColors: [C.secInput, C.accent, C.secCre],
        chartArea: { fill: { color: C.bgPanel } },
        plotArea:  { fill: { color: C.bgPanel } },
        catAxisLabelColor: C.textDim, catAxisLabelFontFace: "Consolas", catAxisLabelFontSize: 9,
        valAxisLabelColor: C.textDim, valAxisLabelFontFace: "Consolas", valAxisLabelFontSize: 9,
        catGridLine: { style: "none" },
        valGridLine: { color: C.rule, size: 0.5 },
        valAxisMinVal: 0, valAxisMaxVal: 65,
        lineSize: 2.5, lineSmooth: true,
        lineDataSymbol: "circle", lineDataSymbolSize: 7,
        showTitle: true, title: "Measured FPS vs Process Scale",
        titleColor: C.text, titleFontFace: "Calibri", titleFontSize: 13,
        showLegend: true, legendPos: "b",
        legendColor: C.textDim, legendFontFace: "Calibri", legendFontSize: 10,
        showCatAxisTitle: true, catAxisTitle: "process_scale",
        catAxisTitleColor: C.textDim, catAxisTitleFontSize: 10, catAxisTitleFontFace: "Calibri",
    });

    // Right: takeaways
    s.addText("FINDINGS", {
        x: 8.7, y: 2.9, w: 5, h: 0.3,
        fontFace: "Consolas", fontSize: 10, color: C.textFaint, bold: true, charSpacing: 4, margin: 0
    });
    const findings = [
        { v: "0.5×",   d: "best quality/speed trade-off for 720p sources" },
        { v: "N=2",    d: "halves detection cost with negligible ID drift" },
        { v: "~30 fps", d: "sustainable at full HD on a mid-range laptop" },
    ];
    findings.forEach((f, i) => {
        const y = 3.3 + i * 1.0;
        s.addText(f.v, {
            x: 8.7, y: y, w: 1.6, h: 0.7,
            fontFace: "Calibri", fontSize: 34, color: C.accent, bold: true, margin: 0
        });
        s.addText(f.d, {
            x: 10.3, y: y + 0.05, w: 2.4, h: 0.7,
            fontFace: "Calibri", fontSize: 12, color: C.textDim, valign: "middle", margin: 0
        });
    });
}

// =====================================================================
//  SLIDE 13 — USE CASES & RESULTS
// =====================================================================
{
    const s = pres.addSlide();
    chrome(s, 13, TOTAL, "11  RESULTS");
    slideTitle(s, "Use Cases & Results", "Where BlobTracker fits");

    const cases = [
        { tag: "RESEARCH",    t: "CV Education",  d: "Live, hands-on illustration of detection, tracking, and assignment.", c: C.secInput },
        { tag: "INDUSTRY",    t: "Surveillance",  d: "Lightweight movement counting on archived video files.",              c: C.secTrack },
        { tag: "CREATIVE",    t: "Visual Arts",   d: "Real-time motion graphics for performance and installation work.",    c: C.secFx },
        { tag: "PROTOTYPING", t: "Iteration",     d: "Rapid parameter tuning without code edits via the parameter store.",  c: C.secCre },
    ];

    cases.forEach((c, i) => {
        const col = i % 2, row = Math.floor(i / 2);
        const x = 0.9 + col * 5.85, y = 2.85 + row * 1.95;
        s.addShape("rect", {
            x: x, y: y, w: 5.55, h: 1.8,
            fill: { color: C.bgCard }, line: { color: C.rule, width: 0.5 }
        });
        s.addShape("rect", {
            x: x, y: y, w: 5.55, h: 0.05,
            fill: { color: c.c }, line: { color: c.c }
        });
        s.addText(c.tag, {
            x: x + 0.3, y: y + 0.2, w: 5, h: 0.3,
            fontFace: "Consolas", fontSize: 9, color: c.c, bold: true, charSpacing: 5, margin: 0
        });
        s.addText(c.t, {
            x: x + 0.3, y: y + 0.55, w: 5, h: 0.5,
            fontFace: "Calibri", fontSize: 22, color: C.text, bold: true, margin: 0
        });
        s.addText(c.d, {
            x: x + 0.3, y: y + 1.1, w: 5, h: 0.65,
            fontFace: "Calibri", fontSize: 12, color: C.textDim, margin: 0
        });
    });
}

// =====================================================================
//  SLIDE 14 — CONCLUSION & FUTURE WORK
// =====================================================================
{
    const s = pres.addSlide();
    chrome(s, 14, TOTAL, "12  CONCLUSION");
    slideTitle(s, "Conclusion & Future Work", "What works, and what comes next");

    // What works (left)
    s.addText("DELIVERED", {
        x: 0.9, y: 2.75, w: 4, h: 0.3,
        fontFace: "Consolas", fontSize: 10, color: C.accent, bold: true, charSpacing: 4, margin: 0
    });
    s.addText([
        { text: "✓  ", options: { color: C.accent } },
        { text: "Real-time detection + tracking pipeline", options: { color: C.text, breakLine: true } },
        { text: "✓  ", options: { color: C.accent } },
        { text: "Eight overlay effects with blend modes", options: { color: C.text, breakLine: true } },
        { text: "✓  ", options: { color: C.accent } },
        { text: "Plugin system with hot reload", options: { color: C.text, breakLine: true } },
        { text: "✓  ", options: { color: C.accent } },
        { text: "Deterministic offline render path", options: { color: C.text, breakLine: true } },
        { text: "✓  ", options: { color: C.accent } },
        { text: "JSON-based preset save/load", options: { color: C.text, breakLine: true } },
        { text: "✓  ", options: { color: C.accent } },
        { text: "Complete docs in 6 reference files", options: { color: C.text } },
    ], {
        x: 0.9, y: 3.1, w: 5.8, h: 3.0,
        fontFace: "Calibri", fontSize: 14, paraSpaceAfter: 6, margin: 0
    });

    // Future work (right)
    s.addText("ROADMAP", {
        x: 7.0, y: 2.75, w: 4, h: 0.3,
        fontFace: "Consolas", fontSize: 10, color: C.secCre, bold: true, charSpacing: 4, margin: 0
    });
    const futures = [
        { t: "Kalman filter tracking", d: "Predictive smoothing under occlusion" },
        { t: "GPU acceleration",       d: "Optional CUDA / OpenCL backend for HD/4K" },
        { t: "Deep learning detector", d: "Plug-in YOLOv8 / DETR for object classes" },
        { t: "Multi-monitor preview",  d: "Decouple operator UI from on-screen output" },
        { t: "Plugin marketplace",     d: "Shareable, versioned effect packs" },
    ];
    futures.forEach((f, i) => {
        const y = 3.1 + i * 0.6;
        s.addShape("rect", {
            x: 7.0, y: y, w: 0.05, h: 0.5,
            fill: { color: C.secCre }, line: { color: C.secCre }
        });
        s.addText(f.t, {
            x: 7.2, y: y, w: 5.5, h: 0.25,
            fontFace: "Calibri", fontSize: 13, color: C.text, bold: true, margin: 0
        });
        s.addText(f.d, {
            x: 7.2, y: y + 0.25, w: 5.5, h: 0.25,
            fontFace: "Calibri", fontSize: 11, color: C.textDim, margin: 0
        });
    });
}

// =====================================================================
//  SLIDE 15 — Q&A / THANK YOU
// =====================================================================
{
    const s = pres.addSlide();
    s.background = { color: C.bg };

    // Side stripe
    s.addShape("rect", {
        x: 0, y: 0, w: 0.25, h: H, fill: { color: C.accentDk }, line: { color: C.accentDk }
    });

    // Faint pattern: scatter of dots
    for (let i = 0; i < 30; i++) {
        const px = 8 + Math.random() * 5;
        const py = 0.5 + Math.random() * 6.5;
        s.addShape("ellipse", {
            x: px, y: py, w: 0.05, h: 0.05,
            fill: { color: C.accent, transparency: 70 + Math.random() * 25 },
            line: { color: C.accent, width: 0 }
        });
    }

    s.addText("QUESTIONS  ·  DISCUSSION", {
        x: 1.0, y: 2.0, w: 10, h: 0.4,
        fontFace: "Consolas", fontSize: 13, color: C.textDim, bold: true, charSpacing: 6, margin: 0
    });
    s.addText("Thank you.", {
        x: 1.0, y: 2.5, w: 11, h: 1.5,
        fontFace: "Calibri", fontSize: 92, color: C.accent, bold: true, margin: 0
    });

    s.addShape("line", {
        x: 1.0, y: 4.4, w: 5, h: 0,
        line: { color: C.rule, width: 1 }
    });

    s.addText("PROJECT", {
        x: 1.0, y: 4.6, w: 4, h: 0.3,
        fontFace: "Consolas", fontSize: 10, color: C.textFaint, bold: true, charSpacing: 4, margin: 0
    });
    s.addText("BlobTracker — Real-time Computer Vision Desktop App", {
        x: 1.0, y: 4.9, w: 10, h: 0.4,
        fontFace: "Calibri", fontSize: 18, color: C.text, margin: 0
    });

    s.addText("AUTHORS", {
        x: 1.0, y: 5.6, w: 4, h: 0.3,
        fontFace: "Consolas", fontSize: 10, color: C.textFaint, bold: true, charSpacing: 4, margin: 0
    });
    s.addText("Hachim Boubdillah   ·   Baqua Abdellah", {
        x: 1.0, y: 5.9, w: 10, h: 0.4,
        fontFace: "Calibri", fontSize: 18, color: C.text, bold: true, margin: 0
    });

    s.addShape("rect", {
        x: 0, y: H - 0.25, w: W, h: 0.25, fill: { color: C.accentDk }, line: { color: C.accentDk }
    });
}

// =====================================================================
pres.writeFile({ fileName: "blobtracker_presentation.pptx" })
    .then(file => console.log("Wrote:", file));
