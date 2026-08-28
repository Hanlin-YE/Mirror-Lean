#!/usr/bin/env python3
"""
Robot speaker relay.

Run this script on the robot (e.g. Unitree Go / Jetson) so the browser
frontend can send synthesized speech to the robot's speaker instead of
the laptop speaker.

    python3 robot-speaker-server.py

It exposes two endpoints:

  POST /speak          - raw audio bytes (MP3/WAV). Plays immediately.
  POST /speak-text     - JSON {"text": "..."}. Uses local TTS fallback.

The script tries common audio players in order: aplay, ffplay, mpg123,
and falls back to local text-to-speech (espeak, say, or pyttsx3) for
plain text.
"""

import os
import sys
import json
import shutil
import tempfile
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

PORT = int(os.environ.get("PORT", "8123"))
HOST = os.environ.get("HOST", "0.0.0.0")


def play_audio_bytes(data: bytes, content_type: str = "audio/mpeg") -> bool:
    """Play raw audio bytes using the first available local player."""
    suffix = ".mp3"
    if "wav" in content_type:
        suffix = ".wav"
    elif "ogg" in content_type:
        suffix = ".ogg"
    elif "flac" in content_type:
        suffix = ".flac"

    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)

        # Try players in order of preference.
        players = [
            ["aplay", path],                         # ALSA
            ["ffplay", "-nodisp", "-autoexit", path],  # ffmpeg
            ["mpg123", path],                        # MP3
            ["cvlc", "--play-and-exit", path],       # VLC headless
        ]
        for cmd in players:
            if shutil.which(cmd[0]):
                try:
                    subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return True
                except Exception as e:
                    print(f"player {cmd[0]} failed: {e}")
        return False
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def speak_text_local(text: str) -> bool:
    """Speak text using local TTS engines."""
    # Try espeak with Chinese voice hint.
    if shutil.which("espeak"):
        try:
            subprocess.run(["espeak", "-v", "zh", text], check=False)
            return True
        except Exception as e:
            print(f"espeak failed: {e}")

    # macOS built-in say.
    if shutil.which("say"):
        try:
            subprocess.run(["say", text], check=False)
            return True
        except Exception as e:
            print(f"say failed: {e}")

    # pyttsx3 cross-platform fallback.
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
        return True
    except Exception as e:
        print(f"pyttsx3 failed: {e}")

    return False


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes = b""):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(length)

        if parsed.path == "/speak":
            ok = play_audio_bytes(data, self.headers.get("Content-Type", "audio/mpeg"))
            if ok:
                self._send(200, b"played")
            else:
                self._send(500, b"no audio player found")
        elif parsed.path == "/speak-text":
            try:
                payload = json.loads(data.decode("utf-8"))
            except json.JSONDecodeError:
                self._send(400, b"invalid json")
                return
            text = payload.get("text", "").strip()
            if not text:
                self._send(400, b"text required")
                return
            ok = speak_text_local(text)
            if ok:
                self._send(200, b"spoken")
            else:
                self._send(500, b"no local tts available")
        else:
            self._send(404, b"not found")

    def log_message(self, format, *args):
        print(format % args)


if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), Handler)
    print(f"Robot speaker server listening on http://{HOST}:{PORT}")
    print("Endpoints: POST /speak (audio bytes), POST /speak-text (JSON)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
