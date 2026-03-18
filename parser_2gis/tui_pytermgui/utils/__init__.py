"""
Утилиты для TUI Parser2GIS.

Содержит Unicode иконки, анимации и вспомогательные функции
для создания современного и красивого интерфейса.

Классы:
    UnicodeIcons: Коллекция Unicode символов и иконок
    SpinnerAnimation: Анимация спиннеров
    GradientText: Градиентный текст
    BoxDrawing: Рисование рамок и границ
    ScreenManager: Менеджер навигации между экранами

Функции:
    format_number: Форматирование чисел с разделителями
    format_time: Форматирование времени
    truncate_text: Обрезка текста
    center_text: Центрирование текста
    create_ascii_art: Создание ASCII-арта
"""

from __future__ import annotations

import time
from typing import Generator, Literal

from .navigation import ScreenManager

__all__ = [
    "UnicodeIcons",
    "SpinnerAnimation",
    "GradientText",
    "BoxDrawing",
    "ScreenManager",
    "format_number",
    "format_time",
    "truncate_text",
    "center_text",
    "create_ascii_art",
]


class UnicodeIcons:
    """
    Коллекция Unicode иконок для TUI.

    Использует символы Unicode для создания красивых визуальных элементов.
    """

    # Стрелки
    ARROW_RIGHT = "→"
    ARROW_LEFT = "←"
    ARROW_UP = "↑"
    ARROW_DOWN = "↓"
    ARROW_DOUBLE_RIGHT = "⇒"
    ARROW_DOUBLE_LEFT = "⇐"
    ARROW_CIRCLE_RIGHT = "➤"
    ARROW_CIRCLE_DOWN = "⬇"
    ARROW_CIRCLE_UP = "⬆"

    # Галочки и крестики
    CHECK = "✓"
    CHECK_BOLD = "✔"
    CHECK_CIRCLE = "☑"
    CROSS = "✗"
    CROSS_BOLD = "✘"
    CROSS_CIRCLE = "☒"

    # Звёзды и точки
    STAR = "★"
    STAR_OUTLINE = "☆"
    BULLET = "•"
    BULLET_SMALL = "·"
    DIAMOND = "♦"
    DIAMOND_OUTLINE = "◇"

    # Прогресс и заполнение
    BLOCK_FULL = "█"
    BLOCK_75 = "▓"
    BLOCK_50 = "▒"
    BLOCK_25 = "░"
    BLOCK_LOWER = "▄"
    BLOCK_UPPER = "▀"
    BLOCK_LEFT = "▌"
    BLOCK_RIGHT = "▐"

    # Линии и границы
    LINE_HORIZONTAL = "─"
    LINE_VERTICAL = "│"
    LINE_CORNER_TOP_LEFT = "┌"
    LINE_CORNER_TOP_RIGHT = "┐"
    LINE_CORNER_BOTTOM_LEFT = "└"
    LINE_CORNER_BOTTOM_RIGHT = "┘"
    LINE_T_RIGHT = "├"
    LINE_T_LEFT = "┤"
    LINE_T_DOWN = "┬"
    LINE_T_UP = "┴"
    LINE_CROSS = "┼"
    LINE_DOUBLE_HORIZONTAL = "═"
    LINE_DOUBLE_VERTICAL = "║"

    # Спиннеры и анимация
    SPINNER_LINE = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    SPINNER_DOTS = ["⠋", "⠙", "⠚", "⠒", "⠂", "⠂", "⠒", "⠲", "⠴", "⠦", "⠧", "⠇", "⠏"]
    SPINNER_CIRCLE = ["◐", "◓", "◑", "◒"]
    SPINNER_ARC = ["◜", "◠", "◝", "◞", "◡", "◟"]
    SPINNER_FLOW = ["⢄", "⢂", "⢁", "⡁", "⡈", "⡐", "⡠"]
    SPINNER_BRAILLE = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]

    # Эмодзи для статусов
    EMOJI_SUCCESS = "✅"
    EMOJI_ERROR = "❌"
    EMOJI_WARNING = "⚠️"
    EMOJI_INFO = "ℹ️"
    EMOJI_DEBUG = "🔍"
    EMOJI_CRITICAL = "🔴"
    EMOJI_START = "🚀"
    EMOJI_STOP = "🛑"
    EMOJI_PAUSE = "⏸️"
    EMOJI_PLAY = "▶️"
    EMOJI_COMPLETE = "🏁"
    EMOJI_LOADING = "⏳"
    EMOJI_TIME = "⏰"
    EMOJI_SPEED = "⚡"
    EMOJI_TARGET = "🎯"
    EMOJI_FOLDER = "📁"
    EMOJI_FILE = "📄"
    EMOJI_CHART = "📊"
    EMOJI_GRAPH = "📈"
    EMOJI_SETTINGS = "⚙️"
    EMOJI_TOOLS = "🔧"
    EMOJI_BROWSER = "🌐"
    EMOJI_DATABASE = "💾"
    EMOJI_SEARCH = "🔍"
    EMOJI_USER = "👤"
    EMOJI_HOME = "🏠"
    EMOJI_BACK = "↩️"
    EMOJI_EXIT = "🚪"
    EMOJI_HELP = "❓"
    EMOJI_LIGHT = "💡"
    EMOJI_FIRE = "🔥"
    EMOJI_HEART = "❤️"
    EMOJI_STAR = "⭐"
    EMOJI_TROPHY = "🏆"
    EMOJI_MEDAL = "🏅"

    # Геометрические фигуры
    CIRCLE = "●"
    CIRCLE_OUTLINE = "○"
    CIRCLE_SMALL = "⚬"
    SQUARE = "■"
    SQUARE_OUTLINE = "□"
    TRIANGLE_UP = "▲"
    TRIANGLE_DOWN = "▼"
    TRIANGLE_LEFT = "◀"
    TRIANGLE_RIGHT = "▶"

    # Специальные символы
    PERCENT = "%"
    DEGREE = "°"
    PLUS_MINUS = "±"
    MULTIPLICATION = "×"
    DIVISION = "÷"
    EQUALS = "="
    NOT_EQUALS = "≠"
    LESS_EQUAL = "≤"
    GREATER_EQUAL = "≥"
    INFINITY = "∞"
    PI = "π"

    # Музыкальные ноты (для декора)
    MUSIC_NOTE = "♪"
    MUSIC_NOTE_BEAMED = "♫"

    # Валюты
    DOLLAR = "$"
    EURO = "€"
    POUND = "£"
    RUBLE = "₽"
    YEN = "¥"

    # Карточные масти
    SPADE = "♠"
    HEART_SUIT = "♥"
    DIAMOND_SUIT = "♦"
    CLUB = "♣"

    # Погода (для декора)
    SUN = "☀"
    CLOUD = "☁"
    RAIN = "☂"
    SNOW = "❄"
    LIGHTNING = "⚡"

    # Животные (для декора)
    CAT = "🐱"
    DOG = "🐶"
    FOX = "🦊"
    BEAR = "🐻"
    PANDA = "🐼"
    CAPYBARA = "🥔"  # Используем картошку как символ капибары :)

    # Еда (для декора)
    APPLE = "🍎"
    BANANA = "🍌"
    CHERRY = "🍒"
    PIZZA = "🍕"
    BURGER = "🍔"
    COFFEE = "☕"
    BEER = "🍺"

    # Транспорт
    CAR = "🚗"
    BUS = "🚌"
    TRAIN = "🚆"
    PLANE = "✈"
    ROCKET = "🚀"
    BICYCLE = "🚲"

    # Здания
    HOUSE = "🏠"
    BUILDING = "🏢"
    FACTORY = "🏭"
    SHOP = "🏪"

    # Офис
    PHONE = "☎"
    EMAIL = "✉"
    CLIP = "📎"
    PIN = "📌"
    BOOKMARK = "🔖"


