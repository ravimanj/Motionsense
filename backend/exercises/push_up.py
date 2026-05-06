"""Push-Up tracker — dual-arm detection, improved thresholds."""
import cv2

from .base import make_pose, calculate_angle, landmark_list, accuracy

import mediapipe as mp
mp_pose = mp.solutions.pose
PL = mp_pose.PoseLandmark

DOWN_THRESHOLD      = 160   # elbow angle at top (arms straight)
UP_THRESHOLD        = 90    # elbow angle at bottom (arms bent)
HIP_ANGLE_THRESHOLD = 150   # relaxed from 160 — less false hip-sag for oblique cameras
TOLERANCE           = 10


class PushUpTracker:
    def __init__(self, reps_target: int = 10, weight: float = 0.0):
        self.reps_target = reps_target
        self.weight      = weight
        self.counter        = 0
        self.correct_reps   = 0
        self.incorrect_reps = 0
        self.form_errors    = set()
        self.stage          = "down"   # "down" = arms straight (top), "up" = arms bent (bottom)
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

        elbow_angles, hip_angles = [], []

        if left_vis >= 0.4:
            elbow_angles.append(calculate_angle(
                [lm[PL.LEFT_SHOULDER].x, lm[PL.LEFT_SHOULDER].y],
                [lm[PL.LEFT_ELBOW].x,    lm[PL.LEFT_ELBOW].y],
                [lm[PL.LEFT_WRIST].x,    lm[PL.LEFT_WRIST].y]))
            if lm[PL.LEFT_HIP].visibility >= 0.4 and lm[PL.LEFT_KNEE].visibility >= 0.4:
                hip_angles.append(calculate_angle(
                    [lm[PL.LEFT_SHOULDER].x, lm[PL.LEFT_SHOULDER].y],
                    [lm[PL.LEFT_HIP].x,      lm[PL.LEFT_HIP].y],
                    [lm[PL.LEFT_KNEE].x,     lm[PL.LEFT_KNEE].y]))

        if right_vis >= 0.4:
            elbow_angles.append(calculate_angle(
                [lm[PL.RIGHT_SHOULDER].x, lm[PL.RIGHT_SHOULDER].y],
                [lm[PL.RIGHT_ELBOW].x,    lm[PL.RIGHT_ELBOW].y],
                [lm[PL.RIGHT_WRIST].x,    lm[PL.RIGHT_WRIST].y]))
            if lm[PL.RIGHT_HIP].visibility >= 0.4 and lm[PL.RIGHT_KNEE].visibility >= 0.4:
                hip_angles.append(calculate_angle(
                    [lm[PL.RIGHT_SHOULDER].x, lm[PL.RIGHT_SHOULDER].y],
                    [lm[PL.RIGHT_HIP].x,      lm[PL.RIGHT_HIP].y],
                    [lm[PL.RIGHT_KNEE].x,     lm[PL.RIGHT_KNEE].y]))

        if not elbow_angles:
            return self._base_result(detected=False,
                                     feedback="⚠ Arms not visible — film from the side",
                                     feedback_type="warning")

        elbow_angle = sum(elbow_angles) / len(elbow_angles)
        hip_angle   = sum(hip_angles) / len(hip_angles) if hip_angles else HIP_ANGLE_THRESHOLD + 1

        frame_errors: set[str] = set()
        feedback      = "Good form! Keep going 💪"
        feedback_type = "success"

        if hip_angle < HIP_ANGLE_THRESHOLD:
            frame_errors.add("hip sag")
            feedback      = "HIP SAG: Keep your core tight and back straight!"
            feedback_type = "error"
        elif self.stage == "down" and elbow_angle < DOWN_THRESHOLD - 10:
            frame_errors.add("incomplete extension")
            feedback      = "INCOMPLETE EXTENSION: Straighten arms fully at the top!"
            feedback_type = "warning"
        elif self.stage == "up" and elbow_angle > UP_THRESHOLD + 10:
            frame_errors.add("incomplete depth")
            feedback      = "INCOMPLETE DEPTH: Lower your chest further!"
            feedback_type = "warning"

        self.form_errors.update(frame_errors)

        rep_completed = False

        # Transition to bottom (arms bent) → count rep
        if elbow_angle < UP_THRESHOLD and self.stage == "down":
            self.stage = "up"
            self.counter += 1
            rep_completed = True
            if frame_errors - {"incomplete extension"}:
                self.incorrect_reps += 1
                feedback      = "Rep counted — check your form!"
                feedback_type = "error"
            else:
                self.correct_reps += 1
                feedback      = "✅ Great push-up!"
                feedback_type = "success"

        # Transition back to top (arms straight)
        elif elbow_angle > DOWN_THRESHOLD and self.stage == "up":
            self.stage = "down"

        re = round(elbow_angles[-1] if right_vis >= 0.4 else elbow_angles[0], 1)
        rh = round(hip_angles[-1]   if (right_vis >= 0.4 and hip_angles) else (hip_angles[0] if hip_angles else 0.0), 1)

        return {
            **self._base_result(detected=True, feedback=feedback, feedback_type=feedback_type),
            "landmarks":     landmark_list(results.pose_landmarks),
            "angles":        {"left_elbow": 0.0, "right_elbow": re,
                              "right_knee": 0.0, "right_hip": rh, "left_hip": 0.0},
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
            "exercise_name": "push_up", "weight": self.weight, "error": None,
        }
