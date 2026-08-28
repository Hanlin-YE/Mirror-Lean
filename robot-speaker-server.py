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
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

PORT = int(os.environ.get("PORT", "8123"))
HOST = os.environ.get("HOST", "0.0.0.0")


def log(msg: str):
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()


def run_ok(cmd: list, timeout: int = 30) -> bool:
    try:
        result = subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=timeout)
        if result.returncode != 0:
            err = result.stderr.decode("utf-8", "ignore").strip()[:200]
            log(f"cmd failed ({' '.join(cmd)}): {err}")
            return False
        return True
    except subprocess.TimeoutExpired:
        log(f"cmd timed out ({' '.join(cmd)})")
        return False
    except Exception as e:
        log(f"cmd exception ({' '.join(cmd)}): {e}")
        return False


def play_audio_bytes(data: bytes, content_type: str = "audio/mpeg") -> bool:
    """Play raw audio bytes using the first available local player.

    aplay only supports WAV, so for MP3 we first try ffplay, then convert
    to WAV with ffmpeg and play that.
    """
    suffix = ".mp3"
    is_wav = "wav" in content_type
    if is_wav:
        suffix = ".wav"
    elif "ogg" in content_type:
        suffix = ".ogg"
    elif "flac" in content_type:
        suffix = ".flac"

    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)

        def play_wav(wav_path: str) -> bool:
            if shutil.which("paplay"):
                log("playing WAV with paplay")
                if run_ok(["paplay", wav_path]):
                    return True
            if shutil.which("aplay"):
                log("playing WAV with aplay")
                if run_ok(["aplay", wav_path]):
                    return True
            return False

        # WAV can go straight to paplay/aplay.
        if is_wav:
            if play_wav(path):
                return True

        # Try ffplay first for compressed formats (route through PulseAudio).
        if shutil.which("ffplay"):
            log("playing with ffplay")
            if run_ok(["ffplay", "-nodisp", "-autoexit", "-hide_banner", "-loglevel", "error", path]):
                return True

        # Fallback: ffmpeg decode to WAV, then play.
        if shutil.which("ffmpeg"):
            wav_fd, wav_path = tempfile.mkstemp(suffix=".wav")
            try:
                os.close(wav_fd)
                log("converting to WAV with ffmpeg")
                if run_ok(["ffmpeg", "-y", "-i", path, "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", wav_path]):
                    if play_wav(wav_path):
                        return True
            finally:
                try:
                    os.unlink(wav_path)
                except OSError:
                    pass

        if shutil.which("mpg123"):
            log("playing with mpg123")
            if run_ok(["mpg123", path]):
                return True

        log("no working audio player found")
        return False
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def detect_speaker_id(text: str) -> int:
    """Unitree TTS: 0 = Chinese/Auto, 1 = English."""
    for ch in text:
        if "\u4e00" <= ch <= "\u9fff":
            return 0
    return 1


def speak_text_unitree(text: str) -> bool:
    """Speak text using the Unitree G1 stock audio service (AudioClient::TtsMaker).

    This relies on the companion C++ binary ``robot-tts`` built from
    ``robot-tts.cc`` against the on-robot unitree_sdk2.
    """
    bin_path = os.environ.get("ROBOT_TTS_BIN", os.path.join(os.path.dirname(__file__), "build", "robot-tts"))
    iface = os.environ.get("ROBOT_TTS_IFACE", "eth0")
    if not os.path.isfile(bin_path):
        log(f"robot-tts binary not found at {bin_path}")
        return False

    speaker_id = detect_speaker_id(text)
    log(f"speaking with Unitree AudioClient TtsMaker (speaker_id={speaker_id})")
    return run_ok([bin_path, iface, text, str(speaker_id)], timeout=15)


def speak_text_local(text: str) -> bool:
    """Speak text using local TTS engines as a fallback."""
    # Try espeak with Chinese voice hint.
    if shutil.which("espeak"):
        log("speaking with espeak")
        if run_ok(["espeak", "-v", "zh", text]):
            return True

    # macOS built-in say.
    if shutil.which("say"):
        log("speaking with say")
        if run_ok(["say", text]):
            return True

    # pyttsx3 cross-platform fallback.
    try:
        import pyttsx3
        log("speaking with pyttsx3")
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
        return True
    except Exception as e:
        log(f"pyttsx3 failed: {e}")

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
            content_type = self.headers.get("Content-Type", "audio/mpeg")
            # Acknowledge receipt immediately; playback can take several seconds.
            self._send(202, b"accepted")
            def _play():
                ok = play_audio_bytes(data, content_type)
                if not ok:
                    log("playback failed for /speak")
            threading.Thread(target=_play, daemon=True).start()
            return
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

            # Return 202 immediately so callers don't hang while the TTS engine
            # synthesizes and plays. Playback is handled in a background thread.
            self._send(202, b"accepted")

            def _speak():
                if speak_text_unitree(text):
                    log(f"/speak-text succeeded via Unitree TTS: {text[:60]!r}")
                    return
                if speak_text_local(text):
                    log(f"/speak-text succeeded via local TTS: {text[:60]!r}")
                    return
                log(f"/speak-text failed for: {text[:60]!r}")

            threading.Thread(target=_speak, daemon=True).start()
            return
        else:
            self._send(404, b"not found")

    def log_message(self, format, *args):
        log(format % args)


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Robot speaker server listening on http://{HOST}:{PORT}")
    print("Endpoints: POST /speak (audio bytes), POST /speak-text (JSON)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
