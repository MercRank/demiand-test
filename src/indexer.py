import os
import pandas as pd
import json
import re
import hashlib
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Qdrant
from langchain.schema import Document
from qdrant_client import QdrantClient
from qdrant_client.http import models
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Конфигурация Qdrant и OpenAI
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "airfryers"  # Используем то же имя коллекции, что и в n8n
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def get_qdrant_client():
    """Создает и возвращает клиент Qdrant."""
    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

def create_collection_if_not_exists():
    """Проверяет наличие коллекции в Qdrant и создает её, если она отсутствует."""
    client = get_qdrant_client()
    collections = client.get_collections().collections
    collection_names = [c.name for c in collections]
    
    if COLLECTION_NAME not in collection_names:
        # Создаем коллекцию с размером вектора 3072 (для text-embedding-3-large)
        # В n8n использовалась модель text-embedding-3-large, у нее размерность 3072
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(size=3072, distance=models.Distance.COSINE),
        )
        print(f"Коллекция '{COLLECTION_NAME}' успешно создана.")
    else:
        print(f"Коллекция '{COLLECTION_NAME}' уже существует.")

def string_to_numeric_id(s):
    """Генерирует числовой ID из строки (аналог функции из n8n)."""
    hash_val = 0
    for char in s:
        hash_val = ((hash_val << 5) - hash_val) + ord(char)
        hash_val |= 0  # Convert to 32bit integer
    return abs(hash_val)

def process_file(file_path):
    """
    Читает Excel или CSV файл, обрабатывает данные (заполнение пропусков, нормализация),
    генерирует эмбеддинги и загружает их в Qdrant.
    """
    print(f"Начинаем обработку файла: {file_path}")
    
    # Чтение файла
    if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
        df = pd.read_excel(file_path)
    elif file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    else:
        raise ValueError("Неподдерживаемый формат файла. Пожалуйста, загрузите .xlsx или .csv")

    # Список колонок для заполнения (forward fill logic from n8n)
    columns_to_fill = [
        "Тип конструкции", "Название модели", "Артикул", "Цвет", "Фото",
        "Объем, л", "Кол-во ТЭНов", "Кол-во программ", "Список программ",
        "Мощность, Вт", "Материал корпуса", "Покрытие чаши", "Покрытие решетки",
        "Температура", "Время", "Особенности", "Комплектация",
        "Совместимость с акскессуарами", "Пример вместимости"
    ]

    # Заполнение пропусков (аналог логики из n8n node "парсим док")
    # В pandas это делается проще через ffill, но сделаем аккуратно для выбранных колонок
    for col in columns_to_fill:
        if col in df.columns:
            df[col] = df[col].ffill()

    documents = []
    
    # Итерация по строкам и подготовка данных
    for index, row in df.iterrows():
        # Пропускаем строки, где нет модели или артикула (на всякий случай)
        if pd.isna(row.get("Название модели")) or pd.isna(row.get("Артикул")):
            continue

        # ===== Нормализация данных (аналог node "Заполняем пустые поля форвардом") =====
        
        # Объем
        try:
            volume = float(str(row.get("Объем, л", "")).replace(',', '.'))
        except ValueError:
            volume = None

        # Кол-во ТЭНов
        ten_match = re.search(r'\d+', str(row.get("Кол-во ТЭНов", "")))
        ten_count = int(ten_match.group(0)) if ten_match else None

        # Мощность
        power_match = re.search(r'\d+', str(row.get("Мощность, Вт", "")))
        power = int(power_match.group(0)) if power_match else None

        # Кол-во программ
        try:
            programs_count = int(row.get("Кол-во программ"))
        except (ValueError, TypeError):
            programs_count = None

        # Формируем полный объект метаданных (payload)
        metadata = row.to_dict()
        # Очищаем от NaN значений для корректного JSON
        metadata = {k: (v if pd.notna(v) else None) for k, v in metadata.items()}
        
        # Добавляем нормализованные поля
        metadata.update({
            "model": row.get("Название модели"),
            "article": row.get("Артикул"),
            "type": str(row.get("Тип конструкции", "")).lower(),
            "color": str(row.get("Цвет", "")).lower(),
            "volume": volume,
            "ten_count": ten_count,
            "programs_count": programs_count,
            "power": power
        })

        # ===== Формирование текста для эмбеддинга (аналог node "Code in JavaScript3") =====
        # В n8n использовался формат:
        # Модель: ...
        # Артикул: ...
        # ...
        
        document_text = f"""
Модель: {metadata.get('Название модели', '')}
Артикул: {metadata.get('Артикул', '')}
Тип конструкции: {metadata.get('Тип конструкции', '')}
Объем: {metadata.get('Объем, л', '')} л
Кол-во ТЭНов: {metadata.get('Кол-во ТЭНов', '')}
Мощность: {metadata.get('Мощность, Вт', '')}
Программы: {metadata.get('Список программ', '')}
Особенности: {metadata.get('Особенности', '')}
        """.strip()

        # Генерация ID (аналог node "Code in JavaScript2")
        # id: base.article + "_" + base.color -> stringToNumericId
        raw_id = f"{metadata.get('article')}_{metadata.get('color')}"
        doc_id = string_to_numeric_id(raw_id)

        # Создаем документ LangChain
        # Важно: мы сохраняем document_text как page_content, чтобы поиск шел по нему
        doc = Document(
            page_content=document_text,
            metadata=metadata
        )
        # Мы не можем явно задать ID в объекте Document для Qdrant через LangChain стандартным способом,
        # но Qdrant wrapper может обрабатывать ids если передать их отдельно.
        # Однако, проще позволить Qdrant сгенерировать UUID или использовать add_documents.
        # Для совместимости с n8n логикой ID, нам пришлось бы использовать raw client.
        # Но для простоты RAG агента, стандартный механизм LangChain тоже подойдет.
        # Если критично сохранить ID как в n8n, нужно использовать client.upsert.
        
        # Для "легкости" решения используем стандартный LangChain подход, 
        # но добавим наш ID в метаданные на всякий случай.
        doc.metadata["custom_id"] = doc_id
        documents.append(doc)

    print(f"Подготовлено {len(documents)} документов из {len(df)} строк.")

    # Инициализация эмбеддингов
    # Используем ту же модель, что и в n8n: text-embedding-3-large
    embeddings = OpenAIEmbeddings(
        openai_api_key=OPENAI_API_KEY,
        model="text-embedding-3-large"
    )

    # Загрузка в Qdrant
    create_collection_if_not_exists()
    
    # Используем Qdrant.from_documents для простоты
    # Это создаст векторы и загрузит их
    Qdrant.from_documents(
        documents,
        embeddings,
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        collection_name=COLLECTION_NAME,
        force_recreate=True # Пересоздаем коллекцию при каждой полной загрузке файла, чтобы избежать дублей
        # Если нужно добавлять, можно поставить False, но тогда нужно следить за дубликатами
    )
    
    print(f"Успешно проиндексировано {len(documents)} документов в Qdrant.")

if __name__ == "__main__":
    # Тестовый запуск
    pass
