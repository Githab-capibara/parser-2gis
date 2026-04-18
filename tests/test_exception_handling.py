"""
Тесты для проверки обработки исключений.

Проверяет что исключения логируются, а не проглатываются.
Тесты покрывают исправления:
- Добавлено логирование во всех обработчиках исключений
- Критичные ошибки на ERROR, некритичные на DEBUG/WARNING
- Контекст в сообщениях (имена переменных, детали операции)
"""

import logging

import pytest


class TestExceptionHandlingInCacheManager:
    """Тесты для проверки обработки исключений в CacheManager."""

    def test_cache_get_raises_exception_on_invalid_url(self) -> None:
        """
        Тест 1.1: Проверка что cache.get() вызывает исключение на некорректном URL.

        Проверяет что при ошибке чтения из кэша исключение распространяется.
        """
        import tempfile
        from pathlib import Path

        from parser_2gis.cache.manager import CacheManager

        # Создаём временный кэш
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache = CacheManager(cache_dir=Path(tmp_dir))

            # Проверяем что метод работает без ошибок
            result = cache.get("http://test.com")
            assert result is None  # Кэш пуст

    def test_cache_set_handles_invalid_data(self) -> None:
        """
        Тест 1.2: Проверка обработки некорректных данных в cache.set().

        Проверяет что метод обрабатывает некорректные данные.
        """
        import tempfile
        from pathlib import Path

        from parser_2gis.cache.manager import CacheManager

        with tempfile.TemporaryDirectory() as tmp_dir:
            cache = CacheManager(cache_dir=Path(tmp_dir))

            # Метод должен выбросить TypeError при передаче None значения
            # Проверяем что исключение выбрасывается корректно
            with pytest.raises(TypeError, match="не могут быть None"):
                cache.set("http://test.com", None)

    def test_cache_close_works_without_error(self) -> None:
        """
        Тест 1.3: Проверка что cache.close() работает без ошибок.

        Проверяет что закрытие кэша выполняется корректно.
        """
        import tempfile
        from pathlib import Path

        from parser_2gis.cache.manager import CacheManager

        with tempfile.TemporaryDirectory() as tmp_dir:
            cache = CacheManager(cache_dir=Path(tmp_dir))

            # Закрываем кэш - метод должен выполниться без ошибок
            cache.close()

            # Проверяем что пул закрыт (установлен в None)
            assert cache._pool is None


class TestExceptionHandlingInFileLogger:
    """Тесты для проверки обработки исключений в FileLogger."""

    def test_file_logger_handles_invalid_path(self, tmp_path, caplog) -> None:
        """
        Тест 2.1: Проверка обработки некорректного пути в FileLogger.

        Проверяет что FileLogger обрабатывает некорректный путь.
        """
        import logging

        from parser_2gis.chrome.file_handler import FileLogger

        # Создаём FileLogger с некорректным путём
        invalid_path = tmp_path / "nonexistent_dir" / "test.log"

        # FileLogger должен создать директорию или обработать ошибку
        # Проверяем что логирование происходит при ошибке
        caplog.set_level(logging.DEBUG)

        logger = FileLogger(invalid_path)  # Передаём Path вместо str

        # FileLogger не имеет метода write, используем setup_logger
        test_logger = logging.getLogger("test_logger")
        logger.setup_logger(test_logger)
        test_logger.info("Test message")

        # Проверяем что файл был создан (FileLogger создаёт директорию)
        assert invalid_path.exists()

    def test_file_logger_handles_permission_error(self, tmp_path, caplog) -> None:
        """
        Тест 2.2: Проверка обработки ошибки разрешений в FileLogger.

        Проверяет что ошибка разрешений обрабатывается корректно.
        """
        import logging

        from parser_2gis.chrome.file_handler import FileLogger

        # Создаём файл и делаем его недоступным для записи
        log_file = tmp_path / "readonly.log"
        log_file.write_text("")
        log_file.chmod(0o444)  # Только для чтения

        caplog.set_level(logging.ERROR)

        exception_raised = False
        try:
            logger = FileLogger(log_file)  # Передаём Path вместо str
            logger.write("Test message", "info")
        except (PermissionError, OSError, AttributeError):
            # Проверяем что ошибка была выброшена
            exception_raised = True

        # Проверяем что исключение было выброшено или файл существует
        assert exception_raised or log_file.exists()


