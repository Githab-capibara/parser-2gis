"""
Тесты для выявления ошибок в TUI Textual.

Тесты заранее выявляют проблемы с инициализацией атрибутов,
такие как перезапись атрибутов родительского класса.
"""

import pytest

try:
    from textual.app import App  # noqa: F401

    from parser_2gis.tui_textual.app import TUIApp

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False
    pytest.skip("textual not installed", allow_module_level=True)


class TestTUILoggerInitialization:
    """Тесты для проверки корректной инициализации логгера в TUIApp."""

    @pytest.mark.asyncio
    async def test_app_log_is_not_none(self):
        """Тест: app.log не должен быть None после инициализации.

        Этот тест выявляет проблему, когда self._logger перезаписывается
        в __init__ дочернего класса после вызова super().__init__(),
        что приводит к AttributeError при запуске приложения.
        """
        app = TUIApp()
        assert app.log is not None, (
            "app.log должен быть инициализирован родительским классом App. "
            "Если app.log is None, значит атрибут _logger был перезаписан "
            "в __init__ после вызова super().__init__()"
        )

    @pytest.mark.asyncio
    async def test_app_logger_is_logger_instance(self):
        """Тест: app._logger должен быть экземпляром Logger (Textual).

        Проверяем, что внутренний атрибут _logger не был перезаписан
        на None или другой тип данных.
        """
        app = TUIApp()
        assert hasattr(app, "_logger"), "Атрибут _logger должен существовать"
        assert app._logger is not None, (
            "app._logger не должен быть None. "
            "Проверьте, что __init__ не перезаписывает _logger после super().__init__()"
        )
        assert not isinstance(
            app._logger, type(None)
        ), "app._logger не должен быть None после инициализации"

    @pytest.mark.asyncio
    async def test_file_logger_does_not_override_textual_logger(self):
        """Тест: Файловый логгер не должен перезаписывать _logger Textual.

        Этот тест проверяет, что файловый логгер использует отдельный
        атрибут (_file_logger), а не _logger, который принадлежит Textual App.
        """
        app = TUIApp()

        textual_logger = app._logger
        assert textual_logger is not None, "Textual _logger должен быть инициализирован"

        assert hasattr(app, "_file_logger"), (
            "Для файлового логгера должен использоваться отдельный атрибут "
            "(например, _file_logger), а не _logger родительского класса"
        )
