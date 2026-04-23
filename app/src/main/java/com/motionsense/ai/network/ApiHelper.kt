package com.motionsense.ai.network

import android.content.Context
import android.content.SharedPreferences
import com.google.gson.annotations.SerializedName
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import java.util.concurrent.TimeUnit

// --- Models ---
data class EmailRequest(val email: String)
data class VerifyOtpRequest(val email: String, @SerializedName("otp_code") val otpCode: String, @SerializedName("new_password") val newPassword: String)
data class LoginRequest(val email: String, val password: String)
data class TokenResponse(@SerializedName("access_token") val accessToken: String, @SerializedName("token_type") val tokenType: String)
data class GenericResponse(val message: String)

data class SessionCreateRequest(@SerializedName("exercise_type") val exerciseType: String, val reps: Int, val weight: Float)
data class SessionResponse(val id: Int, @SerializedName("exercise_type") val exerciseType: String, val reps: Int, val weight: Float, val timestamp: String)

data class DailyLogToggle(val date: String, val completed: Boolean)
data class DailyLogResponse(val date: String, val completed: Boolean)

// --- API Interface ---
interface MotionSenseApi {
    @POST("auth/send-otp")
    suspend fun sendOtp(@Body request: EmailRequest): GenericResponse

    @POST("auth/verify-otp")
    suspend fun verifyOtp(@Body request: VerifyOtpRequest): GenericResponse

    @POST("auth/login")
    suspend fun login(@Body request: LoginRequest): TokenResponse

    @POST("sessions")
    suspend fun createSession(@Body session: SessionCreateRequest): SessionResponse

    @GET("sessions")
    suspend fun getSessions(): List<SessionResponse>

    @POST("daily-logs")
    suspend fun toggleDailyLog(@Body log: DailyLogToggle): DailyLogResponse

    @GET("daily-logs/{date}")
    suspend fun getDailyLog(@Path("date") date: String): DailyLogResponse
}

// --- Retrofit Client ---
object RetrofitClient {
    // Backend hosted on Render
    private const val BASE_URL = "https://motionsense.onrender.com/"

    private var sharedPrefs: SharedPreferences? = null

    fun init(context: Context) {
        sharedPrefs = context.getSharedPreferences("MotionSensePrefs", Context.MODE_PRIVATE)
    }

    fun saveToken(token: String) {
        sharedPrefs?.edit()?.putString("access_token", token)?.apply()
    }

    fun getToken(): String? {
        return sharedPrefs?.getString("access_token", null)
    }
    
    fun clearToken() {
        sharedPrefs?.edit()?.remove("access_token")?.apply()
    }

    private val authInterceptor = Interceptor { chain ->
        val req = chain.request()
        val token = getToken()
        if (token != null) {
            val newReq = req.newBuilder()
                .addHeader("Authorization", "Bearer $token")
                .build()
            chain.proceed(newReq)
        } else {
            chain.proceed(req)
        }
    }

    private val client = OkHttpClient.Builder()
        .addInterceptor(authInterceptor)
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .build()

    val api: MotionSenseApi by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(MotionSenseApi::class.java)
    }
}
