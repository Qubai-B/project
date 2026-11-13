"""Local demo page for the guard: upload a screenshot, see what the model would be shown.

usage: python demo/live_app.py [--port 8765] [--open]      then open http://127.0.0.1:8765

Runs on this computer only (bound to 127.0.0.1). Uploaded images are held in memory, are never
written to disk and are never sent anywhere. Standard library only, so it needs no extra packages.
The page calls the same guard functions as scripts/04_run_guard.py (ocr -> detect -> policy -> mask).
"""
from __future__ import annotations
import argparse, base64, hashlib, io, json, os, shutil, socket, sys, threading, time, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _find_tesseract() -> None:
    """Same lookup as env.ps1, so the page starts without dot-sourcing it first."""
    if shutil.which("tesseract"):
        return
    local = os.environ.get("LOCALAPPDATA", "")
    for d in (Path(r"C:\Program Files\Tesseract-OCR"), Path(local) / "micromamba/envs/tesseract/Library/bin"):
        if (d / "tesseract.exe").exists():
            os.environ["PATH"] = f"{d}{os.pathsep}{os.environ.get('PATH', '')}"
            tessdata = d.parent.parent / "share" / "tessdata"
            if tessdata.exists() and not os.environ.get("TESSDATA_PREFIX"):
                os.environ["TESSDATA_PREFIX"] = str(tessdata)
            return
    sys.exit("Tesseract was not found. Install it or run '. .\\env.ps1' first.")


_find_tesseract()

from PIL import Image, UnidentifiedImageError  # noqa: E402
from common.forms import FIELD_PII_TYPE  # noqa: E402
from common.paths import BENCHMARK, FORMS  # noqa: E402
from guard.detect import detect  # noqa: E402
from guard.mask import paint  # noqa: E402
from guard.ocr import ocr_runs  # noqa: E402
from guard.policy import select  # noqa: E402

PAGE = Path(__file__).with_name("live_page.html")
MAX_BYTES = 15 * 1024 * 1024
MAX_PIXELS = 40_000_000
SAMPLE_IDENTITY = "I0001"

LOCK = threading.Lock()          # one screenshot at a time: OCR already uses every core
READY = threading.Event()        # set once the language model has been loaded
_recent: dict[str, tuple] = {}   # sha256 of the upload -> (image, detections, timings); memory only


def _config() -> dict:
    tasks, samples = [], []
    for manifest_path in sorted(FORMS.glob("*/form.json")):
        m = json.loads(manifest_path.read_text(encoding="utf-8"))
        for task_id, t in m.get("tasks", {}).items():
            tasks.append({"id": task_id, "form": m["title"], "goal": t["goal"], "needs": t["needs"]})
        if _sample_path(m["form_id"]).exists():
            samples.append({"form_id": m["form_id"], "title": m["title"]})
    tasks.sort(key=lambda t: t["id"])
    fields = [{"name": name, "pii_type": pii} for name, pii in FIELD_PII_TYPE.items()]
    return {"fields": fields, "tasks": tasks, "samples": samples}


def _sample_path(form_id: str) -> Path:
    return BENCHMARK / form_id / SAMPLE_IDENTITY / "filled" / "screenshot.png"


def run_guard(data: bytes, mode: str, keep: set[str]) -> dict:
    key = hashlib.sha256(data).hexdigest()
    with LOCK:
        hit = _recent.get(key)
        reused = hit is not None
        if hit is None:
            image = Image.open(io.BytesIO(data))
            if image.width * image.height > MAX_PIXELS:
                raise ValueError("The image is too large.")
            image = image.convert("RGB")
            t0 = time.perf_counter()
            runs = ocr_runs(image)
            t1 = time.perf_counter()
            dets = detect(runs, "hybrid")
            t2 = time.perf_counter()
            hit = (image, dets, {"ocr_ms": (t1 - t0) * 1e3, "detect_ms": (t2 - t1) * 1e3})
            _recent[key] = hit
            while len(_recent) > 3:
                _recent.pop(next(iter(_recent)))
        image, dets, timings = hit
        t3 = time.perf_counter()
        masked = select(dets, mode, keep)
        out = paint(image, masked)
        mask_ms = (time.perf_counter() - t3) * 1e3
    buf = io.BytesIO()
    out.save(buf, "PNG")
    masked_ids = {id(m) for m in masked}
    return {
        "image": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii"),
        "width": image.width, "height": image.height,
        "detections": [{"text": d["text"], "pii_type": d["pii_type"], "field": d.get("field"),
                        "masked": id(d) in masked_ids} for d in dets],
        "timings": {**timings, "mask_ms": mask_ms},
        "reused": reused,
    }


