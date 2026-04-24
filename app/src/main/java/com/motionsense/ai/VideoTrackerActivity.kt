package com.motionsense.ai

import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.SurfaceTexture
import android.media.MediaPlayer
import android.net.Uri
import android.os.Bundle
import android.util.Base64
import android.util.Log
import android.view.Surface
import android.view.TextureView
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.google.gson.Gson
import com.motionsense.ai.databinding.ActivityVideoTrackerBinding
import com.motionsense.ai.model.FrameResult
import com.motionsense.ai.network.SocketEventListener
import com.motionsense.ai.network.WebSocketManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import java.io.ByteArrayOutputStream

class VideoTrackerActivity : AppCompatActivity() {

    private lateinit var binding: ActivityVideoTrackerBinding
    private val TAG = "VideoTracker"

    private var mediaPlayer: MediaPlayer? = null
    private var videoUri: Uri? = null

    // WebSocket
    private var wsManager: WebSocketManager? = null

    // Session state
    private var exerciseKey  = "bicep_curl"
    private var exerciseName = "Bicep Curl"
    private var muscles      = ""
    private var targetReps   = 10
    private var weight       = 0.0

    // Tracked metrics (for summary)
    private var currentCounter  = 0
    private var correctReps     = 0
    private var incorrectReps   = 0
    private var accuracy        = 0
    private val formErrors      = mutableSetOf<String>()

    private val gson = Gson()
    private var frameJob: Job? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityVideoTrackerBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Read intent extras
        exerciseKey  = intent.getStringExtra(Constants.EXTRA_EXERCISE_KEY)  ?: "bicep_curl"
        exerciseName = intent.getStringExtra(Constants.EXTRA_EXERCISE_NAME) ?: "Bicep Curl"
        muscles      = intent.getStringExtra(Constants.EXTRA_MUSCLES)       ?: ""
        targetReps   = intent.getIntExtra(Constants.EXTRA_TARGET_REPS, 10)
        weight       = intent.getDoubleExtra(Constants.EXTRA_WEIGHT, 0.0)
        
        val uriString = intent.getStringExtra("EXTRA_VIDEO_URI")
        if (uriString != null) {
            videoUri = Uri.parse(uriString)
        } else {
            finish()
            return
        }

