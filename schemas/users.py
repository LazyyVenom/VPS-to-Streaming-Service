from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from datetime import datetime, date


class GetUser(BaseModel):
    email: EmailStr
    username: Optional[str]
    role: int


class LoginUser(BaseModel):
    email: EmailStr
    password: str
