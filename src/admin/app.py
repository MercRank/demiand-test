"""Streamlit админ-панель для управления базой знаний"""
import os
import asyncio
import tempfile
import streamlit as st
from dotenv import load_dotenv

from src.core.config import Config
from src.core.logger import setup_logger
from src.ingestion.processor import DataProcessor
from src.rag.vector_store import VectorStore


# Загружаем переменные окружения
load_dotenv()

logger = setup_logger(__name__)

# Настройка страницы
st.set_page_config(
    page_title="Управление Базой Знаний",
    page_icon="📚",
    layout="wide"
)


async def get_collection_info(vector_store: VectorStore) -> dict:
    """Получает информацию о коллекции"""
    try:
        count = await vector_store.count_documents()
        return {"count": count, "error": None}
    except Exception as e:
        return {"count": 0, "error": str(e)}


async def process_uploaded_file(file_path: str, processor: DataProcessor, recreate: bool) -> dict:
    """Обрабатывает загруженный файл"""
    try:
        count = await processor.process_file(file_path, recreate=recreate)
        return {"success": True, "count": count, "error": None}
    except Exception as e:
        logger.error(f"Ошибка обработки файла: {e}", exc_info=True)
        return {"success": False, "count": 0, "error": str(e)}


def main():
    """Главная функция админ-панели"""
    st.title("📚 Управление Базой Знаний")
    
    # Загружаем конфигурацию
    try:
        config = Config.from_env()
    except Exception as e:
        st.error(f"Ошибка загрузки конфигурации: {e}")
        return
    
    # Инициализируем компоненты
    processor = DataProcessor(config)
    vector_store = VectorStore(config)
    
    # Sidebar с информацией
    with st.sidebar:
        st.header("ℹ️ Информация")
        
        if st.button("🔄 Обновить статистику"):
            st.rerun()
        
        # Показываем информацию о коллекции
        info = asyncio.run(get_collection_info(vector_store))
        
        if info["error"]:
            st.error(f"Ошибка подключения к Qdrant: {info['error']}")
        else:
            st.success("✅ Подключено к Qdrant")
            st.metric("Документов в базе", info["count"])
        
        st.divider()
        st.caption(f"Коллекция: {config.collection_name}")
        st.caption(f"Модель: {config.openai_model}")
        st.caption(f"Эмбеддинг: {config.openai_embedding_model}")
    
    # Главная область
    st.header("📁 Загрузка данных")
    st.write("Загрузите Excel или CSV файл для обновления базы знаний.")
    
    # Опция пересоздания коллекции
    recreate_collection = st.checkbox(
        "Пересоздать коллекцию (удалит все существующие данные)",
        value=True,
        help="Если включено, коллекция будет очищена перед загрузкой новых данных"
    )
    
    # Загрузчик файлов
    uploaded_file = st.file_uploader(
        "Выберите файл",
        type=['xlsx', 'xls', 'csv'],
        help="Поддерживаются форматы: .xlsx, .xls, .csv"
    )
    
    if uploaded_file is not None:
        # Показываем информацию о файле
        st.info(f"📄 Файл: {uploaded_file.name} ({uploaded_file.size / 1024:.2f} KB)")
        
        if st.button("🚀 Обработать файл", type="primary"):
            with st.spinner("Обработка файла..."):
                # Сохраняем во временный файл
                with tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=os.path.splitext(uploaded_file.name)[1]
                ) as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                # Обрабатываем файл
                result = asyncio.run(
                    process_uploaded_file(tmp_path, processor, recreate_collection)
                )
                
                # Удаляем временный файл
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
                
                # Показываем результат
                if result["success"]:
                    st.success(
                        f"✅ Файл успешно обработан!\n\n"
                        f"Проиндексировано документов: {result['count']}"
                    )
                    st.balloons()
                else:
                    st.error(f"❌ Ошибка обработки файла:\n\n{result['error']}")
    
    # Инструкция
    st.divider()
    
    with st.expander("📖 Инструкция по использованию"):
        st.markdown("""
        ### Как использовать админ-панель
        
        1. **Загрузите файл** Excel (.xlsx, .xls) или CSV (.csv)
        2. **Выберите режим**:
           - ✅ Пересоздать коллекцию — очистит базу и загрузит новые данные
           - ❌ Добавить к существующим — добавит данные к текущим
        3. **Нажмите "Обработать файл"**
        4. **Дождитесь завершения** — система обработает данные и создаст эмбеддинги
        
        ### Формат файла
        
        Файл должен содержать колонки:
        - Название модели
        - Артикул
        - Тип конструкции
        - Объем, л
        - Кол-во ТЭНов
        - Мощность, Вт
        - Кол-во программ
        - Список программ
        - Особенности
        - Комплектация
        - и другие характеристики
        
        ### Что происходит при обработке
        
        1. Файл читается и нормализуется
        2. Генерируются эмбеддинги через OpenAI API
        3. Данные сохраняются в векторную базу Qdrant
        4. Бот сразу начинает использовать новые данные
        """)


if __name__ == "__main__":
    main()
