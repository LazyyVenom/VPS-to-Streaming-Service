from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from passlib.context import CryptContext
from db import Base

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(Base):
    __tablename__ = "users" 

    id = Column(String(36), primary_key=True)
    username = Column(String, unique=True)
    password_hash = Column(String)
    daily_bandwidth_limit = Column(Integer)
    monthly_bandwidth_limit = Column(Integer)
    created_at = Column(DateTime)

class UserUsage(Base):
    __tablename__ = "user_usage"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"))
    video_id = Column(String(36), ForeignKey("videos.id"))
    bandwidth_used = Column(Integer)
    created_at = Column(DateTime)