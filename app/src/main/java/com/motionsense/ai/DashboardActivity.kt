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

        binding.cbDailyGoal.setOnCheckedChangeListener { _, isChecked ->
            lifecycleScope.launch {
                try {
                    val today = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).format(Date())
                    RetrofitClient.api.toggleDailyLog(DailyLogToggle(today, isChecked))
                } catch (e: Exception) {
                    // Revert visually on error
                }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        // Refresh when coming back from an exercise
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
                // Load Daily Checkbox
                val today = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).format(Date())
                val dailyLog = RetrofitClient.api.getDailyLog(today)
                binding.cbDailyGoal.isChecked = dailyLog.completed

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
