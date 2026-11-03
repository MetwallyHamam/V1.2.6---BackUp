from http.client import HTTPConnection
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

root = Path(__file__).resolve().parent / "1.16.1" / "frontend"

class SpaHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(root), **kwargs)

    def _proxy(self):
        connection = HTTPConnection("127.0.0.1", 8000, timeout=30)
        path = self.path.replace("/SupportHub/backend", "", 1)
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else None
        headers = {key: value for key, value in self.headers.items() if key.lower() not in {"host", "connection"}}
        connection.request(self.command, path, body=body, headers=headers)
        response = connection.getresponse()
        self.send_response(response.status)
        for key, value in response.getheaders():
            if key.lower() not in {"connection", "transfer-encoding"}:
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(response.read())

    def _serve_spa(self):
        if self.path.startswith("/SupportHub/backend/"):
            return self._proxy()
        if self.path == "/":
            self.send_response(302); self.send_header("Location", "/SupportHub/login"); self.end_headers(); return
        relative = self.path.split("?", 1)[0].removeprefix("/SupportHub/")
        requested = root / relative
        self.path = f"/{relative}" if requested.exists() else "/index.html"
        super().do_GET()

    do_GET = _serve_spa
    do_POST = _proxy
    do_PUT = _proxy
    do_PATCH = _proxy
    do_DELETE = _proxy

ThreadingHTTPServer(("127.0.0.1", 5173), SpaHandler).serve_forever()
