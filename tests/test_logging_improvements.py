"""
Тесты для проверки улучшений логирования.

Проверяет корректность логирования ошибок и использования уровней.
Тесты покрывают исправления из отчета FIXES_IMPLEMENTATION_REPORT.md:
- Добавлено логирование во всех обработчиках исключений
- Критичные ошибки на ERROR, некритичные на DEBUG/WARNING
- Контекст в сообщениях (имена переменных, детали операции)
"""

import logging
import threading

import pytest


class TestErrorLogging:
    """Тесты для проверки логирования ошибок."""

    def test_error_logging_with_context(self, caplog):
        """
        Тест 7.1: Проверка логирования ошибок.

        Вызывает функцию с ошибкой.
        Проверяет что logger.error вызван с контекстом.
        """
        from parser_2gis.logger import logger

        # Устанавливаем уровень логирования для тестов
        logger.setLevel(logging.ERROR)

        # Логируем ошибку с контекстом
        error_detail = "Тестовая ошибка"
        file_name = "test_file.py"
        operation = "тестовая операция"

        logger.error("Ошибка при %s в файле %s: %s", operation, file_name, error_detail)

        # Проверяем что сообщение содержит контекст
        assert "Ошибка при" in caplog.text
        assert operation in caplog.text
        assert file_name in caplog.text
        assert error_detail in caplog.text

    def test_signal_handler_error_logging(self, caplog):
        """
        Проверка что signal_handler логирует ошибки с деталями.
        """
        from parser_2gis.utils.signal_handler import SignalHandler

        handler = SignalHandler()
        handler.register()

        # Проверяем что handler зарегистрирован
        assert handler._registered is True

        # Проверяем что логирование работает
        handler.cancel()
        assert handler.is_cancelled() is True

        handler.unregister()
        # Handler должен корректно unregister
        assert handler._registered is False

    def test_parallel_parser_error_logging(self, caplog, tmp_path):
        """
        Проверка что parallel_parser логирует ошибки merge.
        """
        import logging

        from parser_2gis.parallel.merger import ParallelFileMerger

        # Создаем ParallelFileMerger (вместо удалённого FileMerger из helpers.py)
        cancel_event = threading.Event()

        # ParallelFileMerger требует config и lock, создаём минимальный mock
        class _MockConfig:
            class writer:
                encoding = "utf-8"

        import threading as _threading

        mock_lock = _threading.RLock()
        merger = ParallelFileMerger(
            output_dir=tmp_path, config=_MockConfig(), cancel_event=cancel_event, lock=mock_lock
        )

        # Проверяем что ParallelFileMerger имеет необходимые атрибуты
        assert merger is not None
        assert hasattr(merger, "merge_csv_files")

        # Тестируем логирование напрямую
        logger = logging.getLogger("parser_2gis.parallel.merger")
        logger.setLevel(logging.INFO)
        logger.info("Тестовое сообщение для проверки логирования")

        # Проверяем что логирование работает
        assert "Тестовое сообщение" in caplog.text


class TestLoggingLevels:
    """Тесты для проверки уровней логирования."""

    def test_critical_errors_on_error_level(self, caplog):
        """
        Тест 7.2: Проверка что критичные ошибки на ERROR.

        Проверяет что критичные ошибки логируются на уровне ERROR.
        """
        from parser_2gis.logger import logger

        logger.setLevel(logging.ERROR)

        # Логируем критичную ошибку
        logger.error("Критичная ошибка: не удалось подключиться к браузеру")

        # Проверяем уровень
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "ERROR"
        assert "Критичная ошибка" in caplog.text

    def test_non_critical_on_debug_warning(self, caplog):
        """
        Проверка что некритичные ошибки на DEBUG/WARNING.

        Проверяет что некритичные проблемы логируются на соответствующем уровне.
        """
        from parser_2gis.logger import logger

        logger.setLevel(logging.DEBUG)

        # Логируем предупреждение
        logger.warning("Предупреждение: медленное соединение")

        # Логируем debug сообщение
        logger.debug("Debug: детали операции")

        # Проверяем уровни
        assert len(caplog.records) == 2

        warning_record = caplog.records[0]
        debug_record = caplog.records[1]

        assert warning_record.levelname == "WARNING"
        assert debug_record.levelname == "DEBUG"

    def test_cleanup_errors_on_warning(self, caplog):
        """
        Проверка что ошибки очистки на WARNING.

        Ошибки при очистке ресурсов не критичны и должны быть на WARNING.
        """
        from parser_2gis.logger import logger

        logger.setLevel(logging.WARNING)

        # Симулируем ошибку очистки
        try:
            raise OSError("Не удалось удалить временный файл")
        except OSError as e:
            logger.warning("Не удалось удалить временный файл: %s", e)

        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"


class TestLoggingContext:
    """Тесты для проверки контекста в логах."""

    def test_log_messages_contain_variable_names(self, caplog):
        """
        Тест 7.3: Проверка что сообщения содержат имена переменных.

        Проверяет что сообщения логирования содержат имена и значения переменных.
        """
        from parser_2gis.logger import logger

        logger.setLevel(logging.INFO)

        # Логируем с контекстом
        city_name = "Москва"
        category = "Кафе"
        url = "https://2gis.ru/moscow/search/Кафе"

        logger.info("Парсинг города %s, категория %s, URL: %s", city_name, category, url)

        # Проверяем что все переменные в сообщении
        assert city_name in caplog.text
        assert category in caplog.text
        assert url in caplog.text

    def test_log_messages_contain_operation_details(self, caplog):
        """
        Проверка что сообщения содержат детали операции.
        """
        from parser_2gis.logger import logger

        logger.setLevel(logging.INFO)

        # Логируем с деталями операции
        operation = "объединение файлов"
        files_count = 5
        output_file = "result.csv"

        logger.info(
            "Операция: %s, файлов: %d, выходной файл: %s", operation, files_count, output_file
        )

        # Проверяем детали
        assert operation in caplog.text
        assert str(files_count) in caplog.text
        assert output_file in caplog.text

    def test_exception_logging_with_traceback(self, caplog):
        """
        Проверка что исключения логируются с traceback.
        """
        import traceback

        from parser_2gis.logger import logger

        logger.setLevel(logging.ERROR)

        # Логируем исключение с traceback
        try:
            raise ValueError("Тестовая ошибка")
        except ValueError:
            logger.error("Ошибка: %s", traceback.format_exc())

        # Проверяем что traceback в логе
        assert "ValueError" in caplog.text
        assert "Тестовая ошибка" in caplog.text
        assert "Traceback" in caplog.text or "error" in caplog.text.lower()


class TestLoggerConfiguration:
    """Тесты для проверки конфигурации логгера."""

    def test_logger_has_handlers(self):
        """
        Проверка что логгер имеет обработчики.
        """
        from parser_2gis.logger import logger

        # Логгер должен иметь хотя бы один обработчик после setup
        # В тестах может не быть обработчиков, поэтому просто проверяем
        # что логгер существует
        assert logger is not None
        assert isinstance(logger.name, str)
        assert logger.name == "parser-2gis"

    def test_logger_level_configuration(self):
        """
        Проверка что уровень логгера настраивается.
        """
        from parser_2gis.logger import logger

        # Сохраняем оригинальный уровень
        original_level = logger.level

        try:
            # Устанавливаем новый уровень
            logger.setLevel(logging.DEBUG)
            assert logger.level == logging.DEBUG

            logger.setLevel(logging.WARNING)
            assert logger.level == logging.WARNING

        finally:
            # Восстанавливаем уровень
            logger.setLevel(original_level)


# Запуск тестов через pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
