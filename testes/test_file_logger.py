"""
Тесты для модуля файлового логирования (FileLogger).

Проверяют следующие возможности:
- Создание FileLogger
- Настройка обработчика файла
- Запись логов в файл
- Вращение логов
- Валидация уровней логирования
- Контекстный менеджер
"""

import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from parser_2gis.logger import FileLogger


class TestFileLoggerInitialization:
    """Тесты для инициализации FileLogger."""
    
    def test_file_logger_without_file(self):
        """Проверка создания FileLogger без файла логов."""
        # Отключаем автоматическую сессию, чтобы log_file остался None
        file_logger = FileLogger(log_file=None, auto_session=False)

        assert file_logger is not None
        assert file_logger.log_file is None
        assert not file_logger.is_enabled
    
    def test_file_logger_with_file(self):
        """Проверка создания FileLogger с файлом логов."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            log_file = Path(f.name)
        
        try:
            file_logger = FileLogger(log_file=log_file)
            
            assert file_logger is not None
            assert file_logger.log_file == log_file
            assert file_logger.is_enabled
        finally:
            if log_file.exists():
                log_file.unlink()
    
    def test_file_logger_default_level(self):
        """Проверка уровня логирования по умолчанию."""
        file_logger = FileLogger()
        
        assert file_logger is not None
    
    def test_file_logger_custom_level(self):
        """Проверка кастомного уровня логирования."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            log_file = Path(f.name)
        
        try:
            file_logger = FileLogger(log_file=log_file, log_level='INFO')
            
            assert file_logger is not None
            assert file_logger.log_file == log_file
        finally:
            if log_file.exists():
                log_file.unlink()
    
    def test_file_logger_invalid_level(self):
        """Проверка валидации некорректного уровня логирования."""
        with pytest.raises(ValueError, match="Некорректный уровень логирования"):
            FileLogger(log_level='INVALID_LEVEL')


class TestFileLoggerSetup:
    """Тесты для настройки FileLogger."""
    
    def test_file_logger_creates_directory(self):
        """Проверка создания директории для логов."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / 'logs' / 'parser.log'
            
            file_logger = FileLogger(log_file=log_file)
            file_logger.setup_logger(logging.getLogger('test-logger'))
            
            assert log_file.parent.exists()
            assert log_file.parent.is_dir()
    
    def test_file_logger_setup_logger(self):
        """Проверка настройки логгера."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            log_file = Path(f.name)
        
        try:
            file_logger = FileLogger(log_file=log_file, log_level='INFO')
            test_logger = logging.getLogger('test-setup')
            
            file_logger.setup_logger(test_logger)
            
            assert file_logger.is_enabled
            assert len(test_logger.handlers) >= 1
        finally:
            if log_file.exists():
                log_file.unlink()


class TestFileLoggerLogging:
    """Тесты для записи логов в файл."""
    
    def test_file_logger_writes_to_file(self):
        """Проверка записи логов в файл."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = Path(f.name)
        
        try:
            file_logger = FileLogger(log_file=log_file)
            test_logger = logging.getLogger('test-write')
            
            file_logger.setup_logger(test_logger)
            test_logger.info('Тестовое сообщение')
            
            # Закрываем обработчик для сброса буфера
            file_logger.close()
            
            # Читаем файл и проверяем наличие сообщения
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                assert 'Тестовое сообщение' in content
                assert 'INFO' in content
        finally:
            if log_file.exists():
                log_file.unlink()
    
    def test_file_logger_multiple_messages(self):
        """Проверка записи нескольких сообщений."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = Path(f.name)
        
        try:
            file_logger = FileLogger(log_file=log_file)
            test_logger = logging.getLogger('test-multiple')
            
            file_logger.setup_logger(test_logger)
            test_logger.info('Сообщение 1')
            test_logger.warning('Предупреждение 2')
            test_logger.error('Ошибка 3')
            
            file_logger.close()
            
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                assert 'Сообщение 1' in content
                assert 'Предупреждение 2' in content
                assert 'Ошибка 3' in content
                assert 'INFO' in content
                assert 'WARNING' in content
                assert 'ERROR' in content
        finally:
            if log_file.exists():
                log_file.unlink()
    
    def test_file_logger_level_filtering(self):
        """Проверка фильтрации по уровню логирования."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = Path(f.name)
        
        try:
            # Создаем логгер с уровнем WARNING
            file_logger = FileLogger(log_file=log_file, log_level='WARNING')
            test_logger = logging.getLogger('test-level')
            
            file_logger.setup_logger(test_logger)
            test_logger.debug('DEBUG сообщение')
            test_logger.info('INFO сообщение')
            test_logger.warning('WARNING сообщение')
            test_logger.error('ERROR сообщение')
            
            file_logger.close()
            
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                assert 'DEBUG сообщение' not in content
                assert 'INFO сообщение' not in content
                assert 'WARNING сообщение' in content
                assert 'ERROR сообщение' in content
        finally:
            if log_file.exists():
                log_file.unlink()


class TestFileLoggerContextManager:
    """Тесты для контекстного менеджера FileLogger."""
    
    def test_file_logger_context_manager(self):
        """Проверка работы контекстного менеджера."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = Path(f.name)
        
        try:
            with FileLogger(log_file=log_file) as file_logger:
                assert file_logger.is_enabled
                
                test_logger = logging.getLogger('test-context')
                file_logger.setup_logger(test_logger)
                test_logger.info('Сообщение в контексте')
            
            # После выхода из контекста обработчик должен быть закрыт
            # Проверяем, что сообщение было записано
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                assert 'Сообщение в контексте' in content
        finally:
            if log_file.exists():
                log_file.unlink()
    
    def test_file_logger_context_manager_close(self):
        """Проверка закрытия через контекстный менеджер."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            log_file = Path(f.name)
        
        try:
            file_logger = FileLogger(log_file=log_file)
            
            with file_logger:
                assert file_logger.is_enabled
            
            # После выхода из контекста логгер должен быть закрыт
            assert file_logger._file_handler is None
        finally:
            if log_file.exists():
                log_file.unlink()


class TestFileLoggerProperties:
    """Тесты для свойств FileLogger."""
    
    def test_file_logger_log_file_property(self):
        """Проверка свойства log_file."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            log_file = Path(f.name)
        
        try:
            file_logger = FileLogger(log_file=log_file)
            
            assert file_logger.log_file == log_file
        finally:
            if log_file.exists():
                log_file.unlink()
    
    def test_file_logger_is_enabled_property(self):
        """Проверка свойства is_enabled."""
        # Включено
        with tempfile.NamedTemporaryFile(delete=False) as f:
            log_file = Path(f.name)
        
        try:
            file_logger = FileLogger(log_file=log_file)
            assert file_logger.is_enabled is True
        finally:
            if log_file.exists():
                log_file.unlink()

        # Выключено (отключаем автоматическую сессию)
        file_logger = FileLogger(log_file=None, auto_session=False)
        assert file_logger.is_enabled is False


