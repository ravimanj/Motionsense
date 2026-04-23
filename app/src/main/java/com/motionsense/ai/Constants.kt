package com.motionsense.ai

object Constants {
    // ─── Backend URL ─────────────────────────────────────────────────────────────
    // Replace with your actual Render.com backend URL (no trailing slash)
    const val BACKEND_HOST = "motionsense.onrender.com"
    const val WS_BASE_URL  = "wss://$BACKEND_HOST"

    // ─── Exercise keys ───────────────────────────────────────────────────────────
    const val EXERCISE_BICEP_CURL     = "bicep_curl"
    const val EXERCISE_PUSH_UP        = "push_up"
    const val EXERCISE_SQUAT          = "squat"
    const val EXERCISE_SHOULDER_PRESS = "shoulder_press"

    // ─── Intent extras ───────────────────────────────────────────────────────────
    const val EXTRA_EXERCISE_KEY    = "exercise_key"
    const val EXTRA_EXERCISE_NAME   = "exercise_name"
    const val EXTRA_MUSCLES         = "muscles"
    const val EXTRA_TARGET_REPS     = "target_reps"
    const val EXTRA_WEIGHT          = "weight"
    const val EXTRA_COUNTER         = "counter"
    const val EXTRA_CORRECT_REPS    = "correct_reps"
    const val EXTRA_INCORRECT_REPS  = "incorrect_reps"
    const val EXTRA_ACCURACY        = "accuracy"
    const val EXTRA_FORM_ERRORS     = "form_errors"

    // ─── Frame streaming ─────────────────────────────────────────────────────────
    const val FRAME_INTERVAL_MS = 100L
    const val JPEG_QUALITY      = 65
}
