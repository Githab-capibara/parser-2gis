"""
Модуль для файлового логирования.

Предоставляет функциональность для записи логов в файл с поддержкой вращения логов.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


class FileLogger:
    """Логгер с поддержкой записи в файл.
    
    Этот класс предоставляет возможность логирования работы парсера в файл
    для отладки и мониторинга. Поддерживает вращение логов (log rotation)
    для экономии дискового пространства.
    
    Attributes:
        _log_file: Путь к файлу логов
        _log_level: Уровень логирования
        _max_bytes: Максимальный размер файла в байтах
        _backup_count: Количество резервных копий
        _file_handler: Обработчик файла для логирования
    
    Пример использования:
        >>> logger = FileLogger(Path('/var/log/parser.log'), 'DEBUG')
        >>> logger.setup_logger(logging.getLogger('parser-2gis'))
    """
    
    def __init__(
        self,
        log_file: Optional[Path] = None,
        log_level: str = "DEBUG",
        max_bytes: int = 10 * 1024 * 1024,  # 10 MB
        backup_count: int = 5
    ):
        """Инициализация файлового логгера.
        
        Args:
            log_file: Путь к файлу логов. Если None, логирование в файл отключено.
            log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL).
            max_bytes: Максимальный размер файла в байтах перед вращением.
            backup_count: Количество резервных копий логов.
            
        Raises:
            ValueError: Если log_level имеет некорректное значение.
        """
        self._log_file = log_file
        
        # Валидация уровня логирования
        try:
            self._log_level = getattr(logging, log_level.upper())
        except AttributeError:
            raise ValueError(f"Некорректный уровень логирования: {log_level}")
        
        self._max_bytes = max_bytes
        self._backup_count = backup_count
        self._file_handler: Optional[RotatingFileHandler] = None
        
        # Если указан файл логов, настраиваем обработчик
        if log_file:
            self._setup_file_handler()
    
    def _setup_file_handler(self) -> None:
        """Настройка обработчика файла для логирования.
        
        Создает директорию для логов если она не существует,
        и настраивает RotatingFileHandler для автоматического
        вращения логов при достижении максимального размера.
        """
        # Создаём директорию для логов, если её нет
        if self._log_file:
            self._log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Создаём rotating file handler
        self._file_handler = RotatingFileHandler(
            filename=str(self._log_file),
            maxBytes=self._max_bytes,
            backupCount=self._backup_count,
            encoding='utf-8'
        )
        
        # Форматирование логов
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self._file_handler.setFormatter(formatter)
        self._file_handler.setLevel(self._log_level)
    
    def setup_logger(self, logger: logging.Logger) -> None:
        """Настройка логгера для записи в файл.
        
        Добавляет файловый обработчик к указанному логгеру.
        
        Args:
            logger: Логгер для настройки (экземпляр logging.Logger).
        """
        if self._file_handler:
            logger.addHandler(self._file_handler)
            # Устанавливаем минимальный уровень логирования
            if logger.level == 0 or logger.level > self._log_level:
                logger.setLevel(self._log_level)
    
    def close(self) -> None:
        """Закрытие обработчика файла.
        
        Корректно закрывает файловый обработчик и освобождает ресурсы.
        Должен вызываться при завершении работы программы.
        """
        if self._file_handler:
            self._file_handler.close()
            self._file_handler = None
    
    def __enter__(self) -> 'FileLogger':
        """Контекстный менеджер для автоматического закрытия.
        
        Returns:
            Экземпляр FileLogger для использования в with-блоке.
        """
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Автоматическое закрытие при выходе из контекста."""
        self.close()
    
    @property
    def log_file(self) -> Optional[Path]:
        """Путь к файлу логов.
        
        Returns:
            Путь к файлу логов или None, если логирование в файл отключено.
        """
        return self._log_file
    
    @property
    def is_enabled(self) -> bool:
        """Проверка, включено ли логирование в файл.
        
        Returns:
            True, если логирование в файл включено, иначе False.
        """
        return self._file_handler is not None