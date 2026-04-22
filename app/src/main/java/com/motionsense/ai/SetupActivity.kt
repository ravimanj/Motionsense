package com.motionsense.ai

import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.view.Gravity
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.motionsense.ai.databinding.ActivitySetupBinding
import com.motionsense.ai.model.ExerciseRepository
import com.motionsense.ai.utils.CalorieCalculator

class SetupActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySetupBinding

    private val repOptions    = listOf(5, 10, 15, 20, 25, 30)
    private val weightOptions = listOf(0, 5, 10, 15, 20, 25)

    private var selectedReps   = 10
    private var selectedWeight = 0

    private lateinit var exerciseKey:  String
    private lateinit var exerciseName: String
    private lateinit var muscles:      String

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySetupBinding.inflate(layoutInflater)
        setContentView(binding.root)

        exerciseKey  = intent.getStringExtra(Constants.EXTRA_EXERCISE_KEY)  ?: "bicep_curl"
        exerciseName = intent.getStringExtra(Constants.EXTRA_EXERCISE_NAME) ?: "Bicep Curl"
        muscles      = intent.getStringExtra(Constants.EXTRA_MUSCLES)       ?: ""

        binding.tvExerciseName.text = exerciseName
        binding.btnBack.setOnClickListener { finish() }

        buildChips(binding.repsChipGroup, repOptions, selectedReps) { v ->
            selectedReps = v
            updatePreview()
        }
        buildChips(binding.weightChipGroup, weightOptions, selectedWeight) { v ->
            selectedWeight = v
            updatePreview()
        }

        updatePreview()

        binding.btnStartSession.setOnClickListener {
            val intent = Intent(this, LiveTrackerActivity::class.java).apply {
                putExtra(Constants.EXTRA_EXERCISE_KEY,  exerciseKey)
                putExtra(Constants.EXTRA_EXERCISE_NAME, exerciseName)
                putExtra(Constants.EXTRA_MUSCLES,       muscles)
                putExtra(Constants.EXTRA_TARGET_REPS,   selectedReps)
                putExtra(Constants.EXTRA_WEIGHT,        selectedWeight.toDouble())
            }
            startActivity(intent)
            overridePendingTransition(android.R.anim.slide_in_left, android.R.anim.slide_out_right)
        }
    }

    private fun buildChips(
        container: LinearLayout,
        options: List<Int>,
        defaultVal: Int,
        onSelect: (Int) -> Unit
    ) {
        container.removeAllViews()
        val chipViews = mutableListOf<TextView>()

        for (opt in options) {
            val chip = TextView(this).apply {
                text    = if (opt == 0) "BW" else opt.toString()
                gravity = Gravity.CENTER
                val dp8  = (8 * resources.displayMetrics.density).toInt()
                val dp40 = (40 * resources.displayMetrics.density).toInt()
                val dp60 = (60 * resources.displayMetrics.density).toInt()
                setPadding(dp8, 0, dp8, 0)
                minWidth = dp60
                height   = dp40
                textSize = 14f
                setTextColor(if (opt == defaultVal) Color.BLACK else Color.parseColor("#B0B0B0"))
                background = if (opt == defaultVal)
                    getDrawable(R.drawable.bg_chip_selected)
                else
                    getDrawable(R.drawable.bg_chip_unselected)

                val params = LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.WRAP_CONTENT,
                    (40 * resources.displayMetrics.density).toInt()
                ).apply { setMargins((6 * resources.displayMetrics.density).toInt(), 0,
                    (6 * resources.displayMetrics.density).toInt(), 0) }
                layoutParams = params
            }

            chip.setOnClickListener {
                chipViews.forEach { c ->
                    c.background = getDrawable(R.drawable.bg_chip_unselected)
                    c.setTextColor(Color.parseColor("#B0B0B0"))
                }
                chip.background = getDrawable(R.drawable.bg_chip_selected)
                chip.setTextColor(Color.BLACK)
                onSelect(opt)
            }

            chipViews.add(chip)
            container.addView(chip)
        }
    }

    private fun updatePreview() {
        binding.tvPreviewReps.text   = selectedReps.toString()
        binding.tvPreviewWeight.text = selectedWeight.toString()
        val calories = CalorieCalculator.calculate(exerciseKey, selectedReps, 70.0)
        binding.tvPreviewCalories.text = "~${CalorieCalculator.format(calories)}"
    }
}
