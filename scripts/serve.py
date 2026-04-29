#!/usr/bin/env python3
"""Local dev server that mimics GitHub Pages extension-stripping.

Serves foo.html when /foo is requested, so extensionless URLs work locally.
Run:  python3 scripts/serve.py
"""

import functools
import http.server
import os

PORT = 8000
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "output")


class CleanURLHandler(http.server.SimpleHTTPRequestHandler):
    def send_head(self):
        path = self.translate_path(self.path)
        if (not os.path.exists(path)
                and not self.path.endswith("/")
                and "?" not in self.path
                and "#" not in self.path
                and os.path.isfile(path + ".html")):
            self.path += ".html"
        return super().send_head()

    def send_error(self, code, message=None, explain=None):
        # Mirror GitHub Pages: serve the styled 404.html body for any 404.
        if code == 404:
            page = os.path.join(self.directory, "404.html")
            if os.path.isfile(page):
                with open(page, "rb") as f:
                    body = f.read()
                self.send_response(404, message)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(body)
                return
        super().send_error(code, message, explain)


if __name__ == "__main__":
    handler = functools.partial(CleanURLHandler, directory=ROOT)
    with http.server.ThreadingHTTPServer(("", PORT), handler) as httpd:
        print(f"Serving {ROOT} at http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print()
