"""Shared utilities for all exercise trackers."""
import numpy as np
import mediapipe as mp

mp_pose = mp.solutions.pose


def make_pose() -> mp_pose.Pose:
    """
    Create a MediaPipe Pose instance tuned for video analysis.

    Key choices vs. defaults:
    - min_detection_confidence=0.5  : faster re-detection; video frames are
      cleaner than live camera so 0.5 is sufficient.
    - min_tracking_confidence=0.5   : allows tracker to keep going through
      brief occlusions without expensive full re-detection.
    - model_complexity=1            : best speed/accuracy balance (default but
      explicit here for clarity; do NOT use 2 — too slow on CPU).
    - smooth_landmarks=True         : MediaPipe's built-in Kalman-filter
      smoothing replaces the manual per-tracker EMA, giving better lag-free
      smoothing that is aware of the model's uncertainty.
    """
    return mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        smooth_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )


def calculate_angle(a, b, c) -> float:
    """Calculates the angle at vertex B given three 2-D points A, B, C."""
    a, b, c = np.array(a), np.array(b), np.array(c)
    radians = (
        np.arctan2(c[1] - b[1], c[0] - b[0])
        - np.arctan2(a[1] - b[1], a[0] - b[0])
    )
    angle = np.abs(radians * 180.0 / np.pi)
    if angle > 180.0:
        angle = 360.0 - angle
    return float(angle)


def visible(lm, min_vis: float = 0.4) -> bool:
    """Return True if landmark visibility meets the minimum threshold."""
    return lm.visibility >= min_vis


def landmark_list(pose_landmarks) -> list:
    """Serialise MediaPipe pose landmarks to a JSON-safe list of dicts."""
    return [
        {
            "x": lm.x,
            "y": lm.y,
            "z": lm.z,
            "visibility": lm.visibility,
        }
        for lm in pose_landmarks.landmark
    ]


def accuracy(correct: int, incorrect: int) -> int:
    total = correct + incorrect
    if total == 0:
        return 100
    return round((correct / total) * 100)
