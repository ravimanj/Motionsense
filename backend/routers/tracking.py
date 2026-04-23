from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone

from database import get_db
import models, schemas, security
from jose import jwt, JWTError

router = APIRouter(tags=["tracking"])

# Dependency to get current user
def get_current_user(token: str, db: Session):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

from fastapi.security import OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_current_user_dep(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    return get_current_user(token, db)

@router.post("/sessions", response_model=schemas.ExerciseSessionResponse)
def create_session(session: schemas.ExerciseSessionCreate, current_user: models.User = Depends(get_current_user_dep), db: Session = Depends(get_db)):
    db_session = models.ExerciseSession(
        user_id=current_user.id,
        exercise_type=session.exercise_type,
        reps=session.reps,
        weight=session.weight
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

@router.get("/sessions", response_model=List[schemas.ExerciseSessionResponse])
def get_sessions(current_user: models.User = Depends(get_current_user_dep), db: Session = Depends(get_db)):
    return db.query(models.ExerciseSession).filter(models.ExerciseSession.user_id == current_user.id).order_by(models.ExerciseSession.timestamp.desc()).all()

@router.post("/daily-logs", response_model=schemas.DailyLogResponse)
def toggle_daily_log(log: schemas.DailyLogToggle, current_user: models.User = Depends(get_current_user_dep), db: Session = Depends(get_db)):
    db_log = db.query(models.DailyLog).filter(
        models.DailyLog.user_id == current_user.id,
        models.DailyLog.date == log.date
    ).first()
    
    if db_log:
        db_log.completed = log.completed
    else:
        db_log = models.DailyLog(
            user_id=current_user.id,
            date=log.date,
            completed=log.completed
        )
        db.add(db_log)
        
    db.commit()
    db.refresh(db_log)
    return db_log

@router.get("/daily-logs/{date}", response_model=schemas.DailyLogResponse)
def get_daily_log(date: str, current_user: models.User = Depends(get_current_user_dep), db: Session = Depends(get_db)):
    db_log = db.query(models.DailyLog).filter(
        models.DailyLog.user_id == current_user.id,
        models.DailyLog.date == date
    ).first()
    
    if not db_log:
        return schemas.DailyLogResponse(date=date, completed=False)
        
    return db_log