class TestFileLoggerClose:
    """Тесты для закрытия FileLogger."""
    
    def test_file_logger_close(self):
        """Проверка закрытия FileLogger."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            log_file = Path(f.name)
        
        try:
            file_logger = FileLogger(log_file=log_file)
            assert file_logger.is_enabled is True
            
            file_logger.close()
            assert file_logger._file_handler is None
        finally:
            if log_file.exists():
                log_file.unlink()
    
    def test_file_logger_close_multiple_times(self):
        """Проверка многократного закрытия FileLogger."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            log_file = Path(f.name)
        
        try:
            file_logger = FileLogger(log_file=log_file)
            
            # Закрываем несколько раз - не должно вызывать ошибок
            file_logger.close()
            file_logger.close()
            file_logger.close()
        finally:
            if log_file.exists():
                log_file.unlink()


class TestFileLoggerAdvancedFeatures:
    """Тесты для продвинутых возможностей FileLogger."""
    
    def test_file_logger_custom_max_bytes(self):
        """Проверка кастомного максимального размера файла."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            log_file = Path(f.name)
        
        try:
            # Создаем логгер с маленьким размером файла (1 KB)
            file_logger = FileLogger(
                log_file=log_file,
                max_bytes=1024  # 1 KB
            )
            
            assert file_logger is not None
        finally:
            if log_file.exists():
                log_file.unlink()
    
    def test_file_logger_custom_backup_count(self):
        """Проверка кастомного количества резервных копий."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            log_file = Path(f.name)
        
        try:
            # Создаем логгер с 10 резервными копиями
            file_logger = FileLogger(
                log_file=log_file,
                backup_count=10
            )
            
            assert file_logger is not None
        finally:
            if log_file.exists():
                log_file.unlink()
    
    def test_file_logger_multiple_loggers(self):
        """Проверка работы с несколькими логгерами."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = Path(f.name)
        
        try:
            file_logger = FileLogger(log_file=log_file)
            
            # Настраиваем несколько логгеров
            logger1 = logging.getLogger('test-multi-1')
            logger2 = logging.getLogger('test-multi-2')
            
            file_logger.setup_logger(logger1)
            file_logger.setup_logger(logger2)
            
            # Пишем в оба логгера
            logger1.info('Сообщение из logger1')
            logger2.info('Сообщение из logger2')
            
            file_logger.close()
            
            # Проверяем, что оба сообщения записаны
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                assert 'Сообщение из logger1' in content
                assert 'Сообщение из logger2' in content
        finally:
            if log_file.exists():
                log_file.unlink()
    
    def test_file_logger_special_characters(self):
        """Проверка записи специальных символов в лог."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file = Path(f.name)
        
        try:
            file_logger = FileLogger(log_file=log_file)
            test_logger = logging.getLogger('test-special')
            
            file_logger.setup_logger(test_logger)
            
            # Записываем сообщение с русскими символами и эмодзи
            test_logger.info('Привет мир! 🌍 Тест с кириллицей и эмодзи')
            
            file_logger.close()
            
            # Проверяем, что сообщение записано корректно
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                assert 'Привет мир! 🌍' in content
                assert 'Тест с кириллицей и эмодзи' in content
        finally:
            if log_file.exists():
                log_file.unlink()
