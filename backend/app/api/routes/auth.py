from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.core.dependencies import get_current_user
from app.models.models import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenResponse(BaseModel):
    """Ответ с токеном"""
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Ответ с данными пользователя"""
    id: int
    username: str
    role: str


@router.post("/login")
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Вход в систему
    
    Args:
        response: HTTP ответ для установки cookie
        form_data: Данные формы (username, password)
        db: Сессия базы данных
        
    Returns:
        dict: Сообщение об успешном входе
    """
    # Поиск пользователя
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()
    
    # Проверка пароля
    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Неудачная попытка входа: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Создание токена
    access_token = create_access_token(data={"sub": user.username})
    
    # Установка httpOnly cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=86400,  # 24 часа
        samesite="lax",
        secure=False  # В production должно быть True
    )
    
    logger.info(f"Успешный вход: {user.username} (role: {user.role})")
    
    return {
        "message": "Успешный вход",
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role.value
        }
    }


@router.post("/logout")
async def logout(response: Response):
    """
    Выход из системы
    
    Args:
        response: HTTP ответ для удаления cookie
        
    Returns:
        dict: Сообщение об успешном выходе
    """
    response.delete_cookie(key="access_token")
    logger.info("Выход из системы")
    return {"message": "Успешный выход"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Получение информации о текущем пользователе
    
    Args:
        current_user: Текущий пользователь
        
    Returns:
        UserResponse: Данные пользователя
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role.value
    )
