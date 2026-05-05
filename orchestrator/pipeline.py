"""Async orchestrator for Claw Bot.

Receives validated payloads from n8n on localhost:8765, persists them to a
disk spool, queues for async execution by a worker thread, and exposes
status queries.

Strict JSON Schema validation runs here — n8n's pre-flight only catches
obvious garbage; this module is the real gate.
"""

import json
import logging
import queue
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Project root on sys.path so sibling packages (rpa, rhino_worker) import
# regardless of how this script is invoked.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "n8n" / "schemas" / "design_selection.schema.json"
SPOOL_DIR = ROOT / "khep_outputs" / "jobs"
LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 8765

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("orchestrator")

with SCHEMA_PATH.open() as f:
    _SCHEMA = json.load(f)
_VALIDATOR = Draft202012Validator(_SCHEMA)

_job_queue: "queue.Queue[dict]" = queue.Queue()
_job_state: dict = {}
_state_lock = threading.Lock()

for sub in ("queued", "running", "done", "failed"):
    (SPOOL_DIR / sub).mkdir(parents=True, exist_ok=True)


def _set_state(job_id: str, status: str, **extra) -> None:
    with _state_lock:
        _job_state[job_id] = {"status": status, **extra}


def _get_state(job_id: str):
    with _state_lock:
        return _job_state.get(job_id)


def _spool_move(job_id: str, src: str, dst: str) -> None:
    src_path = SPOOL_DIR / src / f"{job_id}.json"
    if src_path.exists():
        src_path.rename(SPOOL_DIR / dst / f"{job_id}.json")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quiet default access logging
        log.info("http %s", fmt % args)

    def _send_json(self, code: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            return self._send_json(200, {"status": "ok"})
        if self.path.startswith("/jobs/"):
            job_id = self.path[len("/jobs/"):]
            state = _get_state(job_id)
            if state is None:
                return self._send_json(404, {"error": "job_id not found"})
            return self._send_json(200, {"job_id": job_id, **state})
        return self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/jobs":
            return self._send_json(404, {"error": "not found"})

        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length).decode())
        except json.JSONDecodeError as e:
            return self._send_json(400, {"error": f"invalid JSON: {e}"})

        errors = list(_VALIDATOR.iter_errors(payload))
        if errors:
            return self._send_json(400, {
                "error": "schema validation failed",
                "details": [
                    {"path": list(e.absolute_path), "message": e.message}
                    for e in errors
                ],
            })

        job_id = payload["job_id"]

        # Idempotency: same job_id arriving again returns the existing state
        existing = _get_state(job_id)
        if existing is not None:
            return self._send_json(200, {
                "job_id": job_id, **existing, "duplicate": True,
            })

        spool_path = SPOOL_DIR / "queued" / f"{job_id}.json"
        with spool_path.open("w") as f:
            json.dump(payload, f, indent=2)

        _set_state(job_id, "queued")
        _job_queue.put(payload)
        log.info("job_queued job_id=%s", job_id)
        self._send_json(200, {"job_id": job_id, "status": "queued"})


def _worker():
    while True:
        payload = _job_queue.get()
        job_id = payload["job_id"]
        _set_state(job_id, "running")
        _spool_move(job_id, "queued", "running")
        log.info("job_started job_id=%s", job_id)

        try:
            # Imports inside the try so any ImportError (missing rpa deps,
            # pyautogui without X11, etc.) marks the job failed with a clear
            # message instead of killing the worker thread.
            from rpa.sequences import build_mala
            from rhino_worker import geometry

            mesh_guid = build_mala.build_mala(payload)
            if mesh_guid is None:
                raise RuntimeError("build_mala did not return a mesh_guid")

            result = geometry.process_production_mesh(
                mesh_guid, payload["karat_target"]
            )
            if result["status"] != "SUCCESS":
                raise RuntimeError(
                    f"geometry validation failed: {result.get('reason')}"
                )

            constraints = payload["constraints"]
            if "max_mass_g" in constraints and result["mass_g"] > constraints["max_mass_g"]:
                raise RuntimeError(
                    f"mass {result['mass_g']}g exceeds max {constraints['max_mass_g']}g"
                )

            _set_state(job_id, "done", result=result)
            _spool_move(job_id, "running", "done")
            log.info(
                "job_done job_id=%s mass_g=%s volume_cm3=%s",
                job_id, result["mass_g"], result["volume_cm3"],
            )

        except Exception as e:
            _set_state(job_id, "failed", error=str(e))
            _spool_move(job_id, "running", "failed")
            log.exception("job_failed job_id=%s", job_id)

        finally:
            _job_queue.task_done()


def _recover_queued():
    """Re-queue any jobs left in queued/ from a prior run."""
    for path in (SPOOL_DIR / "queued").glob("*.json"):
        try:
            with path.open() as f:
                payload = json.load(f)
            _set_state(payload["job_id"], "queued")
            _job_queue.put(payload)
            log.info("recovered_queued job_id=%s", payload["job_id"])
        except Exception:
            log.exception("recover_failed path=%s", path)


def main():
    _recover_queued()
    threading.Thread(target=_worker, name="worker", daemon=False).start()
    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), Handler)
    log.info("orchestrator_listening host=%s port=%s", LISTEN_HOST, LISTEN_PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("shutting_down")
        server.shutdown()


if __name__ == "__main__":
    main()
