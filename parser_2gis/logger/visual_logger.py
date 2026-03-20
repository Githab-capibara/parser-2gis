"""
Модуль визуального логирования.

Предоставляет утилиты для красивого форматирования логов:
- Emoji для различных типов событий
- Цветовое выделение (ANSI коды)
- Форматированные заголовки секций
- Прогресс-бары и статистика
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from typing import Optional

# Получаем логгер для внутреннего использования
_logger = logging.getLogger("parser-2gis.visual_logger")


class ColorCodes:
    """ANSI коды цветов для терминала."""

    # Основные цвета
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"

    # Жирный шрифт
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

    # Сброс
    RESET = "\033[0m"

    # Цвета для уровней логирования
    LEVEL_COLORS = {
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
    """
    Визуальный логгер для красивого вывода в консоль.

    Поддерживает:
    - Цветной вывод (если терминал поддерживает ANSI)
    - Emoji для различных событий
    - Форматированные заголовки
    - Прогресс-бары
    """

    def __init__(
        self, use_colors: Optional[bool] = None, use_emoji: bool = True
    ) -> None:
        """
        Инициализация визуального логгера.

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
        """
        Добавляет цвет к тексту.

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
        """
        Получает текущее время в формате ЧЧ:ММ:СС.мсс.

        Returns:
            Строка времени.
        """
        return datetime.now().strftime("%H:%M:%S.%f")[:-3]

    def format_message(
        self,
        message: str,
        level: str = "INFO",
        emoji: Optional[str] = None,
        bold: bool = False,
    ) -> str:
        """
        Форматирует сообщение с цветом и emoji.

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

        return f"{timestamp} | {emoji_str}{bold_code}{self._colorize(message, color)}{ColorCodes.RESET}"

    def _get_emoji_for_level(self, level: str) -> Optional[str]:
        """
        Получает emoji для уровня логирования.

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

    def print_header(
        self,
        title: str,
        subtitle: Optional[str] = None,
        width: int = 60,
    ) -> None:
        """
        Печатает заголовок секции.

        Args:
            title: Заголовок.
            subtitle: Подзаголовок (опционально).
            width: Ширина заголовка.

        Raises:
            Exception: При ошибке вывода в консоль.
        """
        try:
            border = "═" * width

            if self.use_colors:
                print(
                    f"\n{ColorCodes.CYAN}{ColorCodes.BOLD}╔{border}╗{ColorCodes.RESET}"
                )
                print(
                    f"{ColorCodes.CYAN}{ColorCodes.BOLD}║{ColorCodes.RESET} "
                    f"{ColorCodes.BOLD}{title.center(width)}{ColorCodes.RESET} "
                    f"{ColorCodes.CYAN}{ColorCodes.BOLD}║{ColorCodes.RESET}"
                )
                if subtitle:
                    print(
                        f"{ColorCodes.CYAN}{ColorCodes.BOLD}║{ColorCodes.RESET} "
                        f"{subtitle.center(width)} "
                        f"{ColorCodes.CYAN}{ColorCodes.BOLD}║{ColorCodes.RESET}"
                    )
                print(
                    f"{ColorCodes.CYAN}{ColorCodes.BOLD}╚{border}╝{ColorCodes.RESET}\n"
                )
            else:
                print(f"\n{'=' * width}")
                print(f"{title.center(width)}")
                if subtitle:
                    print(f"{subtitle.center(width)}")
                print(f"{'=' * width}\n")
        except (IOError, OSError) as e:
            # Логгируем ошибку вывода, но не прерываем работу
            _logger.error(
                f"Ошибка вывода заголовка в консоль: {e}. "
                f"Функция: {self.print_header.__name__}, "
                f"Заголовок: {title}"
            )
            # Фолбэк: простой вывод без форматирования
            print(f"\n{title}")
            if subtitle:
                print(f"{subtitle}\n")
        except Exception as e:
            # Логгируем неожиданную ошибку с полным traceback
            _logger.exception(
                f"Неожиданная ошибка при выводе заголовка: {e}. "
                f"Функция: {self.print_header.__name__}, "
                f"Заголовок: {title}"
            )
            raise

    def print_config_section(
        self,
        title: str,
        items: dict[str, str],
        width: int = 60,
    ) -> None:
        """
        Печатает секцию конфигурации.

        Args:
            title: Заголовок секции.
            items: Словарь с параметрами (ключ: значение).
            width: Ширина секции.

        Raises:
            Exception: При ошибке вывода в консоль.
        """
        try:
            if self.use_colors:
                print(
                    f"\n{ColorCodes.BOLD}{ColorCodes.BLUE}┌─ {title} {ColorCodes.RESET}"
                )

                for key, value in items.items():
                    key_colored = f"{ColorCodes.CYAN}{key}:{ColorCodes.RESET}"
                    print(f"  {key_colored} {value}")

                print(f"{ColorCodes.BLUE}└{'─' * (width - 1)}{ColorCodes.RESET}\n")
            else:
                print(f"\n─ {title}")
                for key, value in items.items():
                    print(f"  {key}: {value}")
                print(f"─{'─' * (width - 1)}\n")
        except (IOError, OSError) as e:
            _logger.error(
                f"Ошибка вывода секции конфигурации: {e}. "
                f"Функция: {self.print_config_section.__name__}, "
                f"Заголовок: {title}, "
                f"Параметров: {len(items)}"
            )
            # Фолбэк: простой вывод
            print(f"\n{title}")
            for key, value in items.items():
                print(f"  {key}: {value}")
            print()
        except Exception as e:
            _logger.exception(
                f"Неожиданная ошибка при выводе секции конфигурации: {e}. "
                f"Функция: {self.print_config_section.__name__}, "
                f"Заголовок: {title}"
            )
            raise

    def print_progress_bar(
        self,
        current: int,
        total: int,
        prefix: str = "Прогресс",
        length: int = 40,
        show_percent: bool = True,
        show_count: bool = True,
    ) -> str:
        """
        Создаёт строку прогресс-бара.

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

    def print_stats(
        self,
        stats: dict[str, int | str],
        title: str = "Статистика",
    ) -> None:
        """
        Печатает статистику.

        Args:
            stats: Словарь со статистикой.
            title: Заголовок.

        Raises:
            Exception: При ошибке вывода в консоль.
        """
        try:
            self.print_header(title)

            for key, value in stats.items():
                # Определяем цвет для значения
                if isinstance(value, int):
                    if value > 0:
                        value_str = self._colorize(str(value), ColorCodes.GREEN)
                    elif value < 0:
                        value_str = self._colorize(str(value), ColorCodes.RED)
                    else:
                        value_str = str(value)
                else:
                    value_str = str(value)

                print(f"  {key}: {value_str}")

            print()
        except (IOError, OSError) as e:
            _logger.error(
                f"Ошибка вывода статистики: {e}. "
                f"Функция: {self.print_stats.__name__}, "
                f"Заголовок: {title}, "
                f"Параметров: {len(stats)}"
            )
            # Фолбэк: простой вывод
            print(f"\n{title}")
            for key, value in stats.items():
                print(f"  {key}: {value}")
            print()
        except Exception as e:
            _logger.exception(
                f"Неожиданная ошибка при выводе статистики: {e}. "
                f"Функция: {self.print_stats.__name__}, "
                f"Заголовок: {title}"
            )
            raise

    def print_success(self, message: str) -> None:
        """Печатает сообщение об успехе."""
        try:
            print(self.format_message(message, "SUCCESS", Emoji.SUCCESS))
        except (IOError, OSError) as e:
            _logger.error(
                f"Ошибка вывода сообщения об успехе: {e}. Сообщение: {message}"
            )
            print(f"✅ {message}")
        except Exception as e:
            _logger.exception(
                f"Неожиданная ошибка при выводе успеха: {e}. Сообщение: {message}"
            )
            raise

    def print_error(self, message: str) -> None:
        """Печатает сообщение об ошибке."""
        try:
            print(self.format_message(message, "ERROR", Emoji.ERROR))
        except (IOError, OSError) as e:
            _logger.error(
                f"Ошибка вывода сообщения об ошибке: {e}. Сообщение: {message}"
            )
            print(f"❌ {message}")
        except Exception as e:
            _logger.exception(
                f"Неожиданная ошибка при выводе ошибки: {e}. Сообщение: {message}"
            )
            raise

    def print_warning(self, message: str) -> None:
        """Печатает предупреждение."""
        try:
            print(self.format_message(message, "WARNING", Emoji.WARNING))
        except (IOError, OSError) as e:
            _logger.error(f"Ошибка вывода предупреждения: {e}. Сообщение: {message}")
            print(f"⚠️ {message}")
        except Exception as e:
            _logger.exception(
                f"Неожиданная ошибка при выводе предупреждения: {e}. Сообщение: {message}"
            )
            raise

    def print_info(self, message: str, bold: bool = False) -> None:
        """Печатает информационное сообщение."""
        try:
            print(self.format_message(message, "INFO", Emoji.INFO, bold))
        except (IOError, OSError) as e:
            _logger.error(
                f"Ошибка вывода информационного сообщения: {e}. Сообщение: {message}"
            )
            print(f"ℹ️ {message}")
        except Exception as e:
            _logger.exception(
                f"Неожиданная ошибка при выводе информации: {e}. Сообщение: {message}"
            )
            raise

    def print_debug(self, message: str) -> None:
        """Печатает отладочное сообщение."""
        try:
            print(self.format_message(message, "DEBUG", Emoji.DEBUG))
        except (IOError, OSError) as e:
            _logger.error(
                f"Ошибка вывода отладочного сообщения: {e}. Сообщение: {message}"
            )
            print(f"🔍 {message}")
        except Exception as e:
            _logger.exception(
                f"Неожиданная ошибка при выводе отладки: {e}. Сообщение: {message}"
            )
            raise


