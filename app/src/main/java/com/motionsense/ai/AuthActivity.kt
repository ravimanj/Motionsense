package com.motionsense.ai

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.motionsense.ai.databinding.ActivityAuthBinding
import com.motionsense.ai.network.*
import kotlinx.coroutines.launch

class AuthActivity : AppCompatActivity() {

    private lateinit binding: ActivityAuthBinding
    private var isLoginMode = false
    private var isOtpMode = false
    private var currentEmail = ""

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityAuthBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        // Initialize Retrofit Prefs just in case
        RetrofitClient.init(this)

        updateUiState()

        binding.tvSwitchMode.setOnClickListener {
            isLoginMode = !isLoginMode
            isOtpMode = false
            updateUiState()
        }

        binding.btnPrimary.setOnClickListener {
            if (isLoginMode) {
                handleLogin()
            } else if (isOtpMode) {
                handleVerifyOtp()
            } else {
                handleSendOtp()
            }
        }
    }

    private fun updateUiState() {
        if (isLoginMode) {
            binding.layoutOtp.visibility = View.GONE
            binding.layoutLogin.visibility = View.VISIBLE
            binding.btnPrimary.text = "Log In"
            binding.tvSwitchMode.text = "Need an account? Sign up"
        } else if (isOtpMode) {
            binding.layoutOtp.visibility = View.VISIBLE
            binding.layoutLogin.visibility = View.GONE
            binding.btnPrimary.text = "Verify & Set Password"
            binding.tvSwitchMode.text = "Back to Email"
            binding.etEmail.isEnabled = false
        } else {
            binding.layoutOtp.visibility = View.GONE
            binding.layoutLogin.visibility = View.GONE
            binding.btnPrimary.text = "Send OTP"
            binding.tvSwitchMode.text = "Already have an account? Log in"
            binding.etEmail.isEnabled = true
        }
    }

    private fun handleSendOtp() {
        val email = binding.etEmail.text.toString().trim()
        if (email.isEmpty()) return

        setLoading(true)
        lifecycleScope.launch {
            try {
                RetrofitClient.api.sendOtp(EmailRequest(email))
                currentEmail = email
                isOtpMode = true
                updateUiState()
                Toast.makeText(this@AuthActivity, "OTP Sent to $email", Toast.LENGTH_SHORT).show()
            } catch (e: Exception) {
                Toast.makeText(this@AuthActivity, "Error: ${e.message}", Toast.LENGTH_SHORT).show()
            } finally {
                setLoading(false)
            }
        }
    }

    private fun handleVerifyOtp() {
        val otp = binding.etOtp.text.toString().trim()
        val pwd = binding.etNewPassword.text.toString().trim()
        if (otp.isEmpty() || pwd.isEmpty()) return

        setLoading(true)
        lifecycleScope.launch {
            try {
                RetrofitClient.api.verifyOtp(VerifyOtpRequest(currentEmail, otp, pwd))
                Toast.makeText(this@AuthActivity, "Password set! Please log in.", Toast.LENGTH_SHORT).show()
                isLoginMode = true
                isOtpMode = false
                updateUiState()
                binding.etLoginPassword.setText(pwd)
            } catch (e: Exception) {
                Toast.makeText(this@AuthActivity, "Invalid OTP or Error", Toast.LENGTH_SHORT).show()
            } finally {
                setLoading(false)
            }
        }
    }

    private fun handleLogin() {
        val email = binding.etEmail.text.toString().trim()
        val pwd = binding.etLoginPassword.text.toString().trim()
        if (email.isEmpty() || pwd.isEmpty()) return

        setLoading(true)
        lifecycleScope.launch {
            try {
                val res = RetrofitClient.api.login(LoginRequest(email, pwd))
                RetrofitClient.saveToken(res.accessToken)
                
                // Go to Dashboard
                startActivity(Intent(this@AuthActivity, DashboardActivity::class.java))
                finish()
            } catch (e: Exception) {
                Toast.makeText(this@AuthActivity, "Login failed. Check credentials.", Toast.LENGTH_SHORT).show()
            } finally {
                setLoading(false)
            }
        }
    }

    private fun setLoading(isLoading: Boolean) {
        binding.btnPrimary.isEnabled = !isLoading
        binding.progressBar.visibility = if (isLoading) View.VISIBLE else View.GONE
    }
}
