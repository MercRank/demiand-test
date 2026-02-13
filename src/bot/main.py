"""Точка входа Telegram бота"""
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

from src.core.config import Config
from src.core.logger import setup_logger
from src.rag.retriever import RAGRetriever
from src.rag.vector_store import VectorStore
from src.bot.handlers import setup_handlers


# Загружаем переменные окружения
load_dotenv()

logger = setup_logger(__name__)


async def main() -> None:
    """Главная функция запуска бота"""
    # Загружаем конфигурацию
    config = Config.from_env()
    
    # Валидируем конфигурацию
    try:
        config.validate()
    except ValueError as e:
        logger.error(f"Ошибка конфигурации: {e}")
        return
    
    logger.info("Конфигурация загружена успешно")
    
    # Инициализируем компоненты
    rag_retriever = RAGRetriever(config)
    vector_store = VectorStore(config)
    
    # Проверяем подключение к Qdrant
    try:
        await vector_store.ensure_collection()
        doc_count = await vector_store.count_documents()
        logger.info(f"Подключено к Qdrant. Документов в базе: {doc_count}")
    except Exception as e:
        logger.error(f"Ошибка подключения к Qdrant: {e}")
        return
    
    # Инициализируем бота
    bot = Bot(
        token=config.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Инициализируем диспетчер
    dp = Dispatcher()
    
    # Подключаем обработчики
    handlers_router = setup_handlers(rag_retriever)
    dp.include_router(handlers_router)
    
    logger.info("Бот запускается...")
    
    try:
        # Удаляем webhook на случай если он был установлен
        await bot.delete_webhook(drop_pending_updates=True)
        
        # Запускаем polling
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
