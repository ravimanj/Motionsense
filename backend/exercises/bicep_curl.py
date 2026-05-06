"""Bicep Curl tracker — dual-arm detection, improved thresholds."""
import cv2

from .base import make_pose, calculate_angle, landmark_list, accuracy, visible

import mediapipe as mp
mp_pose = mp.solutions.pose
PL = mp_pose.PoseLandmark

# ── Angle thresholds ──────────────────────────────────────────────────────────
# Widened vs original (160/40) to be more forgiving of oblique camera angles
DOWN_THRESHOLD = 155   # arm straight / extended  (rep "down" position)
UP_THRESHOLD   = 50    # arm fully curled          (rep "up"   position)
TOLERANCE      = 12    # angle tolerance for phase transitions

SWING_THRESHOLD    = 0.08  # max horizontal elbow drift (normalized coords)
BAD_FORM_THRESHOLD = 6     # consecutive bad frames before flagging (at ~7 FPS → ~0.9 s)


class BicepCurlTracker:
    def __init__(self, reps_target: int = 10, weight: float = 0.0):
        self.reps_target = reps_target
        self.weight      = weight

        self.counter        = 0
        self.correct_reps   = 0
        self.incorrect_reps = 0
        self.form_errors    = set()
        self.stage          = "down"   # "down" = arm extended, "up" = arm curled

        self._rep_has_error   = False
        self._bad_form_frames = 0

        # Single shared Pose instance with tuned settings (see base.make_pose)
        self._pose = make_pose()

    # ── Public API ────────────────────────────────────────────────────────────
    def process_frame(self, frame) -> dict:
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._pose.process(img_rgb)

        if not results.pose_landmarks:
            return self._base_result(detected=False,
                                     feedback="⚠ No person detected — step back or improve lighting",
                                     feedback_type="warning")

        lm = results.pose_landmarks.landmark

        # ── Pick best visible arm (or average both) ───────────────────────────
        left_vis  = (lm[PL.LEFT_SHOULDER].visibility + lm[PL.LEFT_ELBOW].visibility + lm[PL.LEFT_WRIST].visibility) / 3
        right_vis = (lm[PL.RIGHT_SHOULDER].visibility + lm[PL.RIGHT_ELBOW].visibility + lm[PL.RIGHT_WRIST].visibility) / 3

        angles = []
        elbow_shifts = []

        if left_vis >= 0.4:
            l_shoulder = [lm[PL.LEFT_SHOULDER].x,  lm[PL.LEFT_SHOULDER].y]
            l_elbow    = [lm[PL.LEFT_ELBOW].x,     lm[PL.LEFT_ELBOW].y]
            l_wrist    = [lm[PL.LEFT_WRIST].x,     lm[PL.LEFT_WRIST].y]
            angles.append(calculate_angle(l_shoulder, l_elbow, l_wrist))
            elbow_shifts.append(abs(l_elbow[0] - l_shoulder[0]))

        if right_vis >= 0.4:
            r_shoulder = [lm[PL.RIGHT_SHOULDER].x, lm[PL.RIGHT_SHOULDER].y]
            r_elbow    = [lm[PL.RIGHT_ELBOW].x,    lm[PL.RIGHT_ELBOW].y]
            r_wrist    = [lm[PL.RIGHT_WRIST].x,    lm[PL.RIGHT_WRIST].y]
            angles.append(calculate_angle(r_shoulder, r_elbow, r_wrist))
            elbow_shifts.append(abs(r_elbow[0] - r_shoulder[0]))

        if not angles:
            return self._base_result(detected=False,
                                     feedback="⚠ Arms not visible — face camera sideways",
                                     feedback_type="warning")

        # Average across visible arms
        angle       = sum(angles) / len(angles)
        elbow_shift = sum(elbow_shifts) / len(elbow_shifts)

        # ── Form checks ───────────────────────────────────────────────────────
        frame_errors: set[str] = set()
        feedback      = "Good form! Keep going 💪"
        feedback_type = "success"

        if elbow_shift > SWING_THRESHOLD:
            frame_errors.add("arm swing")
            feedback      = "ARM SWING: Keep elbow fixed at your side!"
            feedback_type = "warning"
        elif self.stage == "down" and angle < DOWN_THRESHOLD - 10:
            frame_errors.add("incomplete extension")
            feedback      = "Extend your arm fully at the bottom!"
            feedback_type = "warning"
        elif self.stage == "up" and angle > UP_THRESHOLD + 10:
            frame_errors.add("incomplete curl")
            feedback      = "Curl your arm fully — squeeze the bicep!"
            feedback_type = "warning"

        # Stabilise: only flag errors held for BAD_FORM_THRESHOLD consecutive frames
        if frame_errors:
            self._bad_form_frames += 1
        else:
            self._bad_form_frames = 0

        if self._bad_form_frames >= BAD_FORM_THRESHOLD:
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
                feedback      = "Rep counted — work on your form!"
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
                "left_elbow":  round(angles[0] if left_vis >= 0.4 else 0.0, 1),
                "right_elbow": round(angles[-1] if right_vis >= 0.4 else 0.0, 1),
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
            "exercise_name":  "bicep_curl",
            "weight":         self.weight,
            "error":          None,
        }
