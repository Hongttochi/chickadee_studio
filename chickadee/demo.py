from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlsplit


class _Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parts = urlsplit(self.path)
        routes = {"/": "index.html", "/empty": "empty.html", "/frame/outer": "frame.html", "/frame/inner": "inner.html"}
        if parts.path == "/board":
            name = "board2.html" if parse_qs(parts.query).get("id") == ["2"] else "board1.html"
        else:
            name = routes.get(parts.path)
        if not name:
            self.send_error(404)
            return
        self.path = "/" + name
        super().do_GET()

    def log_message(self, *_):
        pass


class DemoSite:
    def __init__(self):
        handler = partial(_Handler, directory=str(Path(__file__).with_name("demo_site")))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.url = f"http://127.0.0.1:{self.server.server_port}/"

    def start(self):
        self.thread.start()
        return self

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def __enter__(self):
        return self.start()

    def __exit__(self, *_):
        self.close()