class SpinnerAnimation:
    """
    Класс для управления спиннер-анимациями.

    Поддерживает различные типы спиннеров и управление частотой кадров.
    """

    def __init__(
        self,
        spinner_type: Literal["line", "dots", "circle", "arc", "flow", "braille"] = "line",
        fps: int = 10,
        message: str = "Загрузка...",
    ) -> None:
        """
        Инициализация спиннера.

        Args:
            spinner_type: Тип спиннера
            fps: Количество кадров в секунду
            message: Сообщение для отображения
        """
        self.spinner_type = spinner_type
        self.fps = fps
        self.message = message
        self.frame_index = 0
        self.running = False
        self._frames: list[str] = []

        # Выбор типа спиннера
        self._set_frames()

    def _set_frames(self) -> None:
        """Установить кадры для текущего типа спиннера."""
        frames_map = {
            "line": UnicodeIcons.SPINNER_LINE,
            "dots": UnicodeIcons.SPINNER_DOTS,
            "circle": UnicodeIcons.SPINNER_CIRCLE,
            "arc": UnicodeIcons.SPINNER_ARC,
            "flow": UnicodeIcons.SPINNER_FLOW,
            "braille": UnicodeIcons.SPINNER_BRAILLE,
        }
        self._frames = frames_map.get(self.spinner_type, UnicodeIcons.SPINNER_LINE)

    def next_frame(self) -> str:
        """
        Получить следующий кадр.

        Returns:
            Строка с текущим кадром спиннера
        """
        frame = self._frames[self.frame_index]
        self.frame_index = (self.frame_index + 1) % len(self._frames)
        return frame

    def render(self) -> str:
        """
        Отрендерить текущий кадр с сообщением.

        Returns:
            Строка для отображения
        """
        frame = self.next_frame()
        return f"{frame} {self.message}"

    def reset(self) -> None:
        """Сбросить спиннер в начальное состояние."""
        self.frame_index = 0
        self.running = False

    def tick(self) -> float:
        """
        Получить задержку для следующего кадра.

        Returns:
            Задержка в секундах
        """
        return 1.0 / self.fps

    def animate_generator(self, duration: float | None = None) -> Generator[str, None, None]:
        """
        Генератор для анимации спиннера.

        Args:
            duration: Продолжительность анимации в секундах (None для бесконечной)

        Yields:
            Строка с текущим кадром
        """
        self.running = True
        start_time = time.time() if duration else None

        while self.running:
            yield self.render()

            if start_time and (time.time() - start_time) >= duration:
                break

            time.sleep(self.tick())

    def stop(self) -> None:
        """Остановить анимацию."""
        self.running = False


