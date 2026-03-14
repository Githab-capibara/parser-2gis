"""
Точка входа для запуска TUI с автоматическим парсингом Омска.

Запускает новый TUI интерфейс на pytermgui с немедленным стартом парсинга
Омска в 10 параллельных потоков по всем 93 категориям.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..config import Configuration
from ..data.categories_93 import CATEGORIES_93
from .app import TUIApp


def run_omsk_parallel() -> None:
    """
    Запустить парсинг Омска в 10 параллельных потоков с новым TUI.

    Точка входа для run.sh.

    Конфигурация:
    - Город: Омск
    - Категории: все 93
    - Потоков: 10
    - Chrome: headless, без изображений
    """
    # Загрузить конфигурацию
    config = Configuration.load_config()

    # Настроить параметры для быстрого парсинга
    config.chrome.headless = True
    config.chrome.disable_images = True
    config.chrome.silent_browser = True
    config.chrome.memory_limit = 2048  # 2GB лимит

    config.parser.stop_on_first_404 = True
    config.parser.max_consecutive_empty_pages = 5
    config.parser.max_retries = 3
    config.parser.retry_on_network_errors = True
    config.parser.retry_delay_base = 1
    config.parser.memory_threshold = 2048

    config.writer.verbose = True
    config.writer.csv.remove_empty_columns = True
    config.writer.csv.remove_duplicates = True

    # Загрузить города и найти Омск
    cities_path = Path(__file__).parent.parent / "data" / "cities.json"
    with open(cities_path, "r", encoding="utf-8") as f:
        all_cities = json.load(f)

    omsk_city = None
    for city in all_cities:
        if city.get("code") == "omsk":
            omsk_city = city
            break

    if not omsk_city:
        print("Ошибка: город Омск не найден в базе городов")
        return

    # Создать приложение
    app = TUIApp()

    # Установить выбранные города и категории
    app.selected_cities = ["Омск"]
    app.selected_categories = [cat["name"] for cat in CATEGORIES_93]

    # Запустить TUI - парсинг начнётся автоматически
    app.run()


if __name__ == "__main__":
    run_omsk_parallel()
