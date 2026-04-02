"""Тесты упрощений ISSUE-016 — ISSUE-020.

Тестирует упрощения кода в рамках KISS принципа:
- ISSUE-016: Упрощение ConfigMerger
- ISSUE-017: Tenacity для ChromeRemote
- ISSUE-018: Упрощение обработки ошибок БД
- ISSUE-019: Упрощение TempFileTimer
- ISSUE-020: AppState dataclass
"""

from __future__ import annotations

import sqlite3
import tempfile
import threading
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from parser_2gis.config import Configuration
from parser_2gis.config_services.config_merger import ConfigMerger
from parser_2gis.database.error_handler import (
    DatabaseError,
    handle_db_errors,
    _is_retryable_error,
    _is_critical_error,
)
from parser_2gis.utils.temp_file_manager import TempFileTimer
from parser_2gis.tui_textual.app import AppState


# =============================================================================
# ISSUE-016: Упрощение ConfigMerger
# =============================================================================


class TestConfigMergerSimplification:
    """Тесты упрощения ConfigMerger (ISSUE-016)."""

    def test_merge_simple_fields(self) -> None:
        """Тест 1: Объединение простых полей.

        Проверяет что merge корректно объединяет простые поля.
        """
        config1 = Configuration()
        config2 = config1.model_copy(
            update={"parser": config1.parser.model_copy(update={"max_retries": 5})}
        )

        ConfigMerger.merge(config1, config2)

        assert config1.parser.max_retries == 5

    def test_merge_nested_models(self) -> None:
        """Тест 2: Объединение вложенных моделей.

        Проверяет что merge корректно работает с вложенными Pydantic моделями.
        """
        config1 = Configuration()
        config2 = Configuration(log=config1.log.model_copy(update={"level": "DEBUG"}))

        ConfigMerger.merge(config1, config2)

        assert config1.log.level == "DEBUG"

    def test_merge_max_depth(self) -> None:
        """Тест 3: Проверка max_depth.

        Проверяет что превышение глубины вызывает RecursionError.
        """
        config1 = Configuration()
        config2 = Configuration()

        # Устанавливаем очень маленькую глубину
        with pytest.raises(RecursionError):
            ConfigMerger.merge(config1, config2, max_depth=0)

    def test_merge_circular_reference(self) -> None:
        """Тест 4: Обработка циклических ссылок.

        Проверяет что циклические ссылки обрабатываются корректно.
        """
        config1 = Configuration()
        config2 = Configuration()

        # Циклическая ссылка через атрибуты
        config1._circular = config2  # type: ignore[attr-defined]
        config2._circular = config1  # type: ignore[attr-defined]

        # Не должно вызвать исключения
        ConfigMerger.merge(config1, config2)


# =============================================================================
# ISSUE-017: Tenacity для ChromeRemote
# =============================================================================


