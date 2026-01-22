from fastapi import Depends, HTTPException, status, Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.models import User, UserRole
import logging

logger = logging.getLogger(__name__)


async def get_current_user(
    access_token: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Получение текущего пользователя из JWT токена в cookie
    
    Args:
        access_token: JWT токен из httpOnly cookie
        db: Сессия базы данных
        
    Returns:
        User: Текущий пользователь
        
    Raises:
        HTTPException: Если токен невалидный или пользователь не найден
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not access_token:
        raise credentials_exception
    
    payload = decode_access_token(access_token)
    if payload is None:
        raise credentials_exception
    
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    
    # Получение пользователя из БД
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Проверка что текущий пользователь - администратор
    
    Args:
        current_user: Текущий пользователь
        
    Returns:
        User: Пользователь с ролью admin
        
    Raises:
        HTTPException: Если пользователь не администратор
    """
    if current_user.role != UserRole.ADMIN:
        logger.warning(f"Попытка доступа к админ-функции пользователем {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав доступа"
        )
    return current_user
