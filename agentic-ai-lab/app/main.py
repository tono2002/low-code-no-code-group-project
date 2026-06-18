"""
FastAPI web app for the Agentic AI lab.

- Single shared password gate (env APP_PASSWORD, default "agenticai").
- One web page where a teammate types a topic and runs the CrewAI supply-chain
  crew. The crew runs server-side (in this container) and the result is shown.
- Runs are serialised with a lock so concurrent users don't blow the Gemini
  free-tier rate limit (10 req/min); a waiting request simply queues.
"""

import asyncio
import os
import time
from pathlib import Path

from fastapi import FastAPI, Form, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.concurrency import run_in_threadpool
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from .crew import run_crew, run_dataset, run_erp, TITAN_SUPPLY_CHAIN_CONTEXT, MAX_TOPIC_CHARS
from .dataset import generate_dataset
from .erp import generate_erp_data, simulate_connection
from .security import client_ip, constant_time_eq, SlidingWindowLimiter, LoginGuard

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
    html = (STATIC_DIR / page).read_text(encoding="utf-8")
    if page == "app.html":
        # Pre-fill the textarea with the Titan scenario.
        html = html.replace("{{DEFAULT_TOPIC}}", TITAN_SUPPLY_CHAIN_CONTEXT)
    return HTMLResponse(html)


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


@app.post("/run")
async def run(request: Request, topic: str = Form("")):
    if not _is_authed(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    # Per-IP rate limit (abuse / cost protection).
    if not _run_limiter.check(client_ip(request), time.time()):
        return JSONResponse(
            {"ok": False, "error": "Rate limit: too many runs. Wait a few minutes."},
            status_code=429,
        )
    # Hard cap input size before it ever reaches the model.
    if len(topic) > MAX_TOPIC_CHARS:
        return JSONResponse(
            {"ok": False, "error": f"Topic too long (max {MAX_TOPIC_CHARS} chars)."},
            status_code=413,
        )
    # Serialise: only one crew at a time. Queue if another run is in flight.
    async with _crew_lock:
        try:
            data = await run_in_threadpool(run_crew, topic)
        except Exception as exc:  # surface a readable error to the UI
            return JSONResponse(
                {"ok": False, "error": f"{type(exc).__name__}: {exc}"},
                status_code=500,
            )
    return JSONResponse({"ok": True, "result": data["result"], "backend": data["backend"]})


@app.get("/dataset")
async def dataset(request: Request, n: int = 12):
    """Generate a fresh synthetic supplier dataset (one click)."""
    if not _is_authed(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return JSONResponse(generate_dataset(n=n))


@app.post("/run-dataset")
async def run_dataset_ep(request: Request, seed: int = Form(...), n: int = Form(12)):
    """Analyse the dataset identified by `seed` with the data-analyst crew."""
    if not _is_authed(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    if not _run_limiter.check(client_ip(request), time.time()):
        return JSONResponse(
            {"ok": False, "error": "Rate limit: too many runs. Wait a few minutes."},
            status_code=429,
        )
    async with _crew_lock:
        try:
            data = await run_in_threadpool(run_dataset, seed, n)
        except Exception as exc:
            return JSONResponse(
                {"ok": False, "error": f"{type(exc).__name__}: {exc}"},
                status_code=500,
            )
    return JSONResponse({"ok": True, "result": data["result"], "backend": data["backend"]})


@app.get("/erp/connect")
async def erp_connect(request: Request):
    """Simulated SAP connection handshake."""
    if not _is_authed(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return JSONResponse(simulate_connection())


@app.get("/erp/data")
async def erp_data(request: Request):
    """Pull a (simulated) SAP S/4HANA supply-chain extract."""
    if not _is_authed(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return JSONResponse(generate_erp_data())


@app.post("/run-erp")
async def run_erp_ep(request: Request, seed: int = Form(...)):
    """Analyse the (simulated) SAP extract for `seed` with the analyst crew."""
    if not _is_authed(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    if not _run_limiter.check(client_ip(request), time.time()):
        return JSONResponse(
            {"ok": False, "error": "Rate limit: too many runs. Wait a few minutes."},
            status_code=429,
        )
    async with _crew_lock:
        try:
            data = await run_in_threadpool(run_erp, seed)
        except Exception as exc:
            return JSONResponse(
                {"ok": False, "error": f"{type(exc).__name__}: {exc}"},
                status_code=500,
            )
    return JSONResponse({"ok": True, "result": data["result"], "backend": data["backend"]})


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
