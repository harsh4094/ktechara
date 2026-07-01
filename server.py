#!/usr/bin/env python3
"""
Local dev server for ktechara static site.
Serves 404/index.html (with the real HTTP status) for any error route,
matching Hostinger/Apache ErrorDocument behaviour.

Usage:
    python server.py          # listens on port 5500
    python server.py 8080     # custom port
"""
import http.server
import sys
from pathlib import Path

PORT = 5500
ROOT = Path(__file__).parent.resolve()
ERROR_PAGE = ROOT / "404" / "index.html"

# Codes handled by .htaccess ErrorDocument directives
HANDLED_CODES = {400, 401, 403, 404, 408, 410, 429, 500, 502, 503, 504}


class SiteHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def send_error(self, code, message=None, explain=None):
        if code in HANDLED_CODES and ERROR_PAGE.exists():
            # Read content before touching the socket so a read failure
            # never corrupts a partially-written response.
            try:
                content = ERROR_PAGE.read_bytes()
            except OSError:
                super().send_error(code, message, explain)
                return
            # Inject ?code= so detectCode() in the page JS works correctly,
            # matching the ?code= query param appended by .htaccess directives.
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            try:
                self.wfile.write(content)
            except OSError:
                pass  # client disconnected after headers — nothing to do
        else:
            super().send_error(code, message, explain)

    def log_message(self, fmt, *args):
        print(f"[{self.address_string()}] {fmt % args}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            print(f"Usage: python server.py [port]  (default: {PORT})", file=sys.stderr)
            sys.exit(1)
    else:
        port = PORT

    if not ERROR_PAGE.exists():
        print(f"Warning: error page not found at {ERROR_PAGE}", file=sys.stderr)

    addr = ("127.0.0.1", port)
    print(f"Serving http://127.0.0.1:{port}/  (Ctrl+C to stop)")
    with http.server.HTTPServer(addr, SiteHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
