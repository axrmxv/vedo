from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import logging
from app.core.database import get_db
from app.core.dependencies import get_current_admin
from app.core.security import get_password_hash, generate_random_password
from app.models.models import User, UserRole

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


class CreateUserRequest(BaseModel):
    """Запрос на создание пользователя"""
    username: str = Field(..., min_length=3, max_length=50)
    role: UserRole = UserRole.USER


class CreateUserResponse(BaseModel):
    """Ответ с данными созданного пользователя"""
    id: int
    username: str
    password: str  # Временный пароль для первого входа
    role: str


class UserListItem(BaseModel):
    """Элемент списка пользователей"""
    id: int
    username: str
    role: str
    created_at: datetime


class UsersListResponse(BaseModel):
    """Ответ со списком пользователей"""
    users: List[UserListItem]
    total: int
    page: int
    page_size: int


class UpdateUserRequest(BaseModel):
    """Запрос на обновление пользователя"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    role: Optional[UserRole] = None
    password: Optional[str] = Field(None, min_length=6)


@router.post("/users", response_model=CreateUserResponse)
async def create_user(
    user_data: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin)
):
    """
    Создание нового пользователя (только для админа)
    
    Args:
        user_data: Данные нового пользователя
        db: Сессия базы данных
        _: Текущий администратор (проверка прав)
        
    Returns:
        CreateUserResponse: Данные созданного пользователя с временным паролем
    """
    # Проверка существования пользователя
    result = await db.execute(
        select(User).where(User.username == user_data.username)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким именем уже существует"
        )
    
    # Генерация случайного пароля
    random_password = generate_random_password()
    hashed_password = get_password_hash(random_password)
    
    # Создание пользователя
    new_user = User(
        username=user_data.username,
        hashed_password=hashed_password,
        role=user_data.role
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    logger.info(f"Создан новый пользователь: {new_user.username} (role: {new_user.role})")
    
    return CreateUserResponse(
        id=new_user.id,
        username=new_user.username,
        password=random_password,
        role=new_user.role.value
    )


@router.get("/users", response_model=UsersListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin)
):
    """
    Получение списка всех пользователей (только для админа)
    
    Args:
        page: Номер страницы
        page_size: Размер страницы
        db: Сессия базы данных
        _: Текущий администратор (проверка прав)
        
    Returns:
        UsersListResponse: Список пользователей с пагинацией
    """
    # Подсчёт общего количества
    count_result = await db.execute(select(func.count(User.id)))
    total = count_result.scalar()
    
    # Пагинация
    offset = (page - 1) * page_size
    query = select(User).order_by(User.created_at.desc()).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return UsersListResponse(
        users=[
            UserListItem(
                id=u.id,
                username=u.username,
                role=u.role.value,
                created_at=u.created_at
            ) for u in users
        ],
        total=total,
        page=page,
        page_size=page_size
    )


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    user_data: UpdateUserRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Обновление данных пользователя (только для админа)
    
    Args:
        user_id: ID пользователя
        user_data: Новые данные пользователя
        db: Сессия базы данных
        current_admin: Текущий администратор
        
    Returns:
        dict: Сообщение об успешном обновлении
    """
    # Получение пользователя
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Запрет на изменение собственной роли
    if user.id == current_admin.id and user_data.role and user_data.role != user.role:
        raise HTTPException(
            status_code=400,
            detail="Нельзя изменить собственную роль"
        )
    
    # Обновление данных
    if user_data.username:
        # Проверка уникальности username
        check_result = await db.execute(
            select(User).where(User.username == user_data.username, User.id != user_id)
        )
        if check_result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Пользователь с таким именем уже существует"
            )
        user.username = user_data.username
    
    if user_data.role:
        user.role = user_data.role
    
    if user_data.password:
        user.hashed_password = get_password_hash(user_data.password)
    
    await db.commit()
    
    logger.info(f"Обновлён пользователь: {user.username}")
    
    return {"message": "Пользователь успешно обновлён"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Удаление пользователя (только для админа)
    
    Args:
        user_id: ID пользователя
        db: Сессия базы данных
        current_admin: Текущий администратор
        
    Returns:
        dict: Сообщение об успешном удалении
    """
    # Получение пользователя
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # Запрет на удаление самого себя
    if user.id == current_admin.id:
        raise HTTPException(
            status_code=400,
            detail="Нельзя удалить собственный аккаунт"
        )
    
    # Удаление пользователя (файлы удалятся каскадно)
    await db.delete(user)
    await db.commit()
    
    logger.info(f"Удалён пользователь: {user.username}")
    
    return {"message": "Пользователь успешно удалён"}
