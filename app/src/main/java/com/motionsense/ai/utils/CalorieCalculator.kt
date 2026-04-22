package com.motionsense.ai.utils

object CalorieCalculator {

    private val metValues = mapOf(
        "bicep_curl"     to 4.0,
        "push_up"        to 5.0,
        "squat"          to 5.0,
        "shoulder_press" to 4.0
    )

    /**
     * Calculates estimated calories burned using MET formula:
     *   Calories = MET × bodyWeight(kg) × time(hours)
     * Time is estimated at 4 seconds per rep.
     */
    fun calculate(
        exerciseKey: String,
        totalReps: Int,
        bodyWeightKg: Double = 70.0
    ): Double {
        val met = metValues[exerciseKey] ?: 4.0
        val timeHours = (totalReps * 4.0) / 3600.0
        return met * bodyWeightKg * timeHours
    }

    /** Format rep count → estimated time string (e.g., "40s", "1m 20s") */
    fun formatTime(totalReps: Int): String {
        val seconds = totalReps * 4
        return if (seconds < 60) "${seconds}s"
        else "${seconds / 60}m ${seconds % 60}s"
    }

    /** Format calorie value to 1 decimal place */
    fun format(calories: Double): String = "%.1f".format(calories)
}
