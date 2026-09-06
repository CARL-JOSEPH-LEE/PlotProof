import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from plotproof.providers import Client, Settings
from plotproof.server import make_server


@pytest.fixture
def server(tmp_path):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<!doctype html><title>PlotProof</title>", encoding="utf-8")
    s = make_server(0, tmp_path / "data", static)
    thread = threading.Thread(target=s.serve_forever, daemon=True)
    thread.start()
    yield s
    s.shutdown()
    s.server_close()
    s.app.close()
    thread.join(timeout=3)


def call(server, path, body=None, method=None, token=True):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-PlotProof-Token"] = server.app.token
    request = Request(
        f"http://127.0.0.1:{server.server_port}{path}",
        headers=headers,
        data=json.dumps(body).encode() if body is not None else None,
        method=method or ("POST" if body is not None else "GET"),
    )
    with urlopen(request, timeout=10) as response:
        data = response.read()
        return json.loads(data) if "application/json" in response.headers["Content-Type"] else data.decode()


def test_full_workbench_flow_survives_reload_and_rechecks(server):
    assert "PlotProof" in call(server, "/")
    assert call(server, "/api/health", token=False)["product"] == "PlotProof"
    doc = call(server, "/api/examples", {"language": "en"})
    assert len(doc["report"]["findings"]) == 4
    finding = doc["report"]["findings"][0]
    reviewed = call(
        server,
        f"/api/projects/{doc['id']}/review",
        {"finding_id": finding["id"], "status": "confirmed", "note": "Fix the date.", "revision": 1},
    )
    assert reviewed["report"]["findings"][0]["note"] == "Fix the date."
    html = call(server, f"/api/projects/{doc['id']}/report.html")
    assert "Fix the date." in html
    assert call(server, f"/api/projects/{doc['id']}")["report"]["findings"][0]["status"] == "confirmed"
    changed = call(
        server,
        f"/api/projects/{doc['id']}",
        {"text": doc["text"].replace("1997", "1994"), "revision": 1},
        "PUT",
    )
    assert changed["revision"] == 2
    with pytest.raises(HTTPError) as exc:
        call(server, f"/api/projects/{doc['id']}/report.html")
    assert exc.value.code == 409
    job = call(server, f"/api/projects/{doc['id']}/analyze", {})
    deadline = time.monotonic() + 3
    while job["status"] == "running" and time.monotonic() < deadline:
        time.sleep(0.02)
        job = call(server, f"/api/jobs/{job['id']}")
    assert job["status"] == "done"
    final = call(server, f"/api/projects/{doc['id']}")
    assert len(final["report"]["findings"]) == 3
    assert final["report"]["revision"] == 2


def test_settings_do_not_persist_or_return_credentials(server):
    result = call(
        server,
        "/api/settings",
        {
            "provider": "compatible",
            "base_url": "https://example.test/v1",
            "model": "test",
            "api_key": "fixture-only-key",
            "language": "en",
        },
    )
    assert result["has_key"] and "fixture-only-key" not in json.dumps(result)
    assert not list(server.app.store.root.rglob("*key*"))
    # Switching endpoint must not forward the previous provider's credential.
    result = call(
        server,
        "/api/settings",
        {"provider": "compatible", "base_url": "https://second.test/v1", "model": "test", "language": "en"},
    )
    assert not result["has_key"]


def test_failed_job_is_reported_and_does_not_replace_previous_report(server):
    doc = call(server, "/api/examples", {"language": "en"})
    original = doc["report"]
    # A closed local endpoint gives a bounded, real transport failure.
    call(
        server,
        "/api/settings",
        {"provider": "ollama", "base_url": "http://127.0.0.1:1", "model": "missing", "language": "en"},
    )
    job = call(server, f"/api/projects/{doc['id']}/analyze", {})
    deadline = time.monotonic() + 8
    while job["status"] == "running" and time.monotonic() < deadline:
        time.sleep(0.05)
        job = call(server, f"/api/jobs/{job['id']}")
    assert job["status"] == "error"
    assert call(server, f"/api/projects/{doc['id']}")["report"] == original


@pytest.mark.parametrize("provider", ["ollama", "compatible"])
def test_real_http_adapters_with_fixture_model_server(provider):
    seen = []

    class ModelHandler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append((self.path, body))
            content = json.dumps({"facts": []})
            result = (
                {"message": {"content": content}, "done": True, "prompt_eval_count": 10, "eval_count": 4}
                if provider == "ollama"
                else {
                    "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 4},
                }
            )
            raw = json.dumps(result).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    s = ThreadingHTTPServer(("127.0.0.1", 0), ModelHandler)
    thread = threading.Thread(target=s.serve_forever, daemon=True)
    thread.start()
    try:
        client = Client(Settings(provider, f"http://127.0.0.1:{s.server_port}", "fixture-model"))
        assert client.complete("Return JSON", {"text": "fixture"}, {"type": "object"}) == {"facts": []}
        assert client.requests == 1 and client.input_tokens == 10 and client.output_tokens == 4
        assert seen[0][0] == ("/api/chat" if provider == "ollama" else "/chat/completions")
        assert seen[0][1]["stream"] is False
        assert "format" in seen[0][1] if provider == "ollama" else "response_format" in seen[0][1]
    finally:
        s.shutdown()
        s.server_close()
        thread.join(timeout=3)
