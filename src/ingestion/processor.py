"""Обработка и индексация файлов Excel/CSV"""
import re
import hashlib
from typing import List, Dict, Any, Tuple
import pandas as pd
from src.core.config import Config
from src.core.logger import setup_logger
from src.rag.embeddings import EmbeddingService
from src.rag.vector_store import VectorStore


logger = setup_logger(__name__)


class DataProcessor:
    """Процессор для обработки и индексации данных"""
    
    def __init__(self, config: Config):
        """
        Args:
            config: Конфигурация приложения
        """
        self.config = config
        self.embedding_service = EmbeddingService(config)
        self.vector_store = VectorStore(config)
    
    @staticmethod
    def normalize_data(row: pd.Series) -> Dict[str, Any]:
        """
        Нормализует данные строки
        
        Args:
            row: Строка DataFrame
        
        Returns:
            Нормализованные данные
        """
        # Объем
        try:
            volume_str = str(row.get("Объем, л", "")).replace(',', '.')
            volume = float(volume_str) if volume_str else None
        except (ValueError, AttributeError):
            volume = None
        
        # Количество ТЭНов
        ten_match = re.search(r'\d+', str(row.get("Кол-во ТЭНов", "")))
        ten_count = int(ten_match.group(0)) if ten_match else None
        
        # Мощность
        power_match = re.search(r'\d+', str(row.get("Мощность, Вт", "")))
        power = int(power_match.group(0)) if power_match else None
        
        # Количество программ
        try:
            programs_count = int(row.get("Кол-во программ", 0))
        except (ValueError, TypeError):
            programs_count = None
        
        return {
            "volume": volume,
            "ten_count": ten_count,
            "power": power,
            "programs_count": programs_count
        }
    
    @staticmethod
    def create_document_text(row: pd.Series) -> str:
        """
        Создаёт текст документа для эмбеддинга
        
        Args:
            row: Строка DataFrame
        
        Returns:
            Текст документа
        """
        return f"""
Модель: {row.get('Название модели', '')}
Артикул: {row.get('Артикул', '')}
Тип конструкции: {row.get('Тип конструкции', '')}
Объем: {row.get('Объем, л', '')} л
Кол-во ТЭНов: {row.get('Кол-во ТЭНов', '')}
Мощность: {row.get('Мощность, Вт', '')} Вт
Кол-во программ: {row.get('Кол-во программ', '')}
Список программ: {row.get('Список программ', '')}
Особенности: {row.get('Особенности', '')}
Комплектация: {row.get('Комплектация', '')}
        """.strip()
    
    @staticmethod
    def generate_id(article: str, color: str) -> str:
        """
        Генерирует уникальный ID для документа
        
        Args:
            article: Артикул
            color: Цвет
        
        Returns:
            Уникальный ID
        """
        raw_id = f"{article}_{color}"
        return hashlib.md5(raw_id.encode()).hexdigest()
    
    def process_dataframe(self, df: pd.DataFrame) -> Tuple[List[str], List[str], List[Dict[str, Any]]]:
        """
        Обрабатывает DataFrame и подготавливает данные для индексации
        
        Args:
            df: DataFrame с данными
        
        Returns:
            Кортеж (ids, texts, metadata)
        """
        # Колонки для заполнения пропусков forward fill
        columns_to_fill = [
            "Тип конструкции", "Название модели", "Артикул", "Цвет", "Фото",
            "Объем, л", "Кол-во ТЭНов", "Кол-во программ", "Список программ",
            "Мощность, Вт", "Материал корпуса", "Покрытие чаши", "Покрытие решетки",
            "Температура", "Время", "Особенности", "Комплектация",
            "Совместимость с акскессуарами", "Пример вместимости"
        ]
        
        # Заполняем пропуски
        for col in columns_to_fill:
            if col in df.columns:
                df[col] = df[col].ffill()
        
        ids = []
        texts = []
        metadata_list = []
        
        # Обрабатываем каждую строку
        for _, row in df.iterrows():
            # Пропускаем строки без модели или артикула
            if pd.isna(row.get("Название модели")) or pd.isna(row.get("Артикул")):
                continue
            
            # Создаём ID
            article = str(row.get("Артикул", ""))
            color = str(row.get("Цвет", "")).lower()
            doc_id = self.generate_id(article, color)
            
            # Создаём текст документа
            doc_text = self.create_document_text(row)
            
            # Создаём метаданные
            metadata = {k: (v if pd.notna(v) else None) for k, v in row.to_dict().items()}
            
            # Добавляем нормализованные данные
            normalized = self.normalize_data(row)
            metadata.update(normalized)
            
            ids.append(doc_id)
            texts.append(doc_text)
            metadata_list.append(metadata)
        
        logger.info(f"Подготовлено {len(ids)} документов из {len(df)} строк")
        return ids, texts, metadata_list
    
    async def process_file(self, file_path: str, recreate: bool = True) -> int:
        """
        Обрабатывает файл и индексирует данные
        
        Args:
            file_path: Путь к файлу
            recreate: Пересоздать коллекцию перед загрузкой
        
        Returns:
            Количество проиндексированных документов
        """
        logger.info(f"Начинаем обработку файла: {file_path}")
        
        # Читаем файл
        if file_path.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_path)
        elif file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            raise ValueError("Неподдерживаемый формат файла. Используйте .xlsx, .xls или .csv")
        
        # Обрабатываем данные
        ids, texts, metadata_list = self.process_dataframe(df)
        
        if not ids:
            logger.warning("Нет данных для индексации")
            return 0
        
        # Пересоздаём коллекцию если нужно
        if recreate:
            await self.vector_store.recreate_collection()
        else:
            await self.vector_store.ensure_collection()
        
        # Генерируем эмбеддинги
        logger.info("Генерация эмбеддингов...")
        vectors = await self.embedding_service.embed_batch(texts)
        
        # Загружаем в Qdrant
        logger.info("Загрузка данных в Qdrant...")
        await self.vector_store.upsert_points(
            ids=ids,
            vectors=vectors,
            texts=texts,
            metadata=metadata_list
        )
        
        logger.info(f"Успешно проиндексировано {len(ids)} документов")
        return len(ids)
