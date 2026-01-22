from sqlalchemy import select
import logging
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.models import User, UserRole

logger = logging.getLogger(__name__)


async def init_default_admin():
    """
    Создание администратора по умолчанию если его нет
    """
    async with AsyncSessionLocal() as db:
        try:
            # Проверка существования админа
            result = await db.execute(
                select(User).where(User.username == settings.ADMIN_USERNAME)
            )
            admin = result.scalar_one_or_none()
            
            if not admin:
                # Создание админа
                admin = User(
                    username=settings.ADMIN_USERNAME,
                    hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                    role=UserRole.ADMIN
                )
                db.add(admin)
                await db.commit()
                logger.info(f"Создан администратор по умолчанию: {settings.ADMIN_USERNAME}")
            else:
                logger.info(f"Администратор {settings.ADMIN_USERNAME} уже существует")
        
        except Exception as e:
            logger.error(f"Ошибка при инициализации администратора: {str(e)}", exc_info=True)
