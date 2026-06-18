"""
FastAPI web app — supply-chain risk console.

- Single shared password gate (env APP_PASSWORD, default "agenticai").
- A data source is loaded into a shared in-memory workspace (synthetic dataset,
  uploaded CSV/XLSX, or a simulated ERP), a simulated logistics-risk layer is
  attached, the crew runs a full risk analysis, and a persistent chat answers
  questions / focused re-analyses over the loaded data.
- Heavy runs are serialised with a lock; all routes are auth-gated + rate-limited.
"""

import asyncio
import os
import time
from pathlib import Path

from fastapi import FastAPI, Form, Request, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.concurrency import run_in_threadpool
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from . import workspace as ws
from .crew import analyze_workspace, run_chat, MAX_TOPIC_CHARS
from .sources import synthetic_source, parse_upload, fetch_public_dataset
from .logistics import generate_logistics
from .forecast import run_forecast
from .erp import generate_erp_data, simulate_connection, SYSTEMS
from .security import client_ip, constant_time_eq, SlidingWindowLimiter, LoginGuard

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB

APP_PASSWORD = os.environ.get("APP_PASSWORD", "agenticai")
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-change-me")
COOKIE_NAME = "agenticai_session"
COOKIE_MAX_AGE = 60 * 60 * 12  # 12 hours

signer = URLSafeTimedSerializer(SECRET_KEY)

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Agentic AI Lab — Supply Chain Crew")

# Only one crew runs at a time (queues concurrent users; bounds cost).
_crew_lock = asyncio.Lock()

# Brute-force protection: lock an IP for 10 min after 6 failed logins in 5 min.
_login_guard = LoginGuard(max_fails=6, window=300, lockout=600)
# Abuse/cost protection: at most 15 runs per 10 min per IP.
_run_limiter = SlidingWindowLimiter(limit=15, window=600)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    return resp


def _is_authed(request: Request) -> bool:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return False
    try:
        signer.loads(token, max_age=COOKIE_MAX_AGE)
        return True
    except (BadSignature, SignatureExpired):
        return False


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    page = "app.html" if _is_authed(request) else "login.html"
    return HTMLResponse((STATIC_DIR / page).read_text(encoding="utf-8"))


def _login_error(message: str, status: int):
    html = (STATIC_DIR / "login.html").read_text(encoding="utf-8")
    html = html.replace("<!--ERROR-->", message)
    return HTMLResponse(html, status_code=status)


@app.post("/login")
async def login(request: Request, password: str = Form(...)):
    ip = client_ip(request)
    now = time.time()

    locked = _login_guard.locked_for(ip, now)
    if locked:
        return _login_error(
            f"Too many attempts. Try again in {locked // 60 + 1} min.", 429)

    if not constant_time_eq(password, APP_PASSWORD):
        _login_guard.record_fail(ip, now)
        await asyncio.sleep(0.7)  # slow down brute force
        return _login_error("Wrong password. Please try again.", 401)

    _login_guard.reset(ip)
    resp = RedirectResponse(url="/", status_code=303)
    token = signer.dumps("ok")
    resp.set_cookie(
        COOKIE_NAME, token, max_age=COOKIE_MAX_AGE,
        httponly=True, samesite="lax",
    )
    return resp


@app.get("/logout")
async def logout():
    resp = RedirectResponse(url="/", status_code=303)
    resp.delete_cookie(COOKIE_NAME)
    return resp


def _require_auth(request: Request):
    if not _is_authed(request):
        raise HTTPException(status_code=401, detail="Not authenticated")


def _rate_limited(request: Request) -> bool:
    return not _run_limiter.check(client_ip(request), time.time())


def _public_workspace(w: dict) -> dict:
    """Trim the workspace to what the UI needs (no heavy LLM text / raw suppliers)."""
    log = w.get("logistics") or {}
    return {
        "loaded": w.get("loaded", False),
        "source": w.get("source"), "label": w.get("label"), "seed": w.get("seed"),
        "summary": w.get("summary", {}), "table": w.get("table", {}),
        "connection": w.get("connection"),
        "logistics": {"summary": log.get("summary", {}),
                      "shipments": log.get("shipments", [])} if log else None,
        "forecast": w.get("forecast"),
        "analysis_md": w.get("analysis_md"), "chat": w.get("chat", []),
    }


