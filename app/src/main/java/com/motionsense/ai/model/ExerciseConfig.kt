package com.motionsense.ai.model

import com.motionsense.ai.R

data class ExerciseConfig(
    val key: String,
    val name: String,
    val muscles: String,
    val iconRes: Int,
    val met: Double
)

object ExerciseRepository {
    val all = listOf(
        ExerciseConfig(
            key     = "bicep_curl",
            name    = "Bicep Curl",
            muscles = "Biceps · Forearms",
            iconRes = R.drawable.ic_bicep_curl,
            met     = 4.0
        ),
        ExerciseConfig(
            key     = "push_up",
            name    = "Push Up",
            muscles = "Chest · Triceps · Shoulders",
            iconRes = R.drawable.ic_push_up,
            met     = 5.0
        ),
        ExerciseConfig(
            key     = "squat",
            name    = "Squat",
            muscles = "Quads · Glutes · Hamstrings",
            iconRes = R.drawable.ic_squat,
            met     = 5.0
        ),
        ExerciseConfig(
            key     = "shoulder_press",
            name    = "Shoulder Press",
            muscles = "Shoulders · Triceps · Core",
            iconRes = R.drawable.ic_shoulder_press,
            met     = 4.0
        )
    )

    fun byKey(key: String) = all.firstOrNull { it.key == key }
}
