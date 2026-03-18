"""
Менеджер навигации между экранами.
"""

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from typing import TYPE_CHECKING


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

    def clear(self) -> None:
        """
        Очистить стек экранов.

        Также удаляет окна из WindowManager если он доступен.
        """
        # Удалить текущее окно из WindowManager
        if self._current_instance and hasattr(self._app, "_manager"):
            manager = getattr(self._app, "_manager", None)
            if manager and hasattr(self._current_instance, "_window"):
                # Используем существующее окно вместо создания нового
                existing_window = getattr(self._current_instance, "_window", None)
                if existing_window:
                    try:
                        manager.remove(existing_window)
                    except Exception as remove_error:
                        # Игнорируем ошибки удаления, но логируем их
                        from ..logger import logger

                        logger.debug("Ошибка при удалении окна: %s", remove_error)

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
