"""
Современный прогресс-бар для TUI Parser2GIS.

Использует Unicode символы, анимацию и градиенты для красивого отображения.
"""

from __future__ import annotations

from typing import Literal

import pytermgui as ptg

from ..utils import (
    GradientText,
    SpinnerAnimation,
    UnicodeIcons,
    format_number,
)


class ProgressBar:
    """
    Современный виджет прогресс-бара.

    Поддерживает:
    - Различные стили заполнения (Unicode символы)
    - Анимацию спиннера
    - Градиентные цвета
    - Индикацию процентов с цветами
    - Несколько режимов отображения
    """

    # Стили заполнения
    FILL_STYLES = {
        "classic": {
            "full": UnicodeIcons.BLOCK_FULL,
            "partial": [
                UnicodeIcons.BLOCK_75,
                UnicodeIcons.BLOCK_50,
                UnicodeIcons.BLOCK_25,
            ],
            "empty": UnicodeIcons.BLOCK_25,
        },
        "smooth": {
            "full": UnicodeIcons.BLOCK_FULL,
            "partial": [
                UnicodeIcons.BLOCK_75,
                UnicodeIcons.BLOCK_50,
                UnicodeIcons.BLOCK_25,
            ],
            "empty": " ",
        },
        "line": {
            "full": "━",
            "partial": ["╸", "╾"],
            "empty": "─",
        },
        "double_line": {
            "full": "═",
            "partial": ["╾", "╼"],
            "empty": "─",
        },
        "braille": {
            "full": "⣿",
            "partial": ["⣶", "⣤", "⣀"],
            "empty": "⣀",
        },
        "circle": {
            "full": "●",
            "partial": ["◉", "◎"],
            "empty": "○",
        },
        "diamond": {
            "full": "◆",
            "partial": ["◇", "◇"],
            "empty": "◇",
        },
    }

    # Цветовые схемы
    COLOR_SCHEMES = {
        "default": {
            "complete": "#00FF88",
            "partial": "#00FFFF",
            "incomplete": "#4A4A4A",
            "text": "#FFFFFF",
            "percentage_high": "#00FF88",
            "percentage_mid": "#FFD700",
            "percentage_low": "#FF4444",
        },
        "neon": {
            "complete": "#00FF88",
            "partial": "#00FFFF",
            "incomplete": "#2D2D2D",
            "text": "#EAEAEA",
            "percentage_high": "#00FF88",
            "percentage_mid": "#FFD700",
            "percentage_low": "#FF1493",
        },
        "fire": {
            "complete": "#FF4500",
            "partial": "#FF6347",
            "incomplete": "#4A4A4A",
            "text": "#FFFFFF",
            "percentage_high": "#FFFF00",
            "percentage_mid": "#FF7F50",
            "percentage_low": "#FF0000",
        },
        "ocean": {
            "complete": "#00CED1",
            "partial": "#40E0D0",
            "incomplete": "#2D4A5C",
            "text": "#E0FFFF",
            "percentage_high": "#7FFFD4",
            "percentage_mid": "#40E0D0",
            "percentage_low": "#006994",
        },
        "cyberpunk": {
            "complete": "#FF00FF",
            "partial": "#00FFFF",
            "incomplete": "#2D1B3C",
            "text": "#FFD700",
            "percentage_high": "#00FFFF",
            "percentage_mid": "#FF00FF",
            "percentage_low": "#FF0055",
        },
        "monochrome": {
            "complete": "#FFFFFF",
            "partial": "#CCCCCC",
            "incomplete": "#4A4A4A",
            "text": "#FFFFFF",
            "percentage_high": "#FFFFFF",
            "percentage_mid": "#CCCCCC",
            "percentage_low": "#888888",
        },
    }

    def __init__(
        self,
        label: str = "Прогресс",
        total: int = 100,
        completed: int = 0,
        bar_width: int = 40,
        fill_style: Literal[
            "classic", "smooth", "line", "double_line", "braille", "circle", "diamond"
        ] = "classic",
        color_scheme: Literal[
            "default", "neon", "fire", "ocean", "cyberpunk", "monochrome"
        ] = "neon",
        show_percentage: bool = True,
        show_count: bool = True,
        show_spinner: bool = False,
        spinner_type: Literal[
            "line", "dots", "circle", "arc", "flow", "braille"
        ] = "dots",
        gradient: bool = False,
        gradient_name: str = "neon",
    ) -> None:
        """
        Инициализация прогресс-бара.

        Args:
            label: Метка прогресс-бара
            total: Общее количество единиц
            completed: Количество завершённых единиц
            bar_width: Ширина полосы прогресса
            fill_style: Стиль заполнения
            color_scheme: Цветовая схема
            show_percentage: Показывать проценты
            show_count: Показывать счётчик
            show_spinner: Показывать спиннер
            spinner_type: Тип спиннера
            gradient: Использовать градиент
            gradient_name: Название градиента
        """
        self._label = label
        self._total = total
        self._completed = completed
        self._bar_width = bar_width
        self._fill_style = fill_style
        self._color_scheme = color_scheme
        self._show_percentage = show_percentage
        self._show_count = show_count
        self._show_spinner = show_spinner
        self._gradient = gradient
        self._gradient_name = gradient_name

        # Инициализация спиннера
        self._spinner = (
            SpinnerAnimation(
                spinner_type=spinner_type,
                message="",
            )
            if show_spinner
            else None
        )

        # Кэш для отрендеренного текста
        self._cached_text: str | None = None

    def _get_percentage_color(self, percent: float) -> str:
        """
        Получить цвет для процентов в зависимости от значения.

        Args:
            percent: Процент выполнения

        Returns:
            Цвет для отображения
        """
        colors = self.COLOR_SCHEMES[self._color_scheme]

        if percent >= 75:
            return colors["percentage_high"]
        elif percent >= 50:
            return colors["percentage_mid"]
        else:
            return colors["percentage_low"]

    def _render_bar(self, percent: float) -> str:
        """
        Отрендерить полосу прогресса.

        Args:
            percent: Процент выполнения

        Returns:
            Строка с полосой прогресса
        """
        fill = self.FILL_STYLES[self._fill_style]
        colors = self.COLOR_SCHEMES[self._color_scheme]

        # Вычислить количество заполненных символов
        filled_count = int(self._bar_width * percent / 100)
        remaining_count = self._bar_width - filled_count

        # Построить полосу
        bar_parts = []

        # Заполненная часть
        for i in range(filled_count):
            if self._gradient and filled_count > 1:
                # Градиентное заполнение
                gradient_colors = GradientText.GRADIENTS.get(
                    self._gradient_name,
                    GradientText.GRADIENTS["neon"],
                )
                color_index = int(
                    i / max(1, filled_count - 1) * (len(gradient_colors) - 1)
                )
                color = gradient_colors[color_index]
                bar_parts.append(f"[{color}]{fill['full']}[/]")
            else:
                bar_parts.append(f"[{colors['complete']}]{fill['full']}[/]")

        # Пустая часть
        for _ in range(remaining_count):
            bar_parts.append(f"[{colors['incomplete']}]{fill['empty']}[/]")

        return "".join(bar_parts)

    def _render_text(self) -> str:
        """
        Получить текстовое представление прогресс-бара.

        Returns:
            Строка с прогресс-баром
        """
        # Вычислить процент
        if self._total <= 0:
            percent = 0.0
        else:
            percent = min(100.0, max(0.0, (self._completed / self._total) * 100))

        colors = self.COLOR_SCHEMES[self._color_scheme]
        parts = []

        # Спиннер (если включён)
        if self._spinner and self._show_spinner:
            spinner_frame = self._spinner.next_frame()
            parts.append(f"[{colors['partial']}]{spinner_frame}[/]")

        # Метка с градиентом или цветом
        if self._gradient:
            label_text = GradientText.apply_gradient(self._label, self._gradient_name)
            parts.append(label_text)
        else:
            parts.append(f"[bold {colors['text']}]{self._label}[/]")

        parts.append(": ")

        # Полоса прогресса
        bar = self._render_bar(percent)
        parts.append(bar)

        # Проценты
        if self._show_percentage:
            percent_color = self._get_percentage_color(percent)
            parts.append(f" [{percent_color}]{percent:5.1f}%[/]")

        # Счётчик
        if self._show_count:
            completed_str = format_number(self._completed)
            total_str = format_number(self._total)
            parts.append(f" ([dim]{completed_str}/{total_str}[/])")

        # Объединить части
        line = "".join(parts)

        # Преобразовать TIM-теги в ANSI-коды
        return ptg.tim.parse(line)

    def render(self) -> ptg.Label:
        """
        Рендерить прогресс-бар.

        Returns:
            Label с прогресс-баром
        """
        return ptg.Label(self._render_text())

    def update(self, completed: int) -> None:
        """
        Обновить прогресс.

        Args:
            completed: Новое количество завершённых единиц
        """
        self._completed = completed
        self._cached_text = None

    def advance(self, amount: int = 1) -> None:
        """
        Продвинуть прогресс на указанное количество.

        Args:
            amount: Количество для продвижения
        """
        self._completed += amount
        self._cached_text = None

    def set_total(self, total: int) -> None:
        """
        Установить общее количество.

        Args:
            total: Общее количество единиц
        """
        self._total = total
        self._cached_text = None

    def reset(self) -> None:
        """Сбросить прогресс."""
        self._completed = 0
        self._cached_text = None

    def set_label(self, label: str) -> None:
        """
        Установить новую метку.

        Args:
            label: Новая метка
        """
        self._label = label
        self._cached_text = None

    def set_spinner_message(self, message: str) -> None:
        """
        Установить сообщение спиннера.

        Args:
            message: Сообщение
        """
        if self._spinner:
            self._spinner.message = message

    @property
    def percent(self) -> float:
        """Процент выполнения."""
        if self._total <= 0:
            return 0.0
        return float(min(100.0, max(0.0, (self._completed / self._total) * 100)))

    @property
    def completed(self) -> int:
        """Количество завершённых единиц."""
        return self._completed

    @property
    def total(self) -> int:
        """Общее количество единиц."""
        return self._total

    @property
    def is_complete(self) -> bool:
        """Завершён ли прогресс."""
        return self._completed >= self._total and self._total > 0


