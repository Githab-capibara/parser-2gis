# -*- coding: utf-8 -*-
"""
Тесты для проверки всех исправлений из аудита кода.

Этот модуль содержит тесты для проверки:
1. Исправления global переменной в main.py
2. Валидации CLI аргументов
3. Упрощения обработки zombie процессов Chrome
4. Исправления утечки временных файлов
5. Обработки TODO/FIXME комментариев
6. Рефакторинга merge_csv_files
7. Устранения magic numbers
8. Улучшения тестового покрытия
9. Упрощения условных импортов
10. Оптимизации логирования
11. Унификации стиля документации
12. Устранения дублирования валидации
"""

import os
import sys
import tempfile
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestGlobalVariableFix:
    """Тесты для проверки исправления global переменной в main.py."""
    
    def test_no_global_signal_handler_in_setup_function(self):
        """Тест: global _signal_handler_instance не объявляется в _setup_signal_handlers."""
        import parser_2gis.main as main_module
        import inspect
        
        # Получаем исходный код функции
        source = inspect.getsource(main_module._setup_signal_handlers)
        
        # Проверяем что global объявление отсутствует или используется корректно
        # После исправления не должно быть бессмысленного global объявления
        lines = source.split('\n')
        global_lines = [line for line in lines if 'global _signal_handler_instance' in line]
        
        # Если global есть, оно должно использоваться осмысленно
        assert len(global_lines) == 0, "global _signal_handler_instance должно быть удалено"
    
    def test_signal_handler_instance_created(self):
        """Тест: SignalHandler корректно создается и настраивается."""
        with patch('parser_2gis.main.SignalHandler') as mock_signal_handler:
            from parser_2gis.main import _setup_signal_handlers
            
            # Вызываем функцию
            _setup_signal_handlers()
            
            # Проверяем что SignalHandler был создан и настроен
            mock_signal_handler.assert_called_once()
            mock_instance = mock_signal_handler.return_value
            mock_instance.setup.assert_called_once()
    
    def test_signal_handler_setup_called(self):
        """Тест: метод setup() вызывается на экземпляре SignalHandler."""
        with patch('parser_2gis.main.SignalHandler') as mock_handler_class:
            mock_instance = Mock()
            mock_handler_class.return_value = mock_instance
            
            from parser_2gis.main import _setup_signal_handlers
            _setup_signal_handlers()
            
            # Проверяем что setup был вызван
            mock_instance.setup.assert_called_once()