class GradientText:
    """
    Утилита для создания градиентного текста.

    Симулирует градиент через последовательность цветов.
    """

    # Цветовые палитры для градиентов
    GRADIENTS = {
        "sunset": ["#FF0000", "#FF7F00", "#FFFF00", "#00FF00", "#0000FF", "#4B0082", "#9400D3"],
        "ocean": ["#006994", "#40E0D0", "#7FFFD4", "#00CED1", "#5F9EA0", "#4682B4", "#6495ED"],
        "forest": ["#228B22", "#32CD32", "#00FF00", "#7CFC00", "#ADFF2F", "#9ACD32", "#6B8E23"],
        "fire": ["#FF0000", "#FF4500", "#FF6347", "#FF7F50", "#FFA07A", "#FFD700", "#FFFF00"],
        "neon": ["#00FFFF", "#00FF88", "#FFD700", "#FF1493", "#9400D3", "#1E90FF", "#32CD32"],
        "cyberpunk": ["#FF00FF", "#00FFFF", "#FF00AA", "#00FFAA", "#AA00FF", "#FFFF00", "#FF0055"],
        "monochrome": ["#FFFFFF", "#CCCCCC", "#999999", "#666666", "#333333"],
        "blue_green": ["#0000FF", "#00FFFF", "#00FF00", "#7FFF00", "#ADFF2F"],
    }

    @classmethod
    def apply_gradient(
        cls,
        text: str,
        gradient_name: str = "neon",
        style_format: str = "[{color}]{char}[/{color}]",
    ) -> str:
        """
        Применить градиент к тексту.

        Args:
            text: Текст для применения градиента
            gradient_name: Название градиента
            style_format: Формат стиля (должен содержать {color} и {char})

        Returns:
            Текст с применённым градиентом
        """
        colors = cls.GRADIENTS.get(gradient_name, cls.GRADIENTS["neon"])
        result = []

        for i, char in enumerate(text):
            color_index = i % len(colors)
            color = colors[color_index]
            result.append(style_format.format(color=color, char=char))

        return "".join(result)

    @classmethod
    def rainbow(cls, text: str) -> str:
        """Создать радужный текст."""
        return cls.apply_gradient(text, "sunset")

    @classmethod
    def neon(cls, text: str) -> str:
        """Создать неоновый текст."""
        return cls.apply_gradient(text, "neon")

    @classmethod
    def cyberpunk(cls, text: str) -> str:
        """Создать текст в стиле киберпанк."""
        return cls.apply_gradient(text, "cyberpunk")

    @classmethod
    def fire(cls, text: str) -> str:
        """Создать огненный текст."""
        return cls.apply_gradient(text, "fire")

    @classmethod
    def ocean(cls, text: str) -> str:
        """Создать текст в стиле океана."""
        return cls.apply_gradient(text, "ocean")

    @classmethod
    def forest(cls, text: str) -> str:
        """Создать текст в стиле леса."""
        return cls.apply_gradient(text, "forest")

    @classmethod
    def blue_green(cls, text: str) -> str:
        """Создать текст в сине-зелёном стиле."""
        return cls.apply_gradient(text, "blue_green")

    @classmethod
    def monochrome(cls, text: str) -> str:
        """Создать монохромный текст."""
        return cls.apply_gradient(text, "monochrome")


