from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta, timezone

# JWT and Firebase
import jwt
from jwt import PyJWTError
import firebase_admin
from firebase_admin import auth as firebase_auth, credentials

# Local Imports
from . import crud, models, schemas
from .database import get_db # Import get_db from database.py

# --- APIRouter ---
router = APIRouter()

# --- Configuration ---
SECRET_KEY = "YOUR_SUPER_SECRET_KEY" # Change this!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

# --- JWT Helpers ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Dependencies (User Fetching) ---
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Dependency to get the current user from a JWT token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except PyJWTError:
        raise credentials_exception
    
    # User ko DB se fetch karo (eager loading ke saath)
    user = crud.get_user_by_email(db, email=email)
    
    if user is None:
        raise credentials_exception
        
    # --- !!! YAHI HAI ASLI FIX !!! ---
    # Force SQLAlchemy to refresh the object from the DB 
    # This gets the latest 'is_verified' status
    db.refresh(user)
    # --- FIX ENDS HERE ---

    return user

async def get_current_active_user(current_user: models.User = Depends(get_current_user)):
    """
    Dependency to get the current active user.
    """
    return current_user

async def get_current_admin_user(current_user: models.User = Depends(get_current_active_user)):
    """
    Dependency to ensure the user is an admin.
    """
    if current_user.email != "62069gaurav@gmail.com":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action"
        )
    return current_user

# --- API Endpoint ---
@router.post("/firebase-login", response_model=schemas.UserWithToken)
async def firebase_login(
    login_data: schemas.FirebaseLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Validate a Firebase ID token and issue a local JWT.
    """
    try:
        decoded_token = firebase_auth.verify_id_token(login_data.token)
        uid = decoded_token['uid']
        
        user = crud.get_user_by_firebase_uid(db, firebase_uid=uid)
        
        if not user:
            # (New User)
            firebase_user_record = firebase_auth.get_user(uid)
            final_dp_url = login_data.dp_url or firebase_user_record.photo_url

            crud.create_user_from_firebase(
                db, 
                firebase_user_record,
                role=login_data.role,
                business_id=login_data.business_id,
                dp_url=final_dp_url
            )
            user = crud.get_user_by_firebase_uid(db, firebase_uid=uid)
        
        else:
            # (Existing User)
            # Hum yahan refresh nahi kar rahe, kyunki user object
            # (cart/wishlist ke saath) already loaded hai.
            # Token banate waqt fresh data fetch hoga.
            pass

        # 'user' object ab fresh data ke liye ready hai
        
        # Token banane se pehle DB se fresh data fetch karo
        db.refresh(user) 
        
        access_token = create_access_token(
            data={
                "sub": user.email,
                "role": user.role,
                "is_verified": user.is_verified, # Yeh ab 100% fresh (True) value hogi
                "dp_url": user.dp_url
            }
        )
        
        setattr(user, 'access_token', access_token)
        return user

    except firebase_auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid Firebase token")
    except Exception as e:
        # Generic error for security
        raise HTTPException(status_code=500, detail="An internal server error occurred.")