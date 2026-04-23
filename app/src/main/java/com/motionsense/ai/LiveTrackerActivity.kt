package com.motionsense.ai

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.Color
import android.os.Bundle
import android.util.Base64
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.google.gson.Gson
import com.motionsense.ai.databinding.ActivityLiveTrackerBinding
import com.motionsense.ai.model.FrameResult
import com.motionsense.ai.network.SocketEventListener
import com.motionsense.ai.network.WebSocketManager
import java.io.ByteArrayOutputStream
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class LiveTrackerActivity : AppCompatActivity() {

    private lateinit var binding: ActivityLiveTrackerBinding
    private val TAG = "LiveTracker"
    private val CAMERA_PERMISSION_CODE = 101

    // Dedicated background executor for image analysis (never block the main thread)
    private lateinit var cameraExecutor: ExecutorService

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

    // Frame throttle
    private var lastFrameTime = 0L
    private val gson = Gson()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLiveTrackerBinding.inflate(layoutInflater)
        setContentView(binding.root)

        cameraExecutor = Executors.newSingleThreadExecutor()

        // Read intent extras
        exerciseKey  = intent.getStringExtra(Constants.EXTRA_EXERCISE_KEY)  ?: "bicep_curl"
        exerciseName = intent.getStringExtra(Constants.EXTRA_EXERCISE_NAME) ?: "Bicep Curl"
        muscles      = intent.getStringExtra(Constants.EXTRA_MUSCLES)       ?: ""
        targetReps   = intent.getIntExtra(Constants.EXTRA_TARGET_REPS, 10)
        weight       = intent.getDoubleExtra(Constants.EXTRA_WEIGHT, 0.0)

        setupUI()
        connectWebSocket()

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
            == PackageManager.PERMISSION_GRANTED) {
            startCamera()
        } else {
            ActivityCompat.requestPermissions(
                this, arrayOf(Manifest.permission.CAMERA), CAMERA_PERMISSION_CODE
            )
        }
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
            wsManager?.disconnect()
            navigateToSummary()
        }

        // Observe BLE Heart Rate
        androidx.lifecycle.lifecycleScope.launchWhenStarted {
            com.motionsense.ai.network.BleHeartRateManager.getInstance(this@LiveTrackerActivity).bpm.collect { bpm ->
                binding.tvBpm.text = if (bpm > 0) bpm.toString() else "--"
                binding.tvBpm.setTextColor(
                    if (bpm > 0) Color.parseColor("#FF1744") else Color.parseColor("#9E9E9E")
                )
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
                        binding.tvFeedback.text = "Start exercising! 💪"
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
                        binding.tvFeedback.text = "⏳ Connection lost — retrying ($attempt/4) in ${delayMs / 1000}s…"
                        binding.tvFeedback.setBackgroundColor(Color.parseColor("#E65100"))
                    }
                }

                override fun onError(error: String) {
                    Log.e(TAG, "WS error: $error")
                    runOnUiThread {
                        binding.tvConnectionStatus.text = "● Offline"
                        binding.tvConnectionStatus.setTextColor(Color.parseColor("#FF1744"))
                        binding.tvFeedback.text = "⚠ Cannot reach server. Check your connection."
                        binding.tvFeedback.setBackgroundColor(Color.parseColor("#B71C1C"))
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
                Log.e(TAG, "Server error: ${result.error}")
                runOnUiThread {
                    binding.tvFeedback.text = "Server: ${result.error}"
                    binding.tvFeedback.setBackgroundColor(Color.parseColor("#B71C1C"))
                }
                return
            }

            runOnUiThread {
                if (!result.detected) {
                    binding.tvFeedback.text = "⚠ No person detected — adjust camera"
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
                val feedbackMsg = result.feedback ?: "Keep going! 💪"
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
                    wsManager?.disconnect()
                    navigateToSummary()
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "JSON parse error: ${e.message} | raw: $json")
        }
    }

    private fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)
        cameraProviderFuture.addListener({
            val cameraProvider = cameraProviderFuture.get()

            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(binding.previewView.surfaceProvider)
            }

            val imageAnalyzer = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_RGBA_8888)
                .build()
                .also { analysis ->
                    // Use dedicated background executor — NEVER the main executor
                    analysis.setAnalyzer(cameraExecutor) { imageProxy ->
                        processFrame(imageProxy)
                    }
                }

            try {
                cameraProvider.unbindAll()
                cameraProvider.bindToLifecycle(
                    this,
                    CameraSelector.DEFAULT_FRONT_CAMERA,
                    preview,
                    imageAnalyzer
                )
            } catch (e: Exception) {
                Log.e(TAG, "Camera bind failed: ${e.message}")
            }
        }, ContextCompat.getMainExecutor(this))
    }

    private fun processFrame(imageProxy: androidx.camera.core.ImageProxy) {
        val now = System.currentTimeMillis()
        // Throttle + only send if WS is actually open
        if (now - lastFrameTime < Constants.FRAME_INTERVAL_MS || wsManager?.connected() != true) {
            imageProxy.close()
            return
        }
        lastFrameTime = now

        try {
            // Read rotation BEFORE closing the proxy
            val rotationDegrees = imageProxy.imageInfo.rotationDegrees
            val bitmap: Bitmap = imageProxy.toBitmap()
            imageProxy.close()

            // toBitmap() does NOT apply CameraX rotation metadata.
            // On a portrait phone the front camera delivers frames rotated 90°,
            // which makes MediaPipe see a sideways person → no detection, no reps.
            val upright: Bitmap = if (rotationDegrees != 0) {
                val matrix = android.graphics.Matrix().apply {
                    postRotate(rotationDegrees.toFloat())
                }
                Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, matrix, true)
                    .also { if (it !== bitmap) bitmap.recycle() }
            } else {
                bitmap
            }

            val out = ByteArrayOutputStream()
            upright.compress(Bitmap.CompressFormat.JPEG, Constants.JPEG_QUALITY, out)
            val b64 = Base64.encodeToString(out.toByteArray(), Base64.NO_WRAP)
            upright.recycle()

            // Send as JSON envelope — FastAPI WebSocket typically uses receive_json()
            wsManager?.send("""{"frame":"$b64"}""")
        } catch (e: Exception) {
            imageProxy.close()
            Log.e(TAG, "Frame processing error: ${e.message}")
        }
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

    override fun onRequestPermissionsResult(
        requestCode: Int, permissions: Array<out String>, grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == CAMERA_PERMISSION_CODE &&
            grantResults.isNotEmpty() &&
            grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            startCamera()
        } else {
            binding.tvFeedback.text = "⚠ Camera permission required"
            binding.tvFeedback.setBackgroundColor(Color.parseColor("#B71C1C"))
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        wsManager?.disconnect()
        cameraExecutor.shutdown()
    }
}
