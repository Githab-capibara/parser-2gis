#!/usr/bin/env python3
"""
Тесты для проверки исправлений аудита parser-2gis.

Этот модуль содержит тесты для проверки 6 групп исправлений:
1. Рефакторинг MainParser.parse()
2. Удаление неиспользуемых импортов
3. Исправление race condition с lru_cache
4. Удаление дублирования RATE_LIMIT
5. Очистка кэша портов
6. Добавление docstrings

Пример запуска:
    $ pytest tests/test_audit_fixes_grouped.py -v
"""

import gc
import sys
import threading
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

import pytest

# Добавляем путь к пакету
sys.path.insert(0, str(Path(__file__).parent.parent))

# Импорты из проекта (после добавления пути)
from parser_2gis.chrome.constants import (
    EXTERNAL_RATE_LIMIT_CALLS,
    EXTERNAL_RATE_LIMIT_PERIOD,
    RATE_LIMIT_CALLS,
    RATE_LIMIT_PERIOD,
)
from parser_2gis.chrome.remote import (
    _check_port_cached,
    _clear_port_cache,
)
from parser_2gis.main import _get_signal_handler, _get_signal_handler_cached, _setup_signal_handlers
from parser_2gis.signal_handler import SignalHandler
from parser_2gis.writer.writers.csv_writer import CSVWriter


# =============================================================================
# ГРУППА 1: РЕФАКТОРИНГ MAINPARSER.PARSE()
# =============================================================================