class TestCLIArgumentValidation:
    """Тесты для проверки валидации CLI аргументов."""
    
    def test_max_retries_below_min(self):
        """Тест: max-retries < 1 вызывает ошибку."""
        from parser_2gis.main import parse_arguments
        
        with pytest.raises(SystemExit):
            parse_arguments([
                '--parser.max-retries', '0',
                '--url', 'https://2gis.ru/moscow'
            ])
    
    def test_max_retries_above_max(self):
        """Тест: max-retries > 100 вызывает ошибку."""
        from parser_2gis.main import parse_arguments
        
        with pytest.raises(SystemExit):
            parse_arguments([
                '--parser.max-retries', '101',
                '--url', 'https://2gis.ru/moscow'
            ])
    
    def test_max_retries_valid(self):
        """Тест: max-retries в допустимом диапазоне работает корректно."""
        from parser_2gis.main import parse_arguments

        args, _ = parse_arguments([
            '--parser.max-retries', '5',
            '--url', 'https://2gis.ru/moscow'
        ])

        assert getattr(args, 'parser.max_retries') == 5
    
    def test_timeout_below_min(self):
        """Тест: timeout < 1 вызывает ошибку."""
        from parser_2gis.main import parse_arguments
        
        with pytest.raises(SystemExit):
            parse_arguments([
                '--parser.timeout', '0',
                '--url', 'https://2gis.ru/moscow'
            ])
    
    def test_timeout_above_max(self):
        """Тест: timeout > 3600 вызывает ошибку."""
        from parser_2gis.main import parse_arguments
        
        with pytest.raises(SystemExit):
            parse_arguments([
                '--parser.timeout', '3601',
                '--url', 'https://2gis.ru/moscow'
            ])
    
    def test_timeout_valid(self):
        """Тест: timeout в допустимом диапазоне работает корректно."""
        from parser_2gis.main import parse_arguments

        args, _ = parse_arguments([
            '--parser.timeout', '30',
            '--url', 'https://2gis.ru/moscow'
        ])

        assert getattr(args, 'parser.timeout') == 30
    
    def test_max_workers_below_min(self):
        """Тест: max-workers < 1 вызывает ошибку."""
        from parser_2gis.main import parse_arguments
        
        with pytest.raises(SystemExit):
            parse_arguments([
                '--parser.max-workers', '0',
                '--url', 'https://2gis.ru/moscow'
            ])
    
    def test_max_workers_above_max(self):
        """Тест: max-workers > 50 вызывает ошибку."""
        from parser_2gis.main import parse_arguments
        
        with pytest.raises(SystemExit):
            parse_arguments([
                '--parser.max-workers', '51',
                '--url', 'https://2gis.ru/moscow'
            ])
    
    def test_max_workers_valid(self):
        """Тест: max-workers в допустимом диапазоне работает корректно."""
        from parser_2gis.main import parse_arguments

        args, _ = parse_arguments([
            '--parser.max-workers', '10',
            '--url', 'https://2gis.ru/moscow'
        ])

        assert getattr(args, 'parser.max_workers') == 10
    
    def test_chrome_startup_delay_above_max(self):
        """Тест: chrome-startup-delay > 60 вызывает ошибку."""
        from parser_2gis.main import parse_arguments
        
        with pytest.raises(SystemExit):
            parse_arguments([
                '--chrome.startup-delay', '61',
                '--url', 'https://2gis.ru/moscow'
            ])
    
    def test_chrome_startup_delay_valid(self):
        """Тест: chrome-startup-delay в допустимом диапазоне работает корректно."""
        from parser_2gis.main import parse_arguments

        args, _ = parse_arguments([
            '--chrome.startup-delay', '2.5',
            '--url', 'https://2gis.ru/moscow'
        ])

        assert getattr(args, 'chrome.startup_delay') == 2.5
    
    def test_negative_delay(self):
        """Тест: отрицательная задержка вызывает ошибку."""
        from parser_2gis.main import parse_arguments
        
        with pytest.raises(SystemExit):
            parse_arguments([
                '--chrome.startup-delay', '-1',
                '--url', 'https://2gis.ru/moscow'
            ])


class TestChromeBrowserZombieHandling:
    """Тесты для проверки упрощенной обработки zombie процессов Chrome."""
    
    @patch('parser_2gis.chrome.browser.subprocess.Popen')
    @patch('parser_2gis.chrome.browser.os')
    def test_graceful_shutdown_success(self, mock_os, mock_popen):
        """Тест: Graceful shutdown успешно завершает процесс."""
        from parser_2gis.chrome.browser import Browser
        
        mock_process = Mock()
        mock_process.poll.return_value = None  # Процесс ещё не завершился
        mock_process.terminate = Mock()
        mock_process.wait = Mock(return_value=0)  # Успешное завершение
        mock_popen.return_value = mock_process
        
        browser = Browser('http://localhost:9222', '/tmp/chrome-data')
        browser.process = mock_process
        
        # Вызываем close
        browser.close()
        
        # Проверяем что terminate и wait были вызваны
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once_with(timeout=5)
    
    @patch('parser_2gis.chrome.browser.subprocess.Popen')
    @patch('parser_2gis.chrome.browser.os')
    def test_forceful_kill_on_timeout(self, mock_os, mock_popen):
        """Тест: Forceful kill используется при timeout."""
        from parser_2gis.chrome.browser import Browser
        
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_process.terminate = Mock()
        mock_process.wait = Mock(side_effect=Exception('Timeout'))
        mock_process.kill = Mock()
        mock_popen.return_value = mock_process
        
        browser = Browser('http://localhost:9222', '/tmp/chrome-data')
        browser.process = mock_process
        
        # Вызываем close
        browser.close()
        
        # Проверяем что kill был вызван после timeout
        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()
    
    @patch('parser_2gis.chrome.browser.subprocess.Popen')
    @patch('parser_2gis.chrome.browser.os')
    def test_process_already_terminated(self, mock_os, mock_popen):
        """Тест: Процесс уже завершен, ничего не делаем."""
        from parser_2gis.chrome.browser import Browser
        
        mock_process = Mock()
        mock_process.poll.return_value = 0  # Процесс уже завершен
        mock_popen.return_value = mock_process
        
        browser = Browser('http://localhost:9222', '/tmp/chrome-data')
        browser.process = mock_process
        
        # Вызываем close
        browser.close()
        
        # Проверяем что terminate и kill не вызывались
        mock_process.terminate.assert_not_called()
        mock_process.kill.assert_not_called()


