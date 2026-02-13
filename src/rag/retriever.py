"""Модуль для RAG retrieval логики"""
from typing import List, Optional
from dataclasses import dataclass
from openai import AsyncOpenAI
from src.core.config import Config
from src.core.logger import setup_logger
from src.rag.embeddings import EmbeddingService
from src.rag.vector_store import VectorStore, SearchResult


logger = setup_logger(__name__)


@dataclass
class RAGResponse:
    """Ответ RAG системы"""
    answer: str
    sources: List[SearchResult]
    context_used: str


class RAGRetriever:
    """Сервис для выполнения RAG запросов"""
    
    def __init__(self, config: Config):
        """
        Args:
            config: Конфигурация приложения
        """
        self.config = config
        self.embedding_service = EmbeddingService(config)
        self.vector_store = VectorStore(config)
        self.openai_client = AsyncOpenAI(
            api_key=config.openai_api_key,
            timeout=config.openai_timeout
        )
    
    async def retrieve(self, query: str) -> List[SearchResult]:
        """
        Выполняет поиск релевантных документов
        
        Args:
            query: Текст запроса
        
        Returns:
            Список релевантных документов
        """
        # Генерируем эмбеддинг запроса
        query_vector = await self.embedding_service.embed_text(query)
        
        # Ищем похожие документы
        results = await self.vector_store.search(
            query_vector=query_vector,
            top_k=self.config.rag_top_k,
            score_threshold=self.config.rag_score_threshold
        )
        
        logger.info(f"Найдено {len(results)} релевантных документов для запроса")
        return results
    
    def _build_context(self, results: List[SearchResult]) -> str:
        """
        Формирует контекст из результатов поиска
        
        Args:
            results: Результаты поиска
        
        Returns:
            Отформатированный контекст
        """
        if not results:
            return "Контекст не найден."
        
        context_parts = []
        for i, result in enumerate(results, 1):
            context_parts.append(f"Документ {i} (релевантность: {result.score:.2f}):\n{result.text}")
        
        return "\n\n".join(context_parts)
    
    async def generate_answer(
        self,
        query: str,
        results: List[SearchResult],
        stream: bool = False
    ) -> RAGResponse:
        """
        Генерирует ответ на основе контекста
        
        Args:
            query: Запрос пользователя
            results: Результаты поиска
            stream: Использовать ли streaming
        
        Returns:
            Ответ RAG системы
        """
        context = self._build_context(results)
        
        messages = [
            {"role": "system", "content": self.config.system_prompt},
            {"role": "user", "content": f"Контекст:\n{context}\n\nВопрос: {query}"}
        ]
        
        try:
            if stream:
                # Streaming ответ для Telegram
                response = await self.openai_client.chat.completions.create(
                    model=self.config.openai_model,
                    messages=messages,
                    temperature=self.config.openai_temperature,
                    max_tokens=self.config.openai_max_tokens,
                    stream=True
                )
                
                full_answer = ""
                async for chunk in response:
                    if chunk.choices[0].delta.content:
                        full_answer += chunk.choices[0].delta.content
                
                return RAGResponse(
                    answer=full_answer,
                    sources=results,
                    context_used=context
                )
            else:
                # Обычный ответ
                response = await self.openai_client.chat.completions.create(
                    model=self.config.openai_model,
                    messages=messages,
                    temperature=self.config.openai_temperature,
                    max_tokens=self.config.openai_max_tokens
                )
                
                answer = response.choices[0].message.content
                
                return RAGResponse(
                    answer=answer,
                    sources=results,
                    context_used=context
                )
        except Exception as e:
            logger.error(f"Ошибка генерации ответа: {e}")
            raise
    
    async def query(self, question: str, stream: bool = False) -> RAGResponse:
        """
        Полный RAG pipeline: поиск + генерация ответа
        
        Args:
            question: Вопрос пользователя
            stream: Использовать ли streaming
        
        Returns:
            Ответ RAG системы
        """
        # Поиск релевантных документов
        results = await self.retrieve(question)
        
        # Генерация ответа
        response = await self.generate_answer(question, results, stream=stream)
        
        return response