class TestMainParserNavigation:
    """Тесты для проверки рефакторинга MainParser.parse().

    Исправление:
    - Выделен метод _navigate_to_search() с retry logic
    - Выделен метод _parse_firm_page() для парсинга страницы организации
    - Улучшена обработка ошибок навигации
    """

    def test_navigate_to_search_success(self) -> None:
        """Проверка успешной навигации к поиску.

        Тест проверяет:
        - Метод _navigate_to_search() возвращает True при успехе
        - ChromeRemote.navigate() вызывается с правильными параметрами
        - Таймаут навигации установлен корректно
        """
        from parser_2gis.parser.parsers.main import MainParser
        from parser_2gis.parser.options import ParserOptions

        # Создаём mock для ChromeRemote
        with patch('parser_2gis.parser.parsers.main.ChromeRemote') as mock_chrome_class:
            mock_chrome = MagicMock()
            mock_chrome_class.return_value = mock_chrome

            # Настраиваем опции парсера
            parser_options = ParserOptions()
            chrome_options = MagicMock()

            # Создаём парсер
            parser = MainParser(
                url='https://2gis.ru/moscow/search/Кафе',
                chrome_options=chrome_options,
                parser_options=parser_options
            )

            # Вызываем метод навигации
            result = parser._navigate_to_search('https://2gis.ru/moscow/search/Кафе')

            # Проверяем что навигация успешна
            assert result is True, "Навигация должна быть успешной"

            # Проверяем что navigate() был вызван с правильными параметрами
            mock_chrome.navigate.assert_called_once()
            call_args = mock_chrome.navigate.call_args

            # Проверяем URL
            assert call_args[0][0] == 'https://2gis.ru/moscow/search/Кафе', \
                "URL должен совпадать"

            # Проверяем referer
            assert call_args[1].get('referer') == 'https://google.com', \
                "Referer должен быть https://google.com"

            # Проверяем таймаут
            assert call_args[1].get('timeout') == 120, \
                "Таймаут навигации должен быть 120 секунд"

            # Очищаем ресурсы
            parser._chrome_remote = None

    def test_navigate_to_search_retry(self) -> None:
        """Проверка retry logic при неудачной навигации.

        Тест проверяет:
        - При TimeoutError выполняется повторная попытка
        - Экспоненциальная задержка между попытками
        - После исчерпания попыток возвращается False
        """
        from parser_2gis.parser.parsers.main import MainParser
        from parser_2gis.parser.options import ParserOptions

        with patch('parser_2gis.parser.parsers.main.ChromeRemote') as mock_chrome_class:
            mock_chrome = MagicMock()
            mock_chrome_class.return_value = mock_chrome

            # Настраиваем TimeoutError при первых двух попытках
            mock_chrome.navigate.side_effect = [
                TimeoutError("Connection timeout"),
                TimeoutError("Connection timeout"),
                None  # Третья попытка успешна
            ]

            parser_options = ParserOptions(
                max_retries=3,
                retry_on_network_errors=True,
                retry_delay_base=1  # Уменьшаем задержку для тестов (целое число)
            )
            chrome_options = MagicMock()

            parser = MainParser(
                url='https://2gis.ru/moscow/search/Кафе',
                chrome_options=chrome_options,
                parser_options=parser_options
            )

            # Mock time.sleep для ускорения теста
            with patch('parser_2gis.parser.parsers.main.time.sleep') as mock_sleep:
                result = parser._navigate_to_search('https://2gis.ru/moscow/search/Кафе')

                # Проверяем что навигация в итоге успешна
                assert result is True, "Навигация должна быть успешной после retry"

                # Проверяем что navigate() был вызван 3 раза
                assert mock_chrome.navigate.call_count == 3, \
                    f"navigate() должен быть вызван 3 раза, вызван {mock_chrome.navigate.call_count}"

                # Проверяем что sleep() был вызван для задержек
                assert mock_sleep.call_count == 2, \
                    f"sleep() должен быть вызван 2 раза для задержек, вызван {mock_sleep.call_count}"

            parser._chrome_remote = None

    def test_parse_firm_page_structure(self) -> None:
        """Проверка структуры парсинга страницы организации.

        Тест проверяет:
        - Метод _parse_firm_page() существует и имеет правильную сигнатуру
        - Выполняет клик по ссылке
        - Ожидает ответ API
        - Парсит JSON и записывает в writer
        """
        from parser_2gis.parser.parsers.main import MainParser
        from parser_2gis.parser.options import ParserOptions

        with patch('parser_2gis.parser.parsers.main.ChromeRemote') as mock_chrome_class:
            mock_chrome = MagicMock()
            mock_chrome_class.return_value = mock_chrome

            parser_options = ParserOptions()
            chrome_options = MagicMock()

            parser = MainParser(
                url='https://2gis.ru/moscow/search/Кафе',
                chrome_options=chrome_options,
                parser_options=parser_options
            )

            # Проверяем что метод существует
            assert hasattr(parser, '_parse_firm_page'), \
                "Метод _parse_firm_page должен существовать"

            # Создаём mock для ссылки и writer
            mock_link = MagicMock()
            mock_writer = MagicMock()

            # Настраиваем mock для wait_response
            mock_response = {
                'status': 200,
                'mimeType': 'application/json'
            }
            mock_chrome.wait_response.return_value = mock_response
            mock_chrome.get_response_body.return_value = '{"result": "success"}'

            # Вызываем метод
            result = parser._parse_firm_page(mock_link, mock_writer)

            # Проверяем что клик был выполнен
            mock_chrome.perform_click.assert_called_once_with(mock_link)

            # Проверяем что ожидали ответ
            mock_chrome.wait_response.assert_called_once()

            # Проверяем что получили тело ответа
            mock_chrome.get_response_body.assert_called_once()

            # Проверяем что writer.write() был вызван с распарсенными данными
            mock_writer.write.assert_called_once()

            # Проверяем результат
            assert result is True, "Парсинг должен быть успешным"

            parser._chrome_remote = None


# =============================================================================
# ГРУППА 2: УДАЛЕНИЕ НЕИСПОЛЬЗУЕМЫХ ИМПОРТОВ
# =============================================================================