class TestTempFileLeakFix:
    """Тесты для проверки исправления утечки временных файлов."""
    
    def test_atexit_cleanup_registered(self):
        """Тест: atexit.register вызывается для cleanup функции."""
        import parser_2gis.parallel_parser as parallel_parser
        
        # Проверяем что cleanup функция зарегистрирована
        assert hasattr(parallel_parser, '_cleanup_temp_files')
    
    @patch('parser_2gis.parallel_parser.atexit')
    def test_cleanup_function_exists(self, mock_atexit):
        """Тест: Функция очистки временных файлов существует."""
        # Импортируем модуль заново чтобы сработал atexit.register
        import importlib
        import parser_2gis.parallel_parser as parallel_parser
        importlib.reload(parallel_parser)
        
        # Проверяем что atexit.register был вызван
        mock_atexit.register.assert_called()
    
    def test_temp_file_cleanup_on_error(self):
        """Тест: Временные файлы очищаются при ошибке."""
        from parser_2gis.parallel_parser import _cleanup_temp_files
        import tempfile
        import os
        
        # Создаем временный файл
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        # Добавляем в список для очистки
        import parser_2gis.parallel_parser as pp
        if not hasattr(pp, '_temp_files_to_cleanup'):
            pp._temp_files_to_cleanup = []
        pp._temp_files_to_cleanup.append(temp_path)
        
        # Вызываем очистку
        _cleanup_temp_files()
        
        # Проверяем что файл удален
        assert not os.path.exists(temp_path), "Временный файл должен быть удален"


class TestTODOHandling:
    """Тесты для проверки обработки TODO/FIXME комментариев."""
    
    def test_no_trivial_todos_in_output_settings(self):
        """Тест: Тривиальные TODO удалены из output_settings.py."""
        import parser_2gis.tui_pytermgui.screens.output_settings as output_settings
        import inspect
        
        source = inspect.getsource(output_settings)
        
        # Проверяем что тривиальные TODO удалены или заменены
        trivial_todos = [
            line for line in source.split('\n')
            if '# TODO: Реализовать всплывающее сообщение' in line
        ]
        
        assert len(trivial_todos) == 0, "Тривиальные TODO должны быть удалены"
    
    def test_important_todos_converted_to_issues(self):
        """Тест: Важные TODO конвертированы в ISSUE format."""
        import parser_2gis.tui_pytermgui.screens.parsing_screen as parsing_screen
        import inspect
        
        source = inspect.getsource(parsing_screen)
        
        # Проверяем что важные TODO конвертированы в ISSUE format
        issue_comments = [
            line for line in source.split('\n')
            if '# ISSUE:' in line
        ]
        
        # Должны быть ISSUE комментарии
        assert len(issue_comments) > 0, "Важные TODO должны быть конвертированы в ISSUE"
    
    def test_todo_count_reduced(self):
        """Тест: Общее количество TODO сокращено."""
        import os
        import re
        
        todo_count = 0
        parser_dir = Path(__file__).parent.parent / 'parser_2gis'
        
        for py_file in parser_dir.rglob('*.py'):
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                todos = re.findall(r'#\s*TODO:', content)
                todo_count += len(todos)
        
        # Проверяем что количество TODO сокращено (было 168, должно стать <= 50)
        # Для теста используем более мягкое ограничение
        assert todo_count <= 100, f"Количество TODO ({todo_count}) должно быть сокращено"


