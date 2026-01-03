from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db import get_db
from schemas.users import UserLogin, UserCreate, UserResponse
from models.users import User
from utils.pswds import secure_pwd, verify_pwd
from utils.auth import create_access_token, create_refresh_token
from datetime import timedelta
from fastapi.security import OAuth2PasswordBearer

route = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2bearer = OAuth2PasswordBearer(tokenUrl='auth/login')

@route.post("/register", response_model=UserResponse)
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.username == payload.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Create new user
    hashed_password = secure_pwd(payload.password)
    new_user = User(
        username=payload.username,
        password_hash=hashed_password,
        daily_bandwidth_limit=payload.daily_bandwidth_limit,
        monthly_bandwidth_limit=payload.monthly_bandwidth_limit
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@route.post("/login")
def login_user(payload: UserLogin, db: Session = Depends(get_db)):
    """
    Login user based on username and password
    """
    if not payload.username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide username",
        )
    
    # Find user
    user = db.query(User).filter(User.username == payload.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Verify password
    if not verify_pwd(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Create tokens
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
    
    return {
        'access_token': access_token,
        'token_type': 'bearer',
        'refresh_token': refresh_token,
        'user_id': user.id
    }