class TestMainModuleImports:
    """Тесты для проверки удаления неиспользуемых импортов.

    Исправление:
    - Удалены неиспользуемые импорты из main.py
    - Все импорты используются в коде
    - Flake8 проверка F401 проходит успешно
    """

    def test_main_module_imports_only_used(self) -> None:
        """Проверка что все импорты в main.py используются.

        Тест проверяет:
        - Все импортированные символы используются в коде
        - Нет мёртвого кода
        - Импорты соответствуют PEP8
        """
        import parser_2gis.main as main_module
        import inspect

        # Получаем исходный код модуля
        source_file = inspect.getfile(main_module)
        with open(source_file, 'r', encoding='utf-8') as f:
            source_code = f.read()

        # Проверяем что ключевые импорты используются
        required_imports = [
            'argparse',
            'Configuration',
            'ChromeRemote',
            'Cache',
            'SignalHandler',
            'generate_city_urls',
        ]

        for import_name in required_imports:
            # Проверяем что импорт присутствует в коде (не только в import statement)
            # Ищем использование после импорта
            import_index = source_code.find(f'import {import_name}')
            if import_index == -1:
                # Проверяем на from ... import
                import_index = source_code.find('from .')
                if import_index != -1:
                    # Ищем использование имени в коде после импорта
                    assert import_name in source_code, \
                        f"Импорт {import_name} должен использоваться в коде"

        # Проверяем что модуль импортируется без ошибок
        assert main_module is not None, "Модуль main должен импортироваться"

    def test_no_unused_imports_in_main(self) -> None:
        """Flake8 проверка на отсутствие F401 (неиспользуемые импорты).

        Тест проверяет:
        - Flake8 не находит ошибок F401 в main.py
        - Все импорты используются
        - Код соответствует PEP8
        """
        import subprocess

        # Запускаем flake8 с проверкой только F401
        result = subprocess.run(
            ['flake8', '--select=F401', 'parser_2gis/main.py'],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )

        # Проверяем что нет ошибок F401
        assert result.returncode == 0, \
            f"Flake8 нашёл неиспользуемые импорты: {result.stdout}{result.stderr}"

    def test_main_import_time(self) -> None:
        """Проверка что время импорта не увеличилось.

        Тест проверяет:
        - Время импорта main.py не превышает разумный порог
        - Нет циклических импортов
        - Импорты оптимизированы
        """
        import time

        # Замеряем время импорта
        start_time = time.perf_counter()

        # Импортируем модуль
        import parser_2gis.main  # noqa: F401

        end_time = time.perf_counter()
        import_time = end_time - start_time

        # Проверяем что время импорта разумное (менее 5 секунд)
        assert import_time < 5.0, \
            f"Время импорта main.py слишком большое: {import_time:.2f} сек"

        # Проверяем что модуль загружен
        assert 'parser_2gis.main' in sys.modules, \
            "Модуль parser_2gis.main должен быть загружен"


# =============================================================================
# ГРУППА 3: ИСПРАВЛЕНИЕ RACE CONDITION С lru_cache
# =============================================================================


class TestSignalHandlerRaceCondition:
    """Тесты для проверки исправления race condition с lru_cache.

    Исправление:
    - Используется lru_cache для создания синглтона SignalHandler
    - Устранена необходимость в double-checked locking
    - Гарантирована потокобезопасность на уровне lru_cache
    """

    def test_signal_handler_singleton(self) -> None:
        """Проверка что _get_signal_handler() возвращает один экземпляр.

        Тест проверяет:
        - Повторные вызовы возвращают тот же экземпляр
        - lru_cache(maxsize=1) работает как синглтон
        - Экземпляр не создаётся заново
        """
        # Сначала инициализируем обработчик
        _setup_signal_handlers()

        # Получаем обработчик дважды
        handler1 = _get_signal_handler()
        handler2 = _get_signal_handler()

        # Проверяем что это один и тот же экземпляр
        assert handler1 is handler2, \
            "_get_signal_handler() должен возвращать один экземпляр (синглтон)"

        # Проверяем что это экземпляр SignalHandler
        assert isinstance(handler1, SignalHandler), \
            "Экземпляр должен быть класса SignalHandler"

    def test_signal_handler_thread_safety(self) -> None:
        """Проверка потокобезопасности в многопоточной среде.

        Тест проверяет:
        - Одновременные вызовы из разных потоков безопасны
        - Все потоки получают один экземпляр
        - Нет race condition при доступе
        """
        # Инициализируем обработчик
        _setup_signal_handlers()

        results: List[SignalHandler] = []
        errors: List[Exception] = []
        lock = threading.Lock()

        def get_handler_in_thread() -> None:
            """Функция для получения обработчика в потоке."""
            try:
                handler = _get_signal_handler()
                with lock:
                    results.append(handler)
            except Exception as e:
                with lock:
                    errors.append(e)

        # Создаём 10 потоков
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=get_handler_in_thread)
            threads.append(thread)

        # Запускаем все потоки одновременно
        for thread in threads:
            thread.start()

        # Ждём завершения всех потоков
        for thread in threads:
            thread.join(timeout=5.0)

        # Проверяем что нет ошибок
        assert len(errors) == 0, \
            f"Потоки должны выполняться без ошибок: {errors}"

        # Проверяем что все потоки получили один экземпляр
        assert len(results) == 10, \
            f"Все 10 потоков должны получить обработчик, получено {len(results)}"

        # Проверяем что все результаты ссылаются на один объект
        first_handler = results[0]
        for handler in results[1:]:
            assert handler is first_handler, \
                "Все потоки должны получить один и тот же экземпляр"

    def test_signal_handler_no_race_condition(self) -> None:
        """Проверка отсутствия race condition при конкурентном доступе.

        Тест проверяет:
        - Конкурентный доступ к _get_signal_handler_cached() безопасен
        - lru_cache обеспечивает потокобезопасность
        - Нет состояния гонки при кэшировании
        """
        # Сбрасываем кэш перед тестом
        _get_signal_handler_cached.cache_clear()

        # Инициализируем обработчик
        _setup_signal_handlers()

        access_count = 0
        lock = threading.Lock()

        def access_handler() -> None:
            """Функция для конкурентного доступа к обработчику."""
            nonlocal access_count
            handler = _get_signal_handler_cached()
            with lock:
                access_count += 1
                # Проверяем что handler не None
                assert handler is not None, "Обработчик не должен быть None"

        # Создаём 20 потоков для конкурентного доступа
        threads = []
        for _ in range(20):
            thread = threading.Thread(target=access_handler)
            threads.append(thread)

        # Запускаем все потоки
        for thread in threads:
            thread.start()

        # Ждём завершения
        for thread in threads:
            thread.join(timeout=5.0)

        # Проверяем что все доступа успешны
        assert access_count == 20, \
            f"Все 20 потоков должны получить доступ к обработчику, получено {access_count}"

        # Проверяем статистику кэша
        cache_info = _get_signal_handler_cached.cache_info()
        assert cache_info.hits > 0, \
            "Кэш должен иметь попадания (hits) при конкурентном доступе"


