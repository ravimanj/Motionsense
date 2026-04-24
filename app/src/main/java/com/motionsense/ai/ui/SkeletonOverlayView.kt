package com.motionsense.ai.ui

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.util.AttributeSet
import android.view.View
import com.motionsense.ai.model.Landmark

class SkeletonOverlayView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
    defStyleAttr: Int = 0
) : View(context, attrs, defStyleAttr) {

    // MediaPipe body connections (same as backend POSE_CONNECTIONS)
    private val POSE_CONNECTIONS = listOf(
        11 to 12, 11 to 13, 13 to 15, 12 to 14, 14 to 16,
        11 to 23, 12 to 24, 23 to 24, 23 to 25, 24 to 26,
        25 to 27, 26 to 28, 27 to 29, 28 to 30, 29 to 31, 30 to 32
    )

    private var landmarks: List<Landmark> = emptyList()

    // Line paint — bright green skeleton lines
    private val linePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#00E676")
        strokeWidth = 5f
        style = Paint.Style.STROKE
        alpha = 210
    }

    // Joint dot paint
    private val dotPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#00E676")
        style = Paint.Style.FILL
    }

    // Key joint accent paint (slightly brighter/larger)
    private val accentDotPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#69FF47")
        style = Paint.Style.FILL
    }

    // Key joint indices to highlight
    private val KEY_JOINTS = setOf(11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28)

    private var smoothedLandmarks: List<Landmark>? = null
    private val alpha = 0.4f // Smoothing factor: lower = smoother but more lag
    
    var isMirrored = true // Default true for front-camera live tracker

    fun updateLandmarks(newLandmarks: List<Landmark>) {
        if (smoothedLandmarks == null || smoothedLandmarks!!.size != newLandmarks.size) {
            smoothedLandmarks = newLandmarks
        } else {
            smoothedLandmarks = newLandmarks.mapIndexed { index, target ->
                val current = smoothedLandmarks!![index]
                Landmark(
                    x = alpha * target.x + (1 - alpha) * current.x,
                    y = alpha * target.y + (1 - alpha) * current.y,
                    z = alpha * target.z + (1 - alpha) * current.z,
                    visibility = target.visibility
                )
            }
        }
        landmarks = smoothedLandmarks!!
        invalidate()
    }

    fun clearLandmarks() {
        smoothedLandmarks = null
        landmarks = emptyList()
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        if (landmarks.isEmpty()) return

        val w = width.toFloat()
        val h = height.toFloat()

        // Draw bone connections
        for ((startIdx, endIdx) in POSE_CONNECTIONS) {
            if (startIdx < landmarks.size && endIdx < landmarks.size) {
                val s = landmarks[startIdx]
                val e = landmarks[endIdx]
                if (s.visibility > 0.4f && e.visibility > 0.4f) {
                    val sx = if (isMirrored) (1f - s.x) * w else s.x * w
                    val ex = if (isMirrored) (1f - e.x) * w else e.x * w
                    canvas.drawLine(sx, s.y * h, ex, e.y * h, linePaint)
                }
            }
        }

        // Draw landmark dots
        for ((idx, lm) in landmarks.withIndex()) {
            if (lm.visibility > 0.4f) {
                val px = if (isMirrored) (1f - lm.x) * w else lm.x * w
                val py = lm.y * h
                val paint = if (idx in KEY_JOINTS) accentDotPaint else dotPaint
                val radius = if (idx in KEY_JOINTS) 9f else 6f
                canvas.drawCircle(px, py, radius, paint)
            }
        }
    }
}
