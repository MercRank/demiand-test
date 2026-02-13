"""Модуль для генерации эмбеддингов через OpenAI API"""
from typing import List
import openai
from openai import AsyncOpenAI
from src.core.config import Config
from src.core.logger import setup_logger


logger = setup_logger(__name__)


class EmbeddingService:
    """Сервис для генерации эмбеддингов текста"""
    
    def __init__(self, config: Config):
        """
        Args:
            config: Конфигурация приложения
        """
        self.config = config
        self.client = AsyncOpenAI(
            api_key=config.openai_api_key,
            timeout=config.openai_timeout
        )
        self.model = config.openai_embedding_model
        self.embedding_dim = 3072  # text-embedding-3-large
    
    async def embed_text(self, text: str) -> List[float]:
        """
        Генерирует эмбеддинг для текста
        
        Args:
            text: Текст для эмбеддинга
        
        Returns:
            Вектор эмбеддинга
        """
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
                encoding_format="float"
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Ошибка генерации эмбеддинга: {e}")
            raise
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Генерирует эмбеддинги для списка текстов
        
        Args:
            texts: Список текстов
        
        Returns:
            Список векторов эмбеддингов
        """
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=texts,
                encoding_format="float"
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"Ошибка генерации batch эмбеддингов: {e}")
            raise
