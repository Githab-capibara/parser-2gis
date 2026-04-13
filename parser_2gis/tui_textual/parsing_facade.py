"""Фасад для взаимодействия между TUI и параллельным парсером.

ISSUE-039: Создаёт уровень абстракции между TUI интерфейсом и ParallelCityParser,
устраняя прямую зависимость TUI от деталей реализации парсера.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from parser_2gis.logger import logger
from parser_2gis.parallel import ParallelCityParser
from parser_2gis.tui_textual.parsing_orchestrator import ParsingOrchestrator


class ParsingFacade:
    """Фасад для запуска парсинга из TUI.

    Отвечает за:
    - Создание и настройку ParallelCityParser
    - Управление конфигурацией (сохранение/восстановление)
    - Координацию callback'ов прогресса
    - Обработку завершения и ошибок
    - Гарантированную очистку ресурсов

    ISSUE-039: Устраняет прямую зависимость TUI от ParallelCityParser.
    """

    def __init__(self, config: Any) -> None:
        """Инициализирует фасад парсинга.

        Args:
            config: Объект конфигурации.

        """
        self._config = config
        self._orchestrator = ParsingOrchestrator()
        self._parser: ParallelCityParser | None = None

    @property
    def orchestrator(self) -> ParsingOrchestrator:
        """Возвращает оркестратор парсинга."""
        return self._orchestrator

    def run_parsing(
        self,
        cities: list[dict[str, Any]],
        categories: list[dict[str, Any]],
        output_dir: str,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> bool:
        """Запускает процесс парсинга.

        Args:
            cities: Список городов.
            categories: Список категорий.
            output_dir: Директория для вывода.
            progress_callback: Функция обновления прогресса.

        Returns:
            True если парсинг успешно завершён.

        """
        # Сохраняем оригинальные значения конфигурации
        saved_config = self._save_config_values()

        # Настраиваем конфигурацию для фонового парсинга
        self._apply_background_parsing_config()

        max_workers = getattr(self._config.parallel, "max_workers", 10)
        total_urls = len(cities) * len(categories)

        self._orchestrator.start(total_urls=total_urls, saved_config=saved_config)

        # Создаём парсер
        self._parser = ParallelCityParser(
            cities=cities,
            categories=categories,
            output_dir=output_dir,
            config=self._config,
            max_workers=max_workers,
            timeout_per_url=1800,  # 30 минут
        )

        # Создаём callback прогресса
        def internal_progress_callback(success: int, failed: int, filename: str) -> None:
            if self._orchestrator.is_cancelled():
                return
            category = filename.replace(".csv", "").split("_")[-1] if "_" in filename else ""
            self._orchestrator.update_progress(
                success=success,
                failed=failed,
                category=category,
                record=success + failed,
            )
            if progress_callback:
                progress_callback(success, failed, filename)

        try:
            output_file = f"парсинг_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.csv"
            result = self._parser.run(
                output_file=output_file,
                progress_callback=internal_progress_callback,
            )

            if self._orchestrator.is_cancelled():
                return False

            return result

        finally:
            self._cleanup_parser()
            self._restore_config_values(saved_config)
            self._orchestrator.complete()

    def stop_parsing(self) -> None:
        """Останавливает текущий процесс парсинга."""
        self._orchestrator.stop()
        if self._parser:
            try:
                self._parser.stop()
            except (OSError, RuntimeError, AttributeError) as e:
                logger.debug("Ошибка при остановке парсера: %s", e)

    def _save_config_values(self) -> dict[str, Any]:
        """Сохраняет оригинальные значения конфигурации."""
        return {
            "chrome_headless": self._config.chrome.headless,
            "chrome_disable_images": self._config.chrome.disable_images,
            "chrome_silent_browser": self._config.chrome.silent_browser,
            "parser_stop_on_first_404": self._config.parser.stop_on_first_404,
            "parser_max_consecutive_empty_pages": self._config.parser.max_consecutive_empty_pages,
            "parser_max_retries": self._config.parser.max_retries,
            "parser_retry_on_network_errors": self._config.parser.retry_on_network_errors,
        }

    def _apply_background_parsing_config(self) -> None:
        """Применяет конфигурацию для фонового парсинга."""
        self._config.chrome.headless = True
        self._config.chrome.disable_images = True
        self._config.chrome.silent_browser = True
        self._config.parser.stop_on_first_404 = True
        self._config.parser.max_consecutive_empty_pages = 5
        self._config.parser.max_retries = 3
        self._config.parser.retry_on_network_errors = True

    def _restore_config_values(self, saved_config: dict[str, Any] | None) -> None:
        """Восстанавливает оригинальные значения конфигурации."""
        if saved_config:
            self._config.chrome.headless = saved_config["chrome_headless"]
            self._config.chrome.disable_images = saved_config["chrome_disable_images"]
            self._config.chrome.silent_browser = saved_config["chrome_silent_browser"]
            self._config.parser.stop_on_first_404 = saved_config["parser_stop_on_first_404"]
            self._config.parser.max_consecutive_empty_pages = saved_config[
                "parser_max_consecutive_empty_pages"
            ]
            self._config.parser.max_retries = saved_config["parser_max_retries"]
            self._config.parser.retry_on_network_errors = saved_config[
                "parser_retry_on_network_errors"
            ]
            logger.debug("Конфигурация восстановлена после парсинга")

    def _cleanup_parser(self) -> None:
        """Очищает ресурсы парсера."""
        if self._parser:
            try:
                self._parser.stop()
                parser_stats = self._parser.get_statistics()
                logger.debug("Статистика парсера после завершения: %s", parser_stats)
            except (OSError, RuntimeError, AttributeError) as cleanup_error:
                logger.debug("Ошибка при очистке парсера: %s", cleanup_error)