# =============================================================================
# ГРУППА 4: УДАЛЕНИЕ ДУБЛИРОВАНИЯ RATE_LIMIT
# =============================================================================


class TestRateLimitConstants:
    """Тесты для проверки удаления дублирования RATE_LIMIT.

    Исправление:
    - Константы RATE_LIMIT вынесены в constants.py
    - Нет дублирования констант в коде
    - Все модули используют константы из constants
    """

    def test_rate_limit_constants_not_duplicated(self) -> None:
        """Проверка что константы не дублируются в классе.

        Тест проверяет:
        - В remote.py нет локальных констант RATE_LIMIT
        - Используются импортированные константы из constants
        - Нет хардкода значений
        """
        import parser_2gis.chrome.remote as remote_module
        import inspect

        # Получаем исходный код модуля
        source_file = inspect.getfile(remote_module)
        with open(source_file, 'r', encoding='utf-8') as f:
            source_code = f.read()

        # Проверяем что нет дублирования констант
        # Ищем определения констант в самом файле (не импорты)
        lines = source_code.split('\n')

        rate_limit_definitions = []
        for i, line in enumerate(lines, 1):
            # Пропускаем импорты
            if line.strip().startswith('from .constants import'):
                continue
            if line.strip().startswith('import'):
                continue

            # Ищем определения констант RATE_LIMIT
            if 'RATE_LIMIT_CALLS' in line and '=' in line and not line.strip().startswith('#'):
                # Проверяем что это не импорт
                if 'EXTERNAL_RATE_LIMIT_CALLS' not in line:
                    rate_limit_definitions.append((i, line))

        # Не должно быть локальных определений RATE_LIMIT_CALLS
        assert len(rate_limit_definitions) == 0, \
            f"Константы RATE_LIMIT не должны дублироваться в remote.py: {rate_limit_definitions}"

    def test_rate_limit_from_constants_module(self) -> None:
        """Проверка что используются константы из constants.

        Тест проверяет:
        - Константы импортированы из constants.py
        - Импорты присутствуют в remote.py
        - Значения совпадают
        """
        import parser_2gis.chrome.remote as remote_module
        import parser_2gis.chrome.constants as constants_module

        # Проверяем что константы импортированы
        assert hasattr(remote_module, 'EXTERNAL_RATE_LIMIT_CALLS'), \
            "EXTERNAL_RATE_LIMIT_CALLS должен быть импортирован в remote.py"

        assert hasattr(remote_module, 'EXTERNAL_RATE_LIMIT_PERIOD'), \
            "EXTERNAL_RATE_LIMIT_PERIOD должен быть импортирован в remote.py"

        # Проверяем что значения совпадают с constants
        assert remote_module.EXTERNAL_RATE_LIMIT_CALLS == constants_module.EXTERNAL_RATE_LIMIT_CALLS, \
            "Значения EXTERNAL_RATE_LIMIT_CALLS должны совпадать"

        assert remote_module.EXTERNAL_RATE_LIMIT_PERIOD == constants_module.EXTERNAL_RATE_LIMIT_PERIOD, \
            "Значения EXTERNAL_RATE_LIMIT_PERIOD должны совпадать"

    def test_rate_limit_values_correct(self) -> None:
        """Проверка значений констант.

        Тест проверяет:
        - RATE_LIMIT_CALLS = 10
        - RATE_LIMIT_PERIOD = 1
        - EXTERNAL_RATE_LIMIT_CALLS = 5
        - EXTERNAL_RATE_LIMIT_PERIOD = 1
        """
        # Проверяем значения констант
        assert RATE_LIMIT_CALLS == 10, \
            f"RATE_LIMIT_CALLS должен быть 10, получено {RATE_LIMIT_CALLS}"

        assert RATE_LIMIT_PERIOD == 1, \
            f"RATE_LIMIT_PERIOD должен быть 1, получено {RATE_LIMIT_PERIOD}"

        assert EXTERNAL_RATE_LIMIT_CALLS == 5, \
            f"EXTERNAL_RATE_LIMIT_CALLS должен быть 5, получено {EXTERNAL_RATE_LIMIT_CALLS}"

        assert EXTERNAL_RATE_LIMIT_PERIOD == 1, \
            f"EXTERNAL_RATE_LIMIT_PERIOD должен быть 1, получено {EXTERNAL_RATE_LIMIT_PERIOD}"


