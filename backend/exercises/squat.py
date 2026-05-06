"""Squat tracker — dual-leg detection, improved thresholds."""
import cv2

from .base import make_pose, calculate_angle, landmark_list, accuracy

import mediapipe as mp
mp_pose = mp.solutions.pose
PL = mp_pose.PoseLandmark

UP_THRESHOLD   = 165   # knee straight (standing)
DOWN_THRESHOLD = 90    # knee bent (squat depth) — widened from 80

FORWARD_LEAN_THRESHOLD = 85   # relaxed from 95


class SquatTracker:
    def __init__(self, reps_target: int = 10, weight: float = 0.0):
        self.reps_target = reps_target
        self.weight      = weight
        self.counter        = 0
        self.correct_reps   = 0
        self.incorrect_reps = 0
        self.form_errors    = set()
        self.stage          = "up"
        self._rep_is_valid  = True
        self._pose = make_pose()

    def process_frame(self, frame) -> dict:
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._pose.process(img_rgb)

        if not results.pose_landmarks:
            return self._base_result(detected=False,
                                     feedback="⚠ No person detected — step back or improve lighting",
                                     feedback_type="warning")

        lm = results.pose_landmarks.landmark

        left_vis  = (lm[PL.LEFT_HIP].visibility + lm[PL.LEFT_KNEE].visibility + lm[PL.LEFT_ANKLE].visibility) / 3
        right_vis = (lm[PL.RIGHT_HIP].visibility + lm[PL.RIGHT_KNEE].visibility + lm[PL.RIGHT_ANKLE].visibility) / 3

        knee_angles, hip_angles = [], []

        if left_vis >= 0.4:
            knee_angles.append(calculate_angle(
                [lm[PL.LEFT_HIP].x, lm[PL.LEFT_HIP].y],
                [lm[PL.LEFT_KNEE].x, lm[PL.LEFT_KNEE].y],
                [lm[PL.LEFT_ANKLE].x, lm[PL.LEFT_ANKLE].y]))
            hip_angles.append(calculate_angle(
                [lm[PL.LEFT_SHOULDER].x, lm[PL.LEFT_SHOULDER].y],
                [lm[PL.LEFT_HIP].x, lm[PL.LEFT_HIP].y],
                [lm[PL.LEFT_KNEE].x, lm[PL.LEFT_KNEE].y]))

        if right_vis >= 0.4:
            knee_angles.append(calculate_angle(
                [lm[PL.RIGHT_HIP].x, lm[PL.RIGHT_HIP].y],
                [lm[PL.RIGHT_KNEE].x, lm[PL.RIGHT_KNEE].y],
                [lm[PL.RIGHT_ANKLE].x, lm[PL.RIGHT_ANKLE].y]))
            hip_angles.append(calculate_angle(
                [lm[PL.RIGHT_SHOULDER].x, lm[PL.RIGHT_SHOULDER].y],
                [lm[PL.RIGHT_HIP].x, lm[PL.RIGHT_HIP].y],
                [lm[PL.RIGHT_KNEE].x, lm[PL.RIGHT_KNEE].y]))

        if not knee_angles:
            return self._base_result(detected=False,
                                     feedback="⚠ Legs not visible — face camera from the side",
                                     feedback_type="warning")

        knee_angle = sum(knee_angles) / len(knee_angles)
        hip_angle  = sum(hip_angles)  / len(hip_angles)

        frame_errors: set[str] = set()
        feedback      = "Good form! Keep going 💪"
        feedback_type = "success"

        if hip_angle < FORWARD_LEAN_THRESHOLD:
            frame_errors.add("forward lean")
            feedback      = "LEAN WARNING: Keep your chest up!"
            feedback_type = "warning"
        elif self.stage == "up" and knee_angle > DOWN_THRESHOLD + 10:
            feedback      = "Squat deeper — aim for thighs parallel to floor!"
            feedback_type = "info"

        self.form_errors.update(frame_errors)

        rep_completed = False

        if knee_angle <= DOWN_THRESHOLD and self.stage == "up":
            self.stage = "down"
            self._rep_is_valid = len(frame_errors) == 0

        elif knee_angle >= UP_THRESHOLD and self.stage == "down":
            self.counter += 1
            rep_completed = True
            if not self._rep_is_valid or frame_errors:
                self.incorrect_reps += 1
                self.form_errors.update(frame_errors)
                feedback      = "Rep counted — check your form!"
                feedback_type = "error"
            else:
                self.correct_reps += 1
                feedback      = "✅ Great squat!"
                feedback_type = "success"
            self.stage = "up"
            self._rep_is_valid = True

        rk = round(knee_angles[-1] if right_vis >= 0.4 else knee_angles[0], 1)
        rh = round(hip_angles[-1]  if right_vis >= 0.4 else hip_angles[0], 1)

        return {
            **self._base_result(detected=True, feedback=feedback, feedback_type=feedback_type),
            "landmarks":     landmark_list(results.pose_landmarks),
            "angles":        {"left_elbow": 0.0, "right_elbow": 0.0,
                              "right_knee": rk, "right_hip": rh, "left_hip": 0.0},
            "primary_angle": round(knee_angle, 1),
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
            "exercise_name": "squat", "weight": self.weight, "error": None,
        }
