"""Обработчики команд и сообщений Telegram бота"""
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from src.core.logger import setup_logger
from src.rag.retriever import RAGRetriever


logger = setup_logger(__name__)
router = Router()


class BotHandlers:
    """Класс с обработчиками бота"""
    
    def __init__(self, rag_retriever: RAGRetriever):
        """
        Args:
            rag_retriever: Сервис RAG для ответов
        """
        self.rag = rag_retriever
    
    async def handle_start(self, message: Message) -> None:
        """Обработчик команды /start"""
        welcome_text = (
            f"👋 Привет, {message.from_user.full_name}! Я помощник по подбору аэрогрилей.\n\n"
            "Помогу:\n"
            "• подобрать модель по объёму, мощности или количеству ТЭНов\n"
            "• сравнить несколько моделей\n"
            "• рассказать о программах и функциях\n"
            "• подобрать аксессуары\n\n"
            "Напишите, что вы ищете."
        )
        await message.answer(welcome_text)
    
    async def handle_message(self, message: Message) -> None:
        """Обработчик текстовых сообщений"""
        try:
            # Показываем индикатор печатает...
            await message.bot.send_chat_action(
                chat_id=message.chat.id,
                action="typing"
            )
            
            # Получаем ответ от RAG системы
            response = await self.rag.query(message.text, stream=False)
            
            # Отправляем ответ
            await message.answer(response.answer)
            
            logger.info(
                f"Ответ отправлен пользователю {message.from_user.id}, "
                f"использовано источников: {len(response.sources)}"
            )
            
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}", exc_info=True)
            await message.answer(
                "Извините, произошла ошибка при обработке вашего запроса. "
                "Попробуйте переформулировать вопрос или попробуйте позже."
            )


def setup_handlers(rag_retriever: RAGRetriever) -> Router:
    """
    Настраивает и возвращает роутер с обработчиками
    
    Args:
        rag_retriever: Сервис RAG
    
    Returns:
        Настроенный роутер
    """
    handlers = BotHandlers(rag_retriever)
    
    # Регистрируем обработчики
    router.message.register(handlers.handle_start, CommandStart())
    router.message.register(handlers.handle_message, F.text)
    
    return router
