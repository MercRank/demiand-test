"""Централизованная настройка логирования"""
import logging
import sys
from typing import Optional


def setup_logger(
    name: str,
    level: int = logging.INFO,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Создаёт и настраивает логгер
    
    Args:
        name: Имя логгера
        level: Уровень логирования
        format_string: Формат логов
    
    Returns:
        Настроенный логгер
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Удаляем существующие хендлеры
    logger.handlers.clear()
    
    # Консольный хендлер
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(format_string))
    
    logger.addHandler(handler)
    
    return logger