        setupUI()
        connectWebSocket()
        setupVideoPlayer()
    }

    private fun setupUI() {
        binding.tvExerciseName.text   = exerciseName
        binding.tvTargetLabel.text    = "/ $targetReps REPS"
        binding.progressBar.max       = targetReps
        binding.tvCounter.text        = "0"
        binding.tvStage.text          = "READY"
        binding.tvConnectionStatus.text = "● Connecting…"
        binding.tvConnectionStatus.setTextColor(Color.parseColor("#FFB300"))

        binding.btnStop.setOnClickListener {
            stopSession()
        }

        // We do not observe BLE Heart Rate here since it's a pre-recorded video
    }

    private fun setupVideoPlayer() {
        binding.textureView.surfaceTextureListener = object : TextureView.SurfaceTextureListener {
            override fun onSurfaceTextureAvailable(surfaceTexture: SurfaceTexture, width: Int, height: Int) {
                val surface = Surface(surfaceTexture)
                try {
                    mediaPlayer = MediaPlayer().apply {
                        setDataSource(this@VideoTrackerActivity, videoUri!!)
                        setSurface(surface)
                        setOnPreparedListener {
                            it.start()
                            startFrameExtraction()
                        }
                        setOnCompletionListener {
                            stopSession()
                        }
                        prepareAsync()
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Failed to start media player", e)
                }
            }

            override fun onSurfaceTextureSizeChanged(surface: SurfaceTexture, width: Int, height: Int) {}
            override fun onSurfaceTextureDestroyed(surface: SurfaceTexture): Boolean = true
            override fun onSurfaceTextureUpdated(surface: SurfaceTexture) {}
        }
    }

    private fun startFrameExtraction() {
        frameJob = lifecycleScope.launch(Dispatchers.IO) {
            while (isActive && mediaPlayer?.isPlaying == true) {
                if (wsManager?.connected() == true) {
                    try {
                        val bitmap = binding.textureView.bitmap
                        if (bitmap != null) {
                            // Scale down if needed to save bandwidth
                            val out = ByteArrayOutputStream()
                            bitmap.compress(Bitmap.CompressFormat.JPEG, Constants.JPEG_QUALITY, out)
                            val b64 = Base64.encodeToString(out.toByteArray(), Base64.NO_WRAP)
                            
                            // Send to WebSocket
                            wsManager?.send("""{"frame":"$b64"}""")
                            bitmap.recycle()
                        }
                    } catch (e: Exception) {
                        Log.e(TAG, "Frame extraction error", e)
                    }
                }
                // Throttle to roughly 10 FPS
                delay(Constants.FRAME_INTERVAL_MS)
            }
        }
    }

    private fun connectWebSocket() {
        wsManager = WebSocketManager(
            exercise = exerciseKey,
            reps     = targetReps,
            weight   = weight,
            listener = object : SocketEventListener {
                override fun onConnected() {
                    runOnUiThread {
                        binding.tvConnectionStatus.text = "● LIVE"
                        binding.tvConnectionStatus.setTextColor(Color.parseColor("#00E676"))
                        binding.tvFeedback.text = "Analyzing video... \uD83E\uDD16"
                        binding.tvFeedback.setBackgroundColor(Color.parseColor("#1B5E20"))
                    }
                }

                override fun onMessageReceived(message: String) {
                    handleFrameResult(message)
                }

                override fun onReconnecting(attempt: Int, delayMs: Long) {
                    runOnUiThread {
                        binding.tvConnectionStatus.text = "● Reconnecting…"
                        binding.tvConnectionStatus.setTextColor(Color.parseColor("#FFB300"))
                    }
                }

                override fun onError(error: String) {
                    runOnUiThread {
                        binding.tvConnectionStatus.text = "● Offline"
                        binding.tvConnectionStatus.setTextColor(Color.parseColor("#FF1744"))
                    }
                }

                override fun onDisconnected() {
                    runOnUiThread {
                        binding.tvConnectionStatus.text = "● Offline"
                        binding.tvConnectionStatus.setTextColor(Color.parseColor("#9E9E9E"))
                    }
                }
            }
        )
        wsManager?.connect()
    }

    private fun handleFrameResult(json: String) {
        try {
            val result = gson.fromJson(json, FrameResult::class.java)

            // Check for server-side error field
            if (!result.error.isNullOrEmpty()) {
                runOnUiThread {
                    binding.tvFeedback.text = "Server: ${result.error}"
                    binding.tvFeedback.setBackgroundColor(Color.parseColor("#B71C1C"))
                }
                return
            }

            runOnUiThread {
                if (!result.detected) {
                    binding.tvFeedback.text = "⚠ No person detected in frame"
                    binding.tvFeedback.setBackgroundColor(Color.parseColor("#E65100"))
                    binding.skeletonOverlay.clearLandmarks()
                    return@runOnUiThread
                }

                // Update tracked state
                currentCounter = result.counter
                correctReps    = result.correct_reps
                incorrectReps  = result.incorrect_reps
                accuracy       = result.accuracy
                result.form_errors?.let { formErrors.addAll(it) }

                // Counter + progress
                binding.tvCounter.text       = result.counter.toString()
                binding.tvTargetLabel.text   = "/ $targetReps REPS"
                binding.progressBar.progress = result.counter

                // Stage pill
                val stageTxt = result.stage?.uppercase() ?: "—"
                binding.tvStage.text = stageTxt
                when (result.stage?.lowercase()) {
                    "up"   -> binding.tvStage.setBackgroundResource(R.drawable.bg_pill_green)
                    "down" -> binding.tvStage.setBackgroundResource(R.drawable.bg_pill_purple)
                    else   -> binding.tvStage.setBackgroundResource(R.drawable.bg_pill_green)
                }

                // Metric cards
                binding.tvCorrectReps.text   = result.correct_reps.toString()
                binding.tvIncorrectReps.text = result.incorrect_reps.toString()
                binding.tvAccuracy.text      = "${result.accuracy}%"
                binding.tvAngle.text         = "${result.primary_angle.toInt()}°"

                // Feedback bar
                val feedbackMsg = result.feedback ?: "Analyzing..."
                binding.tvFeedback.text = feedbackMsg
                val bgColor = when (result.feedback_type) {
                    "warning" -> Color.parseColor("#E65100")
                    "error"   -> Color.parseColor("#B71C1C")
                    else      -> Color.parseColor("#1B5E20")
                }
                binding.tvFeedback.setBackgroundColor(bgColor)

                // Skeleton overlay
                result.landmarks?.let { binding.skeletonOverlay.updateLandmarks(it) }

                // Navigate to summary when target reached
                if (result.target_reached) {
                    stopSession()
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "JSON parse error: ${e.message}")
        }
    }

    private fun stopSession() {
        frameJob?.cancel()
        mediaPlayer?.release()
        mediaPlayer = null
        wsManager?.disconnect()
        navigateToSummary()
    }

    private fun navigateToSummary() {
        val intent = Intent(this, SessionSummaryActivity::class.java).apply {
            putExtra(Constants.EXTRA_EXERCISE_KEY,   exerciseKey)
            putExtra(Constants.EXTRA_EXERCISE_NAME,  exerciseName)
            putExtra(Constants.EXTRA_MUSCLES,        muscles)
            putExtra(Constants.EXTRA_TARGET_REPS,    targetReps)
            putExtra(Constants.EXTRA_WEIGHT,         weight)
            putExtra(Constants.EXTRA_COUNTER,        currentCounter)
            putExtra(Constants.EXTRA_CORRECT_REPS,   correctReps)
            putExtra(Constants.EXTRA_INCORRECT_REPS, incorrectReps)
            putExtra(Constants.EXTRA_ACCURACY,       accuracy)
            putStringArrayListExtra(Constants.EXTRA_FORM_ERRORS, ArrayList(formErrors))
        }
        startActivity(intent)
        finish()
    }

    override fun onDestroy() {
        super.onDestroy()
        frameJob?.cancel()
        mediaPlayer?.release()
        wsManager?.disconnect()
    }
}
