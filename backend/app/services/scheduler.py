from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy import select
import logging
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.models import CalculationFile

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def cleanup_old_files():
    """
    Удаление файлов старше FILE_RETENTION_DAYS дней
    """
    logger.info("Начало очистки старых файлов...")
    
    try:
        async with AsyncSessionLocal() as db:
            # Вычисление даты отсечки
            cutoff_date = datetime.utcnow() - timedelta(days=settings.FILE_RETENTION_DAYS)
            
            # Поиск файлов для удаления
            result = await db.execute(
                select(CalculationFile).where(CalculationFile.created_at < cutoff_date)
            )
            old_files = result.scalars().all()
            
            deleted_count = 0
            for calc_file in old_files:
                # Удаление файла с диска
                file_path = Path(calc_file.file_path)
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Удалён файл: {calc_file.filename}")
                
                # Удаление из БД
                await db.delete(calc_file)
                deleted_count += 1
            
            await db.commit()
            
            logger.info(f"Очистка завершена. Удалено файлов: {deleted_count}")
    
    except Exception as e:
        logger.error(f"Ошибка при очистке файлов: {str(e)}", exc_info=True)


def start_scheduler():
    """
    Запуск планировщика задач
    """
    # Очистка файлов каждый день в 3:00 ночи
    scheduler.add_job(
        cleanup_old_files,
        trigger=CronTrigger(hour=3, minute=0),
        id='cleanup_old_files',
        name='Очистка старых файлов',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Планировщик запущен. Задача очистки: каждый день в 3:00")


def stop_scheduler():
    """
    Остановка планировщика задач
    """
    scheduler.shutdown()
    logger.info("Планировщик остановлен")