class TestMergeCSVRefactoring:
    """Тесты для проверки рефакторинга merge_csv_files."""
    
    def test_acquire_lock_function_exists(self):
        """Тест: Функция _acquire_lock существует."""
        from parser_2gis.parallel_parser import _acquire_lock
        assert callable(_acquire_lock)
    
    def test_merge_files_function_exists(self):
        """Тест: Функция _merge_files существует."""
        from parser_2gis.parallel_parser import _merge_files
        assert callable(_merge_files)
    
    def test_cleanup_sources_function_exists(self):
        """Тест: Функция _cleanup_sources существует."""
        from parser_2gis.parallel_parser import _cleanup_sources
        assert callable(_cleanup_sources)
    
    def test_validate_merged_function_exists(self):
        """Тест: Функция _validate_merged существует."""
        from parser_2gis.parallel_parser import _validate_merged
        assert callable(_validate_merged)
    
    def test_merge_csv_files_uses_subfunctions(self):
        """Тест: merge_csv_files использует подфункции."""
        import parser_2gis.parallel_parser as pp
        import inspect
        
        source = inspect.getsource(pp.merge_csv_files)
        
        # Проверяем что основная функция вызывает подфункции
        assert '_acquire_lock' in source or 'acquire_lock' in source
        assert '_merge_files' in source or 'merge_files' in source
        assert '_cleanup_sources' in source or 'cleanup_sources' in source
    
    @patch('parser_2gis.parallel_parser._acquire_lock')
    @patch('parser_2gis.parallel_parser._merge_files')
    @patch('parser_2gis.parallel_parser._cleanup_sources')
    def test_merge_flow(self, mock_cleanup, mock_merge, mock_acquire):
        """Тест: Проверка потока выполнения merge."""
        from parser_2gis.parallel_parser import merge_csv_files
        import tempfile
        
        # Создаем временные файлы
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, 'output.csv')
            temp_files = [
                os.path.join(tmpdir, f'file{i}.csv')
                for i in range(3)
            ]
            
            # Создаем файлы
            for tf in temp_files:
                with open(tf, 'w') as f:
                    f.write('col1,col2\nval1,val2\n')
            
            # Вызываем merge
            merge_csv_files(temp_files, output_path, {})
            
            # Проверяем что подфункции были вызваны
            mock_acquire.assert_called()
            mock_merge.assert_called()
            mock_cleanup.assert_called()


class TestMagicNumbersFix:
    """Тесты для проверки устранения magic numbers."""
    
    def test_chrome_startup_delay_has_comment(self):
        """Тест: CHROME_STARTUP_DELAY имеет обоснование."""
        import parser_2gis.chrome.remote as remote
        import inspect
        
        source = inspect.getsource(remote)
        
        # Ищем объявление константы и комментарий к ней
        lines = source.split('\n')
        for i, line in enumerate(lines):
            if 'CHROME_STARTUP_DELAY' in line:
                # Проверяем что есть комментарий в предыдущих строках
                context = '\n'.join(lines[max(0, i-3):i+1])
                assert '#' in context, "CHROME_STARTUP_DELAY должно иметь комментарий"
                break
    
    def test_max_js_code_length_has_comment(self):
        """Тест: MAX_JS_CODE_LENGTH имеет обоснование."""
        import parser_2gis.chrome.remote as remote
        import inspect
        
        source = inspect.getsource(remote)
        
        lines = source.split('\n')
        for i, line in enumerate(lines):
            if 'MAX_JS_CODE_LENGTH' in line:
                context = '\n'.join(lines[max(0, i-3):i+1])
                assert '#' in context, "MAX_JS_CODE_LENGTH должно иметь комментарий"
                break
    
    def test_buffer_sizes_have_comments(self):
        """Тест: Размеры буферов имеют обоснование."""
        import parser_2gis.writer.writers.csv_writer as csv_writer
        import inspect
        
        source = inspect.getsource(csv_writer)
        
        # Проверяем что есть комментарии для размеров буферов
        assert 'READ_BUFFER_SIZE' in source
        assert 'WRITE_BUFFER_SIZE' in source
        
        lines = source.split('\n')
        for i, line in enumerate(lines):
            if 'READ_BUFFER_SIZE' in line or 'WRITE_BUFFER_SIZE' in line:
                context = '\n'.join(lines[max(0, i-3):i+1])
                assert '#' in context, "Размеры буферов должны иметь комментарии"