def _load_source(source: dict) -> dict:
    """Attach simulated logistics + ML risk model, store as the active workspace."""
    seed = source.get("seed")
    source["logistics"] = generate_logistics(seed=seed, suppliers=source.get("suppliers"))
    source["forecast"] = run_forecast(source.get("suppliers"), seed=seed)
    ws.set_workspace(source)
    return _public_workspace(ws.get_workspace())


@app.get("/workspace")
async def workspace_state(request: Request):
    _require_auth(request)
    return JSONResponse(_public_workspace(ws.get_workspace()))


@app.get("/sources/synthetic")
async def source_synthetic(request: Request, n: int = 12):
    _require_auth(request)
    return JSONResponse(_load_source(synthetic_source(n=n)))


@app.post("/sources/upload")
async def source_upload(request: Request, file: UploadFile = File(...)):
    _require_auth(request)
    if _rate_limited(request):
        return JSONResponse({"ok": False, "error": "Rate limit — wait a few minutes."}, status_code=429)
    name = (file.filename or "").lower()
    if not name.endswith((".csv", ".xlsx", ".xlsm")):
        return JSONResponse({"ok": False, "error": "Only .csv or .xlsx files are accepted."}, status_code=415)
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        return JSONResponse({"ok": False, "error": "File too large (max 5 MB)."}, status_code=413)
    try:
        source = await run_in_threadpool(parse_upload, file.filename, content)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": f"Could not parse file: {exc}"}, status_code=422)
    return JSONResponse({"ok": True, "workspace": _load_source(source)})


@app.get("/sources/url")
async def source_url(request: Request, key: str = "usaid"):
    _require_auth(request)
    if _rate_limited(request):
        return JSONResponse({"ok": False, "error": "Rate limit — wait a few minutes."}, status_code=429)
    try:
        source = await run_in_threadpool(fetch_public_dataset, key)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": f"Could not load dataset: {exc}"}, status_code=502)
    return JSONResponse({"ok": True, "workspace": _load_source(source)})


@app.get("/erp/connect")
async def erp_connect(request: Request, system: str = "sap"):
    _require_auth(request)
    if system not in SYSTEMS:
        raise HTTPException(status_code=400, detail="Unknown ERP system")
    return JSONResponse(simulate_connection(system))


@app.get("/erp/data")
async def erp_data(request: Request, system: str = "sap"):
    _require_auth(request)
    if system not in SYSTEMS:
        raise HTTPException(status_code=400, detail="Unknown ERP system")
    return JSONResponse(_load_source(generate_erp_data(system=system)))


@app.post("/analyze")
async def analyze(request: Request, focus: str = Form(""), deep: bool = Form(False)):
    _require_auth(request)
    if _rate_limited(request):
        return JSONResponse({"ok": False, "error": "Rate limit — wait a few minutes."}, status_code=429)
    if not ws.is_loaded():
        return JSONResponse({"ok": False, "error": "Load a data source first."}, status_code=400)
    if len(focus) > MAX_TOPIC_CHARS:
        return JSONResponse({"ok": False, "error": f"Focus too long (max {MAX_TOPIC_CHARS} chars)."}, status_code=413)
    async with _crew_lock:
        try:
            data = await run_in_threadpool(analyze_workspace, ws.get_workspace(), focus, deep)
        except Exception as exc:
            return JSONResponse({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, status_code=500)
    if not str(data.get("backend", "")).startswith("guard"):
        ws.set_analysis(data["result"])
    return JSONResponse({"ok": True, "result": data["result"], "backend": data["backend"]})


@app.post("/chat")
async def chat(request: Request, message: str = Form(...)):
    _require_auth(request)
    if _rate_limited(request):
        return JSONResponse({"ok": False, "error": "Rate limit — wait a few minutes."}, status_code=429)
    if not ws.is_loaded():
        return JSONResponse({"ok": False, "error": "Load a data source first."}, status_code=400)
    if len(message) > MAX_TOPIC_CHARS:
        return JSONResponse({"ok": False, "error": f"Message too long (max {MAX_TOPIC_CHARS} chars)."}, status_code=413)
    ws.append_chat("user", message)
    try:
        data = await run_in_threadpool(run_chat, message, ws.get_workspace())
    except Exception as exc:
        return JSONResponse({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, status_code=500)
    ws.append_chat("assistant", data["result"])
    return JSONResponse({"ok": True, "result": data["result"], "backend": data["backend"]})


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
