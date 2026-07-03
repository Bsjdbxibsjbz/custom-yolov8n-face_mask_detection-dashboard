"""
detector.py — auto-starts on import, no thread needed
"""

import atexit
import time
from datetime import datetime

import cv2
import torch.serialization
from ultralytics import YOLO
from ultralytics.nn.tasks import DetectionModel
torch.serialization.add_safe_globals([DetectionModel])

from database import create_database, save_session

MODEL_PATH = "/home/shahid/work/mask_detection/model_training_environment/runs/detect/runs/train/mask_project/jun_4_data/weights/best.pt"

CLASS_NAMES = {
    0: "person",
    1: "clear_face",
    2: "head",
    3: "masked_face",
    4: "not_sure",
}

CLASS_COLOURS = {
    0: (200, 200, 200),
    1: (0, 165, 255),
    2: (255, 255, 0),
    3: (0, 220, 80),
    4: (80, 80, 255),
}

CONF_THRESHOLD = 0.40

# Global state — written by background thread, read by API
_stats = {
    "person": 0,
    "clear_face": 0,
    "head": 0,
    "masked_face": 0,
    "not_sure": 0,
    "compliance": 0.0,
}
_current_frame = None
_session_start = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_stats():
    return dict(_stats)


def get_frame():
    return _current_frame


def _compute_compliance(masked, clear):
    total = masked + clear
    if total == 0:
        return 0.0
    return round((masked / total) * 100, 2)


def _save_on_exit():
    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_session(
        start_time=_session_start,
        end_time=end_time,
        person_count=_stats["person"],
        clear_face_count=_stats["clear_face"],
        head_count=_stats["head"],
        masked_face_count=_stats["masked_face"],
        not_sure_count=_stats["not_sure"],
        compliance=_stats["compliance"],
    )
    print(f"[detector] Session saved — end: {end_time}")


def _run_detector():
    global _current_frame, _stats

    create_database()
    atexit.register(_save_on_exit)

    print("[detector] Loading YOLOv8 model …")
    model = YOLO(MODEL_PATH)
    print("[detector] Model loaded.")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[detector] ERROR: Cannot open webcam.")
        return

    print(f"[detector] Session started at {_session_start}")

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.05)
                continue

            try:
                results = model(frame, conf=CONF_THRESHOLD, verbose=False)[0]
            except Exception as e:
                print(f"[detector] inference error: {e}")
                continue

            frame_counts = {k: 0 for k in CLASS_NAMES.values()}

            for box in results.boxes:
                cls_id = int(box.cls[0])
                conf   = float(box.conf[0])
                label  = CLASS_NAMES.get(cls_id, "unknown")
                colour = CLASS_COLOURS.get(cls_id, (255, 255, 255))
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cv2.rectangle(frame, (x1, y1), (x2, y2), colour, 2)
                text = f"{label} {conf:.2f}"
                (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
                cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 6, y1), colour, -1)
                cv2.putText(frame, text, (x1 + 3, y1 - 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)
                if label in frame_counts:
                    frame_counts[label] += 1

            compliance = _compute_compliance(
                frame_counts["masked_face"], frame_counts["clear_face"]
            )
            cv2.putText(frame, f"Compliance: {compliance:.1f}%", (12, 36),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 220, 80), 2, cv2.LINE_AA)

            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ok:
                continue

            # Direct assignment — no lock needed, GIL protects simple assignment
            _current_frame = buf.tobytes()
            _stats = {
                "person":      frame_counts["person"],
                "clear_face":  frame_counts["clear_face"],
                "head":        frame_counts["head"],
                "masked_face": frame_counts["masked_face"],
                "not_sure":    frame_counts["not_sure"],
                "compliance":  compliance,
            }

    finally:
        cap.release()
        print("[detector] Webcam released.")


def start_detector_thread():
    import threading
    t = threading.Thread(target=_run_detector, daemon=True, name="detector")
    t.start()
    return t