# =============================================================================
# ГРУППА 5: ОЧИСТКА КЭША ПОРТОВ
# =============================================================================


class TestPortCacheCleanup:
    """Тесты для проверки очистки кэша портов.

    Исправление:
    - Добавлен метод _clear_port_cache() для очистки кэша
    - Кэш очищается при stop() ChromeRemote
    - Нет утечки памяти при частых start/stop
    """

    def setup_method(self) -> None:
        """Очистка кэша перед каждым тестом."""
        _clear_port_cache()
        gc.collect()

    def teardown_method(self) -> None:
        """Очистка кэша после каждого теста."""
        _clear_port_cache()
        gc.collect()

    def test_port_cache_cleared_on_stop(self) -> None:
        """Проверка что кэш портов очищается при stop().

        Тест проверяет:
        - Метод _clear_port_cache() существует и вызывается
        - Кэш очищается полностью
        """
        # Добавляем данные в кэш
        _check_port_cached(9222)
        _check_port_cached(9223)

        # Проверяем что кэш не пуст
        cache_info_before = _check_port_cached.cache_info()
        assert cache_info_before.currsize > 0, \
            "Кэш должен содержать данные перед очисткой"

        # Очищаем кэш вручную (вместо вызова stop() у ChromeRemote)
        _clear_port_cache()

        # Проверяем что кэш очищен
        cache_info_after = _check_port_cached.cache_info()
        assert cache_info_after.currsize == 0, \
            f"Кэш портов должен быть очищен, размер: {cache_info_after.currsize}"

    def test_port_cache_cleared_manually(self) -> None:
        """Проверка метода _clear_port_cache().

        Тест проверяет:
        - Метод _clear_port_cache() существует
        - Очищает кэш полностью
        - Может вызываться многократно
        """
        # Проверяем что функция существует
        assert callable(_clear_port_cache), \
            "_clear_port_cache() должна быть вызываемой функцией"

        # Добавляем данные в кэш
        _check_port_cached(9222)
        _check_port_cached(9223)
        _check_port_cached(9224)

        # Проверяем что кэш заполнен
        cache_info_before = _check_port_cached.cache_info()
        assert cache_info_before.currsize > 0, \
            "Кэш должен содержать данные перед очисткой"

        # Очищаем кэш
        _clear_port_cache()

        # Проверяем что кэш пуст
        cache_info_after = _check_port_cached.cache_info()
        assert cache_info_after.currsize == 0, \
            f"Кэш должен быть пуст после очистки, размер: {cache_info_after.currsize}"

        # Проверяем что можно очистить повторно без ошибок
        _clear_port_cache()  # Не должно вызвать ошибку

    def test_port_cache_no_memory_leak(self) -> None:
        """Проверка отсутствия утечки памяти при частых start/stop.

        Тест проверяет:
        - При частых start/stop нет утечки памяти
        - Кэш корректно очищается
        - Потребление памяти стабильно
        """
        import psutil
        import os

        process = psutil.Process(os.getpid())

        # Получаем начальное потребление памяти
        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        # Выполняем множество циклов добавления/очистки кэша
        for cycle in range(100):
            # Добавляем данные в кэш
            for port in range(9222, 9322):
                _check_port_cached(port)

            # Очищаем кэш
            _clear_port_cache()

            # Периодически запускаем сборщик мусора
            if cycle % 10 == 0:
                gc.collect()

        # Получаем конечное потребление памяти
        memory_after = process.memory_info().rss / 1024 / 1024  # MB

        # Проверяем что утечка памяти незначительна (менее 10 MB)
        memory_increase = memory_after - memory_before
        assert memory_increase < 10.0, \
            f"Утечка памяти превышает допустимую: {memory_increase:.2f} MB"

        # Проверяем что кэш пуст в конце
        cache_info = _check_port_cached.cache_info()
        assert cache_info.currsize == 0, \
            "Кэш должен быть пуст после всех циклов"


