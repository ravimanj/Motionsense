"""Shoulder Press tracker — ported from the desktop app."""
import cv2
import mediapipe as mp

from .base import calculate_angle, landmark_list, accuracy

mp_pose = mp.solutions.pose
PL = mp_pose.PoseLandmark

# ── Default thresholds (elbow angle) ─────────────────────────────────────────
DOWN_THRESHOLD = 160   # elbow angle arms fully extended overhead  (top)
UP_THRESHOLD   = 80    # elbow angle arms lowered near ears        (bottom)
LEAN_THRESHOLD = 0.06  # max horizontal hip-shoulder displacement


class ShoulderPressTracker:
    def __init__(self, reps_target: int = 10, weight: float = 0.0):
        self.reps_target = reps_target
        self.weight      = weight

        self.counter        = 0
        self.correct_reps   = 0
        self.incorrect_reps = 0
        self.form_errors    = set()
        # "down" = arms lowered (start), "up" = arms extended (lockout)
        self.stage          = "down"

        self._pose = mp_pose.Pose(
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7,
        )

    def process_frame(self, frame) -> dict:
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._pose.process(img_rgb)

        if not results.pose_landmarks:
            return self._base_result(detected=False,
                                     feedback="⚠ No person detected — adjust camera",
                                     feedback_type="warning")

        lm = results.pose_landmarks.landmark

        r_shoulder = [lm[PL.RIGHT_SHOULDER].x, lm[PL.RIGHT_SHOULDER].y]
        r_elbow    = [lm[PL.RIGHT_ELBOW].x,    lm[PL.RIGHT_ELBOW].y]
        r_wrist    = [lm[PL.RIGHT_WRIST].x,    lm[PL.RIGHT_WRIST].y]
        r_hip      = [lm[PL.RIGHT_HIP].x,      lm[PL.RIGHT_HIP].y]

        raw_elbow_angle = calculate_angle(r_shoulder, r_elbow, r_wrist)
        raw_lean_dx     = abs(r_hip[0] - r_shoulder[0])

        if not hasattr(self, 'smoothed_elbow'):
            self.smoothed_elbow = raw_elbow_angle
            self.smoothed_lean = raw_lean_dx
        else:
            self.smoothed_elbow = 0.4 * raw_elbow_angle + 0.6 * self.smoothed_elbow
            self.smoothed_lean = 0.4 * raw_lean_dx + 0.6 * self.smoothed_lean
            
        elbow_angle = self.smoothed_elbow
        lean_dx = self.smoothed_lean

        # ── Form checks ───────────────────────────────────────────────────────
        frame_errors: set[str] = set()
        feedback      = "Good form! Keep going 💪"
        feedback_type = "success"

        if lean_dx > LEAN_THRESHOLD:
            frame_errors.add("leaning")
            feedback      = "LEANING: Keep your core tight!"
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

        # ── Rep state-machine ────────────────────────────────────────────────
        rep_completed = False

        # Bottom position → ready to press
        if elbow_angle < UP_THRESHOLD:
            self.stage = "down"

        # Pressed to lockout → count rep
        elif elbow_angle > DOWN_THRESHOLD and self.stage == "down":
            self.stage = "up"
            self.counter += 1
            rep_completed = True
            if frame_errors:
                self.incorrect_reps += 1
                feedback      = "Rep counted (form issues noted)"
                feedback_type = "error"
            else:
                self.correct_reps += 1
                feedback      = "✅ Great rep!"
                feedback_type = "success"

        return {
            **self._base_result(detected=True,
                                feedback=feedback,
                                feedback_type=feedback_type),
            "landmarks": landmark_list(results.pose_landmarks),
            "angles": {
                "left_elbow":  0.0,
                "right_elbow": round(elbow_angle, 1),
                "right_knee":  0.0,
                "right_hip":   0.0,
                "left_hip":    0.0,
            },
            "primary_angle": round(elbow_angle, 1),
            "stage":         self.stage,
            "rep_completed": rep_completed,
        }

    def close(self):
        self._pose.close()

    def _base_result(self, *, detected: bool, feedback: str, feedback_type: str) -> dict:
        return {
            "detected":       detected,
            "landmarks":      None,
            "angles":         {"left_elbow": 0, "right_elbow": 0,
                               "right_knee": 0, "right_hip": 0, "left_hip": 0},
            "primary_angle":  0.0,
            "stage":          self.stage,
            "counter":        self.counter,
            "correct_reps":   self.correct_reps,
            "incorrect_reps": self.incorrect_reps,
            "accuracy":       accuracy(self.correct_reps, self.incorrect_reps),
            "reps_target":    self.reps_target,
            "rep_completed":  False,
            "target_reached": self.counter >= self.reps_target,
            "feedback":       feedback,
            "feedback_type":  feedback_type,
            "form_errors":    list(self.form_errors),
            "exercise_name":  "shoulder_press",
            "weight":         self.weight,
            "error":          None,
        }