def _warm_up() -> None:
    """Load the language model before the first upload, so the first result is not the slow one."""
    try:
        sample = next((p for p in sorted(BENCHMARK.glob("*/*/filled/screenshot.png"))), None)
        if sample is not None:
            with LOCK:
                detect(ocr_runs(Image.open(sample).convert("RGB")), "hybrid")
    except Exception as e:  # the page still works; the first upload is just slower
        print(f"warm-up skipped: {e}")
    READY.set()
    print("ready")


class Handler(BaseHTTPRequestHandler):
    server_version = "GuardDemo/1.0"

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj: dict) -> None:
        self._send(code, json.dumps(obj).encode("utf-8"), "application/json; charset=utf-8")

    def _local(self) -> bool:
        """Refuse requests that reach this port under another host name (DNS rebinding)."""
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
        if host in ("127.0.0.1", "localhost"):
            return True
        self._json(403, {"error": "This page only answers on 127.0.0.1."})
        return False

    def do_GET(self) -> None:
        if not self._local():
            return
        path = urlparse(self.path).path
        if path == "/":
            cfg = json.dumps(_config()).replace("</", "<\\/")
            html = PAGE.read_text(encoding="utf-8").replace("__CONFIG__", cfg)
            self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
        elif path == "/api/status":
            self._json(200, {"ready": READY.is_set()})
        elif path.startswith("/sample/"):
            form_id = path.rsplit("/", 1)[1]
            known = {s["form_id"] for s in _config()["samples"]}
            if form_id in known:
                self._send(200, _sample_path(form_id).read_bytes(), "image/png")
            else:
                self._json(404, {"error": "No such sample."})
        else:
            self._json(404, {"error": "Not found."})

    def do_POST(self) -> None:
        if not self._local():
            return
        url = urlparse(self.path)
        if url.path != "/api/redact":
            return self._json(404, {"error": "Not found."})
        if self.headers.get("X-Guard") != "1":          # only this page's own script sends it
            return self._json(403, {"error": "Request not sent by the demo page."})
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if not 0 < length <= MAX_BYTES:
            return self._json(413, {"error": "Send one image of at most 15 MB."})
        data = self.rfile.read(length)
        q = parse_qs(url.query)
        mode = q.get("mode", ["full"])[0]
        if mode not in ("full", "task_aware"):
            return self._json(400, {"error": "Unknown policy."})
        keep = {f for f in q.get("keep", [""])[0].split(",") if f in FIELD_PII_TYPE}
        try:
            self._json(200, run_guard(data, mode, keep))
        except (UnidentifiedImageError, ValueError, OSError) as e:
            msg = str(e) if isinstance(e, ValueError) else "That file could not be read as an image."
            self._json(400, {"error": msg})
        except Exception as e:  # show the reason on the page instead of a dropped connection
            self._json(500, {"error": f"The guard failed: {type(e).__name__}: {e}"})

    def log_message(self, fmt: str, *args) -> None:  # request lines only, never image content
        print(f"{self.log_date_time_string()}  {fmt % args}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--open", action="store_true", help="open the page in the default browser")
    args = ap.parse_args()
    url = f"http://127.0.0.1:{args.port}"
    try:  # started twice (double-clicked again): show the page that is already up instead of a second server
        socket.create_connection(("127.0.0.1", args.port), timeout=1).close()
        print(f"The guard demo is already running on {url}")
        if args.open:
            webbrowser.open(url)
        sys.exit(0)
    except OSError:
        pass
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Guard demo on {url}  (this computer only; Ctrl+C to stop)")
    print("loading the language model ...")
    threading.Thread(target=_warm_up, daemon=True).start()
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("stopped")
