"""
TUI интеграция для параллельного парсинга.

Предоставляет обёртки и утилиты для использования TUI интерфейса
при параллельном парсинге городов и категорий.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from ..config import Configuration


class TUIParallelParserWrapper:
    """
    Обёртка для ParallelCityParser с поддержкой TUI.

    Перехватывает логи и прогресс, отправляя их в TUI интерфейс.
    """

    def __init__(
        self,
        tui_manager: Any,  # TUIManager
        cities: list[dict],
        categories: list[dict],
        output_dir: str,
        config: Configuration,
        max_workers: int = 3,
    ) -> None:
        """
        Инициализация обёртки.

        Args:
            tui_manager: Менеджер TUI
            cities: Список городов
            categories: Список категорий
            output_dir: Директория для выходных файлов
            config: Конфигурация
            max_workers: Количество потоков
        """
        from ..parallel_parser import ParallelCityParser

        self._tui = tui_manager
        self._cities = cities
        self._categories = categories
        self._output_dir = output_dir
        self._config = config
        self._max_workers = max_workers

        # Создаём парсер
        self._parser = ParallelCityParser(
            cities=cities,
            categories=categories,
            output_dir=output_dir,
            config=config,
            max_workers=max_workers,
        )

        # Счётчики
        self._total_urls = len(cities) * len(categories)
        self._completed = 0
        self._success = 0
        self._failed = 0

    def _create_progress_callback(self) -> Callable[[int, int, str], None]:
        """
        Создать callback для обновления прогресса.

        Returns:
            Функция обратного вызова
        """

        def callback(success: int, failed: int, filename: str) -> None:
            self._completed = success + failed
            self._success = success
            self._failed = failed

            # Обновляем TUI
            self._tui.progress(url=1)  # Один URL завершён
            self._tui.update(
                success_count=success,
                error_count=failed,
                current_category=filename.replace(".csv", "").split("_")[-1] if "_" in filename else "",
            )

            # Логируем в TUI
            if success % 5 == 0 or failed > 0:
                self._tui.log(f"Обработано: {success} успешно, {failed} ошибок", "INFO")

        return callback

    def run(self, output_file: Optional[str] = None) -> bool:
        """
        Запустить парсинг с TUI.

        Args:
            output_file: Файл для объединённого результата

        Returns:
            True если успешно
        """
        # Инициализируем TUI
        self._tui.update(
            total_urls=self._total_urls,
            current_city=self._cities[0]["name"] if self._cities else "",
            current_category=self._categories[0]["name"] if self._categories else "",
        )

        self._tui.log(
            f"Запуск парсинга: {len(self._cities)} городов × {len(self._categories)} категорий",
            "INFO",
        )
        self._tui.log(f"Потоков: {self._max_workers}", "DEBUG")

        # Создаём callback
        progress_callback = self._create_progress_callback()

        # Запускаем парсинг
        try:
            result = self._parser.run(
                output_file=output_file,
                progress_callback=progress_callback,
            )

            if result:
                self._tui.log("Парсинг завершён успешно!", "SUCCESS")
            else:
                self._tui.log("Парсинг завершён с ошибками", "ERROR")

            return result

        except KeyboardInterrupt:
            self._tui.log("Парсинг прерван пользователем", "WARNING")
            self._parser.stop()
            return False
        except Exception as e:
            self._tui.log(f"Критическая ошибка: {e}", "ERROR")
            return False


def run_parallel_with_tui(
    cities: list[dict],
    categories: list[dict],
    output_dir: str,
    config: Configuration,
    max_workers: int = 3,
    output_file: Optional[str] = None,
    version: str = "1.0",
) -> bool:
    """
    Запустить параллельный парсинг с TUI интерфейсом.

    Args:
        cities: Список городов
        categories: Список категорий
        output_dir: Директория для выходных файлов
        config: Конфигурация
        max_workers: Количество потоков
        output_file: Файл для объединённого результата
        version: Версия приложения

    Returns:
        True если успешно
    """
    from .app import TUIManager

    # Создаём TUI менеджер
    tui = TUIManager(version=version, log_dir=Path("logs"), log_level="DEBUG")

    # Запускаем TUI
    tui.start()

    try:
        # Создаём обёртку
        wrapper = TUIParallelParserWrapper(
            tui_manager=tui,
            cities=cities,
            categories=categories,
            output_dir=output_dir,
            config=config,
            max_workers=max_workers,
        )

        # Запускаем парсинг
        result = wrapper.run(output_file)

        # Останавливаем TUI
        tui.stop(success=result)

        return result

    except Exception:
        tui.stop(success=False)
        raise