# Глобальный экземпляр для удобства
visual_logger = VisualLogger()


# Удобные функции для быстрого использования
def print_header(title: str, subtitle: Optional[str] = None) -> None:
    """Выводит заголовок секции."""
    try:
        visual_logger.print_header(title, subtitle)
    except Exception as e:
        _logger.exception(f"Ошибка в глобальной функции print_header: {e}")
        raise


def print_config(title: str, items: dict[str, str]) -> None:
    """Выводит секцию конфигурации."""
    try:
        visual_logger.print_config_section(title, items)
    except Exception as e:
        _logger.exception(
            f"Ошибка в глобальной функции print_config: {e}. Заголовок: {title}"
        )
        raise


def print_progress(current: int, total: int, prefix: str = "Прогресс") -> str:
    """Возвращает строку прогресс-бара."""
    return visual_logger.print_progress_bar(current, total, prefix)


def print_success(message: str) -> None:
    """Выводит сообщение об успехе."""
    try:
        visual_logger.print_success(message)
    except Exception as e:
        _logger.exception(
            f"Ошибка в глобальной функции print_success: {e}. Сообщение: {message}"
        )
        raise


def print_error(message: str) -> None:
    """Выводит сообщение об ошибке."""
    try:
        visual_logger.print_error(message)
    except Exception as e:
        _logger.exception(
            f"Ошибка в глобальной функции print_error: {e}. Сообщение: {message}"
        )
        raise


def print_warning(message: str) -> None:
    """Выводит предупреждение."""
    try:
        visual_logger.print_warning(message)
    except Exception as e:
        _logger.exception(
            f"Ошибка в глобальной функции print_warning: {e}. Сообщение: {message}"
        )
        raise


def print_info(message: str, bold: bool = False) -> None:
    """Выводит информационное сообщение."""
    try:
        visual_logger.print_info(message, bold)
    except Exception as e:
        _logger.exception(
            f"Ошибка в глобальной функции print_info: {e}. Сообщение: {message}"
        )
        raise


def print_debug(message: str) -> None:
    """Выводит отладочное сообщение."""
    try:
        visual_logger.print_debug(message)
    except Exception as e:
        _logger.exception(
            f"Ошибка в глобальной функции print_debug: {e}. Сообщение: {message}"
        )
        raise


def print_stats(stats: dict[str, int | str], title: str = "Статистика") -> None:
    """Выводит статистику."""
    try:
        visual_logger.print_stats(stats, title)
    except Exception as e:
        _logger.exception(
            f"Ошибка в глобальной функции print_stats: {e}. Заголовок: {title}"
        )
        raise