class BoxDrawing:
    """
    Утилиты для рисования рамок и границ.

    Поддерживает различные стили рамок: одинарные, двойные, круглые.
    """

    # Стили рамок
    BOX_STYLES = {
        "single": {
            "tl": "┌",
            "tr": "┐",
            "bl": "└",
            "br": "┘",
            "h": "─",
            "v": "│",
            "tr_down": "┬",
            "tr_up": "┴",
            "tl_right": "├",
            "tr_left": "┤",
            "cross": "┼",
        },
        "double": {
            "tl": "╔",
            "tr": "╗",
            "bl": "╚",
            "br": "╝",
            "h": "═",
            "v": "║",
            "tr_down": "╦",
            "tr_up": "╩",
            "tl_right": "╠",
            "tr_left": "╣",
            "cross": "╬",
        },
        "round": {
            "tl": "╭",
            "tr": "╮",
            "bl": "╰",
            "br": "╯",
            "h": "─",
            "v": "│",
            "tr_down": "┬",
            "tr_up": "┴",
            "tl_right": "├",
            "tr_left": "┤",
            "cross": "┼",
        },
        "heavy": {
            "tl": "┏",
            "tr": "┓",
            "bl": "┗",
            "br": "┛",
            "h": "━",
            "v": "┃",
            "tr_down": "┳",
            "tr_up": "┻",
            "tl_right": "┣",
            "tr_left": "┫",
            "cross": "╋",
        },
        "ascii": {
            "tl": "+",
            "tr": "+",
            "bl": "+",
            "br": "+",
            "h": "-",
            "v": "|",
            "tr_down": "+",
            "tr_up": "+",
            "tl_right": "+",
            "tr_left": "+",
            "cross": "+",
        },
    }

    @classmethod
    def draw_box(
        cls,
        width: int,
        height: int,
        style: str = "single",
        title: str | None = None,
    ) -> list[str]:
        """
        Нарисовать рамку.

        Args:
            width: Ширина рамки
            height: Высота рамки
            style: Стиль рамки
            title: Заголовок рамки

        Returns:
            Список строк с рамкой
        """
        box = cls.BOX_STYLES.get(style, cls.BOX_STYLES["single"])
        lines = []

        # Верхняя граница
        if title:
            title_space = max(0, width - 4 - len(title))
            left_space = title_space // 2
            right_space = title_space - left_space
            top_line = box["tl"] + box["h"] * left_space + f" {title} " + box["h"] * right_space + box["tr"]
        else:
            top_line = box["tl"] + box["h"] * (width - 2) + box["tr"]
        lines.append(top_line)

        # Боковые границы
        for _ in range(height - 2):
            lines.append(box["v"] + " " * (width - 2) + box["v"])

        # Нижняя граница
        lines.append(box["bl"] + box["h"] * (width - 2) + box["br"])

        return lines

    @classmethod
    def draw_horizontal_line(
        cls,
        width: int,
        style: str = "single",
        title: str | None = None,
    ) -> str:
        """
        Нарисовать горизонтальную линию.

        Args:
            width: Ширина линии
            style: Стиль линии
            title: Заголовок линии

        Returns:
            Строка с линией
        """
        box = cls.BOX_STYLES.get(style, cls.BOX_STYLES["single"])

        if title:
            title_space = width - 4 - len(title)
            left_space = title_space // 2
            right_space = title_space - left_space
            return box["tl_right"] + box["h"] * left_space + f" {title} " + box["h"] * right_space + box["tr_left"]
        else:
            return box["h"] * width


