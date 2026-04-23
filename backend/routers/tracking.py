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

@router.post("/workout-plan", response_model=schemas.WorkoutPlanUpdate)
def update_workout_plan(plan: schemas.WorkoutPlanUpdate, current_user: models.User = Depends(get_current_user_dep), db: Session = Depends(get_db)):
    # Clear existing plan for this user
    db.query(models.WorkoutPlan).filter(models.WorkoutPlan.user_id == current_user.id).delete()
    
    # Add new plan items
    items = [
        models.WorkoutPlan(user_id=current_user.id, exercise_type="bicep_curl", target_reps=plan.bicep_curl),
        models.WorkoutPlan(user_id=current_user.id, exercise_type="squat", target_reps=plan.squat),
        models.WorkoutPlan(user_id=current_user.id, exercise_type="push_up", target_reps=plan.push_up),
        models.WorkoutPlan(user_id=current_user.id, exercise_type="shoulder_press", target_reps=plan.shoulder_press)
    ]
    db.add_all(items)
    db.commit()
    
    return plan

@router.get("/daily-progress/{date}", response_model=schemas.DailyProgressResponse)
def get_daily_progress(date: str, current_user: models.User = Depends(get_current_user_dep), db: Session = Depends(get_db)):
    # 1. Fetch user's workout plan
    plans = db.query(models.WorkoutPlan).filter(models.WorkoutPlan.user_id == current_user.id).all()
    
    # If no plan exists, return empty progress
    if not plans:
        return schemas.DailyProgressResponse(date=date, is_fully_completed=False, progress=[])
        
    # 2. Fetch today's sessions
    sessions = db.query(models.ExerciseSession).filter(
        models.ExerciseSession.user_id == current_user.id
    ).all()
    
    # Filter sessions by the exact date (timestamp is datetime, date is string YYYY-MM-DD)
    todays_sessions = [s for s in sessions if s.timestamp.strftime('%Y-%m-%d') == date]
    
    # 3. Aggregate completed reps per exercise
    completed_reps_map = {}
    for s in todays_sessions:
        completed_reps_map[s.exercise_type] = completed_reps_map.get(s.exercise_type, 0) + s.reps
        
    # 4. Build progress response
    progress_items = []
    is_fully_completed = True
    
    for p in plans:
        # If target is 0, they didn't schedule it, so we don't necessarily show it, 
        # or we do show it but it's automatically completed. Let's just show it.
        comp = completed_reps_map.get(p.exercise_type, 0)
        progress_items.append(schemas.DailyProgressItem(
            exercise_type=p.exercise_type,
            target_reps=p.target_reps,
            completed_reps=comp
        ))
        if p.target_reps > 0 and comp < p.target_reps:
            is_fully_completed = False
            
    # If all targets were 0, technically they are fully completed, but it's an empty day.
    # We will let is_fully_completed be true if they had at least one >0 target and met it.
    has_active_targets = any(p.target_reps > 0 for p in plans)
    if not has_active_targets:
        is_fully_completed = False

    return schemas.DailyProgressResponse(
        date=date,
        is_fully_completed=is_fully_completed,
        progress=progress_items
    )
