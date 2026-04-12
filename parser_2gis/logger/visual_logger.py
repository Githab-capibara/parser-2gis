"""Модуль визуального логирования.

Предоставляет утилиты для красивого форматирования логов:
- Emoji для различных типов событий
- Цветовое выделение (ANSI коды)
- Форматированные заголовки секций
- Прогресс-бары и статистика

Примечание о дизайне:
    Этот модуль намеренно использует print() для вывода в консоль вместо
    стандартной системы логирования (logging). Причина в том, что VisualLogger
    предназначен для визуального интерактивного отображения информации
    непосредственно пользователю в терминале — с цветами, emoji, прогресс-барами
    и форматированными заголовками. Системный логгер (logging) используется
    параллельно для записи ошибок и отладочной информации в файлы, а print()
    обеспечивает мгновенную визуальную обратную связь в консоли.
"""

from __future__ import annotations

import logging
import sys
from datetime import UTC, datetime
from typing import ClassVar

# Получаем логгер для внутреннего использования
_logger = logging.getLogger("parser-2gis.visual_logger")


class ColorCodes:
    r"""ANSI коды цветов для терминала.

    Все коды используют формат ESC[Nm где ESC = \\033.
    """

    # Основные цвета (яркие/high-intensity варианты)
    RED = "\033[91m"  # Красный — ошибки, критические проблемы
    GREEN = "\033[92m"  # Зелёный — успешные операции
    YELLOW = "\033[93m"  # Жёлтый — предупреждения
    BLUE = "\033[94m"  # Синий — информационные заголовки
    MAGENTA = "\033[95m"  # Пурпурный — критические события
    CYAN = "\033[96m"  # Голубой — информационные сообщения
    WHITE = "\033[97m"  # Белый — текст по умолчанию
    GRAY = "\033[90m"  # Серый — отладочные сообщения

    # Модификаторы отображения
    BOLD = "\033[1m"  # Жирный шрифт — заголовки, акценты
    UNDERLINE = "\033[4m"  # Подчёркивание — важные ссылки

    # Сброс всех атрибутов
    RESET = "\033[0m"  # Возврат к стилям по умолчанию

    # Цвета для уровней логирования
    LEVEL_COLORS: ClassVar[dict[str, str]] = {
        "DEBUG": GRAY,
        "INFO": CYAN,
        "INFO_BOLD": BLUE,
        "WARNING": YELLOW,
        "ERROR": RED,
        "CRITICAL": MAGENTA,
        "SUCCESS": GREEN,
    }


class Emoji:
    """Emoji для различных типов событий."""

    # Основные события
    START = "🚀"
    STOP = "🛑"
    FINISH = "🏁"

    # Статус
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    DEBUG = "🔍"

    # Прогресс
    PROGRESS = "📊"
    DOWNLOAD = "📥"
    UPLOAD = "📤"
    SAVE = "💾"

    # Данные
    FILE = "📄"
    FOLDER = "📁"
    LINK = "🔗"
    DATABASE = "🗄️"

    # Время
    CLOCK = "⏰"
    TIMER = "⏱️"
    CALENDAR = "📅"

    # Браузер
    BROWSER = "🌐"
    TAB = "📑"

    # Парсинг
    PARSE = "🔎"
    EXTRACT = "📋"
    SEARCH = "🔍"


