"""Squat tracker — ported from the desktop app."""
import cv2
import mediapipe as mp

from .base import calculate_angle, landmark_list, accuracy

mp_pose = mp.solutions.pose
PL = mp_pose.PoseLandmark

# ── Default thresholds (knee angle) ──────────────────────────────────────────
UP_THRESHOLD   = 170   # knee angle when standing fully upright
DOWN_THRESHOLD = 80    # knee angle at squat depth

FORWARD_LEAN_THRESHOLD = 95   # min shoulder-hip-knee angle (torso lean)


class SquatTracker:
    def __init__(self, reps_target: int = 10, weight: float = 0.0):
        self.reps_target = reps_target
        self.weight      = weight

        self.counter        = 0
        self.correct_reps   = 0
        self.incorrect_reps = 0
        self.form_errors    = set()
        # "up" = standing, "down" = at squat depth
        self.stage          = "up"

        self._rep_is_valid = True

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

        r_hip      = [lm[PL.RIGHT_HIP].x,      lm[PL.RIGHT_HIP].y]
        r_knee     = [lm[PL.RIGHT_KNEE].x,      lm[PL.RIGHT_KNEE].y]
        r_ankle    = [lm[PL.RIGHT_ANKLE].x,     lm[PL.RIGHT_ANKLE].y]
        r_shoulder = [lm[PL.RIGHT_SHOULDER].x,  lm[PL.RIGHT_SHOULDER].y]

        knee_angle = calculate_angle(r_hip, r_knee, r_ankle)
        hip_angle  = calculate_angle(r_shoulder, r_hip, r_knee)

        # ── Form checks ───────────────────────────────────────────────────────
        frame_errors: set[str] = set()
        feedback      = "Good form! Keep going 💪"
        feedback_type = "success"

        if hip_angle < FORWARD_LEAN_THRESHOLD:
            frame_errors.add("forward lean")
            feedback      = "LEAN WARNING: Keep chest up!"
            feedback_type = "warning"
        elif self.stage == "up" and knee_angle > DOWN_THRESHOLD + 5:
            feedback      = "Squat deeper!"
            feedback_type = "info"

        self.form_errors.update(frame_errors)

        # ── Rep state-machine ────────────────────────────────────────────────
        rep_completed = False

        # Hit depth → enter "down" stage
        if knee_angle < DOWN_THRESHOLD and self.stage == "up":
            self.stage = "down"
            self._rep_is_valid = len(frame_errors) == 0

        # Fully stood up → count rep
        elif knee_angle > UP_THRESHOLD and self.stage == "down":
            self.counter += 1
            rep_completed = True
            if not self._rep_is_valid or frame_errors:
                self.incorrect_reps += 1
                self.form_errors.update(frame_errors)
                feedback      = "Rep counted (form issues noted)"
                feedback_type = "error"
            else:
                self.correct_reps += 1
                feedback      = "✅ Great rep!"
                feedback_type = "success"
            self.stage = "up"
            self._rep_is_valid = True

        return {
            **self._base_result(detected=True,
                                feedback=feedback,
                                feedback_type=feedback_type),
            "landmarks": landmark_list(results.pose_landmarks),
            "angles": {
                "left_elbow":  0.0,
                "right_elbow": 0.0,
                "right_knee":  round(knee_angle, 1),
                "right_hip":   round(hip_angle, 1),
                "left_hip":    0.0,
            },
            "primary_angle": round(knee_angle, 1),
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
            "exercise_name":  "squat",
            "weight":         self.weight,
            "error":          None,
        }
