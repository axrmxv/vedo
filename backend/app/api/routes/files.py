"""
Маршруты работы с файлами
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import FileResponse as StarletteFileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import List
from pathlib import Path
from datetime import datetime
import uuid
import os
import logging
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_admin
from app.core.config import settings
from app.models.models import User, CalculationFile
from app.services.calculator import calculator_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["files"])


class FileResponseModel(BaseModel):
    """Ответ с информацией о файле"""
    id: int
    filename: str
    original_filename: str
    file_size: int
    created_at: datetime


class FilesListResponse(BaseModel):
    """Ответ со списком файлов"""
    files: List[FileResponseModel]
    total: int
    page: int
    page_size: int


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Загрузка и обработка файла
    
    Args:
        file: Загружаемый файл
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        dict: Информация об обработанном файле
    """
    logger.info(f"Пользователь {current_user.username} загружает файл: {file.filename}")
    
    # Проверка расширения
    if not file.filename:
        raise HTTPException(status_code=400, detail="Имя файла не указано")
    
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ['.txt', '.xlsx']:
        raise HTTPException(
            status_code=400,
            detail="Поддерживаются только файлы .txt и .xlsx"
        )
    
    # Проверка размера
    content = await file.read()
    file_size = len(content)
    
    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Файл слишком большой. Максимальный размер: {settings.MAX_FILE_SIZE / 1024 / 1024} МБ"
        )
    
    # Создание временного файла для обработки
    temp_path = Path(settings.STORAGE_PATH) / f"temp_{uuid.uuid4()}{file_extension}"
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Сохранение временного файла
        with open(temp_path, 'wb') as f:
            f.write(content)
        
        # Обработка файла
        if file_extension == '.txt':
            df = await calculator_service.process_file(
                temp_path, 
                file_extension,
                content=content.decode('utf-8')
            )
        else:
            df = await calculator_service.process_file(temp_path, file_extension)
        
        # Генерация уникального имени выходного файла
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        original_name = Path(file.filename).stem
        unique_id = str(uuid.uuid4())[:8]
        output_filename = f"{timestamp}_АвтоРасчет_{original_name}_{unique_id}.xlsx"
        output_path = Path(settings.STORAGE_PATH) / output_filename
        
        # Сохранение результата
        df.to_excel(output_path, index=False)
        output_size = output_path.stat().st_size
        
        # Сохранение в БД
        calc_file = CalculationFile(
            filename=output_filename,
            original_filename=file.filename,
            file_path=str(output_path),
            file_size=output_size,
            user_id=current_user.id
        )
        db.add(calc_file)
        await db.commit()
        await db.refresh(calc_file)
        
        logger.info(f"Файл успешно обработан: {output_filename}")
        
        return {
            "message": "Файл успешно обработан",
            "file": {
                "id": calc_file.id,
                "filename": calc_file.filename,
                "file_size": calc_file.file_size,
                "created_at": calc_file.created_at
            }
        }
    
    except Exception as e:
        logger.error(f"Ошибка обработки файла: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка обработки файла: {str(e)}"
        )
    finally:
        # Удаление временного файла
        if temp_path.exists():
            temp_path.unlink()


@router.get("/list", response_model=FilesListResponse)
async def list_files(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение списка файлов пользователя
    
    Args:
        page: Номер страницы
        page_size: Размер страницы
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        FilesListResponse: Список файлов с пагинацией
    """
    # Фильтр по пользователю (админ видит все файлы)
    query = select(CalculationFile)
    count_query = select(func.count(CalculationFile.id))
    
    if current_user.role.value != "admin":
        query = query.where(CalculationFile.user_id == current_user.id)
        count_query = count_query.where(CalculationFile.user_id == current_user.id)
    
    # Подсчёт общего количества
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Пагинация
    offset = (page - 1) * page_size
    query = query.order_by(CalculationFile.created_at.desc()).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    files = result.scalars().all()
    
    return FilesListResponse(
        files=[
            FileResponseModel(
                id=f.id,
                filename=f.filename,
                original_filename=f.original_filename,
                file_size=f.file_size,
                created_at=f.created_at
            ) for f in files
        ],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/download/{file_id}")
async def download_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Скачивание файла
    
    Args:
        file_id: ID файла
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        FileResponse: Файл для скачивания
    """
    # Получение файла
    result = await db.execute(
        select(CalculationFile).where(CalculationFile.id == file_id)
    )
    calc_file = result.scalar_one_or_none()
    
    if not calc_file:
        raise HTTPException(status_code=404, detail="Файл не найден")
    
    # Проверка прав доступа
    if current_user.role.value != "admin" and calc_file.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нет доступа к файлу")
    
    # Проверка существования файла
    file_path = Path(calc_file.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Файл не найден на диске")
    
    logger.info(f"Пользователь {current_user.username} скачивает файл: {calc_file.filename}")
    
    return StarletteFileResponse(
        path=str(file_path),
        filename=calc_file.filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@router.delete("/{file_id}")
async def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Удаление файла
    
    Args:
        file_id: ID файла
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        dict: Сообщение об успешном удалении
    """
    # Получение файла
    result = await db.execute(
        select(CalculationFile).where(CalculationFile.id == file_id)
    )
    calc_file = result.scalar_one_or_none()
    
    if not calc_file:
        raise HTTPException(status_code=404, detail="Файл не найден")
    
    # Проверка прав доступа
    if current_user.role.value != "admin" and calc_file.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нет доступа к файлу")
    
    # Удаление файла с диска
    file_path = Path(calc_file.file_path)
    if file_path.exists():
        file_path.unlink()
    
    # Удаление из БД
    await db.delete(calc_file)
    await db.commit()
    
    logger.info(f"Пользователь {current_user.username} удалил файл: {calc_file.filename}")
    
    return {"message": "Файл успешно удалён"}
