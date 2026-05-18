"""Mistral-powered in-app assistant for BlobTracker.

Provides a dockable chat panel that helps users discover and use features.
The API key is read from the MISTRAL_API_KEY environment variable.
"""
from __future__ import annotations

import json
import os
import ssl
import time
import urllib.error
import urllib.request
from typing import List, Dict, Optional

from PyQt6.QtCore import QObject, QThread, Qt, pyqtSignal
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import (
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


MISTRAL_ENDPOINT = "https://api.mistral.ai/v1/chat/completions"
DEFAULT_MODEL = "mistral-small-latest"

# Ordered fallback list used when a model returns 429 / capacity exceeded.
# Each entry is tried once, in order, before giving up.
FALLBACK_MODELS = [
    "mistral-small-latest",
    "open-mistral-7b",
    "open-mixtral-8x7b",
    "mistral-tiny-latest",
    "ministral-3b-latest",
]

SYSTEM_PROMPT = """You are the in-app assistant for BlobTracker, a Python/PyQt6/OpenCV
desktop application for real-time blob detection, tracking, and creative video effects.

Help the user use the app. Answer concisely (1-4 short paragraphs or a short list).
When pointing to UI, name the panel (Control Panel on the left dock), and the relevant
section. Key features you can guide users on:

- Input: webcam or video file (File > Open Video...). Set target FPS, source type,
  webcam index, or file path in the Control Panel > Input section.
- Playback: play/pause, skip start/end, loop, and timeline scrubber in the bottom bar.
- Detection: threshold, blur_radius, min/max area, max count, detector mode (contour or
  simple), min circularity. Found under Control Panel > Blob Detection.
- Tracking: smoothing, max trail length, max disappeared frames. Control Panel > Tracking.
- Effects: bounding boxes, labels (IDs, coords), trails, connection lines between blobs,
  zoom inset, optical flow overlay, base frame (desaturate/grain/vignette).
- Creative filters chain: Grain, Glitch, Thermal, Edge, Chromatic Aberration, plus user
  plugins from blobtracker/plugins/. Reorder under Control Panel > Creative.
- Blend modes: normal, screen, overlay, multiply.
- Presets: save/load named presets (default, surveillance). Use View > Preset Browser.
- Projects: File > Save/Load Project (.btrack) stores params + source path.
- Recording: live record to mp4 / png_seq / prores from the current preview.
- Offline render: high-quality frame-by-frame render of the whole source file to mp4.
- Plugins: drop CreativeFilter subclasses into blobtracker/plugins/ and use
  Effects > Hot Reload Plugins.
- Hotkeys: Space = play/pause, plus record toggle, preset browser, fullscreen.

If the user asks something unrelated to BlobTracker, briefly steer back to the app.
Do not invent UI elements or parameters that aren't listed above."""


class MistralWorker(QObject):
    """Runs a single chat completion request on a background thread."""

    chunk = pyqtSignal(str)
    finished = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, api_key: str, model: str, messages: List[Dict[str, str]]) -> None:
        super().__init__()
        self._api_key = api_key
        self._model = model
        self._messages = messages

    def _models_to_try(self) -> List[str]:
        ordered: List[str] = [self._model]
        for m in FALLBACK_MODELS:
            if m and m not in ordered:
                ordered.append(m)
        return ordered

    def _call(self, model: str) -> tuple:
        """Return (content, error_message, http_code). content set on success."""
        payload = {
            "model": model,
            "messages": self._messages,
            "temperature": 0.3,
            "stream": False,
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            MISTRAL_ENDPOINT,
            data=body,
            method="POST",
            headers={
                "Authorization": "Bearer {}".format(self._api_key),
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
            choices = data.get("choices") or []
            if not choices:
                return ("", "Empty response from Mistral.", 0)
            content = choices[0].get("message", {}).get("content", "")
            return (content or "", "", 200)
        except urllib.error.HTTPError as e:
            try:
                detail = e.read().decode("utf-8", errors="replace")
            except Exception:
                detail = ""
            return ("", "HTTP {}: {}".format(e.code, detail[:400]), e.code)
        except urllib.error.URLError as e:
            return ("", "Network error: {}".format(e.reason), 0)
        except Exception as e:
            return ("", "Error: {}".format(e), 0)

    def run(self) -> None:
        last_err = "No models attempted."
        for idx, model in enumerate(self._models_to_try()):
            content, err, code = self._call(model)
            if not err:
                self.finished.emit(content)
                return
            last_err = "[{}] {}".format(model, err)
            # Only fall through on capacity / rate-limit signals; everything
            # else (auth, bad request, network) is fatal and reported now.
            is_capacity = code == 429 or "capacity" in err.lower() or "rate" in err.lower()
            if not is_capacity:
                self.failed.emit(last_err)
                return
            # Brief backoff before trying the next model.
            if idx + 1 < len(self._models_to_try()):
                time.sleep(0.4)
        self.failed.emit("All models busy. Last error: {}".format(last_err))


class ChatbotDock(QDockWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("Assistant", parent)
        self.setObjectName("chatbot_dock")
        self.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea
        )

        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        self.transcript = QTextEdit(container)
        self.transcript.setReadOnly(True)
        self.transcript.setObjectName("chatbot_transcript")
        layout.addWidget(self.transcript, 1)

        input_row = QHBoxLayout()
        input_row.setSpacing(4)
        self.input = QLineEdit(container)
        self.input.setPlaceholderText("Ask how to use a feature...")
        self.input.returnPressed.connect(self._on_send)
        self.send_btn = QPushButton("Send", container)
        self.send_btn.clicked.connect(self._on_send)
        self.clear_btn = QPushButton("Clear", container)
        self.clear_btn.clicked.connect(self._on_clear)
        input_row.addWidget(self.input, 1)
        input_row.addWidget(self.send_btn)
        input_row.addWidget(self.clear_btn)
        layout.addLayout(input_row)

        self.status = QLabel("", container)
        self.status.setObjectName("chatbot_status")
        layout.addWidget(self.status)

        self.setWidget(container)

        self._history: List[Dict[str, str]] = []
        self._thread: Optional[QThread] = None
        self._worker: Optional[MistralWorker] = None
        self._model = os.environ.get("MISTRAL_MODEL", DEFAULT_MODEL)

        if not self._api_key():
            self._append("system", "Set MISTRAL_API_KEY in your environment to enable the assistant.")
            self.input.setEnabled(False)
            self.send_btn.setEnabled(False)
        else:
            self._append(
                "assistant",
                "Hi! Ask me anything about BlobTracker — e.g. \"how do I record a video?\" or "
                "\"what does the connection effect do?\".",
            )

    def _api_key(self) -> str:
        return os.environ.get("MISTRAL_API_KEY", "").strip()

    def _append(self, role: str, text: str) -> None:
        if role == "user":
            prefix = '<div style="color:#7cd3ff;margin-top:6px;"><b>You</b></div>'
        elif role == "assistant":
            prefix = '<div style="color:#a8e6a3;margin-top:6px;"><b>Assistant</b></div>'
        else:
            prefix = '<div style="color:#bbbbbb;margin-top:6px;"><i>system</i></div>'
        safe = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>")
        )
        html = '{}<div style="white-space:pre-wrap;">{}</div>'.format(prefix, safe)
        self.transcript.append(html)
        self.transcript.moveCursor(QTextCursor.MoveOperation.End)

    def _on_clear(self) -> None:
        self._history.clear()
        self.transcript.clear()
        self.status.setText("")

    def _on_send(self) -> None:
        if self._thread is not None:
            return
        text = self.input.text().strip()
        if not text:
            return
        key = self._api_key()
        if not key:
            self.status.setText("MISTRAL_API_KEY not set.")
            return

        self.input.clear()
        self._append("user", text)
        self._history.append({"role": "user", "content": text})

        messages: List[Dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        # Cap history length to last 12 turns to keep prompt small.
        messages.extend(self._history[-12:])

        self.send_btn.setEnabled(False)
        self.input.setEnabled(False)
        self.status.setText("Thinking...")

        self._thread = QThread(self)
        self._worker = MistralWorker(key, self._model, messages)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        self._thread.start()

    def _on_finished(self, content: str) -> None:
        self._append("assistant", content)
        self._history.append({"role": "assistant", "content": content})
        self.status.setText("")

    def _on_failed(self, err: str) -> None:
        self._append("system", "Request failed: {}".format(err))
        if self._history and self._history[-1]["role"] == "user":
            self._history.pop()
        self.status.setText("Error.")

    def _cleanup_thread(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None
        if self._thread is not None:
            self._thread.deleteLater()
            self._thread = None
        self.send_btn.setEnabled(True)
        self.input.setEnabled(True)
        self.input.setFocus()
