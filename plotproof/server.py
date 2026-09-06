"""Local workbench API. No accounts, activation, telemetry, or cloud storage."""

import json
import mimetypes
import secrets
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from . import __version__
from .document import digest
from .engine import Cancelled, analyze
from .export import html_report, json_report
from .providers import ProviderError, Settings
from .storage import Conflict, Store


class Workbench:
    def __init__(self, data_dir: Path, static_dir: Path):
        self.store = Store(data_dir)
        self.static_dir = static_dir.resolve()
        self.settings = Settings()
        self.token = secrets.token_urlsafe(24)
        self.jobs = {}
        self.lock = threading.RLock()
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="plotproof")
        self.active = None

    def start(self, ident):
        with self.lock:
            if self.active:
                raise Conflict("已有检查正在进行，请等待或取消 / An analysis is already running.")
            doc = self.store.read(ident)
            settings = Settings(**vars(self.settings)).validate()
            job_id = uuid.uuid4().hex
            event = threading.Event()
            self.jobs[job_id] = {
                "id": job_id,
                "project_id": ident,
                "revision": doc["revision"],
                "status": "running",
                "progress": {"stage": "extract", "current": 0, "total": 1},
                "cancel": event,
            }
            self.active = job_id
            # Retain a bounded number of completed progress records.
            for old in list(self.jobs)[:-30]:
                if self.jobs[old]["status"] != "running":
                    del self.jobs[old]
            self.pool.submit(self.run, job_id, doc, settings, event)
            return self.job(job_id)

    def job(self, ident):
        with self.lock:
            if ident not in self.jobs:
                raise FileNotFoundError()
            return {k: v for k, v in self.jobs[ident].items() if k != "cancel"}

    def run(self, ident, doc, settings, event):
        def progress(value):
            with self.lock:
                self.jobs[ident]["progress"] = value

        try:
            report = analyze(
                doc["text"], settings, progress=progress, cancel=event, cache_dir=self.store.root / "cache"
            )
            with self.lock:
                if event.is_set():
                    raise Cancelled()
                self.store.save_report(doc["id"], report, doc["revision"])
                self.jobs[ident]["status"] = "done"
        except Cancelled:
            with self.lock:
                self.jobs[ident]["status"] = "cancelled"
        except (ProviderError, ValueError, OSError) as exc:
            with self.lock:
                self.jobs[ident].update(
                    status="error",
                    error=str(exc)
                    if isinstance(exc, (ValueError, ProviderError))
                    else "无法保存本地文件 / Could not save local files.",
                )
        except Exception:
            with self.lock:
                self.jobs[ident].update(status="error", error="检查发生内部错误 / Internal analysis error.")
        finally:
            with self.lock:
                self.active = None

    def close(self):
        with self.lock:
            for job in self.jobs.values():
                job["cancel"].set()
        self.pool.shutdown(wait=True, cancel_futures=True)


