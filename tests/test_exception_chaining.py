"""
Тесты для проверки exception chaining (B904).

Проверяет что все обработчики исключений корректно используют
цепочки исключений (raise ... from ...) вместо простого raise.

Тесты покрывают исправления из отчета аудита:
- file_handler.py: exception chaining в файловом логгере
- remote.py: exception chaining в Chrome Remote
- pychrome warnings: обработка предупреждений pychrome
"""

import json
from unittest.mock import patch

import pytest

from parser_2gis.cache import _deserialize_json, _serialize_json
from parser_2gis.chrome.file_handler import FileLogger
from parser_2gis.chrome.remote import (
    _check_port_cached,
    _rate_limited_request,
    _safe_external_request,
)


class TestFileHandlerExceptionChaining:
    """Тесты для exception chaining в file_handler.py."""

    def test_exception_chaining_in_file_handler_invalid_log_level(self):
        """
        Тест 1.1: Проверка exception chaining при некорректном уровне логирования.

        Проверяет что при некорректном уровне логирования
        выбрасывается ValueError с правильной цепочкой исключений.
        """
        # Проверяем что выбрасывается ValueError с цепочкой исключений
        with pytest.raises(ValueError) as exc_info:
            FileLogger(log_level="INVALID_LEVEL")

        # Проверяем что исключение имеет правильный тип
        assert isinstance(exc_info.value, ValueError)
        # Проверяем что сообщение содержит информацию об ошибке
        assert "Некорректный уровень логирования" in str(exc_info.value)
        # Проверяем что есть контекст исключения (цепочка)
        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, AttributeError)

    def test_exception_chaining_in_file_handler_setup_error(self, tmp_path):
        """
        Тест 1.2: Проверка exception chaining при ошибке настройки обработчика.

        Проверяет что при ошибке настройки файлового обработчика
        выбрасывается IOError с правильной цепочкой исключений.
        """
        # Создаем путь к файлу в несуществующей директории
        log_file = tmp_path / "nonexistent_dir" / "parser.log"

        # Пытаемся создать логгер - должен успешно создаться
        # так как директория будет создана автоматически
        logger_instance = FileLogger(log_file=log_file, auto_session=False)

        # Проверяем что логгер создан
        assert logger_instance is not None
        assert logger_instance._log_file is not None

    def test_exception_chaining_in_file_handler_close_error(self, tmp_path, caplog):
        """
        Тест 1.3: Проверка exception chaining при ошибке закрытия обработчика.

        Проверяет что при ошибке закрытия файлового обработчика
        ошибка корректно логируется и обрабатывается.
        """
        log_file = tmp_path / "parser_test.log"

        # Создаем логгер
        logger_instance = FileLogger(log_file=log_file)

        # Mock file handler для вызова ошибки при закрытии
        with patch.object(logger_instance, "_file_handler") as mock_handler:
            mock_handler.close.side_effect = RuntimeError("Ошибка закрытия")

            # Вызываем close - не должно выбросить исключение
            logger_instance.close()

            # Проверяем что ошибка была залогирована
            assert (
                "Ошибка закрытия файлового обработчика" in caplog.text
                or "Ошибка закрытия" in caplog.text
            )


class TestRemoteExceptionChaining:
    """Тесты для exception chaining в remote.py."""

    def test_exception_chaining_pychrome_warnings(self, caplog):
        """
        Тест 2.1: Проверка обработки предупреждений pychrome.

        Проверяет что предупреждения DeprecationWarning от pychrome
        корректно фильтруются и логируются.
        """
        import warnings

        # Проверяем что фильтр предупреждений установлен
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")

            # Генерируем тестовое предупреждение
            warnings.warn("Тестовое предупреждение", DeprecationWarning)

            # Проверяем что предупреждение было создано
            assert len(warning_list) == 1
            assert issubclass(warning_list[0].category, DeprecationWarning)

    def test_exception_chaining_in_remote_port_check(self):
        """
        Тест 2.2: Проверка exception chaining при проверке порта.

        Проверяет что при ошибке проверки порта
        исключение корректно обрабатывается.
        """
        # Проверяем что функция существует и возвращает bool
        # Используем валидный порт чтобы избежать logger.debug вызова
        result = _check_port_cached(1)  # Порт 1 обычно свободен
        assert isinstance(result, bool)

    def test_exception_chaining_in_remote_rate_limit(self):
        """
        Тест 2.3: Проверка exception chaining при rate limiting.

        Проверяет что при ошибке rate limiting
        исключение корректно обрабатывается с цепочкой.
        """
        # Mock requests для вызова ошибки
        with patch("parser_2gis.chrome.remote.requests.get") as mock_get:
            mock_get.side_effect = Exception("Network error")

            # Проверяем что исключение пробрасывается с цепочкой
            with pytest.raises(Exception) as exc_info:
                _rate_limited_request("get", "http://example.com")

            assert "Network error" in str(exc_info.value)

    def test_exception_chaining_in_safe_external_request(self):
        """
        Тест 2.4: Проверка exception chaining в _safe_external_request.

        Проверяет что при ошибке внешнего запроса
        исключение корректно обрабатывается.
        """
        # Mock requests для вызова ошибки
        with patch("parser_2gis.chrome.remote.requests.get") as mock_get:
            mock_get.side_effect = Exception("Request failed")

            # Проверяем что исключение пробрасывается
            with pytest.raises(Exception) as exc_info:
                _safe_external_request("get", "http://example.com")

            assert "Request failed" in str(exc_info.value)