class MultiProgressBar:
    """
    Виджет для отображения нескольких прогресс-баров.

    Используется для отображения прогресса по разным метрикам одновременно.
    """

    def __init__(
        self,
        bars: dict[str, dict] | None = None,
        color_scheme: str = "neon",
        fill_style: str = "classic",
    ) -> None:
        """
        Инициализация мульти-прогресс бара.

        Args:
            bars: Словарь с конфигурацией баров
                  {name: {total, completed, show_percentage, show_count}}
            color_scheme: Цветовая схема
            fill_style: Стиль заполнения
        """
        self._bars: dict[str, ProgressBar] = {}
        self._color_scheme = color_scheme
        self._fill_style = fill_style

        if bars:
            for name, config in bars.items():
                self.add_bar(name, **config)

    def add_bar(
        self,
        name: str,
        total: int = 100,
        completed: int = 0,
        show_percentage: bool = True,
        show_count: bool = True,
        bar_width: int = 30,
    ) -> None:
        """
        Добавить прогресс-бар.

        Args:
            name: Название бара
            total: Общее количество
            completed: Завершённое количество
            show_percentage: Показывать проценты
            show_count: Показывать счётчик
            bar_width: Ширина бара
        """
        self._bars[name] = ProgressBar(
            label=name,
            total=total,
            completed=completed,
            bar_width=bar_width,
            fill_style=self._fill_style,
            color_scheme=self._color_scheme,
            show_percentage=show_percentage,
            show_count=show_count,
        )

    def update(self, name: str, completed: int) -> None:
        """
        Обновить прогресс бара.

        Args:
            name: Название бара
            completed: Завершённое количество
        """
        if name in self._bars:
            self._bars[name].update(completed)

    def advance(self, name: str, amount: int = 1) -> None:
        """
        Продвинуть прогресс бара.

        Args:
            name: Название бара
            amount: Количество для продвижения
        """
        if name in self._bars:
            self._bars[name].advance(amount)

    def set_total(self, name: str, total: int) -> None:
        """
        Установить общее количество для бара.

        Args:
            name: Название бара
            total: Общее количество
        """
        if name in self._bars:
            self._bars[name].set_total(total)

    def render(self) -> str:
        """
        Отрендерить все прогресс-бары.

        Returns:
            Строка со всеми прогресс-барами
        """
        lines = []
        for bar in self._bars.values():
            lines.append(bar._render_text())

        return "\n".join(lines)

    def render_label(self) -> ptg.Container:
        """
        Отрендерить как контейнер.

        Returns:
            Container с прогресс-барами
        """
        labels = []
        for bar in self._bars.values():
            labels.append(ptg.Label(bar._render_text()))

        return ptg.Container(*labels, box="EMPTY_VERTICAL")

    @property
    def bar_count(self) -> int:
        """Количество прогресс-баров."""
        return len(self._bars)
