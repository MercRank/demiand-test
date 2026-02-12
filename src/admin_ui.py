import streamlit as st
import os
import tempfile
from indexer import process_file

# Настройка страницы
st.set_page_config(page_title="Управление Базой Знаний", page_icon="📚")

st.title("📚 Управление Базой Знаний")
st.write("Загрузите Excel или CSV файл для обновления базы знаний.")

# Загрузчик файлов
uploaded_file = st.file_uploader("Выберите файл", type=['xlsx', 'xls', 'csv'])

if uploaded_file is not None:
    if st.button("Обработать файл"):
        with st.spinner("Обработка файла..."):
            try:
                # Сохраняем загруженный файл во временный файл
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name

                # Запускаем процесс индексации
                process_file(tmp_path)

                # Удаляем временный файл
                os.remove(tmp_path)

                st.success(f"Файл {uploaded_file.name} успешно обработан и добавлен в базу знаний!")
            except Exception as e:
                st.error(f"Ошибка при обработке файла: {e}")

st.markdown("---")
st.subheader("Инструкция")
st.markdown("""
1. Загрузите файл Excel (.xlsx) или CSV (.csv).
2. Нажмите кнопку 'Обработать файл'.
3. Система прочитает файл, сгенерирует эмбеддинги и обновит векторную базу данных Qdrant.
""")
