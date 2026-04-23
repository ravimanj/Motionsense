import requests
import sys

URL = "https://motionsense.onrender.com"

# 1. Send OTP
print("Requesting OTP...")
res = requests.post(f"{URL}/auth/send-otp", json={"email": "test@example.com"})
print(res.status_code, res.text)
if res.status_code != 200:
    sys.exit(1)

# 2. Verify OTP (Will fail because we don't know the OTP, but we can see the exact error)
print("\nVerifying OTP...")
res = requests.post(f"{URL}/auth/verify-otp", json={"email": "test@example.com", "otp_code": "123456", "new_password": "password"})
print(res.status_code, res.text)
