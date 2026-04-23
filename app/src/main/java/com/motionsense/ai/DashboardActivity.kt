package com.motionsense.ai

import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.motionsense.ai.databinding.ActivityDashboardBinding
import com.motionsense.ai.network.DailyLogToggle
import com.motionsense.ai.network.RetrofitClient
import com.motionsense.ai.network.SessionResponse
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

class DashboardActivity : AppCompatActivity() {

    private lateinit var binding: ActivityDashboardBinding
    private val historyList = mutableListOf<SessionResponse>()
    private lateinit var adapter: HistoryAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDashboardBinding.inflate(layoutInflater)
        setContentView(binding.root)

        RetrofitClient.init(this)
        if (RetrofitClient.getToken() == null) {
            startActivity(Intent(this, SplashActivity::class.java))
            finish()
            return
        }

        setupRecyclerView()
        loadDashboardData()

        binding.btnLogout.setOnClickListener {
            RetrofitClient.clearToken()
            startActivity(Intent(this, SplashActivity::class.java))
            finish()
        }

        binding.btnNewSession.setOnClickListener {
            startActivity(Intent(this, ExerciseSelectActivity::class.java))
        }

        binding.btnEditPlan.setOnClickListener {
            startActivity(Intent(this, WorkoutPlanActivity::class.java))
        }
    }

    override fun onResume() {
        super.onResume()
        // Refresh when coming back from an exercise or edit plan
        loadDashboardData()
    }

    private fun setupRecyclerView() {
        adapter = HistoryAdapter(historyList)
        binding.rvHistory.layoutManager = LinearLayoutManager(this)
        binding.rvHistory.adapter = adapter
    }

    private fun loadDashboardData() {
        lifecycleScope.launch {
            try {
                // Load Daily Progress
                val today = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).format(Date())
                val progressData = RetrofitClient.api.getDailyProgress(today)
                
                binding.containerProgressBars.removeAllViews()
                
                if (progressData.progress.isEmpty()) {
                    binding.containerProgressBars.addView(binding.tvEmptyPlan)
                } else {
                    for (item in progressData.progress) {
                        if (item.targetReps > 0) {
                            val itemView = createProgressView(item.exerciseType, item.completedReps, item.targetReps)
                            binding.containerProgressBars.addView(itemView)
                        }
                    }
                    if (binding.containerProgressBars.childCount == 0) {
                        binding.containerProgressBars.addView(binding.tvEmptyPlan)
                    }
                }
                
                // Show celebration popup if completed
                if (progressData.isFullyCompleted) {
                    val prefs = getSharedPreferences("MotionSensePrefs", MODE_PRIVATE)
                    val lastCongrats = prefs.getString("last_congrats_date", "")
                    if (lastCongrats != today) {
                        prefs.edit().putString("last_congrats_date", today).apply()
                        showCongratulatoryPopup()
                    }
                }

                // Load History
                val sessions = RetrofitClient.api.getSessions()
                historyList.clear()
                historyList.addAll(sessions)
                adapter.notifyDataSetChanged()
                
            } catch (e: Exception) {
                // Handle error
            }
        }
    }
    
    private fun createProgressView(type: String, completed: Int, target: Int): View {
        val view = LayoutInflater.from(this).inflate(android.R.layout.simple_list_item_1, binding.containerProgressBars, false)
        val tv = view.findViewById<TextView>(android.R.id.text1)
        tv.setTextColor(resources.getColor(R.color.text_primary, null))
        val typeName = type.replace("_", " ").capitalize()
        val percent = if (target > 0) (completed * 100) / target else 100
        tv.text = "$typeName: $completed / $target ($percent%)"
        return view
    }
    
    private fun showCongratulatoryPopup() {
        androidx.appcompat.app.AlertDialog.Builder(this)
            .setTitle("Target Reached! 🎉")
            .setMessage("Congratulations! You have successfully completed today’s workout. Keep up the great work!")
            .setPositiveButton("Awesome") { dialog, _ -> dialog.dismiss() }
            .show()
    }

    inner class HistoryAdapter(private val sessions: List<SessionResponse>) : 
        RecyclerView.Adapter<HistoryAdapter.ViewHolder>() {

        inner class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
            val tvType: TextView = view.findViewById(android.R.id.text1)
            val tvDetails: TextView = view.findViewById(android.R.id.text2)
        }

        override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
            val view = LayoutInflater.from(parent.context).inflate(android.R.layout.simple_list_item_2, parent, false)
            // Fix text color for dark theme
            view.findViewById<TextView>(android.R.id.text1).setTextColor(resources.getColor(R.color.text_primary, null))
            view.findViewById<TextView>(android.R.id.text2).setTextColor(resources.getColor(R.color.accent_green, null))
            return ViewHolder(view)
        }

        override fun onBindViewHolder(holder: ViewHolder, position: Int) {
            val session = sessions[position]
            holder.tvType.text = session.exerciseType.replace("_", " ").capitalize()
            
            // Format timestamp
            val dateStr = try {
                val parser = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault())
                val formatter = SimpleDateFormat("MMM dd, HH:mm", Locale.getDefault())
                val date = parser.parse(session.timestamp)
                if (date != null) formatter.format(date) else session.timestamp
            } catch (e: Exception) { session.timestamp }
            
            holder.tvDetails.text = "${session.reps} reps · ${session.weight} kg · $dateStr"
        }

        override fun getItemCount() = sessions.size
    }
}