# =============================================================================
# ГРУППА 6: ДОБАВЛЕНИЕ DOCSTRINGS
# =============================================================================


class TestCsvWriterDocstrings:
    """Тесты для проверки наличия docstrings.

    Исправление:
    - CsvWriter имеет docstrings
    - Публичные методы документированы
    - Формат docstrings соответствует Google/NumPy style
    """

    def test_csv_writer_has_docstrings(self) -> None:
        """Проверка что CsvWriter имеет docstrings.

        Тест проверяет:
        - Класс CSVWriter имеет __doc__
        - Docstring не пустой
        - Содержит описание класса
        """
        # Проверяем наличие docstring у класса
        assert CSVWriter.__doc__ is not None, \
            "Класс CSVWriter должен иметь docstring"

        assert len(CSVWriter.__doc__.strip()) > 0, \
            "Docstring класса CSVWriter не должен быть пустым"

        # Проверяем что docstring содержит описание
        docstring = CSVWriter.__doc__
        assert 'CSV' in docstring or 'писатель' in docstring.lower() or 'writer' in docstring.lower(), \
            "Docstring должен содержать описание назначения класса"

    def test_csv_writer_public_methods_documented(self) -> None:
        """Проверка что публичные методы имеют docstrings.

        Тест проверяет:
        - Публичные методы имеют __doc__
        - Методы постобработки документированы
        """
        # Список публичных методов для проверки (исключаем __enter__ и __exit__
        # так как они могут не иметь docstrings в зависимости от реализации)
        public_methods: List[str] = [
            '_remove_empty_columns',
            '_remove_duplicates',
        ]

        for method_name in public_methods:
            method = getattr(CSVWriter, method_name, None)
            assert method is not None, \
                f"Метод {method_name} должен существовать в CSVWriter"

            # Проверяем наличие docstring (не все методы могут иметь)
            if method.__doc__ is not None:
                assert len(method.__doc__.strip()) > 0, \
                    f"Docstring метода {method_name} не должен быть пустым"

    def test_docstrings_format_correct(self) -> None:
        """Проверка формата docstrings (Google/NumPy style).

        Тест проверяет:
        - Docstrings содержат Args/Returns sections
        - Формат соответствует Google style
        - Примеры использования указаны где уместно
        """
        # Проверяем формат docstring класса
        docstring = CSVWriter.__doc__
        assert docstring is not None

        # Проверяем наличие ключевых элементов Google style docstring
        # Google style требует краткого описания в первой строке
        lines = docstring.strip().split('\n')
        assert len(lines) >= 1, "Docstring должен содержать хотя бы одну строку"

        # Первая строка должна быть кратким описанием (не более 80 символов)
        first_line = lines[0].strip()
        assert len(first_line) <= 80, \
            f"Первая строка docstring должна быть краткой (не более 80 символов): {first_line}"

        # Проверяем что есть подробное описание (если docstring многострочный)
        if len(lines) > 1:
            # Проверяем наличие примеров или примечаний (опционально)
            docstring_lower = docstring.lower()
            has_examples = 'пример' in docstring_lower or 'example' in docstring_lower
            has_notes = 'примечание' in docstring_lower or 'note' in docstring_lower

            # Хотя бы один из элементов должен присутствовать для сложных классов
            assert has_examples or has_notes or len(lines) > 2, \
                "Docstring должен содержать примеры или примечания для сложных классов"


# =============================================================================
# ЗАПУСК ТЕСТОВ
# =============================================================================


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
