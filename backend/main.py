"""
MotionSense AI — FastAPI WebSocket Backend
==========================================
WebSocket endpoint: ws(s)://<host>/ws/{exercise}?reps=<int>&weight=<float>

Frame protocol
--------------
  Android → Server : JSON  {"frame": "<base64-JPEG>"}
                     or plain base64 string (fallback)
  Server  → Android: JSON matching FrameResult data class (see below)
"""
import base64
import json
import logging
import numpy as np
import cv2

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from exercises.bicep_curl     import BicepCurlTracker
from exercises.push_up        import PushUpTracker
from exercises.squat          import SquatTracker
from exercises.shoulder_press import ShoulderPressTracker

import models
from database import engine
from routers import auth, tracking

# Create database tables
models.Base.metadata.create_all(bind=engine)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("motionsense")

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="MotionSense AI API",
    version="2.0.0",
    description="Real-time pose estimation & rep counting via WebSocket",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(tracking.router)

# Map URL exercise key → tracker class
EXERCISE_MAP = {
    "bicep_curl":     BicepCurlTracker,
    "push_up":        PushUpTracker,
    "squat":          SquatTracker,
    "shoulder_press": ShoulderPressTracker,
}


# ── HTTP endpoints ────────────────────────────────────────────────────────────
@app.get("/")
async def health():
    return {"status": "ok", "service": "MotionSense AI API", "version": "2.0.0"}


@app.get("/exercises")
async def list_exercises():
    return {
        "exercises": [
            {
                "key":     "bicep_curl",
                "name":    "Bicep Curl",
                "muscles": "Biceps, Forearms",
                "icon":    "💪",
            },
            {
                "key":     "push_up",
                "name":    "Push Up",
                "muscles": "Chest, Shoulders (Anterior Deltoid), Triceps, Core",
                "icon":    "🙌",
            },
            {
                "key":     "squat",
                "name":    "Squat",
                "muscles": "Quads, Glutes, Hamstrings, Core",
                "icon":    "🦵",
            },
            {
                "key":     "shoulder_press",
                "name":    "Shoulder Press",
                "muscles": "Shoulders (Deltoids), Triceps, Trapezius",
                "icon":    "🏋️",
            },
        ]
    }


# ── WebSocket endpoint ────────────────────────────────────────────────────────
@app.websocket("/ws/{exercise}")
async def websocket_endpoint(
    websocket: WebSocket,
    exercise: str,
    reps: int   = 10,
    weight: float = 0.0,
):
    await websocket.accept()
    logger.info(f"WS connected  exercise={exercise}  reps={reps}  weight={weight}")

    tracker_class = EXERCISE_MAP.get(exercise)
    if tracker_class is None:
        await websocket.send_json({
            "error":    f"Unknown exercise '{exercise}'. "
                        f"Valid: {list(EXERCISE_MAP.keys())}",
            "detected": False,
        })
        await websocket.close(code=1003)
        return

    tracker = tracker_class(reps_target=reps, weight=weight)

    try:
        while True:
            raw = await websocket.receive_text()

            # ── Decode frame ─────────────────────────────────────────────────
            frame_b64 = _extract_base64(raw)
            if not frame_b64:
                await websocket.send_json({
                    "error":    "Empty frame received",
                    "detected": False,
                })
                continue

            frame, decode_error = _decode_frame(frame_b64)
            if frame is None:
                logger.warning(f"Frame decode failed ({exercise}): {decode_error}")
                await websocket.send_json({
                    "error":    f"Frame decode failed: {decode_error}",
                    "detected": False,
                })
                continue

            # ── Run exercise tracker ──────────────────────────────────────────
            result = tracker.process_frame(frame)
            await websocket.send_json(result)

            # Close gracefully when target is reached
            if result.get("target_reached"):
                logger.info(f"Target reached for {exercise}")
                break

    except WebSocketDisconnect:
        logger.info(f"WS disconnected  exercise={exercise}")
    except Exception as exc:
        logger.exception(f"WS error  exercise={exercise}: {exc}")
        try:
            await websocket.send_json({"error": str(exc), "detected": False})
        except Exception:
            pass
    finally:
        tracker.close()


# ── Helpers ───────────────────────────────────────────────────────────────────
def _extract_base64(raw: str) -> str:
    """Accept either a JSON envelope {"frame":"..."} or a raw base64 string."""
    raw = raw.strip()
    if raw.startswith("{"):
        try:
            msg = json.loads(raw)
            return msg.get("frame", "")
        except json.JSONDecodeError:
            pass
    return raw   # assume raw base64


def _decode_frame(b64: str) -> tuple:
    """
    Decode a base64-encoded JPEG into an OpenCV BGR frame.

    Returns (frame, None) on success or (None, error_message) on failure.
    Handles:
      - Missing base64 padding (Android sometimes omits trailing '=')
      - URL-safe base64 characters ('-' and '_')
    """
    try:
        # ── Normalise: URL-safe → standard; add missing '=' padding ──────────
        b64_clean = b64.replace("-", "+").replace("_", "/")
        # Pad to a multiple of 4
        missing = len(b64_clean) % 4
        if missing:
            b64_clean += "=" * (4 - missing)

        img_bytes = base64.b64decode(b64_clean, validate=True)
        arr       = np.frombuffer(img_bytes, dtype=np.uint8)
        frame     = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            return None, "imdecode returned None — not a valid JPEG"
        return frame, None
    except Exception as exc:
        return None, str(exc)
