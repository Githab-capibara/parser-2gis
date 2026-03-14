#!/usr/bin/env python3
"""
Тестовый скрипт для проверки TUI интерфейса.

Запускает демонстрацию TUI без реального парсинга.
"""

import sys
import time
from pathlib import Path

# Добавляем путь к модулю
sys.path.insert(0, str(Path(__file__).parent))

from parser_2gis.tui.app import TUIManager  # noqa: E402


def test_tui_demo():
    """Демонстрация работы TUI."""
    print("🎨 Запуск демонстрации TUI...")
    print("Создаём TUI менеджер...")

    # Создаём менеджер
    tui = TUIManager(version="1.0-test", log_dir=Path("logs"), log_level="DEBUG")

    # Запускаем
    print("Запускаем TUI...")
    tui.start()

    try:
        # Имитация работы
        tui.log("Инициализация парсера...", "INFO")
        time.sleep(1)

        tui.update(
            total_urls=100,
            current_city="Омск",
            current_category="Кафе",
            total_pages=500,
        )
        tui.log("Загрузка браузера...", "DEBUG")
        time.sleep(1)

        # Имитация прогресса
        for i in range(1, 101):
            tui.progress(url=0, page=5, record=10)
            tui.update(
                current_page=i * 5,
                success_count=i * 10,
            )

            if i % 10 == 0:
                tui.log(f"Обработано {i * 5} страниц", "INFO")

            time.sleep(0.05)

        tui.log("Парсинг завершён успешно!", "SUCCESS")
        time.sleep(2)

    except KeyboardInterrupt:
        tui.log("Прервано пользователем", "WARNING")
        tui.stop(success=False)
    except Exception as e:
        tui.log(f"Ошибка: {e}", "ERROR")
        tui.stop(success=False)
    else:
        tui.stop(success=True)

    print("✅ Демонстрация завершена!")
    print(f"📄 Лог файл: {tui.log_file}")


if __name__ == "__main__":
    test_tui_demo()
