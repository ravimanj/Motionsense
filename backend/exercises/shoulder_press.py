"""Shoulder Press tracker — dual-arm detection, improved thresholds."""
import cv2

from .base import make_pose, calculate_angle, landmark_list, accuracy

import mediapipe as mp
mp_pose = mp.solutions.pose
PL = mp_pose.PoseLandmark

DOWN_THRESHOLD = 160   # elbow fully extended overhead (top)
UP_THRESHOLD   = 80    # elbow lowered near ears       (bottom)
LEAN_THRESHOLD = 0.08  # max horizontal hip-shoulder displacement (relaxed slightly)


class ShoulderPressTracker:
    def __init__(self, reps_target: int = 10, weight: float = 0.0):
        self.reps_target = reps_target
        self.weight      = weight
        self.counter        = 0
        self.correct_reps   = 0
        self.incorrect_reps = 0
        self.form_errors    = set()
        self.stage          = "down"   # "down" = arms lowered, "up" = arms extended
        self._pose = make_pose()

    def process_frame(self, frame) -> dict:
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._pose.process(img_rgb)

        if not results.pose_landmarks:
            return self._base_result(detected=False,
                                     feedback="⚠ No person detected — step back or improve lighting",
                                     feedback_type="warning")

        lm = results.pose_landmarks.landmark

        left_vis  = (lm[PL.LEFT_SHOULDER].visibility + lm[PL.LEFT_ELBOW].visibility + lm[PL.LEFT_WRIST].visibility) / 3
        right_vis = (lm[PL.RIGHT_SHOULDER].visibility + lm[PL.RIGHT_ELBOW].visibility + lm[PL.RIGHT_WRIST].visibility) / 3

        elbow_angles, lean_dxs = [], []

        if left_vis >= 0.4:
            elbow_angles.append(calculate_angle(
                [lm[PL.LEFT_SHOULDER].x, lm[PL.LEFT_SHOULDER].y],
                [lm[PL.LEFT_ELBOW].x,    lm[PL.LEFT_ELBOW].y],
                [lm[PL.LEFT_WRIST].x,    lm[PL.LEFT_WRIST].y]))
            if lm[PL.LEFT_HIP].visibility >= 0.4:
                lean_dxs.append(abs(lm[PL.LEFT_HIP].x - lm[PL.LEFT_SHOULDER].x))

        if right_vis >= 0.4:
            elbow_angles.append(calculate_angle(
                [lm[PL.RIGHT_SHOULDER].x, lm[PL.RIGHT_SHOULDER].y],
                [lm[PL.RIGHT_ELBOW].x,    lm[PL.RIGHT_ELBOW].y],
                [lm[PL.RIGHT_WRIST].x,    lm[PL.RIGHT_WRIST].y]))
            if lm[PL.RIGHT_HIP].visibility >= 0.4:
                lean_dxs.append(abs(lm[PL.RIGHT_HIP].x - lm[PL.RIGHT_SHOULDER].x))

        if not elbow_angles:
            return self._base_result(detected=False,
                                     feedback="⚠ Arms not visible — face camera from the front",
                                     feedback_type="warning")

        elbow_angle = sum(elbow_angles) / len(elbow_angles)
        lean_dx     = sum(lean_dxs) / len(lean_dxs) if lean_dxs else 0.0

        frame_errors: set[str] = set()
        feedback      = "Good form! Keep going 💪"
        feedback_type = "success"

        if lean_dx > LEAN_THRESHOLD:
            frame_errors.add("leaning")
            feedback      = "LEANING: Keep your core tight — don't arch!"
            feedback_type = "error"
        elif self.stage == "down" and elbow_angle < DOWN_THRESHOLD - 10:
            frame_errors.add("incomplete lockout")
            feedback      = "INCOMPLETE LOCKOUT: Press fully overhead!"
            feedback_type = "warning"
        elif self.stage == "up" and elbow_angle > UP_THRESHOLD + 10:
            frame_errors.add("incomplete depth")
            feedback      = "INCOMPLETE DEPTH: Lower closer to shoulders!"
            feedback_type = "warning"

        self.form_errors.update(frame_errors)

        rep_completed = False

        # Bottom position (arms lowered)
        if elbow_angle < UP_THRESHOLD:
            self.stage = "down"

        # Pressed to lockout → count rep
        elif elbow_angle > DOWN_THRESHOLD and self.stage == "down":
            self.stage = "up"
            self.counter += 1
            rep_completed = True
            if frame_errors:
                self.incorrect_reps += 1
                feedback      = "Rep counted — watch your form!"
                feedback_type = "error"
            else:
                self.correct_reps += 1
                feedback      = "✅ Great press!"
                feedback_type = "success"

        re = round(elbow_angles[-1] if right_vis >= 0.4 else elbow_angles[0], 1)

        return {
            **self._base_result(detected=True, feedback=feedback, feedback_type=feedback_type),
            "landmarks":     landmark_list(results.pose_landmarks),
            "angles":        {"left_elbow": 0.0, "right_elbow": re,
                              "right_knee": 0.0, "right_hip": 0.0, "left_hip": 0.0},
            "primary_angle": round(elbow_angle, 1),
            "stage":         self.stage,
            "rep_completed": rep_completed,
        }

    def close(self):
        self._pose.close()

    def _base_result(self, *, detected: bool, feedback: str, feedback_type: str) -> dict:
        return {
            "detected": detected, "landmarks": None,
            "angles": {"left_elbow": 0, "right_elbow": 0, "right_knee": 0, "right_hip": 0, "left_hip": 0},
            "primary_angle": 0.0, "stage": self.stage,
            "counter": self.counter, "correct_reps": self.correct_reps,
            "incorrect_reps": self.incorrect_reps,
            "accuracy": accuracy(self.correct_reps, self.incorrect_reps),
            "reps_target": self.reps_target, "rep_completed": False,
            "target_reached": self.counter >= self.reps_target,
            "feedback": feedback, "feedback_type": feedback_type,
            "form_errors": list(self.form_errors),
            "exercise_name": "shoulder_press", "weight": self.weight, "error": None,
        }
