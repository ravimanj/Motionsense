"""Push-Up tracker — ported from the desktop app."""
import cv2
import mediapipe as mp

from .base import calculate_angle, landmark_list, accuracy

mp_pose = mp.solutions.pose
PL = mp_pose.PoseLandmark

# ── Default thresholds ────────────────────────────────────────────────────────
DOWN_THRESHOLD      = 160   # elbow angle when arms straight (top position)
UP_THRESHOLD        = 90    # elbow angle when arms bent     (bottom position)
HIP_ANGLE_THRESHOLD = 160   # min hip-shoulder-knee angle (straight back)
TOLERANCE           = 10


class PushUpTracker:
    def __init__(self, reps_target: int = 10, weight: float = 0.0):
        self.reps_target = reps_target
        self.weight      = weight

        self.counter        = 0
        self.correct_reps   = 0
        self.incorrect_reps = 0
        self.form_errors    = set()
        # "down" = arms straight / top of push-up, ready to descend
        # "up"   = arms bent    / bottom of push-up
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
        r_knee     = [lm[PL.RIGHT_KNEE].x,     lm[PL.RIGHT_KNEE].y]

        raw_elbow_angle = calculate_angle(r_shoulder, r_elbow, r_wrist)
        raw_hip_angle   = calculate_angle(r_shoulder, r_hip,   r_knee)

        if not hasattr(self, 'smoothed_elbow'):
            self.smoothed_elbow = raw_elbow_angle
            self.smoothed_hip = raw_hip_angle
        else:
            self.smoothed_elbow = 0.4 * raw_elbow_angle + 0.6 * self.smoothed_elbow
            self.smoothed_hip = 0.4 * raw_hip_angle + 0.6 * self.smoothed_hip
            
        elbow_angle = self.smoothed_elbow
        hip_angle = self.smoothed_hip

        # ── Form checks ───────────────────────────────────────────────────────
        frame_errors: set[str] = set()
        feedback      = "Good form! Keep going 💪"
        feedback_type = "success"

        if hip_angle < HIP_ANGLE_THRESHOLD:
            frame_errors.add("hip sag")
            feedback      = "HIP SAG: Keep your back straight!"
            feedback_type = "error"
        elif self.stage == "down" and elbow_angle < DOWN_THRESHOLD - 10:
            frame_errors.add("incomplete extension")
            feedback      = "INCOMPLETE EXTENSION: Straighten arms fully!"
            feedback_type = "warning"
        elif self.stage == "up" and elbow_angle > UP_THRESHOLD + 10:
            frame_errors.add("incomplete depth")
            feedback      = "INCOMPLETE DEPTH: Go lower!"
            feedback_type = "warning"

        self.form_errors.update(frame_errors)

        # ── Rep state-machine ────────────────────────────────────────────────
        rep_completed = False

        # Transition to bottom (arms bent)
        if elbow_angle < UP_THRESHOLD and self.stage == "down":
            self.stage = "up"
            self.counter += 1
            rep_completed = True
            if frame_errors - {"incomplete extension"}:  # hip sag or depth
                self.incorrect_reps += 1
                feedback      = "Rep counted (form issues noted)"
                feedback_type = "error"
            else:
                self.correct_reps += 1
                feedback      = "✅ Great rep!"
                feedback_type = "success"

        # Transition back to top (arms straight)
        elif elbow_angle > DOWN_THRESHOLD and self.stage == "up":
            self.stage = "down"

        return {
            **self._base_result(detected=True,
                                feedback=feedback,
                                feedback_type=feedback_type),
            "landmarks": landmark_list(results.pose_landmarks),
            "angles": {
                "left_elbow":  0.0,
                "right_elbow": round(elbow_angle, 1),
                "right_knee":  0.0,
                "right_hip":   round(hip_angle, 1),
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
            "exercise_name":  "push_up",
            "weight":         self.weight,
            "error":          None,
        }