class VisualLogger:
    """Визуальный логгер для красивого вывода в консоль.

    Поддерживает:
    - Цветной вывод (если терминал поддерживает ANSI)
    - Emoji для различных событий
    - Форматированные заголовки
    - Прогресс-бары
    """

    def __init__(self, *, use_colors: bool | None = None, use_emoji: bool = True) -> None:
        """Инициализация визуального логгера.

        Args:
            use_colors: Использовать ли цвета. Если None, определяется автоматически.
            use_emoji: Использовать ли emoji.

        """
        self.use_emoji = use_emoji

        # Автоматически определяем поддержку цветов
        if use_colors is None:
            # Проверяем, является ли stdout терминалом
            self.use_colors = sys.stdout.isatty()
        else:
            self.use_colors = use_colors

    def _colorize(self, text: str, color: str) -> str:
        """Добавляет цвет к тексту.

        Args:
            text: Текст для раскраски.
            color: ANSI код цвета.

        Returns:
            Раскрашенный текст или оригинальный текст, если цвета отключены.

        """
        if self.use_colors:
            return f"{color}{text}{ColorCodes.RESET}"
        return text

    def _get_timestamp(self) -> str:
        """Получает текущее время в формате ЧЧ:ММ:СС.мсс.

        Returns:
            Строка времени.

        """
        return datetime.now(UTC).strftime("%H:%M:%S.%f")[:-3]

    def format_message(
        self, message: str, level: str = "INFO", emoji: str | None = None, *, bold: bool = False
    ) -> str:
        """Форматирует сообщение с цветом и emoji.

        Args:
            message: Сообщение для форматирования.
            level: Уровень логирования.
            emoji: Emoji для добавления (или None для автоматического выбора).
            bold: Сделать ли текст жирным.

        Returns:
            Отформатированное сообщение.

        """
        # Выбираем emoji
        if emoji is None:
            emoji = self._get_emoji_for_level(level)

        # Выбираем цвет
        color = ColorCodes.LEVEL_COLORS.get(level, ColorCodes.WHITE)

        # Формируем сообщение
        timestamp = self._get_timestamp()
        emoji_str = f"{emoji} " if self.use_emoji and emoji else ""
        bold_code = ColorCodes.BOLD if bold else ""

        return (
            f"{timestamp} | {emoji_str}{bold_code}"
            f"{self._colorize(message, color)}{ColorCodes.RESET}"
        )

    def _get_emoji_for_level(self, level: str) -> str | None:
        """Получает emoji для уровня логирования.

        Args:
            level: Уровень логирования.

        Returns:
            Emoji или None.

        """
        emoji_map = {
            "DEBUG": Emoji.DEBUG,
            "INFO": Emoji.INFO,
            "WARNING": Emoji.WARNING,
            "ERROR": Emoji.ERROR,
            "CRITICAL": Emoji.ERROR,
            "SUCCESS": Emoji.SUCCESS,
        }
        return emoji_map.get(level)

    def print_header(self, title: str, subtitle: str | None = None, width: int = 60) -> None:
        """Печатает заголовок секции.

        Args:
            title: Заголовок.
            subtitle: Подзаголовок (опционально).
            width: Ширина заголовка.

        Raises:
            Exception: При ошибке вывода в консоль.

        """
        try:
            "═" * width

            if self.use_colors:
                if subtitle:
                    pass
            else:
                if subtitle:
                    pass
        except (OSError, TypeError, RuntimeError) as e:
            # Логгируем ошибку вывода заголовка, но не прерываем работу
            _logger.exception(
                "Ошибка вывода заголовка в консоль: %s. Функция: %s, Заголовок: %s",
                e,
                self.print_header.__name__,
                title,
            )
            # Фолбэк: простой вывод без форматирования
            if subtitle:
                pass

    def print_config_section(self, title: str, items: dict[str, str], width: int = 60) -> None:
        """Печатает секцию конфигурации.

        Args:
            title: Заголовок секции.
            items: Словарь с параметрами (ключ: значение).
            width: Ширина секции.

        Raises:
            Exception: При ошибке вывода в консоль.

        """
        try:
            if self.use_colors:
                for _key, _value in items.items():
                    pass

            else:
                for _key, _value in items.items():
                    pass
        except (OSError, TypeError, RuntimeError) as e:
            _logger.exception(
                "Ошибка вывода секции конфигурации: %s. Функция: %s, Заголовок: %s, Параметров: %d",
                e,
                self.print_config_section.__name__,
                title,
                len(items),
            )
            # Фолбэк: простой вывод
            for _key, _value in items.items():
                pass

    def print_progress_bar(
        self,
        current: int,
        total: int,
        prefix: str = "Прогресс",
        length: int = 40,
        *,
        show_percent: bool = True,
        show_count: bool = True,
    ) -> str:
        """Создаёт строку прогресс-бара.

        Args:
            current: Текущее значение.
            total: Общее значение.
            prefix: Префикс.
            length: Длина бара в символах.
            show_percent: Показывать ли процент.
            show_count: Показывать ли счётчик.

        Returns:
            Строка прогресс-бара.

        """
        percent = current / total if total > 0 else 0
        filled_length = int(length * percent)
        bar = "█" * filled_length + "░" * (length - filled_length)

        percent_str = f"{percent * 100:.1f}%" if show_percent else ""
        count_str = f"({current}/{total})" if show_count else ""

        parts = [prefix, f"[{bar}]", percent_str, count_str]
        return " ".join(filter(None, parts))

    def print_stats(self, stats: dict[str, int | str], title: str = "Статистика") -> None:
        """Печатает статистику.

        Args:
            stats: Словарь со статистикой.
            title: Заголовок.

        Raises:
            Exception: При ошибке вывода в консоль.

        """
        try:
            self.print_header(title)

            for _key, value in stats.items():
                # Определяем цвет для значения
                if isinstance(value, int):
                    if value > 0:
                        self._colorize(str(value), ColorCodes.GREEN)
                    elif value < 0:
                        self._colorize(str(value), ColorCodes.RED)
                    else:
                        str(value)
                else:
                    str(value)

        except (OSError, TypeError, RuntimeError) as e:
            _logger.exception(
                "Ошибка вывода статистики: %s. Функция: %s, Заголовок: %s, Параметров: %d",
                e,
                self.print_stats.__name__,
                title,
                len(stats),
            )
            # Фолбэк: простой вывод
            for _key, _value in stats.items():
                pass

    def print_success(self, message: str) -> None:
        """Печатает сообщение об успехе."""
        try:
            pass
        except OSError as e:
            _logger.exception("Ошибка вывода сообщения об успехе: %s. Сообщение: %s", e, message)
        except (TypeError, RuntimeError) as e:
            _logger.exception("Неожиданная ошибка при выводе успеха: %s. Сообщение: %s", e, message)
            raise

    def print_error(self, message: str) -> None:
        """Печатает сообщение об ошибке."""
        try:
            pass
        except OSError as e:
            _logger.exception("Ошибка вывода сообщения об ошибке: %s. Сообщение: %s", e, message)
        except (TypeError, RuntimeError) as e:
            _logger.exception("Неожиданная ошибка при выводе ошибки: %s. Сообщение: %s", e, message)
            raise

    def print_warning(self, message: str) -> None:
        """Печатает предупреждение."""
        try:
            pass
        except OSError as e:
            _logger.exception("Ошибка вывода предупреждения: %s. Сообщение: %s", e, message)
        except (TypeError, RuntimeError) as e:
            _logger.exception(
                "Неожиданная ошибка при выводе предупреждения: %s. Сообщение: %s", e, message
            )
            raise

    def print_info(self, message: str, *, bold: bool = False) -> None:
        """Печатает информационное сообщение."""
        try:
            pass
        except OSError as e:
            _logger.exception(
                "Ошибка вывода информационного сообщения: %s. Сообщение: %s", e, message
            )
        except (TypeError, RuntimeError) as e:
            _logger.exception(
                "Неожиданная ошибка при выводе информации: %s. Сообщение: %s", e, message
            )
            raise

    def print_debug(self, message: str) -> None:
        """Печатает отладочное сообщение."""
        try:
            pass
        except OSError as e:
            _logger.exception("Ошибка вывода отладочного сообщения: %s. Сообщение: %s", e, message)
        except (TypeError, RuntimeError) as e:
            _logger.exception(
                "Неожиданная ошибка при выводе отладки: %s. Сообщение: %s", e, message
            )
            raise


