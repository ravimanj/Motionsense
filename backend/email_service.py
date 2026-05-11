"""
email_service.py — Send OTP emails via SendGrid HTTP API
=========================================================
WHY NOT SMTP?
  Render's free tier blocks outbound TCP on port 587 (SMTP).
  SendGrid's HTTP API uses port 443 (HTTPS) which works on all tiers.

Required environment variables (set in .env or Render dashboard):
  SENDGRID_API_KEY  — your SendGrid API key (starts with "SG.")
  SENDGRID_FROM     — the verified sender email address

Quick setup (5 minutes, free):
  1. Sign up at https://signup.sendgrid.com  (free — 100 emails/day)
  2. Go to Settings → Sender Authentication → Single Sender Verification
  3. Add & verify your email address (click the link SendGrid sends you)
  4. Go to Settings → API Keys → Create API Key
     - Permission: "Restricted" → enable "Mail Send" only
     - Copy the key (starts with "SG.")
  5. Set env vars on Render dashboard:
       SENDGRID_API_KEY = SG.xxxxxxxxxxxx
       SENDGRID_FROM    = yourverified@gmail.com
"""
import os
import logging
import urllib.request
import urllib.error
import json

logger = logging.getLogger("motionsense.email")

# ── Load from environment ──────────────────────────────────────────────────────
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
SENDGRID_FROM    = os.getenv("SENDGRID_FROM", "")

# SendGrid Mail Send endpoint (HTTPS — works on Render free tier)
_SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"


def send_otp_email(to_email: str, otp_code: str) -> bool:
    """
    Send a 6-digit OTP to *to_email* via SendGrid's HTTP API (HTTPS / port 443).

    Returns True on success, False on any failure.
    Falls back to console logging when credentials are not configured so that
    local development still works without an API key.
    """
    if not SENDGRID_API_KEY or not SENDGRID_FROM:
        # Dev fallback — print to console so local dev still works
        logger.warning("SendGrid credentials not set. Falling back to console OTP.")
        print(f"\n{'='*50}")
        print(f"  [DEV] OTP for {to_email}: {otp_code}")
        print(f"{'='*50}\n")
        return True  # treat as "sent" so the API still responds OK

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

    # ── Build SendGrid v3 JSON payload ────────────────────────────────────────
    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": SENDGRID_FROM, "name": "MotionSense AI"},
        "subject": "Your MotionSense Verification Code",
        "content": [{"type": "text/html", "value": html_body}],
    }

    # ── Send via HTTPS (no SMTP, works on Render free tier) ───────────────────
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            _SENDGRID_URL,
            data=data,
            headers={
                "Authorization": f"Bearer {SENDGRID_API_KEY}",
                "Content-Type":  "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
            # SendGrid returns 202 Accepted on success
            if status == 202:
                logger.info(f"OTP email sent to {to_email} (HTTP {status})")
                return True
            else:
                logger.error(f"SendGrid unexpected status {status} for {to_email}")
                return False

    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        logger.error(
            f"SendGrid HTTP error {exc.code} for {to_email}: {body}\n"
            "Check that SENDGRID_FROM is a verified sender in your SendGrid account."
        )
        return False
    except Exception as exc:
        logger.error(f"Failed to send OTP email to {to_email}: {exc}")
        return False