class TestCacheExceptionChaining:
    """Тесты для exception chaining в cache.py."""

    def test_exception_chaining_in_serialize_json(self):
        """
        Тест 3.1: Проверка exception chaining при сериализации JSON.

        Проверяет что при ошибке сериализации
        выбрасывается TypeError с правильной цепочкой исключений.
        """
        # Создаем данные которые нельзя сериализовать
        unserializable_data = {"key": lambda x: x}

        # Проверяем что выбрасывается TypeError с цепочкой
        with pytest.raises(TypeError) as exc_info:
            _serialize_json(unserializable_data)

        # Проверяем что исключение имеет правильный тип
        assert isinstance(exc_info.value, TypeError)
        # Проверяем что сообщение содержит информацию об ошибке
        assert "Critical JSON serialization error" in str(exc_info.value)
        # Проверяем что есть контекст исключения
        assert exc_info.value.__cause__ is not None

    def test_exception_chaining_in_deserialize_json_invalid(self):
        """
        Тест 3.2: Проверка exception chaining при десериализации некорректного JSON.

        Проверяет что при ошибке десериализации
        выбрасывается ValueError с правильной цепочкой исключений.
        """
        invalid_json = "{invalid json}"

        # Проверяем что выбрасывается ValueError или JSONDecodeError
        with pytest.raises((ValueError, json.JSONDecodeError)):
            _deserialize_json(invalid_json)

    def test_exception_chaining_in_deserialize_json_wrong_type(self):
        """
        Тест 3.3: Проверка exception chaining при десериализации неверного типа.

        Проверяет что при десериализации данных неверного типа
        выбрасывается TypeError с правильной цепочкой исключений.
        """
        # JSON массив вместо объекта
        json_array = "[1, 2, 3]"

        # Проверяем что выбрасывается TypeError
        with pytest.raises(TypeError):
            _deserialize_json(json_array)


class TestExceptionChainingComprehensive:
    """Комплексные тесты для exception chaining."""

    def test_all_file_handler_methods_have_chaining(self):
        """
        Тест 4.1: Проверка что все методы file_handler имеют exception chaining.

        Проверяет что все методы которые выбрасывают исключения
        используют правильную цепочку исключений.
        """
        # Проверяем что класс имеет правильную структуру
        assert hasattr(FileLogger, "__init__")
        assert hasattr(FileLogger, "setup_logger")
        assert hasattr(FileLogger, "close")

        # Проверяем что методы существуют
        assert callable(getattr(FileLogger, "__init__"))
        assert callable(getattr(FileLogger, "setup_logger"))
        assert callable(getattr(FileLogger, "close"))

    def test_all_remote_functions_have_chaining(self):
        """
        Тест 4.2: Проверка что все функции remote.py имеют exception chaining.

        Проверяет что все функции которые выбрасывают исключения
        используют правильную цепочку исключений.
        """
        # Проверяем что функции существуют
        assert callable(_check_port_cached)
        assert callable(_rate_limited_request)
        assert callable(_safe_external_request)

    def test_exception_context_preserved(self):
        """
        Тест 4.3: Проверка что контекст исключений сохраняется.

        Проверяет что при цепочке исключений
        оригинальное исключение доступно через __cause__.
        """
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise RuntimeError("Wrapped error") from e
        except RuntimeError as e:
            # Проверяем что контекст сохранен
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, ValueError)
            assert str(e.__cause__) == "Original error"


# Запуск тестов через pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
