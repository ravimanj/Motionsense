"""Shared utilities for all exercise trackers."""
import numpy as np
import mediapipe as mp

mp_pose = mp.solutions.pose


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
