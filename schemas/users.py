from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    username: str
    password: str
    daily_bandwidth_limit: Optional[int] = None
    monthly_bandwidth_limit: Optional[int] = None


class UserLogin(BaseModel):
    username: str
    password: str

class UserShortResponse(BaseModel):
    username: str

class UserResponse(BaseModel):
    id: str
    username: str
    daily_bandwidth_limit: Optional[int]
    monthly_bandwidth_limit: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class UserUsageCreate(BaseModel):
    user_id: str
    video_id: Optional[str] = None
    bandwidth_used: int


class UserUsageResponse(BaseModel):
    id: str
    user_id: str
    video_id: Optional[str]
    bandwidth_used: int
    created_at: datetime

    class Config:
        from_attributes = True
