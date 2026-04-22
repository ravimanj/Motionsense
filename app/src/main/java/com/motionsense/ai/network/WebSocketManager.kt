package com.motionsense.ai.network

import android.os.Handler
import android.os.Looper
import android.util.Log
import com.motionsense.ai.Constants
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger

interface SocketEventListener {
    fun onConnected()
    fun onMessageReceived(message: String)
    fun onError(error: String)
    fun onReconnecting(attempt: Int, delayMs: Long)
    fun onDisconnected()
}

class WebSocketManager(
    private val exercise: String,
    private val reps: Int,
    private val weight: Double,
    private val listener: SocketEventListener
) {
    private val TAG = "WebSocketManager"

    private var webSocket: WebSocket? = null
    private val isConnected = AtomicBoolean(false)
    private val isDestroyed = AtomicBoolean(false)
    private val retryCount = AtomicInteger(0)
    private val mainHandler = Handler(Looper.getMainLooper())

    companion object {
        private const val MAX_RETRIES = 4
        private val RETRY_DELAYS_MS = longArrayOf(3_000, 6_000, 12_000, 20_000)
    }

    // Increased timeouts for Render free-tier cold starts.
    // pingInterval deliberately omitted — Render's free tier does not reliably
    // respond to OkHttp WebSocket-level pings within 20 s, causing false failures.
    private val client = OkHttpClient.Builder()
        .connectTimeout(60, TimeUnit.SECONDS)
        .readTimeout(90, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .retryOnConnectionFailure(true)
        .build()

    fun connect() {
        if (isDestroyed.get()) return
        val url = "${Constants.WS_BASE_URL}/ws/$exercise?reps=$reps&weight=$weight"
        Log.d(TAG, "Connecting to: $url (attempt ${retryCount.get() + 1})")
        val request = Request.Builder().url(url).build()

        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                Log.d(TAG, "WebSocket opened")
                isConnected.set(true)
                retryCount.set(0)          // reset backoff on success
                listener.onConnected()
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                listener.onMessageReceived(text)
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.e(TAG, "WS failure: ${t.message}")
                isConnected.set(false)

                if (isDestroyed.get()) return

                val attempt = retryCount.getAndIncrement()
                if (attempt < MAX_RETRIES) {
                    val delay = RETRY_DELAYS_MS[attempt]
                    Log.d(TAG, "Reconnecting in ${delay}ms (attempt ${attempt + 1}/$MAX_RETRIES)")
                    listener.onReconnecting(attempt + 1, delay)
                    mainHandler.postDelayed({ connect() }, delay)
                } else {
                    Log.e(TAG, "Max retries reached — giving up")
                    listener.onError(t.message ?: "Connection failed after $MAX_RETRIES retries")
                }
            }

            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                webSocket.close(1000, null)
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                Log.d(TAG, "WS closed: $code / $reason")
                isConnected.set(false)
                if (!isDestroyed.get()) {
                    listener.onDisconnected()
                }
            }
        })
    }

    fun send(data: String): Boolean {
        if (!isConnected.get()) return false
        return webSocket?.send(data) ?: false
    }

    fun connected() = isConnected.get()

    fun disconnect() {
        isDestroyed.set(true)
        isConnected.set(false)
        mainHandler.removeCallbacksAndMessages(null)   // cancel any pending reconnect
        try {
            webSocket?.close(1000, "Session ended")
        } catch (e: Exception) {
            Log.w(TAG, "Close error: ${e.message}")
        }
        webSocket = null
    }
}

