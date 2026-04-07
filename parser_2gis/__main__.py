"""Главный модуль для запуска Parser2GIS через `python -m parser_2gis`.

Этот модуль позволяет запускать парсер как пакет из командной строки:
    python -m parser_2gis --help
    python -m parser_2gis --url https://2gis.ru/moscow/search/Аптеки -o output.csv -f csv
"""

from . import main
from .chrome.browser import cleanup_orphaned_profiles
from .logger import logger

if __name__ == "__main__":
    # Очистка осиротевших профилей Chrome от предыдущих запусков
    # Это предотвращает накопление временных файлов после аварийных завершений
    try:
        deleted_count = cleanup_orphaned_profiles()
        if deleted_count > 0:
            logger.info("Очищено %d осиротевших профилей Chrome", deleted_count)
    except (OSError, RuntimeError) as e:
        logger.warning("Ошибка при очистке осиротевших профилей: %s", e)

    # Запуск основного приложения
    main()
