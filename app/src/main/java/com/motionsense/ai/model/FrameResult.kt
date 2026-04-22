package com.motionsense.ai.model

data class Landmark(
    val x: Float = 0f,
    val y: Float = 0f,
    val z: Float = 0f,
    val visibility: Float = 0f
)

data class Angles(
    val left_elbow: Float  = 0f,
    val right_elbow: Float = 0f,
    val right_knee: Float  = 0f,
    val right_hip: Float   = 0f,
    val left_hip: Float    = 0f
)

data class FrameResult(
    val detected: Boolean        = false,
    val landmarks: List<Landmark>? = null,
    val angles: Angles?          = null,
    val primary_angle: Float     = 0f,
    val stage: String?           = null,
    val counter: Int             = 0,
    val correct_reps: Int        = 0,
    val incorrect_reps: Int      = 0,
    val accuracy: Int            = 0,
    val reps_target: Int         = 10,
    val rep_completed: Boolean   = false,
    val target_reached: Boolean  = false,
    val feedback: String?        = null,
    val feedback_type: String?   = null,
    val form_errors: List<String>? = null,
    val exercise_name: String?   = null,
    val weight: Float            = 0f,
    val error: String?           = null
)