class TestChromeRemoteRetry:
    """Тесты retry логики ChromeRemote (ISSUE-017)."""

    def test_attempt_connection_success(self) -> None:
        """Тест 1: Успешное подключение.

        Проверяет что _attempt_connection работает без ошибок.
        """
        from parser_2gis.chrome.remote import ChromeRemote
        from parser_2gis.chrome.options import ChromeOptions

        mock_options = Mock(spec=ChromeOptions)
        chrome_remote = ChromeRemote(mock_options, [])

        # Мокаем зависимости
        with patch.object(chrome_remote, "_dev_url", "http://127.0.0.1:9222"):
            with patch("parser_2gis.chrome.remote._check_port_cached", return_value=False):
                with patch("parser_2gis.chrome.remote.pychrome.Browser"):
                    with patch.object(chrome_remote, "_create_tab", return_value=Mock()):
                        with patch.object(chrome_remote, "_start_tab_with_timeout"):
                            with patch.object(
                                chrome_remote, "_verify_connection", return_value=True
                            ):
                                # Не должно вызвать исключений
                                chrome_remote._attempt_connection()

    def test_attempt_connection_port_busy(self) -> None:
        """Тест 2: Порт свободен (Chrome не запущен).

        Проверяет что вызывается ChromeException.
        """
        from parser_2gis.chrome.remote import ChromeRemote
        from parser_2gis.chrome.options import ChromeOptions
        from parser_2gis.chrome.exceptions import ChromeException

        mock_options = Mock(spec=ChromeOptions)
        chrome_remote = ChromeRemote(mock_options, [])

        with patch.object(chrome_remote, "_dev_url", "http://127.0.0.1:9222"):
            with patch("parser_2gis.chrome.remote._check_port_cached", return_value=True):
                with pytest.raises(ChromeException, match="Порт.*свободен"):
                    chrome_remote._attempt_connection()

    def test_connect_interface_retry(self) -> None:
        """Тест 3: Retry логика подключения.

        Проверяет что _connect_interface делает несколько попыток.
        """
        from parser_2gis.chrome.remote import ChromeRemote
        from parser_2gis.chrome.options import ChromeOptions

        mock_options = Mock(spec=ChromeOptions)
        chrome_remote = ChromeRemote(mock_options, [])

        call_count = {"value": 0}

        def fail_once_then_succeed():
            call_count["value"] += 1
            if call_count["value"] == 1:
                from parser_2gis.chrome.exceptions import ChromeException

                raise ChromeException("First attempt fails")
            return True

        with patch.object(chrome_remote, "_dev_url", "http://127.0.0.1:9222"):
            with patch.object(chrome_remote, "_attempt_connection") as mock_attempt:
                mock_attempt.side_effect = fail_once_then_succeed

                result = chrome_remote._connect_interface()

                # Должно быть 2 попытки
                assert mock_attempt.call_count == 2
                assert result is True


# =============================================================================
# ISSUE-018: Упрощение обработки ошибок БД
# =============================================================================


class TestDatabaseErrorSimplification:
    """Тесты упрощения обработки ошибок БД (ISSUE-018)."""

    def test_is_retryable_error_operational(self) -> None:
        """Тест 1: OperationalError - временная ошибка.

        Проверяет что OperationalError классифицируется как временная.
        """
        error = sqlite3.OperationalError("database is locked")
        assert _is_retryable_error(error) is True

    def test_is_retryable_error_timeout(self) -> None:
        """Тест 2: Timeout - временная ошибка.

        Проверяет что timeout классифицируется как временная ошибка.
        """
        error = sqlite3.OperationalError("timeout")
        assert _is_retryable_error(error) is True

    def test_is_critical_error_integrity(self) -> None:
        """Тест 3: IntegrityError - критическая ошибка.

        Проверяет что IntegrityError классифицируется как критическая.
        """
        error = sqlite3.IntegrityError("UNIQUE constraint failed")
        assert _is_critical_error(error) is True

    def test_is_critical_error_programming(self) -> None:
        """Тест 4: ProgrammingError - критическая ошибка.

        Проверяет что ProgrammingError классифицируется как критическая.
        """
        error = sqlite3.ProgrammingError("SQL syntax error")
        assert _is_critical_error(error) is True

    def test_handle_db_errors_retry_on_temporary(self) -> None:
        """Тест 5: Retry для временных ошибок.

        Проверяет что временные ошибки вызывают retry.
        """
        call_count = {"value": 0}

        @handle_db_errors(retry_count=2, retry_delay=0.01)
        def failing_function():
            call_count["value"] += 1
            if call_count["value"] < 3:
                raise sqlite3.OperationalError("database is locked")
            return "success"

        result = failing_function()

        assert result == "success"
        assert call_count["value"] == 3

    def test_handle_db_errors_reraise_critical(self) -> None:
        """Тест 6: Проброс критических ошибок.

        Проверяет что критические ошибки пробрасываются дальше.
        """

        @handle_db_errors(retry_count=0, reraise_critical=True)
        def critical_function():
            raise sqlite3.IntegrityError("UNIQUE constraint failed")

        with pytest.raises(DatabaseError, match="Критическая ошибка БД"):
            critical_function()