# Глобальный экземпляр для удобства
visual_logger = VisualLogger()


# Удобные функции для быстрого использования
def print_header(title: str, subtitle: str | None = None) -> None:
    """Выводит заголовок секции."""
    try:
        visual_logger.print_header(title, subtitle)
    except (OSError, TypeError, RuntimeError) as e:
        _logger.exception("Ошибка в глобальной функции print_header: %s", e)
        raise


def print_config(title: str, items: dict[str, str]) -> None:
    """Выводит секцию конфигурации."""
    try:
        visual_logger.print_config_section(title, items)
    except (OSError, TypeError, RuntimeError) as e:
        _logger.exception("Ошибка в глобальной функции print_config: %s. Заголовок: %s", e, title)
        raise


def print_progress(current: int, total: int, prefix: str = "Прогресс") -> str:
    """Возвращает строку прогресс-бара."""
    return visual_logger.print_progress_bar(current, total, prefix)


def print_success(message: str) -> None:
    """Выводит сообщение об успехе."""
    try:
        visual_logger.print_success(message)
    except (OSError, TypeError, RuntimeError) as e:
        _logger.exception(
            "Ошибка в глобальной функции print_success: %s. Сообщение: %s", e, message
        )
        raise


def print_error(message: str) -> None:
    """Выводит сообщение об ошибке."""
    try:
        visual_logger.print_error(message)
    except (OSError, TypeError, RuntimeError) as e:
        _logger.exception("Ошибка в глобальной функции print_error: %s. Сообщение: %s", e, message)
        raise


def print_warning(message: str) -> None:
    """Выводит предупреждение."""
    try:
        visual_logger.print_warning(message)
    except (OSError, TypeError, RuntimeError) as e:
        _logger.exception(
            "Ошибка в глобальной функции print_warning: %s. Сообщение: %s", e, message
        )
        raise


def print_info(message: str, *, bold: bool = False) -> None:
    """Выводит информационное сообщение."""
    try:
        visual_logger.print_info(message, bold=bold)
    except (OSError, TypeError, RuntimeError) as e:
        _logger.exception("Ошибка в глобальной функции print_info: %s. Сообщение: %s", e, message)
        raise


def print_debug(message: str) -> None:
    """Выводит отладочное сообщение."""
    try:
        visual_logger.print_debug(message)
    except (OSError, TypeError, RuntimeError) as e:
        _logger.exception("Ошибка в глобальной функции print_debug: %s. Сообщение: %s", e, message)
        raise


def print_stats(stats: dict[str, int | str], title: str = "Статистика") -> None:
    """Выводит статистику."""
    try:
        visual_logger.print_stats(stats, title)
    except (OSError, TypeError, RuntimeError) as e:
        _logger.exception("Ошибка в глобальной функции print_stats: %s. Заголовок: %s", e, title)
        raise
