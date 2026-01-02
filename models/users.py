from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from passlib.context import CryptContext
from db import Base
import uuid

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(Base):
    __tablename__ = "users" 

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True)
    password_hash = Column(String, nullable=False)
    daily_bandwidth_limit = Column(Integer)
    monthly_bandwidth_limit = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())

class UserUsage(Base):
    __tablename__ = "user_usage"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    video_id = Column(String(36), ForeignKey("videos.id"))
    bandwidth_used = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())