def make_server(port: int, data_dir: Path, static_dir: Path):
    app = Workbench(data_dir, static_dir)

    class Handler(BaseHTTPRequestHandler):
        server_version = "PlotProof/" + __version__

        def log_message(self, *_):
            pass

        def reply(self, value, status=200, mime="application/json", download=None):
            body = (
                json.dumps(value, ensure_ascii=False).encode("utf-8")
                if mime == "application/json"
                else (value.encode("utf-8") if isinstance(value, str) else value)
            )
            self.send_response(status)
            self.send_header(
                "Content-Type",
                mime + ("; charset=utf-8" if mime.startswith("text/") or mime == "application/json" else ""),
            )
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            if download:
                self.send_header("Content-Disposition", f'attachment; filename="{download}"')
            self.end_headers()
            self.wfile.write(body)

        def handle_request(self, method):
            try:
                host = self.headers.get("Host", "")
                allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
                if host not in allowed:
                    return self.reply({"error": "Use the local PlotProof address."}, 403)
                origin = self.headers.get("Origin")
                if origin and origin not in {"http://" + value for value in allowed}:
                    return self.reply({"error": "Cross-origin requests are not supported."}, 403)
                path = urlsplit(self.path).path
                if path == "/api/health" and method == "GET":
                    return self.reply({"ok": True, "product": "PlotProof", "version": __version__})
                if path == "/api/session" and method == "GET":
                    return self.reply({"token": app.token, "version": __version__})
                if path.startswith("/api/"):
                    if self.headers.get("X-PlotProof-Token", "") != app.token:
                        return self.reply({"error": "请刷新页面 / Refresh the page."}, 403)
                    body = {}
                    if method in {"POST", "PUT", "PATCH"}:
                        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                            return self.reply({"error": "Expected application/json."}, 415)
                        size = int(self.headers.get("Content-Length", "0"))
                        if size < 0 or size > 2_000_000:
                            return self.reply({"error": "Request too large."}, 413)
                        self.connection.settimeout(15)
                        body = json.loads(self.rfile.read(size))
                        if not isinstance(body, dict):
                            raise ValueError("Expected a JSON object.")
                    return self.api(path, method, body)
                if method != "GET":
                    return self.reply({"error": "Not found."}, 404)
                if not app.static_dir.exists():
                    return self.reply(
                        "PlotProof JSON API is ready. Launch the native desktop with: python -m plotproof",
                        200,
                        "text/plain",
                    )
                target = (app.static_dir / path.lstrip("/")).resolve()
                if not target.is_relative_to(app.static_dir):
                    return self.reply({"error": "Not found."}, 404)
                if target.is_dir():
                    target = target / "index.html"
                if not target.is_file():
                    return self.reply({"error": "Not found."}, 404)
                # Windows file associations must not decide executable web asset types.
                types = {
                    ".js": "text/javascript",
                    ".mjs": "text/javascript",
                    ".css": "text/css",
                    ".svg": "image/svg+xml",
                    ".html": "text/html",
                }
                return self.reply(
                    target.read_bytes(),
                    mime=types.get(target.suffix.lower())
                    or mimetypes.guess_type(str(target))[0]
                    or "application/octet-stream",
                )
            except Conflict as exc:
                self.reply({"error": str(exc)}, 409)
            except FileNotFoundError:
                self.reply({"error": "文件或项目不存在 / Not found."}, 404)
            except (ValueError, TypeError, KeyError, UnicodeError) as exc:
                self.reply({"error": str(exc) if isinstance(exc, ValueError) else "Invalid request."}, 400)
            except OSError:
                self.reply({"error": "本地文件操作失败 / Local file operation failed."}, 500)

        def api(self, path, method, body):
            parts = path.strip("/").split("/")
            if path == "/api/shutdown" and method == "POST":
                with app.lock:
                    if app.active:
                        raise Conflict("请先取消正在进行的检查 / Cancel the active analysis first.")
                self.reply({"ok": True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            if path == "/api/settings":
                if method == "POST":
                    with app.lock:
                        same_endpoint = (
                            body.get("base_url", "") == app.settings.base_url
                            and body.get("provider") == app.settings.provider
                        )
                        key = body.get("api_key", app.settings.api_key if same_endpoint else "")
                        app.settings = Settings(
                            provider=body.get("provider", "rules"),
                            base_url=body.get("base_url", ""),
                            model=body.get("model", ""),
                            api_key=key,
                            language=body.get("language", "zh"),
                        ).validate()
                elif method != "GET":
                    return self.reply({"error": "Method not allowed."}, 405)
                s = app.settings
                return self.reply(
                    {**s.public(), "base_url": s.base_url, "model": s.model, "has_key": bool(s.api_key)}
                )
            if path == "/api/projects":
                if method == "GET":
                    return self.reply(app.store.list())
                if method == "POST":
                    return self.reply(app.store.create(body.get("title", ""), body.get("text", "")), 201)
            if path == "/api/examples" and method == "POST":
                lang = body.get("language", "zh")
                if lang not in {"zh", "en"}:
                    raise ValueError("Unsupported example.")
                content = (Path(__file__).parent / "examples" / f"{lang}.txt").read_text(encoding="utf-8")
                doc = app.store.create(
                    "雾港来信 · 示例" if lang == "zh" else "Letters from the Harbor · Example", content
                )
                return self.reply(
                    app.store.save_report(
                        doc["id"], analyze(content, Settings(language=lang)), doc["revision"]
                    ),
                    201,
                )
            if path == "/api/active-job" and method == "GET":
                with app.lock:
                    return self.reply(app.job(app.active) if app.active else None)
            if len(parts) >= 3 and parts[1] == "jobs":
                ident = parts[2]
                if len(parts) == 3 and method == "GET":
                    return self.reply(app.job(ident))
                if len(parts) == 4 and parts[3] == "cancel" and method == "POST":
                    with app.lock:
                        app.job(ident)
                        app.jobs[ident]["cancel"].set()
                    return self.reply(app.job(ident))
            if len(parts) >= 3 and parts[1] == "projects":
                ident = parts[2]
                if len(parts) == 3:
                    if method == "GET":
                        return self.reply(app.store.read(ident))
                    if method == "PUT":
                        return self.reply(app.store.update(ident, body.get("text", ""), body.get("revision")))
                if len(parts) == 4:
                    action = parts[3]
                    if action == "analyze" and method == "POST":
                        return self.reply(app.start(ident), 202)
                    if action == "review" and method == "POST":
                        return self.reply(
                            app.store.review(
                                ident,
                                body.get("finding_id"),
                                body.get("status"),
                                body.get("note", ""),
                                body.get("revision"),
                            )
                        )
                    if action in {"report.html", "report.json"} and method == "GET":
                        doc = app.store.read(ident)
                        if not doc["report"] or doc["report"]["source_hash"] != digest(doc["text"]):
                            raise Conflict(
                                "请先检查当前稿件 / Analyze the current manuscript before exporting."
                            )
                        if action.endswith("html"):
                            return self.reply(
                                html_report(doc), mime="text/html", download="plotproof-report.html"
                            )
                        return self.reply(
                            json_report(doc), mime="text/plain", download="plotproof-report.json"
                        )
            return self.reply({"error": "Not found."}, 404)

        def do_GET(self):
            self.handle_request("GET")

        def do_POST(self):
            self.handle_request("POST")

        def do_PUT(self):
            self.handle_request("PUT")

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.app = app
    return server
