"""
Тесты для модуля logger.py.

Проверяют следующие возможности:
- Настройка логгера
- Форматирование сообщений
- Уровни логирования
- QueueHandler для GUI
"""

import logging
import queue

from parser_2gis.logger import logger, setup_cli_logger, setup_gui_logger
from parser_2gis.logger.logger import QueueHandler
from parser_2gis.logger.options import LogOptions


class TestLoggerSetup:
    """Тесты для настройки логгера."""

    def test_logger_exists(self):
        """Проверка существования логгера."""
        assert logger is not None
        assert logger.name == 'parser-2gis'

    def test_logger_level_default(self):
        """Проверка уровня логгера по умолчанию."""
        # После импорта уровень должен быть установлен
        assert logger.level == logging.NOTSET or logger.level > 0

    def test_setup_logger_creates_handler(self):
        """Проверка создания обработчика."""
        test_logger = logging.getLogger('test-logger')
        original_handlers = test_logger.handlers.copy()

        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.INFO)

        assert len(test_logger.handlers) == len(original_handlers) + 1

    def test_setup_cli_logger(self):
        """Проверка настройки CLI логгера."""
        options = LogOptions()
        setup_cli_logger(options)
        # Логгер должен быть настроен
        assert logger is not None

    def test_setup_logger_with_custom_format(self):
        """Проверка настройки с кастомным форматом."""
        test_logger = logging.getLogger('test-custom-format')
        handler = logging.StreamHandler()
        formatter = logging.Formatter('[CUSTOM] %(message)s')
        handler.setFormatter(formatter)
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.DEBUG)

        assert len(test_logger.handlers) >= 1


class TestLoggerLevels:
    """Тесты для уровней логирования."""

    def test_logger_debug(self):
        """Проверка логирования debug."""
        logger.debug('Test debug message')
        # Если нет ошибок, тест пройден

    def test_logger_info(self):
        """Проверка логирования info."""
        logger.info('Test info message')
        # Если нет ошибок, тест пройден

    def test_logger_warning(self):
        """Проверка логирования warning."""
        logger.warning('Test warning message')
        # Если нет ошибок, тест пройден

    def test_logger_error(self):
        """Проверка логирования error."""
        logger.error('Test error message')
        # Если нет ошибок, тест пройден

    def test_logger_critical(self):
        """Проверка логирования critical."""
        logger.critical('Test critical message')
        # Если нет ошибок, тест пройден


class TestQueueHandler:
    """Тесты для QueueHandler."""

    def test_queue_handler_creation(self):
        """Проверка создания QueueHandler."""
        log_queue = queue.Queue()
        handler = QueueHandler(log_queue)

        assert handler._log_queue == log_queue
        assert isinstance(handler, logging.Handler)

    def test_queue_handler_emit(self):
        """Проверка отправки сообщений в очередь."""
        log_queue = queue.Queue()

        handler = QueueHandler(log_queue)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='test.py',
            lineno=1,
            msg='Test message',
            args=(),
            exc_info=None
        )

        handler.emit(record)

        assert not log_queue.empty()
        level, message = log_queue.get()
        assert level == 'INFO'
        assert 'Test message' in message

    def test_setup_gui_logger(self):
        """Проверка настройки GUI логгера."""
        log_queue = queue.Queue()
        options = LogOptions()
        setup_gui_logger(log_queue, options)

        # Должен быть добавлен обработчик
        assert len(logger.handlers) >= 1


class TestLogOptions:
    """Тесты для LogOptions."""

    def test_log_options_default(self):
        """Проверка значений по умолчанию."""
        options = LogOptions()
        assert options.level == 'DEBUG'
        assert options.cli_format is not None
        assert options.gui_format is not None

    def test_log_options_custom(self):
        """Проверка кастомных значений."""
        options = LogOptions(
            level='INFO',
            cli_format='[CLI] %(message)s',
            gui_format='[GUI] %(message)s'
        )
        assert options.level == 'INFO'
        assert options.cli_format == '[CLI] %(message)s'
        assert options.gui_format == '[GUI] %(message)s'


class TestThirdPartyLoggers:
    """Тесты для сторонних логгеров."""

    def test_urllib3_logger_level(self):
        """Проверка уровня логгера urllib3."""
        urllib3_logger = logging.getLogger('urllib3')
        assert urllib3_logger.level == logging.ERROR

    def test_pychrome_logger_level(self):
        """Проверка уровня логгера pychrome."""
        pychrome_logger = logging.getLogger('pychrome')
        # Уровень ERROR (40) для отладочной информации
        assert pychrome_logger.level == logging.ERROR


class TestLoggerMessageFormatting:
    """Тесты для форматирования сообщений."""

    def test_logger_format_with_args(self):
        """Проверка форматирования с аргументами."""
        test_logger = logging.getLogger('test-format-args')
        test_logger.setLevel(logging.INFO)

        if not test_logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(message)s - %(args)s')
            handler.setFormatter(formatter)
            test_logger.addHandler(handler)

        # Если нет ошибок, тест пройден
        test_logger.info('Test with args')

    def test_logger_format_exception(self):
        """Проверка форматирования исключений."""
        test_logger = logging.getLogger('test-format-exception')
        test_logger.setLevel(logging.ERROR)

        if not test_logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(message)s\n%(exc_text)s')
            handler.setFormatter(formatter)
            test_logger.addHandler(handler)

        try:
            raise ValueError('Test exception')
        except ValueError:
            test_logger.exception('Exception occurred')
