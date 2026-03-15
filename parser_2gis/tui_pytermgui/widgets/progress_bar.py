"""
Прогресс-бар для TUI Parser2GIS.
"""

import pytermgui as ptg


class ProgressBar:
    """
    Виджет прогресс-бара.

    Отображает прогресс выполнения задачи.
    """

    def __init__(
        self,
        label: str = "Прогресс",
        total: int = 100,
        completed: int = 0,
        bar_width: int = 40,
    ) -> None:
        """
        Инициализация прогресс-бара.

        Args:
            label: Метка прогресс-бара
            total: Общее количество единиц
            completed: Количество завершённых единиц
            bar_width: Ширина полосы прогресса
        """
        self._label = label
        self._total = total
        self._completed = completed
        self._bar_width = bar_width

    def _render_text(self) -> str:
        """
        Получить текстовое представление прогресс-бара.

        Returns:
            Строка с прогресс-баром
        """
        # Вычислить процент
        if self._total <= 0:
            percent = 0
        else:
            percent = min(100, max(0, (self._completed / self._total) * 100))

        # Вычислить количество заполненных символов
        filled_width = int(self._bar_width * percent / 100)
        empty_width = self._bar_width - filled_width

        # Создать строку прогресс-бара
        bar = "█" * filled_width + "░" * empty_width

        # Создать метку
        return f"{self._label}: [{bar}] {percent:.1f}% ({self._completed}/{self._total})"

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

    def set_total(self, total: int) -> None:
        """
        Установить общее количество.

        Args:
            total: Общее количество единиц
        """
        self._total = total

    def reset(self) -> None:
        """Сбросить прогресс."""
        self._completed = 0
        self._total = 100

    @property
    def percent(self) -> float:
        """Процент выполнения."""
        if self._total <= 0:
            return 0.0
        return float(min(100.0, max(0.0, (self._completed / self._total) * 100)))
