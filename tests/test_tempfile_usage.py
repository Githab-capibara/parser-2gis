#!/usr/bin/env python3
"""
Тесты для проверки использования tempfile.gettempdir() вместо hardcoded /tmp.

Проверяет что:
- Используется tempfile.gettempdir() для кроссплатформенности
- Отсутствует Path("/tmp") в коде
- Временные директории создаются корректно

Тесты покрывают исправления важной проблемы #8 из audit-report.md.
"""

import tempfile
from pathlib import Path

import ast
import pytest


class TestTempfileUsageInMain:
    """Тесты для проверки использования tempfile в main.py."""

    def test_main_uses_tempfile_gettempdir(self) -> None:
        """
        Тест 1.1: Проверка что main.py использует tempfile.gettempdir().

        Проверяет что в main.py импортируется tempfile
        и используется gettempdir() вместо hardcoded "/tmp".

        Note:
            tempfile.gettempdir() возвращает платформо-зависимую
            временную директорию
        """
        # Читаем исходный код файла main.py
        main_py_path = Path(__file__).parent.parent / "parser_2gis" / "main.py"

        with open(main_py_path, "r", encoding="utf-8") as f:
            source = f.read()

        # Проверяем что используется gettempdir
        assert "tempfile.gettempdir()" in source, (
            "main.py должен использовать tempfile.gettempdir()"
        )

    def test_main_no_hardcoded_tmp_path(self) -> None:
        """
        Тест 1.2: Проверка отсутствия Path("/tmp") в main.py.

        Проверяет что в main.py не используется
        hardcoded путь Path("/tmp").

        Note:
            Hardcoded пути нарушают кроссплатформенность
        """
        import inspect

        from parser_2gis import main

        source = inspect.getsource(main)

        # Проверяем отсутствие hardcoded путей
        assert 'Path("/tmp")' not in source, 'main.py не должен содержать Path("/tmp")'
        assert "Path('/tmp')" not in source, "main.py не должен содержать Path('/tmp')"

    def test_main_allowed_base_dirs_includes_tempdir(self) -> None:
        """
        Тест 1.3: Проверка что _ALLOWED_BASE_DIRS включает tempfile.gettempdir().

        Проверяет что список разрешённых директорий
        включает системную временную директорию.

        Note:
            Временная директория должна быть в списке разрешённых
        """
        from parser_2gis.main import _ALLOWED_BASE_DIRS

        # Получаем системную временную директорию
        expected_temp_dir = Path(tempfile.gettempdir())

        # Проверяем что временная директория в списке
        assert expected_temp_dir in _ALLOWED_BASE_DIRS, (
            f"_ALLOWED_BASE_DIRS должен включать {expected_temp_dir}"
        )


class TestTempfileUsageInBrowser:
    """Тесты для проверки использования tempfile в browser.py."""

    def test_browser_uses_tempfile_gettempdir(self) -> None:
        """
        Тест 2.1: Проверка что browser.py использует tempfile.gettempdir().

        Проверяет что в browser.py импортируется tempfile
        и используется gettempdir().

        Note:
            Профили браузеров должны создаваться во временной директории
        """
        import inspect

        from parser_2gis.chrome import browser

        source = inspect.getsource(browser)

        # Проверяем что используется gettempdir
        assert "tempfile.gettempdir()" in source, (
            "browser.py должен использовать tempfile.gettempdir()"
        )

    def test_browser_no_hardcoded_tmp_path(self) -> None:
        """
        Тест 2.2: Проверка отсутствия Path("/tmp") в browser.py.

        Проверяет что в browser.py не используется
        hardcoded путь Path("/tmp").

        Note:
            Hardcoded пути нарушают кроссплатформенность
        """
        import inspect

        from parser_2gis.chrome import browser

        source = inspect.getsource(browser)

        # Проверяем отсутствие hardcoded путей
        assert 'Path("/tmp")' not in source, 'browser.py не должен содержать Path("/tmp")'
        assert "Path('/tmp')" not in source, "browser.py не должен содержать Path('/tmp')"


class TestTempfileModuleAvailability:
    """Тесты для проверки доступности модуля tempfile."""

    def test_tempfile_module_available(self) -> None:
        """
        Тест 3.1: Проверка что модуль tempfile доступен.

        Проверяет что tempfile может быть импортирован.

        Note:
            tempfile - стандартный модуль Python
        """
        import tempfile

        # Проверяем что модуль доступен
        assert tempfile is not None

    def test_tempfile_gettempdir_returns_path(self) -> None:
        """
        Тест 3.2: Проверка что gettempdir() возвращает путь.

        Проверяет что gettempdir() возвращает строку
        с путём к временной директории.

        Note:
            Возвращаемое значение зависит от платформы
        """
        import tempfile

        temp_dir = tempfile.gettempdir()

        # Проверяем что возвращена строка
        assert isinstance(temp_dir, str), "gettempdir() должен вернуть строку"

        # Проверяем что путь существует
        assert Path(temp_dir).exists(), f"Временная директория {temp_dir} должна существовать"

    def test_tempfile_gettempdir_is_absolute(self) -> None:
        """
        Тест 3.3: Проверка что gettempdir() возвращает абсолютный путь.

        Проверяет что возвращаемый путь является абсолютным.

        Note:
            Абсолютные пути предпочтительнее относительных
        """
        import tempfile

        temp_dir = tempfile.gettempdir()

        # Проверяем что путь абсолютный
        assert Path(temp_dir).is_absolute(), f"Путь {temp_dir} должен быть абсолютным"


class TestHardcodedPathDetection:
    """Тесты для обнаружения hardcoded путей в коде."""

    def test_no_hardcoded_tmp_in_parser_2gis(self) -> None:
        """
        Тест 4.1: Проверка отсутствия hardcoded /tmp в parser_2gis.

        Сканирует все Python файлы в parser_2gis
        на наличие Path("/tmp") или Path('/tmp').

        Note:
            Используем AST для точного анализа
        """
        parser_2gis_dir = Path(__file__).parent.parent / "parser_2gis"

        hardcoded_paths = []

        # Сканируем все Python файлы
        for py_file in parser_2gis_dir.rglob("*.py"):
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    source = f.read()

                # Проверяем наличие hardcoded путей
                if 'Path("/tmp")' in source or "Path('/tmp')" in source:
                    # Исключаем комментарии и docstrings
                    tree = ast.parse(source)

                    # Ищем в коде (не в строках документации)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Call):
                            if isinstance(node.func, ast.Name) and node.func.id == "Path":
                                if node.args:
                                    arg = node.args[0]
                                    if isinstance(arg, ast.Constant):
                                        if arg.value == "/tmp":
                                            hardcoded_paths.append((str(py_file), node.lineno))

            except (SyntaxError, UnicodeDecodeError):
                # Пропускаем файлы с ошибками синтаксиса
                continue

        # Проверяем что hardcoded пути не найдены
        assert len(hardcoded_paths) == 0, f'Найдены hardcoded пути Path("/tmp"): {hardcoded_paths}'

    def test_tempfile_imported_in_modules(self) -> None:
        """
        Тест 4.2: Проверка что tempfile импортирован в нужных модулях.

        Проверяет что модули использующие временные файлы
        импортируют tempfile.

        Note:
            tempfile должен быть импортирован в main.py и browser.py
        """
        import inspect

        from parser_2gis.chrome import browser

        # Проверяем browser.py
        browser_source = inspect.getsource(browser)
        assert "import tempfile" in browser_source, "browser.py должен импортировать tempfile"


class TestTempfileCrossPlatform:
    """Тесты для проверки кроссплатформенности tempfile."""

    def test_tempfile_works_on_linux(self) -> None:
        """
        Тест 5.1: Проверка что tempfile работает на Linux.

        Проверяет что gettempdir() возвращает корректный
        путь на Linux системах.

        Note:
            На Linux это обычно /tmp
        """
        import os
        import tempfile

        # Проверяем что мы на Linux
        if os.name == "posix":
            temp_dir = tempfile.gettempdir()

            # На Linux путь должен быть /tmp или /var/tmp
            assert temp_dir.startswith("/"), f"Путь {temp_dir} должен начинаться с /"

    def test_tempfile_dir_is_writable(self) -> None:
        """
        Тест 5.2: Проверка что временная директория доступна для записи.

        Проверяет что в временную директорию можно записать файл.

        Note:
            Временная директория должна быть доступна для записи
        """
        import os
        import tempfile

        temp_dir = Path(tempfile.gettempdir())

        # Проверяем что директория существует
        assert temp_dir.exists(), f"Директория {temp_dir} должна существовать"
        # Проверяем что директория доступна для записи
        assert os.access(temp_dir, os.W_OK), (
            f"Директория {temp_dir} должна быть доступна для записи"
        )

    def test_tempfile_creates_file_successfully(self) -> None:
        """
        Тест 5.3: Проверка что tempfile может создать файл.

        Проверяет что tempfile.NamedTemporaryFile работает
        корректно.

        Note:
            NamedTemporaryFile должен создавать файлы
        """
        import tempfile

        # Создаём временный файл
        with tempfile.NamedTemporaryFile(delete=True) as tmp:
            # Проверяем что файл создан
            assert tmp.name is not None

            # Записываем данные
            tmp.write(b"test data")
            tmp.flush()

            # Проверяем что данные записаны
            tmp.seek(0)
            assert tmp.read() == b"test data"


# Запуск тестов через pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
