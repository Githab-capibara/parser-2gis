"""Мост между инфраструктурным логгером и презентационным визуальным логгером.

ISSUE 106: Устраняет нарушение слоёв — инфраструктурный logger/logger.py
не импортирует напрямую visual_logger (презентационный слой).
Вместо этого используется LoggerPresentationBridge, который опционально
делегирование к visual_logger.

Пример использования:
    >>> from parser_2gis.logger import LoggerPresentationBridge
    >>> bridge = LoggerPresentationBridge()
    >>> bridge.log_parser_start("1.0.0", 10, "output.csv", "csv")
"""

from __future__ import annotations

from typing import Any


class LoggerPresentationBridge:
    """Мост между инфраструктурным и презентационным слоями логирования.

    ISSUE 106: Инфраструктурный логгер (logger.py) использует этот мост
    для опциональной делегации к visual_logger, устраняя прямую зависимость
    infrastructure -> presentation.

    По умолчанию visual_logger отключён для предотвращения побочных эффектов.
    Для включения необходимо вызвать enable_visual_logger().
    """

    def __init__(self) -> None:
        """Инициализирует мост с отключённым визуальным логгером."""
        self._enabled: bool = False

    def enable(self) -> None:
        """Включает делегирование к визуальном логгеру."""
        self._enabled = True

    def disable(self) -> None:
        """Отключает делегирование к визуальном логгеру."""
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        """Возвращает состояние делегирования."""
        return self._enabled

    def log_parser_start(
        self,
        version: str,
        urls_count: int,
        output_path: str,
        output_format: str,
        config_summary: dict[str, Any] | None = None,
    ) -> None:
        """Логирует запуск парсера через визуальный логгер.

        Args:
            version: Версия парсера.
            urls_count: Количество URL для парсинга.
            output_path: Путь к выходному файлу.
            output_format: Формат выходного файла.
            config_summary: Краткая сводка конфигурации.

        """
        if not self._enabled:
            return

        from .visual_logger import Emoji, print_config, print_header

        # Заголовок
        print_header(f"{Emoji.START} Parser2GIS запущен", subtitle=f"Версия: {version}")

        # Основная информация
        main_info = {
            "URL для парсинга": str(urls_count),
            "Выходной файл": output_path,
            "Формат": format.upper(),
        }
        print_config("📋 Основная информация", main_info)

        # Конфигурация браузера
        if config_summary:
            if "chrome" in config_summary:
                print_config("🌐 Браузер", config_summary["chrome"])

            if "parser" in config_summary:
                print_config("🔎 Парсер", config_summary["parser"])

            if "writer" in config_summary:
                print_config("📄 Writer", config_summary["writer"])

    def log_parser_finish(
        self, success: bool = True, stats: dict[str, Any] | None = None, duration: str | None = None
    ) -> None:
        """Логирует завершение парсера через визуальный логгер.

        Args:
            success: Успешно ли завершено.
            stats: Статистика работы.
            duration: Продолжительность работы.

        """
        if not self._enabled:
            return

        from .visual_logger import Emoji, print_error, print_header, print_stats, print_success

        emoji = Emoji.SUCCESS if success else Emoji.ERROR
        title = f"{emoji} Парсинг завершён"

        if success:
            print_success("Парсинг успешно завершён!")
        else:
            print_error("Парсинг завершён с ошибками")

        # Статистика
        if stats:
            if duration:
                stats_copy = dict(stats)
                stats_copy["Время работы"] = duration
                print_stats(stats_copy, title="📊 Итоговая статистика")
            else:
                print_stats(stats, title="📊 Итоговая статистика")

        print_header(title)


# Глобальный экземпляр моста (по умолчанию отключён)
logger_presentation_bridge = LoggerPresentationBridge()
