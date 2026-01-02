from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db import get_db
from schemas import LoginUser
from datetime import timedelta
from fastapi.security import OAuth2PasswordBearer

route = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2bearer = OAuth2PasswordBearer(tokenUrl = 'auth/login')

@route.post("/login")
def login_user(payload: LoginUser, db: Session = Depends(get_db)):
    """
    Login user based on email and password
    """
    if not payload.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please add Phone number",
        )
    
    user = get_user(db, payload.email)
    token =  create_access_token(user.id, timedelta(minutes=30)) 
    refresh = create_refresh_token(user.id,timedelta(minutes = 1008))

    return {'access_token': token, 'token_type': 'bearer','refresh_token':refresh,"user_id":user.id}
