from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import random

from database import get_db
import models, schemas, security

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/send-otp", status_code=status.HTTP_200_OK)
def send_otp(request: schemas.EmailRequest, db: Session = Depends(get_db)):
    # Clean up old OTPs for this email
    db.query(models.OTPRequest).filter(models.OTPRequest.email == request.email).delete()
    
    # Generate 6-digit OTP
    otp_code = f"{random.randint(100000, 999999)}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    
    otp_request = models.OTPRequest(
        email=request.email,
        otp_code=otp_code,
        expires_at=expires_at
    )
    db.add(otp_request)
    db.commit()
    
    # In a real app, send email here. For now, log it.
    print(f"\n=======================================")
    print(f"OTP for {request.email}: {otp_code}")
    print(f"=======================================\n")
    
    return {"message": "OTP sent successfully"}

@router.post("/verify-otp", status_code=status.HTTP_200_OK)
def verify_otp(request: schemas.VerifyOTPRequest, db: Session = Depends(get_db)):
    otp_record = db.query(models.OTPRequest).filter(
        models.OTPRequest.email == request.email,
        models.OTPRequest.otp_code == request.otp_code
    ).first()
    
    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid OTP")
        
    if otp_record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="OTP expired")
        
    # Check if user exists, else create
    user = db.query(models.User).filter(models.User.email == request.email).first()
    hashed_pwd = security.get_password_hash(request.new_password)
    
    if user:
        user.hashed_password = hashed_pwd
    else:
        user = models.User(email=request.email, hashed_password=hashed_pwd)
        db.add(user)
        
    db.delete(otp_record)
    db.commit()
    
    return {"message": "Password set successfully"}

@router.post("/login", response_model=schemas.Token)
def login(request: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == request.email).first()
    if not user or not security.verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
        
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
