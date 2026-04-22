package com.motionsense.ai

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.motionsense.ai.adapter.ExerciseAdapter
import com.motionsense.ai.databinding.ActivityExerciseSelectBinding
import com.motionsense.ai.model.ExerciseConfig
import com.motionsense.ai.model.ExerciseRepository

class ExerciseSelectActivity : AppCompatActivity() {

    private lateinit var binding: ActivityExerciseSelectBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityExerciseSelectBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.btnBack.setOnClickListener { finish() }

        val adapter = ExerciseAdapter(ExerciseRepository.all) { exercise ->
            openSetup(exercise)
        }

        binding.recyclerExercises.apply {
            layoutManager = LinearLayoutManager(this@ExerciseSelectActivity)
            this.adapter = adapter
        }
    }

    private fun openSetup(exercise: ExerciseConfig) {
        val intent = Intent(this, SetupActivity::class.java).apply {
            putExtra(Constants.EXTRA_EXERCISE_KEY, exercise.key)
            putExtra(Constants.EXTRA_EXERCISE_NAME, exercise.name)
            putExtra(Constants.EXTRA_MUSCLES, exercise.muscles)
        }
        startActivity(intent)
        overridePendingTransition(android.R.anim.slide_in_left, android.R.anim.slide_out_right)
    }
}
