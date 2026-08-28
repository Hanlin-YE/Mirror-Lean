#!/usr/bin/env python3
"""Serve Mirror-Lean frontend and inject the MOSTAI_API_KEY from .env.

Run with:
    python serve.py
Then open http://localhost:8081/demos/g1_23dof_coach.html
"""
import os
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