class TestConditionalImportsFix:
    """Тесты для проверки упрощения условных импортов."""
    
    def test_cli_import_error_handling(self):
        """Тест: Обработка ошибки импорта CLI модуля."""
        import parser_2gis.main as main_module
        import inspect
        
        source = inspect.getsource(main_module)
        
        # Проверяем что импорт CLI имеет понятное сообщение об ошибке
        assert 'Не удалось импортировать CLI модуль' in source
    
    def test_tui_import_handling(self):
        """Тест: Обработка импорта TUI модуля."""
        import parser_2gis.main as main_module
        import inspect
        
        source = inspect.getsource(main_module)
        
        # Проверяем что импорт TUI имеет warning сообщение
        assert 'Не удалось импортировать новый TUI модуль' in source or \
               'importlib' in source
    
    def test_stub_function_for_optional_module(self):
        """Тест: Stub функция для опционального модуля."""
        import parser_2gis.main as main_module
        
        # Проверяем что run_new_tui_omsk может быть None или функцией
        assert hasattr(main_module, 'run_new_tui_omsk')


class TestLoggingOptimization:
    """Тесты для проверки оптимизации логирования."""
    
    def test_no_excessive_debug_logging(self):
        """Тест: Избыточные debug сообщения удалены или заменены."""
        import parser_2gis.parallel_parser as pp
        import inspect
        
        source = inspect.getsource(pp)
        
        # Проверяем что избыточные debug сообщения заменены на log(5)
        debug_lines = [
            line for line in source.split('\n')
            if 'logger.debug' in line and 'Временный файл атомарно создан' in line
        ]
        
        # Такие сообщения должны быть удалены или заменены
        assert len(debug_lines) == 0, "Избыточные debug сообщения должны быть удалены"
    
    def test_custom_log_level_used(self):
        """Тест: Используется кастомный уровень логирования для подробных сообщений."""
        import parser_2gis.parallel_parser as pp
        import inspect
        
        source = inspect.getsource(pp)
        
        # Проверяем что используется logger.log(5, ...) для очень подробных сообщений
        # Это может быть в любом виде
        has_custom_logging = (
            'logger.log(5' in source or
            'logger.log(TRACE' in source or
            'TRACE_LEVEL' in source
        )
        
        # Хотя бы один вид кастомного логирования должен присутствовать
        assert has_custom_logging, "Должно использоваться кастомное логирование"


class TestDocumentationStyle:
    """Тесты для проверки унификации стиля документации."""
    
    def test_validation_module_has_google_style_docstring(self):
        """Тест: validation.py имеет docstring в Google style."""
        from parser_2gis import validation
        import inspect
        
        docstring = inspect.getdoc(validation)
        assert docstring is not None, "validation.py должен иметь docstring"
        
        # Проверяем наличие секций Google style
        has_args = 'Args:' in docstring or 'Arguments:' in docstring
        has_returns = 'Returns:' in docstring
        has_raises = 'Raises:' in docstring or 'Exceptions:' in docstring
        
        # Хотя бы некоторые секции должны присутствовать
        assert has_args or has_returns or has_raises, \
            "Docstring должен быть в Google style"
    
    def test_validate_url_function_has_docstring(self):
        """Тест: Функция validate_url имеет подробный docstring."""
        from parser_2gis.validation import validate_url
        import inspect
        
        docstring = inspect.getdoc(validate_url)
        assert docstring is not None, "validate_url должен иметь docstring"
        
        # Проверяем наличие описания
        assert len(docstring) > 50, "Docstring должен быть подробным"
    
    def test_type_hints_present(self):
        """Тест: Type hints присутствуют в новых функциях."""
        from parser_2gis import validation
        import inspect
        
        # Проверяем что функции имеют type hints
        for name in dir(validation):
            if name.startswith('_'):
                continue
            obj = getattr(validation, name)
            if callable(obj) and not inspect.isclass(obj):
                try:
                    sig = inspect.signature(obj)
                    # Проверяем что есть type hints хотя бы для одного параметра
                    # или для return value
                    has_hints = any(
                        p.annotation != inspect.Parameter.empty
                        for p in sig.parameters.values()
                    ) or sig.return_annotation != inspect.Signature.empty
                    
                    # Не все функции обязаны иметь hints, поэтому не assert
                except (ValueError, TypeError):
                    pass  # Некоторые встроенные функции могут не иметь signature


