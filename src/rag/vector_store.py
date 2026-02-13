"""Модуль для работы с Qdrant векторной базой данных"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
    SearchParams,
    Filter,
    FieldCondition,
    MatchValue
)
from src.core.config import Config
from src.core.logger import setup_logger


logger = setup_logger(__name__)


@dataclass
class SearchResult:
    """Результат поиска в векторной базе"""
    id: str
    score: float
    text: str
    metadata: Dict[str, Any]


class VectorStore:
    """Сервис для работы с Qdrant векторной базой"""
    
    def __init__(self, config: Config):
        """
        Args:
            config: Конфигурация приложения
        """
        self.config = config
        self.client = AsyncQdrantClient(
            url=config.qdrant_url,
            api_key=config.qdrant_api_key
        )
        self.collection_name = config.collection_name
        self.embedding_dim = 3072  # text-embedding-3-large
    
    async def ensure_collection(self) -> None:
        """Создаёт коллекцию, если она не существует"""
        try:
            collections = await self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if self.collection_name not in collection_names:
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dim,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Создана коллекция: {self.collection_name}")
            else:
                logger.info(f"Коллекция уже существует: {self.collection_name}")
        except Exception as e:
            logger.error(f"Ошибка создания коллекции: {e}")
            raise
    
    async def recreate_collection(self) -> None:
        """Пересоздаёт коллекцию (удаляет и создаёт заново)"""
        try:
            await self.client.delete_collection(collection_name=self.collection_name)
            logger.info(f"Удалена коллекция: {self.collection_name}")
        except Exception:
            logger.info(f"Коллекция не существовала: {self.collection_name}")
        
        await self.ensure_collection()
    
    async def upsert_points(
        self,
        ids: List[str],
        vectors: List[List[float]],
        texts: List[str],
        metadata: List[Dict[str, Any]]
    ) -> None:
        """
        Добавляет или обновляет точки в коллекции
        
        Args:
            ids: Список ID документов
            vectors: Список векторов эмбеддингов
            texts: Список текстов документов
            metadata: Список метаданных документов
        """
        try:
            points = [
                PointStruct(
                    id=id_,
                    vector=vector,
                    payload={
                        "text": text,
                        **meta
                    }
                )
                for id_, vector, text, meta in zip(ids, vectors, texts, metadata)
            ]
            
            await self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            logger.info(f"Добавлено {len(points)} документов в коллекцию")
        except Exception as e:
            logger.error(f"Ошибка добавления документов: {e}")
            raise
    
    async def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        score_threshold: Optional[float] = None
    ) -> List[SearchResult]:
        """
        Выполняет поиск по вектору запроса
        
        Args:
            query_vector: Вектор запроса
            top_k: Количество результатов
            score_threshold: Минимальный порог схожести
        
        Returns:
            Список результатов поиска
        """
        try:
            results = await self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,
                score_threshold=score_threshold
            )
            
            return [
                SearchResult(
                    id=str(result.id),
                    score=result.score,
                    text=result.payload.get("text", ""),
                    metadata={k: v for k, v in result.payload.items() if k != "text"}
                )
                for result in results
            ]
        except Exception as e:
            logger.error(f"Ошибка поиска: {e}")
            raise
    
    async def count_documents(self) -> int:
        """Возвращает количество документов в коллекции"""
        try:
            collection_info = await self.client.get_collection(
                collection_name=self.collection_name
            )
            return collection_info.points_count
        except Exception as e:
            logger.error(f"Ошибка получения количества документов: {e}")
            return 0
