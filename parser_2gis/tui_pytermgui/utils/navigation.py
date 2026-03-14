"""
Менеджер навигации между экранами.
"""

from typing import TYPE_CHECKING, Any, Optional


class ScreenManager:
    """
    Менеджер экранов для навигации между окнами.

    Управляет стеком экранов и переключением между ними.
    """

    def __init__(self, app: Any) -> None:
        """
        Инициализация менеджера экранов.

        Args:
            app: Главное приложение TUI
        """
        self._app = app
        self._screen_stack: list[tuple[str, Any]] = []
        self._current_screen: Optional[str] = None
        self._current_instance: Optional[Any] = None

    def push(self, screen_name: str, screen_instance: Any) -> None:
        """
        Добавить экран в стек и сделать его текущим.

        Args:
            screen_name: Имя экрана
            screen_instance: Экземпляр экрана
        """
        if self._current_screen:
            self._screen_stack.append((self._current_screen, self._current_instance))

        self._current_screen = screen_name
        self._current_instance = screen_instance

    def pop(self) -> Optional[str]:
        """
        Вернуться к предыдущему экрану.

        Returns:
            Имя предыдущего экрана или None
        """
        if not self._screen_stack:
            return None

        previous_name, previous_instance = self._screen_stack.pop()
        self._current_screen = previous_name
        self._current_instance = previous_instance

        return previous_name

    def get_current(self) -> Optional[str]:
        """
        Получить имя текущего экрана.

        Returns:
            Имя текущего экрана или None
        """
        return self._current_screen

    def clear(self) -> None:
        """
        Очистить стек экранов.
        """
        self._screen_stack.clear()
        self._current_screen = None
        self._current_instance = None

    @property
    def current_instance(self) -> Optional[Any]:
        """Текущий экземпляр экрана."""
        return self._current_instance

    @property
    def stack_size(self) -> int:
        """Размер стека экранов."""
        return len(self._screen_stack)