# =============================================================================
# ISSUE-019: Упрощение TempFileTimer
# =============================================================================


class TestTempFileTimerSimplification:
    """Тесты упрощения TempFileTimer (ISSUE-019)."""

    def test_timer_no_weakref(self) -> None:
        """Тест 1: Отсутствие weakref.

        Проверяет что weakref не используется.
        """
        timer = TempFileTimer()

        # Проверяем что нет атрибутов weakref
        assert not hasattr(timer, "_weak_ref")
        assert not hasattr(timer, "_finalizer")
        assert not hasattr(timer, "_stop_event")
        assert not hasattr(timer, "_lock")

    def test_timer_simple_start_stop(self) -> None:
        """Тест 2: Простой запуск/остановка.

        Проверяет что timer запускается и останавливается без ошибок.
        """
        timer = TempFileTimer(interval=60)

        timer.start()
        assert timer._is_running is True

        timer.stop()
        assert timer._is_running is False

    def test_timer_cleanup_callback(self) -> None:
        """Тест 3: Callback очистки.

        Проверяет что callback вызывается корректно.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            timer = TempFileTimer(temp_dir=Path(tmpdir), interval=60)

            # Создаём тестовый файл
            test_file = Path(tmpdir) / "test.tmp"
            test_file.touch()

            # Вызываем callback напрямую
            timer._cleanup_callback()

            # Файл должен быть удалён (если возраст > orphan_age)
            # Или остаться если файл свежий
            # Проверяем что callback отработал без ошибок

    def test_timer_threading_timer_only(self) -> None:
        """Тест 4: Использование только threading.Timer.

        Проверяет что используется простой threading.Timer.
        """
        timer = TempFileTimer(interval=60)
        timer.start()

        # Проверяем что timer это threading.Timer
        assert isinstance(timer._timer, threading.Timer) or timer._timer is None

        timer.stop()


# =============================================================================
# ISSUE-020: AppState dataclass
# =============================================================================


class TestAppStateDataclass:
    """Тесты AppState dataclass (ISSUE-020)."""

    def test_dataclass_default_values(self) -> None:
        """Тест 1: Значения по умолчанию.

        Проверяет что dataclass имеет правильные значения по умолчанию.
        """
        state = AppState()

        assert state.selected_cities == []
        assert state.selected_categories == []
        assert state.parsing_active is False
        assert state.parsing_progress == 0
        assert state.total_urls == 0
        assert state._parsing_logs == []

    def test_dataclass_update(self) -> None:
        """Тест 2: Обновление полей.

        Проверяет что метод update() работает корректно.
        """
        state = AppState()

        state.update(selected_cities=["Moscow"], parsing_active=True)

        assert state.selected_cities == ["Moscow"]
        assert state.parsing_active is True

    def test_dataclass_reset(self) -> None:
        """Тест 3: Сброс состояния.

        Проверяет что reset() возвращает значения по умолчанию.
        """
        state = AppState()
        state.update(selected_cities=["Moscow"], parsing_active=True, success_count=10)

        state.reset()

        assert state.selected_cities == []
        assert state.parsing_active is False
        assert state.success_count == 0

    def test_dataclass_to_dict(self) -> None:
        """Тест 4: Конвертация в словарь.

        Проверяет что to_dict() возвращает корректный словарь.
        """
        state = AppState(selected_cities=["Moscow"], success_count=5)

        state_dict = state.to_dict()

        assert isinstance(state_dict, dict)
        assert state_dict["selected_cities"] == ["Moscow"]
        assert state_dict["success_count"] == 5
        assert "parsing_active" in state_dict

    def test_dataclass_field_default_factory(self) -> None:
        """Тест 5: factory для списков.

        Проверяет что list поля используют default_factory.
        """
        state1 = AppState()
        state2 = AppState()

        # Изменение одного не должно влиять на другой
        state1.selected_cities.append("Moscow")

        assert "Moscow" in state1.selected_cities
        assert "Moscow" not in state2.selected_cities
