package com.motionsense.ai

import android.content.Intent
import android.os.Bundle
import android.view.animation.AlphaAnimation
import android.view.animation.AnimationSet
import android.view.animation.TranslateAnimation
import androidx.appcompat.app.AppCompatActivity
import com.motionsense.ai.databinding.ActivitySplashBinding
import com.motionsense.ai.network.RetrofitClient

class SplashActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySplashBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySplashBinding.inflate(layoutInflater)
        setContentView(binding.root)
        RetrofitClient.init(this)
        if (RetrofitClient.getToken() != null) {
            startActivity(Intent(this, DashboardActivity::class.java))
            finish()
            return
        }

        // Animate logo slide-in + fade-in
        val fadeIn = AlphaAnimation(0f, 1f).apply { duration = 900 }
        val slideUp = TranslateAnimation(0f, 0f, 80f, 0f).apply { duration = 900 }
        val animSet = AnimationSet(true).apply {
            addAnimation(fadeIn)
            addAnimation(slideUp)
        }
        binding.logoContainer.startAnimation(animSet)

        // Animate button fade in after logo
        val btnFade = AlphaAnimation(0f, 1f).apply {
            duration = 600
            startOffset = 600
            fillAfter = true
        }
        binding.btnStartTraining.startAnimation(btnFade)

        // Navigate on button click
        binding.btnStartTraining.setOnClickListener {
            goToExerciseSelect()
        }

        binding.tvLoginSignup.setOnClickListener {
            startActivity(Intent(this, AuthActivity::class.java))
            overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
        }
    }

    private fun goToExerciseSelect() {
        startActivity(Intent(this, ExerciseSelectActivity::class.java))
        overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
    }
}