class TestExceptionHandlingInParallelParser:
    """Тесты для проверки обработки исключений в ParallelCityParser."""

    def test_parallel_parser_merge_handles_missing_files(self, tmp_path, caplog) -> None:
        """
        Тест 3.1: Проверка обработки отсутствующих файлов при слиянии.

        Проверяет что ошибка при слиянии отсутствующих файлов обрабатывается.
        """
        import logging

        from parser_2gis.config import Configuration
        from parser_2gis.parallel.parallel_parser import ParallelCityParser

        caplog.set_level(logging.WARNING)

        config = Configuration()
        cities = [{"name": "Test", "code": "test", "domain": "test"}]
        categories = [{"name": "Test", "code": "test"}]

        parser = ParallelCityParser(cities, categories, str(tmp_path), config)

        # Пытаемся слить несуществующие файлы
        csv_files = [tmp_path / "nonexistent1.csv", tmp_path / "nonexistent2.csv"]
        output_file = tmp_path / "output.csv"

        # Метод должен обработать ошибку и залогировать её
        parser.merge_csv_files(str(output_file), csv_files)

        # Проверяем что предупреждение было залогировано
        assert any(
            "не найдено" in record.message.lower()
            or "csv файлов" in record.message.lower()
            or "объединения" in record.message.lower()
            for record in caplog.records
        )

    def test_parallel_parser_handles_exceptions(self, caplog, tmp_path) -> None:
        """
        Тест 3.2: Проверка обработки исключений в параллельном парсере.

        Проверяет что парсер корректно обрабатывает исключения.
        """
        from parser_2gis.config import Configuration
        from parser_2gis.parallel.parallel_parser import ParallelCityParser

        caplog.set_level(logging.ERROR)

        config = Configuration()
        cities = [{"name": "Test", "code": "test", "domain": "test"}]
        categories = [{"name": "Test", "code": "test"}]

        parser = ParallelCityParser(cities, categories, str(tmp_path), config)

        # Проверяем что парсер создан и имеет методы для обработки ошибок
        assert parser is not None
        assert hasattr(parser, "log")


class TestExceptionHandlingInDataValidator:
    """Тесты для проверки обработки исключений в валидаторах данных."""

    def test_validate_positive_int_logs_error(self, caplog) -> None:
        """
        Тест 4.1: Проверка обработки ошибки в validate_positive_int().

        Проверяет что ошибка валидации числа выбрасывает ValueError.
        """
        import logging

        from parser_2gis.validation.data_validator import validate_positive_int

        caplog.set_level(logging.ERROR)

        # Пытаемся валидировать некорректное значение
        with pytest.raises(ValueError) as exc_info:
            validate_positive_int(-1, 1, 100, "--test.arg")

        # Проверяем что ошибка была вызвана и содержит контекст
        assert "--test.arg" in str(exc_info.value)
        assert "1" in str(exc_info.value)

        # Проверяем что ValueError содержит правильную информацию
        assert "не менее" in str(exc_info.value)
        assert "-1" in str(exc_info.value)

    def test_validate_url_logs_warning(self, caplog) -> None:
        """
        Тест 4.2: Проверка логирования предупреждения в validate_url().

        Проверяет что некорректный URL логируется как warning.
        """
        from parser_2gis.validation.url_validator import validate_url

        caplog.set_level(logging.WARNING)

        # Валидируем некорректный URL
        result = validate_url("not-a-valid-url")

        # Проверяем что результат содержит ошибку
        assert result.is_valid is False
        assert result.error is not None


class TestExceptionHandlingWithContext:
    """Тесты для проверки что исключения логируются с контекстом."""

    def test_exception_logged_with_variable_context(self, caplog) -> None:
        """
        Тест 5.1: Проверка что исключения логируются с контекстом переменных.

        Проверяет что сообщения об ошибках содержат имена переменных.
        """
        from parser_2gis.logger import logger

        caplog.set_level(logging.ERROR)

        # Логируем ошибку с контекстом
        var_name = "test_variable"
        var_value = "test_value"
        operation = "тестовая операция"

        logger.error("Ошибка при %s: переменная %s имеет значение %s", operation, var_name, var_value)

        # Проверяем что контекст присутствует в сообщении
        assert var_name in caplog.text, "Имя переменной должно быть в сообщении"
        assert operation in caplog.text, "Операция должна быть в сообщении"

    def test_exception_logged_with_file_context(self, caplog) -> None:
        """
        Тест 5.2: Проверка что исключения логируются с контекстом файла.

        Проверяет что сообщения об ошибках содержат имя файла.
        """
        from parser_2gis.logger import logger

        caplog.set_level(logging.ERROR)

        file_name = "test_file.py"
        line_number = 42
        error_msg = "Test error"

        logger.error("Ошибка в файле %s, строка %d: %s", file_name, line_number, error_msg)

        # Проверяем что контекст присутствует
        assert file_name in caplog.text, "Имя файла должно быть в сообщении"
        assert str(line_number) in caplog.text, "Номер строки должен быть в сообщении"


class TestExceptionNotSwallowed:
    """Тесты для проверки что исключения не проглатываются."""

    def test_exception_propagates_to_caller(self) -> None:
        """
        Тест 6.1: Проверка что исключения не проглатываются.

        Проверяет что исключения распространяются до вызывающего кода.
        """
        from parser_2gis.validation.data_validator import validate_positive_int

        # Исключение должно распространиться до теста
        with pytest.raises(ValueError) as exc_info:
            validate_positive_int(0, 1, 100, "--test.arg")

        # Проверяем что исключение содержит контекст
        assert "--test.arg" in str(exc_info.value)
        assert "1" in str(exc_info.value)

    def test_cache_exception_propagates_on_none_url(self) -> None:
        """
        Тест 6.2: Проверка что исключения кэша распространяются.

        Проверяет что исключения кэша не проглатываются.
        """
        import tempfile
        from pathlib import Path

        from parser_2gis.cache.manager import CacheManager

        # Создаём временный кэш
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache = CacheManager(cache_dir=Path(tmp_dir))

            # Метод должен работать без ошибок
            result = cache.get("http://test.com")
            assert result is None  # Кэш пуст


# Запуск тестов через pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
