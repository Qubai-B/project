"""Web interface for the guard: load a screenshot, see what the model would be shown.

Local use (default):   python demo/live_app.py [--port 8765] [--open]     then open http://127.0.0.1:8765
    Bound to 127.0.0.1 and answers this computer only.

Hosted use:            GUARD_HOSTED=1 GUARD_ACCESS_CODE=<code> PORT=7860 python demo/live_app.py
    Bound to 0.0.0.0 so that a hosting service can route a public link to it. An access code is
    compulsory in this mode; every request for a sample or a redaction must carry it.
    GUARD_UPLOADS=off limits the page to the three benchmark samples; GUARD_MAX_MB sets the largest
    upload accepted (default 15).

In both modes a screenshot is held in memory only and is never written to disk. Standard library
only for the web part. The page calls the same guard functions as scripts/04_run_guard.py
(ocr -> detect -> policy -> mask).
"""
from __future__ import annotations
import argparse, base64, hashlib, hmac, io, json, os, shutil, socket, sys, threading, time, webbrowser
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
MAX_MB = max(1, int(os.environ.get("GUARD_MAX_MB", "15")))   # some hosts cap a request body (Vercel: 4.5 MB)
MAX_BYTES = MAX_MB * 1024 * 1024
MAX_PIXELS = 40_000_000
SAMPLE_IDENTITY = "I0001"

HOSTED = os.environ.get("GUARD_HOSTED") == "1"
ACCESS_CODE = os.environ.get("GUARD_ACCESS_CODE", "")
UPLOADS = os.environ.get("GUARD_UPLOADS", "on").lower() != "off"
MAX_FAILED_CODES = 10            # wrong codes allowed per client in FAILED_WINDOW seconds
FAILED_WINDOW = 600

LOCK = threading.Lock()                    # one screenshot at a time: OCR already uses every core
WAITING = threading.BoundedSemaphore(4)    # at most four requests queued for the guard
READY = threading.Event()                  # set once the language model has been loaded
_recent: dict[str, tuple] = {}             # sha256 of the upload -> (image, detections, timings); memory only
_failed: dict[str, list[float]] = {}       # client -> times of recent wrong access codes
_failed_lock = threading.Lock()


def _sample_path(form_id: str) -> Path:
    return BENCHMARK / form_id / SAMPLE_IDENTITY / "filled" / "screenshot.png"


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
    return {"fields": fields, "tasks": tasks, "samples": samples,
            "hosted": HOSTED, "needs_code": bool(ACCESS_CODE), "uploads": UPLOADS, "max_mb": MAX_MB}


def _sample_hashes() -> set[str]:
    return {hashlib.sha256(_sample_path(s["form_id"]).read_bytes()).hexdigest() for s in _config()["samples"]}


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
    server_version = "GuardDemo/1.1"

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy",
                         "default-src 'none'; img-src 'self' data: blob:; style-src 'unsafe-inline'; "
                         "script-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj: dict) -> None:
        self._send(code, json.dumps(obj).encode("utf-8"), "application/json; charset=utf-8")

    def _local(self) -> bool:
        """Local mode only: refuse requests that reach this port under another host name (DNS rebinding)."""
        if HOSTED:
            return True
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
        if host in ("127.0.0.1", "localhost"):
            return True
        self._json(403, {"error": "This page only answers on 127.0.0.1."})
        return False

    def _client(self) -> str:
        forwarded = (self.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
        return forwarded or self.client_address[0]

    def _authorised(self) -> bool:
        """True if no access code is set, or the request carries the right one. Replies 401/429 itself."""
        if not ACCESS_CODE:
            return True
        who, now = self._client(), time.time()
        with _failed_lock:
            recent = [t for t in _failed.get(who, []) if now - t < FAILED_WINDOW]
            _failed[who] = recent
            locked_out = len(recent) >= MAX_FAILED_CODES
        if locked_out:
            self._json(429, {"error": "Too many wrong access codes. Try again in ten minutes."})
            return False
        given = self.headers.get("X-Access-Code") or ""
        if hmac.compare_digest(given.encode("utf-8"), ACCESS_CODE.encode("utf-8")):
            return True
        if given:
            with _failed_lock:
                _failed.setdefault(who, []).append(now)
            time.sleep(1)                      # slow down guessing
        self._json(401, {"error": "An access code is needed." if not given else "That access code is not right."})
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
        elif path == "/api/check":
            if self._authorised():
                self._json(200, {"ok": True})
        elif path.startswith("/sample/"):
            if not self._authorised():
                return
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
            return self._json(403, {"error": "Request not sent by the page."})
        if not self._authorised():
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if not 0 < length <= MAX_BYTES:
            return self._json(413, {"error": f"Send one image of at most {MAX_MB} MB."})
        data = self.rfile.read(length)
        if not UPLOADS and hashlib.sha256(data).hexdigest() not in _sample_hashes():
            return self._json(403, {"error": "Uploads are switched off here. Use one of the sample forms."})
        q = parse_qs(url.query)
        mode = q.get("mode", ["full"])[0]
        if mode not in ("full", "task_aware"):
            return self._json(400, {"error": "Unknown policy."})
        keep = {f for f in q.get("keep", [""])[0].split(",") if f in FIELD_PII_TYPE}
        if not WAITING.acquire(blocking=False):
            return self._json(503, {"error": "The server is busy. Try again in a moment."})
        try:
            self._json(200, run_guard(data, mode, keep))
        except (UnidentifiedImageError, ValueError, OSError) as e:
            msg = str(e) if isinstance(e, ValueError) else "That file could not be read as an image."
            self._json(400, {"error": msg})
        except Exception as e:  # show the reason on the page instead of a dropped connection
            self._json(500, {"error": f"The guard failed: {type(e).__name__}: {e}"})
        finally:
            WAITING.release()

    def log_message(self, fmt: str, *args) -> None:  # request lines only, never image content or the access code
        print(f"{self.log_date_time_string()}  {fmt % args}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8765")))
    ap.add_argument("--host", default=os.environ.get("GUARD_HOST", "0.0.0.0" if HOSTED else "127.0.0.1"))
    ap.add_argument("--open", action="store_true", help="open the page in the default browser (local use)")
    args = ap.parse_args()
    if HOSTED and not ACCESS_CODE:
        sys.exit("Hosted mode needs an access code: set the GUARD_ACCESS_CODE environment variable.")
    url = f"http://127.0.0.1:{args.port}"
    try:  # started twice (double-clicked again): show the page that is already up instead of a second server
        socket.create_connection(("127.0.0.1", args.port), timeout=1).close()
        print(f"The guard interface is already running on {url}")
        if args.open:
            webbrowser.open(url)
        sys.exit(0)
    except OSError:
        pass
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    where = "hosted mode, all interfaces" if HOSTED else "this computer only"
    print(f"Guard interface on {args.host}:{args.port}  ({where}; access code {'on' if ACCESS_CODE else 'off'}; "
          f"uploads {'on' if UPLOADS else 'off'}; Ctrl+C to stop)")
    print("loading the language model ...")
    threading.Thread(target=_warm_up, daemon=True).start()
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("stopped")
