#!/usr/bin/env python3
"""Serve Mirror-Lean frontend and inject the MOSTAI_API_KEY from .env.

Run with:
    python serve.py
Then open http://localhost:8081/demos/g1_23dof_coach.html
"""
import json
import os
import http.client
import shlex
import subprocess
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).parent.resolve()


def load_dotenv():
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _send_json(self, code, body):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _proxy_to_robot(self, robot_path, method, content_type, body):
        try:
            conn = http.client.HTTPConnection("192.168.52.241", 8123, timeout=15)
            headers = {"Content-Length": str(len(body))}
            if content_type:
                headers["Content-Type"] = content_type
            conn.request(method, robot_path, body=body, headers=headers)
            resp = conn.getresponse()
            status = resp.status
            resp_body = resp.read()
            conn.close()
            return status, resp_body
        except Exception as e:
            return 502, str(e).encode("utf-8")

    def _robot_say_via_ssh(self, text: str) -> tuple:
        """Run the robot's say.py via SSH+expect (password auth).

        The robot-side command is confirmed working:
            ssh unitree@192.168.52.241 "python3 ~/say.py eth0 '...'"
        """
        if not text:
            return 400, b"text required"
        # Shell-quote the text so single quotes inside do not break the SSH command.
        safe_text = "'" + text.replace("'", "'\\''") + "'"
        expect_script = ROOT / "ssh-say.exp"
        try:
            result = subprocess.run(
                ["expect", str(expect_script), safe_text],
                capture_output=True,
                text=True,
                timeout=25,
            )
            if result.returncode == 0:
                return 200, b"spoken"
            err = (result.stderr or result.stdout or "expect/ssh failed").encode("utf-8")
            return 502, err
        except subprocess.TimeoutExpired:
            return 504, b"ssh say timed out"
        except Exception as e:
            return 502, str(e).encode("utf-8")

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/proxy/robot-speaker":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            content_type = self.headers.get("Content-Type", "audio/mpeg")
            status, resp_body = self._proxy_to_robot("/speak", "POST", content_type, body)
            self._send_json(status, resp_body)
            return
        if parsed.path == "/proxy/robot-speaker-text":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                payload = json.loads(body.decode("utf-8"))
                text = payload.get("text", "").strip()
            except Exception:
                self._send_json(400, b"invalid json")
                return
            status, resp_body = self._robot_say_via_ssh(text)
            self._send_json(status, resp_body)
            return
        self._send_json(404, "not found")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path in ("/", "/demos/g1_23dof_coach.html"):
            html_path = ROOT / "demos" / "g1_23dof_coach.html"
            html = html_path.read_bytes()
            mostai_key = os.environ.get("MOSTAI_API_KEY", "")
            openai_key = os.environ.get("OPENAI_API_KEY", "")
            injection = (
                f'<script>'
                f'window.__MOSTAI_API_KEY__={mostai_key!r};'
                f'window.__OPENAI_API_KEY__={openai_key!r};'
                f'</script>'
            ).encode()
            # Insert right before the closing </head> so it is available to the module script.
            html = html.replace(b"</head>", injection + b"</head>", 1)
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html)
            return
        super().do_GET()


if __name__ == "__main__":
    load_dotenv()
    port = int(os.environ.get("PORT", "8081"))
    server = HTTPServer(("localhost", port), Handler)
    print(f"Serving Mirror-Lean at http://localhost:{port}")
    print(f"Demo page: http://localhost:{port}/demos/g1_23dof_coach.html")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
