"""Конфигурация приложения через переменные окружения"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Централизованная конфигурация приложения"""
    
    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-large"
    openai_temperature: float = 0.0
    openai_max_tokens: int = 2000
    openai_timeout: int = 60
    
    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None
    collection_name: str = "knowledge_base"
    
    # Telegram
    telegram_bot_token: str = ""
    
    # RAG
    rag_top_k: int = 10
    rag_score_threshold: float = 0.3
    
    # System
    system_prompt: str = """Ты — ассистент по подбору и анализу моделей аэрогрилей.

Ты ОБЯЗАН использовать предоставленный контекст для ответов на вопросы о:
- моделях
- характеристиках
- количестве ТЭНов
- объёме
- мощности
- программах
- сравнении моделей
- фильтрации по параметрам

Ты НЕ имеешь права отвечать из собственных знаний, если информации нет в контексте.
Отвечай ТОЛЬКО на основе данных, полученных из базы знаний.

При анализе:
- Внимательно читай поле "Кол-во ТЭНов"
- Если в этом поле содержится число 2 — модель относится к моделям с двумя ТЭНами
- Извлекай название модели из поля "Название модели"

Никогда не говори, что данные отсутствуют, если они есть в контексте.
Если подходящих моделей нет — честно скажи, что по найденным данным таких моделей нет."""
    
    @classmethod
    def from_env(cls) -> "Config":
        """Загружает конфигурацию из переменных окружения"""
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            openai_embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large"),
            openai_temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.0")),
            openai_max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "2000")),
            openai_timeout=int(os.getenv("OPENAI_TIMEOUT", "60")),
            qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
            qdrant_api_key=os.getenv("QDRANT_API_KEY", None),
            collection_name=os.getenv("COLLECTION_NAME", "knowledge_base"),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            rag_top_k=int(os.getenv("RAG_TOP_K", "5")),
            rag_score_threshold=float(os.getenv("RAG_SCORE_THRESHOLD", "0.7")),
            system_prompt=os.getenv("SYSTEM_PROMPT", cls.system_prompt),
        )
    
    def validate(self) -> None:
        """Проверяет обязательные параметры"""
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY не установлен")
        if not self.telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN не установлен")
