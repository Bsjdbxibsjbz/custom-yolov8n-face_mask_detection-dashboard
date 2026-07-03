# MaskGuard — Face Mask Detection Analytics Platform

A production-grade real-time analytics dashboard that runs YOLOv8 mask detection on a laptop webcam and streams live statistics to an enterprise-style web UI.

---

## Architecture

```
Laptop Webcam
      ↓
YOLOv8 Detector  (detector.py — background thread inside api.py)
      ↓
FastAPI Backend  (api.py)
      ↓          ↓
SQLite DB     MJPEG Stream
      ↓          ↓
HTML + CSS + JavaScript Dashboard  (templates/index.html)
```

---

## Project Structure

```
face_mask_dashboard/
├── best.pt                  ← Your custom YOLOv8 weights (place here)
├── database.py              ← SQLite helpers (create / save / query)
├── detector.py              ← YOLOv8 inference + frame streaming
├── api.py                   ← FastAPI app (routes, startup, MJPEG)
├── templates/
│   └── index.html           ← Dashboard HTML
├── static/
│   ├── style.css            ← Enterprise dark-theme CSS
│   └── script.js            ← Async polling + DOM updates
├── database/
│   └── mask_detection.db    ← Auto-created on first run
├── requirements.txt
└── README.md
```

---

## Model Classes

| ID | Class        |
|----|-------------|
| 0  | person      |
| 1  | clear_face  |
| 2  | head        |
| 3  | masked_face |
| 4  | not_sure    |

---

## Compliance Formula

```
compliance = (masked_face / (masked_face + clear_face)) × 100
```

Division-by-zero is handled safely (returns 0.0).

---

## Installation

```bash
# 1. Clone / copy the project folder
cd face_mask_dashboard

# 2. Create and activate a virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Place your YOLOv8 weights file
cp /path/to/best.pt .
```

---

## Running

### Single-terminal mode (recommended)

The detector thread is launched automatically by `api.py` on startup:

```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

Open **http://localhost:8000** in your browser.

### Two-terminal mode (standalone detector with preview window)

**Terminal 1** — run detector with a local preview window:

```bash
python detector.py
```

Press **q** to stop. The session is saved automatically on exit.

**Terminal 2** — run the API server:

```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

Open **http://localhost:8000**.

---

## API Endpoints

| Method | Path                | Description                              |
|--------|---------------------|------------------------------------------|
| GET    | `/`                 | Serve the analytics dashboard            |
| GET    | `/stats`            | Live per-frame detection counts + compliance |
| GET    | `/previous-session` | Last saved session from SQLite           |
| GET    | `/video_feed`       | MJPEG stream with bounding boxes         |

### `GET /stats` — example response

```json
{
  "person": 3,
  "clear_face": 1,
  "head": 3,
  "masked_face": 2,
  "not_sure": 0,
  "compliance": 66.67
}
```

### `GET /previous-session` — example response

```json
{
  "id": 1,
  "start_time": "2025-06-25 09:00:00",
  "end_time": "2025-06-25 09:32:15",
  "person_count": 145,
  "clear_face_count": 42,
  "head_count": 145,
  "masked_face_count": 95,
  "not_sure_count": 8,
  "compliance": 69.34
}
```

Returns `404` if no session has been recorded yet.

---

## Session Lifecycle

- **Session begins** when `api.py` starts (the detector thread spawns and records `start_time`).
- **Session ends** when the process is stopped (Ctrl-C or kill signal); Python's `atexit` hook saves the final summary to SQLite.
- Only one row per run is written — the final aggregate, not per-frame data.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Black / loading feed | Make sure `uvicorn api:app` is running and webcam isn't in use by another app |
| `Cannot open webcam` | Change `cv2.VideoCapture(0)` to `cv2.VideoCapture(1)` if you have multiple cameras |
| `best.pt not found` | Confirm `best.pt` is in the same directory as `detector.py` / `api.py` |
| Low frame rate | Reduce resolution in `detector.py` (`CAP_PROP_FRAME_WIDTH` / `HEIGHT`) or lower `CONF_THRESHOLD` |
| Port already in use | Run on a different port: `uvicorn api:app --port 8001` |
| No previous session | Run and stop the app at least once; atexit saves the session on clean exit |

---

## Configuration

Key constants you can tune in `detector.py`:

```python
MODEL_PATH      = "best.pt"   # Path to YOLOv8 weights
CONF_THRESHOLD  = 0.40        # Detection confidence threshold (0–1)
```

---

## License

MIT — use freely, attribution appreciated.
