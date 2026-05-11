"""
email_service.py — Send OTP emails via Gmail SMTP (TLS)
========================================================
Required environment variables (set in .env or Render dashboard):
  GMAIL_USER     — your Gmail address, e.g. yourapp@gmail.com
  GMAIL_APP_PASS — 16-char Gmail App Password (NOT your real password)

How to generate a Gmail App Password:
  1. Enable 2-Step Verification on your Google account
  2. Go to: https://myaccount.google.com/apppasswords
  3. Create an app password for "Mail" → copy the 16-char code
  4. Paste it as GMAIL_APP_PASS in your .env file
"""
import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger("motionsense.email")

# ── Load from environment ──────────────────────────────────────────────────────
GMAIL_USER     = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASS", "")


def send_otp_email(to_email: str, otp_code: str) -> bool:
    """
    Send a 6-digit OTP to *to_email* via Gmail SMTP over TLS (port 587).

    Returns True on success, False on any SMTP/network failure.
    Falls back to console logging when credentials are not configured so that
    local development still works without email setup.
    """
    if not GMAIL_USER or not GMAIL_APP_PASS:
        # Dev fallback — print to console instead of crashing
        logger.warning("Email credentials not set. Falling back to console OTP.")
        print(f"\n{'='*45}")
        print(f"  OTP for {to_email}: {otp_code}")
        print(f"{'='*45}\n")
        return True  # treat as "sent" so the API still responds OK

    # ── Build the HTML email ───────────────────────────────────────────────────
    subject = "Your MotionSense Verification Code"
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background: #0d0d0d; color: #f0f0f0; padding: 32px;">
        <div style="max-width: 480px; margin: auto; background: #1a1a1a; border-radius: 16px;
                    padding: 32px; box-shadow: 0 4px 24px rgba(0,0,0,0.4);">

          <h2 style="color: #00E676; margin: 0 0 8px;">MotionSense AI 🏋️</h2>
          <p style="color: #9E9E9E; margin: 0 0 24px; font-size: 14px;">
            Fitness Tracker — Email Verification
          </p>

          <p style="font-size: 16px; margin-bottom: 8px;">Your one-time password is:</p>

          <div style="background: #272727; border: 2px solid #00E676; border-radius: 12px;
                      text-align: center; padding: 20px; margin: 16px 0;">
            <span style="font-size: 42px; font-weight: bold; letter-spacing: 12px;
                         color: #00E676; font-family: monospace;">
              {otp_code}
            </span>
          </div>

          <p style="color: #9E9E9E; font-size: 13px; margin-top: 16px;">
            ⏱ This code expires in <strong style="color: #FFB300;">10 minutes</strong>.
          </p>
          <p style="color: #9E9E9E; font-size: 13px;">
            If you didn't request this, ignore this email. Your account is safe.
          </p>

          <hr style="border: none; border-top: 1px solid #333; margin: 24px 0;" />
          <p style="color: #555; font-size: 11px; text-align: center;">
            MotionSense AI · Do not reply to this email
          </p>
        </div>
      </body>
    </html>
    """

    # ── Compose MIME message ───────────────────────────────────────────────────
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"MotionSense AI <{GMAIL_USER}>"
    msg["To"]      = to_email
    msg.attach(MIMEText(html_body, "html"))

    # ── Send via Gmail SMTP (TLS, port 587) ────────────────────────────────────
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(GMAIL_USER, GMAIL_APP_PASS)
            server.sendmail(GMAIL_USER, to_email, msg.as_string())
        logger.info(f"OTP email sent to {to_email}")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error(
            "Gmail SMTP auth failed — check GMAIL_USER and GMAIL_APP_PASS. "
            "Make sure you are using a 16-char App Password, not your real password."
        )
        return False
    except Exception as exc:
        logger.error(f"Failed to send OTP email to {to_email}: {exc}")
        return False
