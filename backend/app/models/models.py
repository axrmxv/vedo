from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base


class UserRole(str, enum.Enum):
    """Роли пользователей"""
    ADMIN = "admin"
    USER = "user"


class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Связь с файлами
    files = relationship("CalculationFile", back_populates="owner", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


class CalculationFile(Base):
    """Модель файла расчёта"""
    __tablename__ = "calculation_files"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), unique=True, nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False)  # в байтах
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Связь с пользователем
    owner = relationship("User", back_populates="files")
    
    def __repr__(self) -> str:
        return f"<CalculationFile(id={self.id}, filename='{self.filename}', user_id={self.user_id})>"