def format_number(num: int) -> str:
    """
    Форматировать число с разделителями тысяч.

    Args:
        num: Число для форматирования

    Returns:
        Форматированная строка
    """
    return f"{num:,}".replace(",", " ")


def format_time(seconds: float) -> str:
    """
    Форматировать время в читаемый формат.

    Args:
        seconds: Время в секундах

    Returns:
        Форматированная строка времени
    """
    if seconds < 60:
        return f"{seconds:.1f} сек"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} мин"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} ч"


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Обрезать текст до максимальной длины.

    Args:
        text: Текст для обрезки
        max_length: Максимальная длина
        suffix: Суффикс для обрезанного текста

    Returns:
        Обрезанный текст
    """
    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix


def center_text(text: str, width: int) -> str:
    """
    Центрировать текст по ширине.

    Args:
        text: Текст для центрирования
        width: Ширина для центрирования

    Returns:
        Центрированный текст
    """
    text_width = len(text)
    if text_width >= width:
        return text

    padding = width - text_width
    left_padding = padding // 2
    right_padding = padding - left_padding

    return " " * left_padding + text + " " * right_padding


def create_ascii_art(text: str, style: str = "block") -> list[str]:
    """
    Создать ASCII-арт из текста.

    Args:
        text: Текст для преобразования
        style: Стиль ASCII-арта

    Returns:
        Список строк с ASCII-артом
    """
    # Простая реализация блочного ASCII-арта
    if style == "block":
        letters = {
            "P": [
                "██████",
                "██   ██",
                "██████",
                "██",
                "██",
            ],
            "2": [
                "██████",
                "     ██",
                "██████",
                "██     ",
                "██████",
            ],
            "G": [
                "██████",
                "██     ",
                "██  ███",
                "██   ██",
                "██████",
            ],
            "I": [
                "██████",
                "   ██   ",
                "   ██   ",
                "   ██   ",
                "██████",
            ],
            "S": [
                "██████",
                "██     ",
                "██████",
                "     ██",
                "██████",
            ],
        }

        result = [""] * 5
        for char in text.upper():
            if char in letters:
                char_art = letters[char]
                for i, line in enumerate(char_art):
                    result[i] += line + " "

        return result

    # По умолчанию вернуть простой текст
    return [text]
