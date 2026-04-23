import sys
sys.path.append('.')
from database import SessionLocal, engine
import models
from datetime import datetime, timezone, timedelta

# Create tables
models.Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Add OTP
email = "test_local@example.com"
otp_code = "123456"
expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

db.query(models.OTPRequest).filter(models.OTPRequest.email == email).delete()
db.add(models.OTPRequest(email=email, otp_code=otp_code, expires_at=expires_at))
db.commit()

# Retrieve OTP
otp_record = db.query(models.OTPRequest).filter(
    models.OTPRequest.email == email,
    models.OTPRequest.otp_code == otp_code
).first()

if otp_record:
    print(f"Found OTP record: {otp_record.expires_at}")
    print(f"Aware? {otp_record.expires_at.tzinfo}")
    
    expires_aware = otp_record.expires_at.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    print(f"Expires at (aware): {expires_aware}")
    print(f"Now (aware):        {now}")
    print(f"Is expired?         {expires_aware < now}")
else:
    print("OTP NOT FOUND!")

db.close()
