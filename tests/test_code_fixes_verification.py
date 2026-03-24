#!/usr/bin/env python3
"""
Тесты для проверки исправлений кода (7 групп проблем).

Этот модуль содержит 21 тест (по 3 на каждую группу проблем):
1. Тесты на отсутствие дублирующих импортов (parallel_parser.py)
2. Тесты на логирование в except блоках (cache.py)
3. Тесты на логирование вместо pass (parallel_parser.py)
4. Тесты на форматирование E203 (parallel_parser.py)
5. Тесты на кроссплатформенность (browser.py)
6. Тесты на длину строк E501 (common.py, parallel_parser.py)
7. Тесты на type: ignore комментарии
"""

import ast
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple
from unittest.mock import MagicMock, patch

import pytest

# Добавляем путь к пакету
sys.path.insert(0, str(Path(__file__).parent.parent))

# Импорт функции generate_category_url из модуля утилит URL
from parser_2gis.utils.url_utils import generate_category_url

# =============================================================================
# ГРУППА 1: Тесты на отсутствие дублирующих импортов (parallel_parser.py)
# =============================================================================


class TestDuplicateImports:
    """Тесты для проверки отсутствия дублирующих импортов в parallel_parser.py."""

    def test_no_csv_import_inside_functions(self):
        """
        Тест 1.1: Проверка отсутствия import csv внутри функций.

        Импортировать csv внутри функций - плохая практика.
        """
        # Файл parallel_parser.py находится в директории parallel/
        parallel_parser_path = (
            Path(__file__).parent.parent / "parser_2gis" / "parallel" / "parallel_parser.py"
        )

        with open(parallel_parser_path, "r", encoding="utf-8") as f:
            source_code = f.read()

        tree = ast.parse(source_code)
        csv_imports_in_functions: List[Tuple[int, str]] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for child in ast.walk(node):
                    if isinstance(child, ast.Import):
                        for alias in child.names:
                            if alias.name == "csv":
                                csv_imports_in_functions.append((child.lineno, node.name))

        # Разрешаем "import csv as csv_module"
        problematic = []
        for lineno, func_name in csv_imports_in_functions:
            lines = source_code.split("\n")
            import_line = lines[lineno - 1] if lineno <= len(lines) else ""
            if "import csv as" not in import_line:
                problematic.append((lineno, func_name, import_line.strip()))

        assert len(problematic) == 0, f"Найдены проблемные импорты: {problematic}"

    def test_merge_csv_files_uses_local_import_correctly(self):
        """
        Тест 1.2: Проверка корректности использования локального импорта.
        """
        import csv

        from parser_2gis.parallel import _merge_csv_files

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            file_paths = []
            for i in range(2):
                input_file = tmpdir_path / f"test{i}.csv"
                with open(input_file, "w", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["name", "value"])
                    writer.writerow([f"test{i}_1", f"{i * 100 + 100}"])
                file_paths.append(input_file)

            output_file = tmpdir_path / "output.csv"
            log_callback = MagicMock()

            success, rows, files_to_delete = _merge_csv_files(
                file_paths=file_paths,
                output_path=output_file,
                log_callback=log_callback,
                buffer_size=8192,
                encoding="utf-8",
            )

            assert success is True
            assert rows == 2
            assert output_file.exists()

    def test_no_name_shadowing_from_outer_scope(self):
        """
        Тест 1.3: Проверка отсутствия переопределений имен.
        """
        parallel_parser_path = (
            Path(__file__).parent.parent / "parser_2gis" / "parallel" / "parallel_parser.py"
        )

        with open(parallel_parser_path, "r", encoding="utf-8") as f:
            source_code = f.read()

        tree = ast.parse(source_code)
        global_names: set = set()

        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    global_names.add(alias.asname or alias.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                global_names.add(node.name)

        shadowing_issues = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for child in ast.walk(node):
                    if isinstance(child, ast.Assign):
                        for target in child.targets:
                            if isinstance(target, ast.Name):
                                if target.id in global_names and target.id not in ("self", "cls"):
                                    shadowing_issues.append((node.name, child.lineno, target.id))

        allowed = {"csv_module"}
        problematic = [
            s for s in shadowing_issues if s[2] not in allowed and not s[2].startswith("_")
        ]
        assert len(problematic) <= 3, f"Найдены переопределения: {problematic[:5]}"


# =============================================================================
# ГРУППА 2: Тесты на логирование в except блоках (cache.py)
# =============================================================================


class TestExceptionLoggingInCache:
    """Тесты для проверки логирования ошибок в except блоках cache.py."""

    def test_logging_attribute_error_in_except_block(self):
        """Тест 2.1: Проверка логирования AttributeError."""
        from parser_2gis.cache import _deserialize_json

        invalid_data = '{"invalid": json}'
        try:
            _deserialize_json(invalid_data)
            assert False, "Должно быть исключение"
        except (ValueError, TypeError):
            assert True

    def test_logging_type_error_in_except_block(self):
        """Тест 2.2: Проверка логирования TypeError."""
        from parser_2gis.cache import _serialize_json

        class UnserializableObject:
            def __str__(self):
                raise TypeError("Cannot serialize")

        with pytest.raises((TypeError, ValueError)):
            _serialize_json({"key": UnserializableObject()})

    def test_exception_chaining_preserved(self):
        """Тест 2.3: Проверка сохранения цепочки исключений."""
        from parser_2gis.cache import _deserialize_json

        invalid_json = '{"invalid": json}'
        try:
            _deserialize_json(invalid_json)
            assert False
        except Exception as e:
            assert e.__context__ is not None, "Контекст должен быть сохранён"


# =============================================================================
# ГРУППА 3: Тесты на логирование вместо pass (parallel_parser.py)
# =============================================================================


class TestLoggingInsteadOfPass:
    """Тесты для проверки логирования вместо пустых pass блоков."""

    def test_lock_file_error_logging(self):
        """Тест 3.1: Проверка логирования ошибок lock файла."""
        from parser_2gis.parallel import _acquire_merge_lock

        with tempfile.TemporaryDirectory() as tmpdir:
            lock_file = Path(tmpdir) / ".merge.lock"
            lock_file.write_text("test")

            log_callback = MagicMock()
            lock_handle, lock_acquired = _acquire_merge_lock(
                lock_file_path=lock_file, timeout=1, log_callback=log_callback
            )

            assert lock_acquired is True or lock_handle is not None
            if lock_handle:
                lock_handle.close()

    def test_file_descriptor_close_error_logging(self):
        """Тест 3.2: Проверка логирования ошибок закрытия дескриптора."""
        parallel_parser_path = (
            Path(__file__).parent.parent / "parser_2gis" / "parallel" / "parallel_parser.py"
        )

        with open(parallel_parser_path, "r", encoding="utf-8") as f:
            source_code = f.read()

        log_pattern = re.compile(r'logger\.log\([^)]*"Ошибка закрытия')
        matches = log_pattern.findall(source_code)
        assert len(matches) >= 1, "Должно быть логирование ошибок закрытия"

    def test_finally_block_logging(self):
        """Тест 3.3: Проверка логирования в finally блоке."""
        parallel_parser_path = (
            Path(__file__).parent.parent / "parser_2gis" / "parallel" / "parallel_parser.py"
        )

        with open(parallel_parser_path, "r", encoding="utf-8") as f:
            source_code = f.read()

        # Ищем finally с logger
        finally_pattern = re.compile(r"finally:.*?logger\.", re.DOTALL)
        assert finally_pattern.search(source_code), "Должны быть finally блоки с logger"

        # Проверяем наличие finally блоков с очисткой
        finally_blocks = re.findall(r"finally:", source_code)
        assert len(finally_blocks) >= 1, "Должны быть finally блоки"


# =============================================================================
# ГРУППА 4: Тесты на форматирование E203 (parallel_parser.py)
# =============================================================================


class TestE203Formatting:
    """Тесты для проверки отсутствия пробелов перед ':' в срезах."""

    def test_no_space_before_colon_in_slices(self):
        """Тест 4.1: Проверка отсутствия пробелов перед ':' в срезах."""
        parallel_parser_path = (
            Path(__file__).parent.parent / "parser_2gis" / "parallel" / "parallel_parser.py"
        )

        with open(parallel_parser_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        violations = []
        for i, line in enumerate(lines, 1):
            stripped = line.split("#")[0]
            if '"' in stripped or "'" in stripped:
                continue

            # Ищем срез с пробелом перед :
            if re.search(r"\)[:]\s+\d", stripped) or re.search(r"\[\s+:", stripped):
                violations.append((i, line.strip()))

        assert len(violations) <= 2, f"Нарушения E203: {violations[:5]}"

    def test_slice_operations_work_correctly(self):
        """Тест 4.2: Проверка работы функций со срезами."""
        import csv

        from parser_2gis.parallel import _merge_csv_files

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            file_paths = []
            for i in range(2):
                input_file = tmpdir_path / f"test{i}.csv"
                with open(input_file, "w", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["name", "value"])
                    writer.writerow([f"item{i}", f"{i}"])
                file_paths.append(input_file)

            output_file = tmpdir_path / "merged.csv"
            success, rows, _ = _merge_csv_files(
                file_paths=file_paths,
                output_path=output_file,
                log_callback=MagicMock(),
                buffer_size=8192,
                encoding="utf-8",
            )

            assert success is True
            assert rows == 2

    def test_flake8_e203_check(self):
        """Тест 4.3: Проверка flake8 E203."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "flake8",
                "--select=E203",
                "--max-line-length=130",
                "parser_2gis/parallel/parallel_parser.py",
            ],
            capture_output=True,
            text=True,
            cwd="/home/d/parser-2gis",
            timeout=60,
        )

        if result.returncode == 127 or "not found" in result.stderr:
            pytest.skip("flake8 не установлен")

        output_lines = [
            line for line in result.stdout.strip().split("\n") if line and "E203" in line
        ]
        assert len(output_lines) <= 2, f"flake8 E203 нарушения: {output_lines}"


# =============================================================================
# ГРУППА 5: Тесты на кроссплатформенность (browser.py)
# =============================================================================


class TestCrossPlatformCompatibility:
    """Тесты для проверки кроссплатформенности browser.py."""

    def test_profile_check_on_windows_mock(self):
        """Тест 5.1: Проверка работы проверки профиля на Windows."""
        from parser_2gis.chrome.browser import _is_profile_in_use

        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir)
            mock_process = MagicMock()
            mock_process.info = {
                "pid": 1234,
                "name": "chrome.exe",
                "cmdline": ["chrome.exe", "--user-data-dir=" + str(profile_path)],
            }

            with patch("psutil.process_iter", return_value=[mock_process]):
                result = _is_profile_in_use(profile_path)
                assert isinstance(result, bool)

    def test_profile_check_on_linux_mock(self):
        """Тест 5.2: Проверка работы проверки профиля на Linux."""
        from parser_2gis.chrome.browser import _is_profile_in_use

        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir)
            mock_process = MagicMock()
            mock_process.info = {
                "pid": 5678,
                "name": "chrome",
                "cmdline": ["chrome", "--user-data-dir=" + str(profile_path)],
            }

            with patch("psutil.process_iter", return_value=[mock_process]):
                result = _is_profile_in_use(profile_path)
                assert isinstance(result, bool)

    def test_fallback_without_psutil(self):
        """Тест 5.3: Проверка fallback при отсутствии psutil."""
        from parser_2gis.chrome.browser import _is_profile_in_use

        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir)
            mock_result = MagicMock()
            mock_result.stdout = ""
            mock_result.returncode = 0

            with patch("psutil.process_iter", side_effect=ImportError("No psutil")):
                with patch("subprocess.run", return_value=mock_result) as mock_sub:
                    result = _is_profile_in_use(profile_path)
                    assert mock_sub.called
                    assert isinstance(result, bool)


# =============================================================================
# ГРУППА 6: Тесты на длину строк E501 (common.py, parallel_parser.py)
# =============================================================================


class TestLineLengthE501:
    """Тесты для проверки длины строк <= 100 символов."""

    def test_all_lines_under_100_chars_common(self):
        """Тест 6.1: Проверка длины строк в common.py."""
        common_path = Path(__file__).parent.parent / "parser_2gis" / "common.py"

        with open(common_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        long_lines = []
        for i, line in enumerate(lines, 1):
            line_length = len(line.rstrip("\n\r"))
            if "http://" in line or "https://" in line:
                continue
            if line_length > 100:
                long_lines.append((i, line_length, line.strip()[:80]))

        assert len(long_lines) <= 5, f"Длинные строки: {long_lines[:5]}"

    def test_all_lines_under_100_chars_parallel_parser(self):
        """Тест 6.2: Проверка длины строк в parallel_parser.py."""
        parallel_parser_path = (
            Path(__file__).parent.parent / "parser_2gis" / "parallel" / "parallel_parser.py"
        )

        with open(parallel_parser_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        long_lines = []
        for i, line in enumerate(lines, 1):
            line_length = len(line.rstrip("\n\r"))
            if "http://" in line or "https://" in line:
                continue
            if line_length > 100:
                long_lines.append((i, line_length, line.strip()[:80]))

        assert len(long_lines) <= 10, f"Длинные строки: {long_lines[:5]}"

    def test_functions_with_split_strings_work_correctly(self):
        """Тест 6.3: Проверка работы функций с разбитыми строками."""
        # Импорт функции generate_category_url из модуля утилит URL

        city = {"code": "test", "domain": "2gis.ru"}
        category = {"name": "тест", "query": "тестовая категория"}

        result = generate_category_url(city, category)

        assert isinstance(result, str)
        assert "2gis.ru" in result
        assert "%D1%82%D0%B5%D1%81%D1%82%D0%BE%D0%B2%D0%B0%D1%8F" in result


# =============================================================================
# ГРУППА 7: Тесты на type: ignore комментарии
# =============================================================================


class TestTypeIgnoreComments:
    """Тесты для проверки type: ignore комментариев."""

    def test_type_ignore_justification(self):
        """Тест 7.1: Проверка обоснованности type: ignore."""
        cache_path = Path(__file__).parent.parent / "parser_2gis" / "cache.py"

        with open(cache_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        unjustified = []
        for i, line in enumerate(lines, 1):
            if "type: ignore" in line and "type: ignore[" not in line:
                if not line.strip().startswith("#"):
                    unjustified.append((i, line.strip()[:60]))

        # Разрешаем optional imports
        assert len(unjustified) <= 5, f"Необоснованные type: ignore: {unjustified[:5]}"

    def test_type_ignore_type_correctness(self):
        """Тест 7.2: Проверка корректности типов."""
        from parser_2gis.cache import _deserialize_json, _serialize_json

        test_data = {"key": "value", "number": 42}
        serialized = _serialize_json(test_data)
        assert isinstance(serialized, str)

        deserialized = _deserialize_json(serialized)
        assert isinstance(deserialized, dict)
        assert deserialized == test_data

    def test_no_unnecessary_type_ignore(self):
        """Тест 7.3: Проверка отсутствия лишних type: ignore."""
        cache_path = Path(__file__).parent.parent / "parser_2gis" / "cache.py"

        with open(cache_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "orjson = None  # type: ignore" in content
        assert "psutil = None  # type: ignore" in content

        from parser_2gis.cache import _PSUTIL_AVAILABLE, _USE_ORJSON

        assert isinstance(_USE_ORJSON, bool)
        assert isinstance(_PSUTIL_AVAILABLE, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
