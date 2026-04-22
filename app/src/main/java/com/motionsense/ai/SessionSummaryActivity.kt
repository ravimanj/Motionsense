package com.motionsense.ai

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.motionsense.ai.databinding.ActivitySessionSummaryBinding
import com.motionsense.ai.utils.CalorieCalculator

class SessionSummaryActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySessionSummaryBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySessionSummaryBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Read data from intent
        val exerciseKey  = intent.getStringExtra(Constants.EXTRA_EXERCISE_KEY)  ?: "bicep_curl"
        val exerciseName = intent.getStringExtra(Constants.EXTRA_EXERCISE_NAME) ?: "Exercise"
        val muscles      = intent.getStringExtra(Constants.EXTRA_MUSCLES)       ?: "—"
        val targetReps   = intent.getIntExtra(Constants.EXTRA_TARGET_REPS, 10)
        val counter      = intent.getIntExtra(Constants.EXTRA_COUNTER, 0)
        val correctReps  = intent.getIntExtra(Constants.EXTRA_CORRECT_REPS, 0)
        val incorrectReps= intent.getIntExtra(Constants.EXTRA_INCORRECT_REPS, 0)
        val accuracy     = intent.getIntExtra(Constants.EXTRA_ACCURACY, 0)
        val weight       = intent.getDoubleExtra(Constants.EXTRA_WEIGHT, 70.0)
        val formErrors   = intent.getStringArrayListExtra(Constants.EXTRA_FORM_ERRORS) ?: arrayListOf()

        // Calculate calories and time
        val bodyWeight = if (weight > 0) weight else 70.0
        val calories   = CalorieCalculator.calculate(exerciseKey, counter, bodyWeight)
        val timeStr    = CalorieCalculator.formatTime(counter)

        // Populate UI
        binding.tvExerciseName.text  = "$exerciseName · Session Complete"
        binding.tvBigReps.text       = counter.toString()
        binding.tvTotalReps.text     = "$counter / $targetReps"
        binding.tvCorrectReps.text   = correctReps.toString()
        binding.tvIncorrectReps.text = incorrectReps.toString()
        binding.tvAccuracy.text      = "$accuracy%"
        binding.tvCalories.text      = CalorieCalculator.format(calories)
        binding.tvTime.text          = timeStr
        binding.tvMuscles.text       = muscles

        // Form errors
        if (formErrors.isEmpty()) {
            binding.tvFormErrors.text = "✅ Perfect Form — No errors!"
        } else {
            val errorText = formErrors.joinToString("\n") { "⚠️ ${it.replaceFirstChar { c -> c.uppercase() }}" }
            binding.tvFormErrors.text = errorText
        }

        // Buttons
        binding.btnAnotherSet.setOnClickListener {
            // Go back to Setup with same exercise
            val intent = Intent(this, SetupActivity::class.java).apply {
                putExtra(Constants.EXTRA_EXERCISE_KEY,  exerciseKey)
                putExtra(Constants.EXTRA_EXERCISE_NAME, exerciseName)
                putExtra(Constants.EXTRA_MUSCLES,       muscles)
            }
            startActivity(intent)
            finish()
        }

        binding.btnBackToHome.setOnClickListener {
            // Go all the way back to Exercise Select
            val intent = Intent(this, ExerciseSelectActivity::class.java)
            intent.flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
            startActivity(intent)
            finish()
        }
    }
}