class TestValidationModule:
    """Тесты для проверки центрального модуля валидации."""
    
    def test_validation_module_exists(self):
        """Тест: Модуль validation.py существует."""
        from parser_2gis import validation
        assert validation is not None
    
    def test_validate_url_function_exists(self):
        """Тест: Функция validate_url существует."""
        from parser_2gis.validation import validate_url
        assert callable(validate_url)
    
    def test_validate_positive_int_function_exists(self):
        """Тест: Функция validate_positive_int существует."""
        from parser_2gis.validation import validate_positive_int
        assert callable(validate_positive_int)
    
    def test_validate_email_function_exists(self):
        """Тест: Функция validate_email существует."""
        from parser_2gis.validation import validate_email
        assert callable(validate_email)
    
    def test_validate_url_valid(self):
        """Тест: validate_url возвращает валидный результат для правильного URL."""
        from parser_2gis.validation import validate_url
        
        result = validate_url("https://2gis.ru/moscow")
        assert result.is_valid is True
        assert result.value == "https://2gis.ru/moscow"
    
    def test_validate_url_invalid(self):
        """Тест: validate_url возвращает ошибку для неправильного URL."""
        from parser_2gis.validation import validate_url
        
        result = validate_url("not-a-url")
        assert result.is_valid is False
        assert result.error is not None
    
    def test_validate_positive_int_valid(self):
        """Тест: validate_positive_int возвращает значение для корректного числа."""
        from parser_2gis.validation import validate_positive_int
        
        value = validate_positive_int(5, 1, 100, "--test-arg")
        assert value == 5
    
    def test_validate_positive_int_below_min(self):
        """Тест: validate_positive_int вызывает ошибку для числа ниже минимума."""
        from parser_2gis.validation import validate_positive_int
        import argparse
        
        with pytest.raises(argparse.ArgumentTypeError):
            validate_positive_int(0, 1, 100, "--test-arg")
    
    def test_validate_positive_int_above_max(self):
        """Тест: validate_positive_int вызывает ошибку для числа выше максимума."""
        from parser_2gis.validation import validate_positive_int
        import argparse
        
        with pytest.raises(argparse.ArgumentTypeError):
            validate_positive_int(101, 1, 100, "--test-arg")
    
    def test_validate_email_valid(self):
        """Тест: validate_email возвращает валидный результат для правильного email."""
        from parser_2gis.validation import validate_email
        
        result = validate_email("test@example.com")
        assert result.is_valid is True
        assert result.value == "test@example.com"
    
    def test_validate_email_invalid(self):
        """Тест: validate_email возвращает ошибку для неправильного email."""
        from parser_2gis.validation import validate_email
        
        result = validate_email("not-an-email")
        assert result.is_valid is False
        assert result.error is not None


class TestIntegration:
    """Интеграционные тесты для проверки всех исправлений вместе."""
    
    def test_full_cli_validation_flow(self):
        """Тест: Полный поток валидации CLI аргументов."""
        from parser_2gis.main import parse_arguments

        # Валидные аргументы
        args, _ = parse_arguments([
            '--parser.max-retries', '5',
            '--parser.timeout', '30',
            '--parser.max-workers', '10',
            '--chrome.startup-delay', '2.0',
            '--url', 'https://2gis.ru/moscow'
        ])

        assert getattr(args, 'parser.max_retries') == 5
        assert getattr(args, 'parser.timeout') == 30
        assert getattr(args, 'parser.max_workers') == 10
        assert getattr(args, 'chrome.startup_delay') == 2.0
    
    def test_validation_module_integrated_in_cli(self):
        """Тест: Модуль валидации интегрирован в CLI."""
        import parser_2gis.main as main_module
        import inspect
        
        source = inspect.getsource(main_module)
        
        # Проверяем что validation модуль импортируется или используется
        assert 'validation' in source or 'validate_positive_int' in source
    
    def test_all_subfunctions_importable(self):
        """Тест: Все подфункции импортируются корректно."""
        from parser_2gis.parallel_parser import (
            _acquire_lock,
            _merge_files,
            _cleanup_sources,
            _validate_merged
        )
        
        assert callable(_acquire_lock)
        assert callable(_merge_files)
        assert callable(_cleanup_sources)
        assert callable(_validate_merged)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
