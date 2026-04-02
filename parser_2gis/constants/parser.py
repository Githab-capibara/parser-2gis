"""Константы парсера для parser-2gis.

Этот модуль содержит константы связанные с парсингом:
- Параметры параллельного выполнения
- Таймауты
- Лимиты ресурсов

Пример использования:
    >>> from parser_2gis.constants.parser import MAX_WORKERS, DEFAULT_TIMEOUT
    >>> print(f"Максимальное количество workers: {MAX_WORKERS}")
"""

from __future__ import annotations

# =============================================================================
# ПАРАЛЛЕЛЬНЫЙ ПАРСИНГ
# =============================================================================

# Минимальное количество workers
MIN_WORKERS: int = 1

# Максимальное количество workers
MAX_WORKERS: int = 50

# Минимальный таймаут в секундах
MIN_TIMEOUT: int = 60

# Максимальный таймаут в секундах
MAX_TIMEOUT: int = 72000

# Таймаут по умолчанию в секундах
DEFAULT_TIMEOUT: int = 7200

# Интервал очистки временных файлов в секундах
TEMP_FILE_CLEANUP_INTERVAL: int = 120

# Максимальное количество временных файлов для мониторинга
MAX_TEMP_FILES_MONITORING: int = 1000

# Возраст orphaned временных файлов в секундах
ORPHANED_TEMP_FILE_AGE: int = 600

# Таймаут блокировки для merge операций
MERGE_LOCK_TIMEOUT: int = 7200

# Максимальный возраст lock файла в секундах
MAX_LOCK_FILE_AGE: int = 120

# Максимальное количество временных файлов
MAX_TEMP_FILES: int = 1000

# Интервал обновления прогресса
PROGRESS_UPDATE_INTERVAL: int = 3

# Задержка по умолчанию
DEFAULT_SLEEP_TIME: float = 0.1


# =============================================================================
# ЛИМИТЫ ПАРСЕРА
# =============================================================================

# Максимальное количество посещённых ссылок в памяти
MAX_VISITED_LINKS_SIZE: int = 10000

# Коэффициент для расчёта max_records
MAX_RECORDS_MEMORY_COEFFICIENT: int = 550

# Делитель для расчёта max_records
MAX_RECORDS_MEMORY_DIVISOR: int = 1024

# Базовое смещение для расчёта max_records
MAX_RECORDS_BASE_OFFSET: int = 400

# Порог памяти для вызова gc.collect() (MB)
GC_MEMORY_THRESHOLD_MB: int = 100

# =============================================================================
# POLLING КОНСТАНТЫ
# =============================================================================

# Интервал polling по умолчанию (сек)
DEFAULT_POLL_INTERVAL: float = 0.1

# Максимальный интервал polling (сек)
MAX_POLL_INTERVAL: float = 1.0

# Множитель для экспоненциальной задержки
EXPONENTIAL_BACKOFF_MULTIPLIER: float = 2.0


__all__ = [
    "MIN_WORKERS",
    "MAX_WORKERS",
    "MIN_TIMEOUT",
    "MAX_TIMEOUT",
    "DEFAULT_TIMEOUT",
    "TEMP_FILE_CLEANUP_INTERVAL",
    "MAX_TEMP_FILES_MONITORING",
    "ORPHANED_TEMP_FILE_AGE",
    "MERGE_LOCK_TIMEOUT",
    "MAX_LOCK_FILE_AGE",
    "MAX_TEMP_FILES",
    "PROGRESS_UPDATE_INTERVAL",
    "DEFAULT_SLEEP_TIME",
    "MAX_VISITED_LINKS_SIZE",
    "MAX_RECORDS_MEMORY_COEFFICIENT",
    "MAX_RECORDS_MEMORY_DIVISOR",
    "MAX_RECORDS_BASE_OFFSET",
    "GC_MEMORY_THRESHOLD_MB",
    # Polling
    "DEFAULT_POLL_INTERVAL",
    "MAX_POLL_INTERVAL",
    "EXPONENTIAL_BACKOFF_MULTIPLIER",
]
