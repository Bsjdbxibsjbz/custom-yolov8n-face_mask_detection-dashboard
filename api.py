import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from database import create_database, get_previous_session
from detector import get_frame, get_stats, start_detector_thread

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent

app = FastAPI(title="Face Mask Detection Analytics")

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# ---------------------------------------------------------------------------
# Startup: initialise DB and launch detector thread
# ---------------------------------------------------------------------------

@app.on_event("startup")
def on_startup():
    create_database()
    start_detector_thread()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/stats")
async def stats():
    return JSONResponse(content=get_stats())


@app.get("/previous-session")
async def previous_session():
    session = get_previous_session()
    if session is None:
        return JSONResponse(content={"detail": "No previous session found."}, status_code=404)
    return JSONResponse(content=session)


# ---------------------------------------------------------------------------
# Single JPEG frame endpoint — polled by canvas every 100ms
# ---------------------------------------------------------------------------

@app.get("/frame")
def get_single_frame():
    frame = get_frame()
    if frame is None:
        return Response(status_code=204)
    return Response(content=frame, media_type="image/jpeg")


# ---------------------------------------------------------------------------
# MJPEG streaming — kept as fallback
# ---------------------------------------------------------------------------

def _mjpeg_generator_sync():
    boundary = b"--frame\r\n"
    header   = b"Content-Type: image/jpeg\r\n\r\n"
    for _ in range(300):
        if get_frame() is not None:
            break
        time.sleep(0.1)
    while True:
        frame = get_frame()
        if frame is not None:
            yield boundary + header + frame + b"\r\n"
        time.sleep(0.033)


@app.get("/video_feed")
def video_feed():
    return StreamingResponse(
        _mjpeg_generator_sync(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )