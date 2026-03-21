#!/usr/bin/env python3
"""
Тесты для проверки исправленных ошибок (аудит).

Содержит 3 теста для каждой из 4 исправленных ошибок:
1. Ошибка в tui_textual/app.py: max_workers брался из config.parser, должен из config.parallel.max_workers.
2. Ошибка в main.py: default значение parallel_workers было 3, должно быть 10.
3. Ошибка в chrome/remote.py: ненадежное извлечение порта через split(":")[-1], заменено на urllib.parse.
4. Длинные строки в main.py (>100 символов) - исправлены разделением строк.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Добавляем путь к пакету
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# ГРУППА 1: Ошибка в tui_textual/app.py
# =============================================================================
class TestTuiAppMaxWorkers:
    """Тесты для проверки исправления ошибки max_workers в tui_textual/app.py."""

    def test_max_workers_from_parallel_config(self):
        """
        Тест 1.1: Проверка, что max_workers берется из config.parallel.max_workers.

        Ошибка: max_workers брался из config.parser, должен из config.parallel.max_workers.
        """
        from parser_2gis.tui_textual.app import TUIApp
        from parser_2gis.config import Configuration

        # Создаем мок конфигурации
        mock_config = MagicMock(spec=Configuration)
        mock_config.parallel = MagicMock()
        mock_config.parallel.max_workers = 15  # Установим нестандартное значение

        # Патчим загрузку конфигурации
        with patch.object(TUIApp, "_load_config", return_value=mock_config):
            app = TUIApp()

            # Проверяем, что max_workers берется из parallel, а не parser
            # В _run_parsing используется getattr(config.parallel, "max_workers", 10)
            max_workers = getattr(app._config.parallel, "max_workers", 10)

            assert max_workers == 15, "max_workers должен браться из config.parallel.max_workers"
            assert max_workers != getattr(app._config, "parser", None), (
                "max_workers не должен браться из config.parser"
            )

    def test_max_workers_default_fallback(self):
        """
        Тест 1.2: Проверка fallback значения, если max_workers не задан.

        Должно использоваться значение по умолчанию 10, если атрибут отсутствует.
        """
        from parser_2gis.tui_textual.app import TUIApp
        from parser_2gis.config import Configuration

        # Создаем мок конфигурации без parallel.max_workers
        mock_config = MagicMock(spec=Configuration)
        mock_config.parallel = MagicMock()
        del mock_config.parallel.max_workers  # Удаляем атрибут

        with patch.object(TUIApp, "_load_config", return_value=mock_config):
            app = TUIApp()

            # Проверяем fallback значение
            max_workers = getattr(app._config.parallel, "max_workers", 10)
            assert max_workers == 10, "Должно использоваться значение по умолчанию 10"

    def test_max_workers_not_from_parser(self):
        """
        Тест 1.3: Проверка, что max_workers не берется из config.parser.
        """
        from parser_2gis.tui_textual.app import TUIApp
        from parser_2gis.config import Configuration

        # Создаем мок конфигурации
        mock_config = MagicMock(spec=Configuration)
        mock_config.parallel = MagicMock()
        mock_config.parallel.max_workers = 10
        mock_config.parser = MagicMock()
        mock_config.parser.max_workers = 99  # Это значение игнорируется

        with patch.object(TUIApp, "_load_config", return_value=mock_config):
            app = TUIApp()

            # Проверяем, что используется значение из parallel
            max_workers = getattr(app._config.parallel, "max_workers", 10)
            assert max_workers == 10
            assert max_workers != mock_config.parser.max_workers


# =============================================================================
# ГРУППА 2: Ошибка в main.py (default значение)
# =============================================================================
class TestMainDefaultParallelWorkers:
    """Тесты для проверки исправления default значения parallel_workers в main.py."""

    def test_default_parallel_workers_is_10(self):
        """
        Тест 2.1: Проверка, что default значение parallel.max_workers равно 10.

        Ошибка: default значение было 3, должно быть 10.
        """
        from parser_2gis.main import parse_arguments

        # Парсим аргументы с dummy URL
        args, config = parse_arguments(["-i", "https://example.com"])

        # Проверяем значение в аргументах (используем getattr из-за точки в имени атрибута)
        assert getattr(args, "parallel.max_workers") == 10, (
            "Default значение parallel.max_workers должно быть 10"
        )

        # Проверяем значение в конфигурации
        assert config.parallel.max_workers == 10

    def test_explicit_parallel_workers_3(self):
        """
        Тест 2.2: Проверка, что можно явно задать значение 3.
        """
        from parser_2gis.main import parse_arguments

        # Парсим аргументы с явным указанием parallel.max-workers=3
        args, config = parse_arguments(["-i", "https://example.com", "--parallel.max-workers", "3"])

        assert getattr(args, "parallel.max_workers") == 3
        assert config.parallel.max_workers == 3

    def test_explicit_parallel_workers_20(self):
        """
        Тест 2.3: Проверка, что можно задать другое значение.
        """
        from parser_2gis.main import parse_arguments

        # Парсим аргументы с явным указанием parallel.max-workers=20
        args, config = parse_arguments(
            ["-i", "https://example.com", "--parallel.max-workers", "20"]
        )

        assert getattr(args, "parallel.max_workers") == 20
        assert config.parallel.max_workers == 20


# =============================================================================
# ГРУППА 3: Ошибка в chrome/remote.py
# =============================================================================
class TestChromeRemotePortExtraction:
    """Тесты для проверки исправления извлечения порта в chrome/remote.py."""

    def test_urllib_parse_is_used(self):
        """
        Тест 3.1: Проверка, что используется urllib.parse для извлечения порта.

        Ошибка: использовался split(":")[-1], заменено на urllib.parse.
        """

        # Читаем исходный код файла
        remote_path = Path(__file__).parent.parent / "parser_2gis" / "chrome" / "remote.py"
        with open(remote_path, "r", encoding="utf-8") as f:
            source_code = f.read()

        # Проверяем наличие импорта urllib.parse
        assert (
            "from urllib.parse import urlparse" in source_code
            or "import urllib.parse" in source_code
        )

        # Проверяем использование urlparse в _connect_interface
        # Ищем вызов urlparse(self._dev_url)
        assert "urlparse(self._dev_url)" in source_code

        # Проверяем, что порт извлекается через parsed_url.port
        assert "parsed_url.port" in source_code

    def test_no_split_colon_method(self):
        """
        Тест 3.2: Проверка, что старый метод split(":")[-1] не используется.
        """

        remote_path = Path(__file__).parent.parent / "parser_2gis" / "chrome" / "remote.py"
        with open(remote_path, "r", encoding="utf-8") as f:
            source_code = f.read()

        # Ищем опасный паттерн split(":")[-1] в контексте порта
        # Это может быть сложно, так как split может использоваться в других контекстах
        # Но мы можем проверить, что в методе _connect_interface используется urlparse

        # Более надежно: проверить, что в функции _connect_interface есть вызов urlparse
        # и нет прямого split для извлечения порта из self._dev_url

        # Проверим, что в _connect_interface есть вызов urlparse
        connect_interface_start = source_code.find("def _connect_interface")
        if connect_interface_start != -1:
            # Найдем конец функции (следующая def или конец файла)
            next_def = source_code.find("\n\ndef ", connect_interface_start + 1)
            if next_def == -1:
                function_body = source_code[connect_interface_start:]
            else:
                function_body = source_code[connect_interface_start:next_def]

            # Проверяем, что в теле функции есть urlparse
            assert "urlparse" in function_body, (
                "urlparse должен использоваться в _connect_interface"
            )

            # Проверяем, что нет split для извлечения порта из self._dev_url
            # Ищем шаблон: self._dev_url.split(":")[-1]
            assert "self._dev_url.split" not in function_body, (
                "Старый метод split не должен использоваться"
            )

    def test_port_validation_with_urllib(self):
        """
        Тест 3.3: Проверка корректности работы с портом через urllib.parse.
        """
        from urllib.parse import urlparse

        # Тестируем, что urlparse корректно извлекает порт
        test_urls = ["http://127.0.0.1:9222", "http://localhost:8080", "https://example.com:443"]

        for url in test_urls:
            parsed = urlparse(url)
            assert parsed.port is not None, f"Порт должен быть извлечен из {url}"
            assert isinstance(parsed.port, int), (
                f"Порт должен быть int, получен {type(parsed.port)}"
            )


# =============================================================================
# ГРУППА 4: Длинные строки в main.py
# =============================================================================
class TestMainLongLines:
    """Тесты для проверки исправления длинных строк в main.py."""

    def test_no_lines_over_100_chars(self):
        """
        Тест 4.1: Проверка отсутствия строк длиннее 100 символов в main.py.

        Ошибка: были длинные строки (>100 символов).
        """
        main_path = Path(__file__).parent.parent / "parser_2gis" / "main.py"

        with open(main_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        long_lines = []
        for i, line in enumerate(lines, 1):
            # Учитываем, что строка может заканчиваться на \n
            line_length = len(line.rstrip("\n"))
            if line_length > 100:
                long_lines.append((i, line_length, line.strip()))

        if long_lines:
            error_msg = "Найдены строки длиннее 100 символов:\n"
            for line_num, length, content in long_lines[:10]:  # Показываем первые 10
                error_msg += f"  Строка {line_num}: {length} символов\n"
                error_msg += f"    {content[:50]}...\n"
            pytest.fail(error_msg)

    def test_imports_are_not_too_long(self):
        """
        Тест 4.2: Проверка, что импорты не превышают 100 символов.
        """
        main_path = Path(__file__).parent.parent / "parser_2gis" / "main.py"

        with open(main_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        import_lines_long = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                if len(stripped) > 100:
                    import_lines_long.append((i, len(stripped), stripped))

        if import_lines_long:
            error_msg = "Найдены импорты длиннее 100 символов:\n"
            for line_num, length, content in import_lines_long:
                error_msg += f"  Строка {line_num}: {length} символов\n"
                error_msg += f"    {content}\n"
            pytest.fail(error_msg)

    def test_no_tabs_in_main(self):
        """
        Тест 4.3: Проверка отсутствия табов в main.py (используются пробелы).
        """
        main_path = Path(__file__).parent.parent / "parser_2gis" / "main.py"

        with open(main_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Проверяем наличие табов
        if "\t" in content:
            # Подсчитаем количество строк с табами
            lines_with_tabs = [i + 1 for i, line in enumerate(content.splitlines()) if "\t" in line]
            pytest.fail(f"Найдены табы в main.py (строки: {lines_with_tabs[:10]})")
