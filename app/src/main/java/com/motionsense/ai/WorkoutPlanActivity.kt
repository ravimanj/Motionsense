package com.motionsense.ai

import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.motionsense.ai.databinding.ActivityWorkoutPlanBinding
import com.motionsense.ai.network.RetrofitClient
import com.motionsense.ai.network.WorkoutPlanUpdate
import kotlinx.coroutines.launch

class WorkoutPlanActivity : AppCompatActivity() {

    private lateinit var binding: ActivityWorkoutPlanBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityWorkoutPlanBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.btnBack.setOnClickListener { finish() }

        binding.btnSavePlan.setOnClickListener {
            savePlan()
        }
    }

    private fun savePlan() {
        val bicep = binding.etBicepCurl.text.toString().toIntOrNull() ?: 0
        val squat = binding.etSquat.text.toString().toIntOrNull() ?: 0
        val pushUp = binding.etPushUp.text.toString().toIntOrNull() ?: 0
        val shoulder = binding.etShoulderPress.text.toString().toIntOrNull() ?: 0

        binding.progressBar.visibility = View.VISIBLE
        binding.btnSavePlan.isEnabled = false

        lifecycleScope.launch {
            try {
                val req = WorkoutPlanUpdate(bicep, squat, pushUp, shoulder)
                RetrofitClient.api.updateWorkoutPlan(req)
                Toast.makeText(this@WorkoutPlanActivity, "Plan updated!", Toast.LENGTH_SHORT).show()
                finish()
            } catch (e: Exception) {
                Toast.makeText(this@WorkoutPlanActivity, "Error saving plan", Toast.LENGTH_SHORT).show()
            } finally {
                binding.progressBar.visibility = View.GONE
                binding.btnSavePlan.isEnabled = true
            }
        }
    }
}
