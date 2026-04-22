"""Bicep Curl tracker — ported from the desktop app."""
import cv2
import mediapipe as mp

from .base import calculate_angle, landmark_list, accuracy

mp_pose = mp.solutions.pose
PL = mp_pose.PoseLandmark

# ── Default angle thresholds (arm fully extended → arm fully curled) ──────────
DOWN_THRESHOLD = 160   # arm straight / extended  (rep "down" position)
UP_THRESHOLD   = 40    # arm fully curled          (rep "up"   position)

SWING_THRESHOLD    = 0.06  # max horizontal elbow drift
BAD_FORM_THRESHOLD = 10    # consecutive bad frames before flagging error
TOLERANCE          = 12    # angle tolerance for phase transitions


class BicepCurlTracker:
    def __init__(self, reps_target: int = 10, weight: float = 0.0):
        self.reps_target = reps_target
        self.weight      = weight

        self.counter       = 0
        self.correct_reps  = 0
        self.incorrect_reps = 0
        self.form_errors   = set()
        self.stage         = "down"          # "down" = arm extended, "up" = arm curled

        self._rep_has_error  = False
        self._bad_form_frames = 0

        self._pose = mp_pose.Pose(
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7,
        )

    # ── Public API ────────────────────────────────────────────────────────────
    def process_frame(self, frame) -> dict:
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._pose.process(img_rgb)

        if not results.pose_landmarks:
            return self._base_result(detected=False,
                                     feedback="⚠ No person detected — adjust camera",
                                     feedback_type="warning")

        lm = results.pose_landmarks.landmark

        shoulder = [lm[PL.LEFT_SHOULDER].x, lm[PL.LEFT_SHOULDER].y]
        elbow    = [lm[PL.LEFT_ELBOW].x,    lm[PL.LEFT_ELBOW].y]
        wrist    = [lm[PL.LEFT_WRIST].x,    lm[PL.LEFT_WRIST].y]

        angle       = calculate_angle(shoulder, elbow, wrist)
        elbow_shift = abs(elbow[0] - shoulder[0])

        # ── Form checks ───────────────────────────────────────────────────────
        frame_errors: set[str] = set()
        feedback      = "Good form! Keep going 💪"
        feedback_type = "success"

        if elbow_shift > SWING_THRESHOLD:
            frame_errors.add("arm swing")
            feedback      = "ARM SWING: Keep elbow fixed!"
            feedback_type = "warning"
        elif self.stage == "down" and angle < DOWN_THRESHOLD - 10:
            frame_errors.add("incomplete extension")
            feedback      = "Extend your arm fully!"
            feedback_type = "warning"
        elif self.stage == "up" and angle > UP_THRESHOLD + 10:
            frame_errors.add("incomplete curl")
            feedback      = "Curl your arm fully!"
            feedback_type = "warning"

        # Stabilise: only count errors held for BAD_FORM_THRESHOLD frames
        if frame_errors:
            self._bad_form_frames += 1
        else:
            self._bad_form_frames = 0

        if self._bad_form_frames > BAD_FORM_THRESHOLD:
            self._rep_has_error = True
            self.form_errors.update(frame_errors)

        # ── Rep state-machine ────────────────────────────────────────────────
        rep_completed = False

        if angle < UP_THRESHOLD + TOLERANCE and self.stage == "down":
            self.stage = "up"

        elif angle > DOWN_THRESHOLD - TOLERANCE and self.stage == "up":
            self.counter += 1
            rep_completed = True
            if self._rep_has_error:
                self.incorrect_reps += 1
                feedback      = "Rep counted (form issues noted)"
                feedback_type = "error"
            else:
                self.correct_reps += 1
                feedback      = "✅ Great rep!"
                feedback_type = "success"

            self._rep_has_error   = False
            self._bad_form_frames = 0
            self.stage = "down"

        return {
            **self._base_result(detected=True,
                                feedback=feedback,
                                feedback_type=feedback_type),
            "landmarks":     landmark_list(results.pose_landmarks),
            "angles": {
                "left_elbow":  round(angle, 1),
                "right_elbow": 0.0,
                "right_knee":  0.0,
                "right_hip":   0.0,
                "left_hip":    0.0,
            },
            "primary_angle": round(angle, 1),
            "stage":         self.stage,
            "rep_completed": rep_completed,
        }

    def close(self):
        self._pose.close()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _base_result(self, *, detected: bool, feedback: str, feedback_type: str) -> dict:
        return {
            "detected":      detected,
            "landmarks":     None,
            "angles":        {"left_elbow": 0, "right_elbow": 0,
                              "right_knee": 0, "right_hip": 0, "left_hip": 0},
            "primary_angle": 0.0,
            "stage":         self.stage,
            "counter":       self.counter,
            "correct_reps":  self.correct_reps,
            "incorrect_reps": self.incorrect_reps,
            "accuracy":      accuracy(self.correct_reps, self.incorrect_reps),
            "reps_target":   self.reps_target,
            "rep_completed": False,
            "target_reached": self.counter >= self.reps_target,
            "feedback":      feedback,
            "feedback_type": feedback_type,
            "form_errors":   list(self.form_errors),
            "exercise_name": "bicep_curl",
            "weight":        self.weight,
            "error":         None,
        }
