package com.motionsense.ai.adapter

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.motionsense.ai.databinding.ItemExerciseCardBinding
import com.motionsense.ai.model.ExerciseConfig

class ExerciseAdapter(
    private val exercises: List<ExerciseConfig>,
    private val onItemClick: (ExerciseConfig) -> Unit
) : RecyclerView.Adapter<ExerciseAdapter.ExerciseViewHolder>() {

    inner class ExerciseViewHolder(
        private val binding: ItemExerciseCardBinding
    ) : RecyclerView.ViewHolder(binding.root) {

        fun bind(exercise: ExerciseConfig) {
            binding.tvExerciseName.text = exercise.name
            binding.tvMuscles.text = exercise.muscles
            binding.ivExerciseIcon.setImageResource(exercise.iconRes)
            binding.root.setOnClickListener { onItemClick(exercise) }
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ExerciseViewHolder {
        val binding = ItemExerciseCardBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return ExerciseViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ExerciseViewHolder, position: Int) {
        holder.bind(exercises[position])
    }

    override fun getItemCount() = exercises.size
}
