from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

# Auth Schemas
class EmailRequest(BaseModel):
    email: EmailStr

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp_code: str
    new_password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: int
    email: EmailStr

    class Config:
        from_attributes = True

# Tracking Schemas
class ExerciseSessionCreate(BaseModel):
    exercise_type: str
    reps: int
    weight: float

class ExerciseSessionResponse(BaseModel):
    id: int
    exercise_type: str
    reps: int
    weight: float
    timestamp: datetime

    class Config:
        from_attributes = True

class DailyLogToggle(BaseModel):
    date: str # YYYY-MM-DD
    completed: bool

class DailyLogResponse(BaseModel):
    date: str
    completed: bool

    class Config:
        from_attributes = True

class WorkoutPlanUpdate(BaseModel):
    bicep_curl: int
    squat: int
    push_up: int
    shoulder_press: int

class DailyProgressItem(BaseModel):
    exercise_type: str
    target_reps: int
    completed_reps: int

class DailyProgressResponse(BaseModel):
    date: str
    is_fully_completed: bool
    progress: List[DailyProgressItem]
