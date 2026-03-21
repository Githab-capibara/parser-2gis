#!/usr/bin/env python3
"""
Тесты для проверки форматирования кода и импортов.

Проверяет ВСЕ Python файлы в папке parser_2gis/:
1. black форматирование (line-length 100)
2. isort сортировка импортов (profile black, line-length 100)
3. Отсутствие неиспользуемых импортов (autoflake)
4. Отсутствие синтаксических ошибок в Python файлах

Все тесты помечены маркером @pytest.mark.formatting
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

import ast
import pytest

# =============================================================================
# КОНСТАНТЫ И ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================

# Путь к корню проекта
PROJECT_ROOT = Path(__file__).parent.parent

# Путь к исходному коду parser_2gis
PARSER_2GIS_DIR = PROJECT_ROOT / "parser_2gis"

# Исключения для проверки (директории и файлы)
EXCLUDE_PATTERNS = [
    "__pycache__",
    "*.pyc",
    ".git",
    "venv",
    ".venv",
    "node_modules",
    "build",
    "dist",
    "*.egg-info",
    ".benchmarks",
    ".pytest_cache",
]


def get_all_python_files() -> List[Path]:
    """
    Получает список ВСЕХ Python файлов в parser_2gis/.

    Returns:
        Список путей к Python файлам.
    """
    python_files = []

    if not PARSER_2GIS_DIR.exists():
        pytest.skip(f"Директория {PARSER_2GIS_DIR} не найдена")

    for py_file in PARSER_2GIS_DIR.rglob("*.py"):
        # Проверяем на исключения
        excluded = False
        for pattern in EXCLUDE_PATTERNS:
            if pattern in str(py_file):
                excluded = True
                break

        if not excluded:
            python_files.append(py_file)

    if not python_files:
        pytest.skip("Python файлы не найдены в parser_2gis/")

    return python_files


def run_black_check(files: List[Path]) -> Tuple[int, str, str]:
    """
    Запускает black --check для указанных файлов.

    Args:
        files: Список путей к файлам для проверки.

    Returns:
        Кортеж (return_code, stdout, stderr).
    """
    file_paths = [str(f) for f in files]
    result = subprocess.run(
        [sys.executable, "-m", "black", "--check", "--line-length=100", *file_paths],
        capture_output=True,
        text=True,
        timeout=300,  # 5 минут таймаут
        cwd=str(PROJECT_ROOT),
    )
    return result.returncode, result.stdout, result.stderr


def run_ruff_format_check(files: List[Path]) -> Tuple[int, str, str]:
    """
    Запускает ruff format --check для указанных файлов.

    Args:
        files: Список путей к файлам для проверки.

    Returns:
        Кортеж (return_code, stdout, stderr).
    """
    file_paths = [str(f) for f in files]
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "format", "--check", *file_paths],
        capture_output=True,
        text=True,
        timeout=300,  # 5 минут таймаут
        cwd=str(PROJECT_ROOT),
    )
    return result.returncode, result.stdout, result.stderr


def run_isort_check(files: List[Path]) -> Tuple[int, str, str]:
    """
    Запускает isort --check-only для указанных файлов.

    Args:
        files: Список путей к файлам для проверки.

    Returns:
        Кортеж (return_code, stdout, stderr).
    """
    file_paths = [str(f) for f in files]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "isort",
            "--check-only",
            "--profile=black",
            "--line-length=100",
            *file_paths,
        ],
        capture_output=True,
        text=True,
        timeout=300,  # 5 минут таймаут
        cwd=str(PROJECT_ROOT),
    )
    return result.returncode, result.stdout, result.stderr


def run_autoflake_check(files: List[Path]) -> Tuple[int, str, str]:
    """
    Запускает autoflake --check для указанных файлов.

    Args:
        files: Список путей к файлам для проверки.

    Returns:
        Кортеж (return_code, stdout, stderr).
    """
    file_paths = [str(f) for f in files]
    result = subprocess.run(
        [sys.executable, "-m", "autoflake", "--check", "--remove-all-unused-imports", *file_paths],
        capture_output=True,
        text=True,
        timeout=300,  # 5 минут таймаут
        cwd=str(PROJECT_ROOT),
    )
    return result.returncode, result.stdout, result.stderr


def check_syntax_errors(files: List[Path]) -> List[Tuple[Path, str, int]]:
    """
    Проверяет Python файлы на синтаксические ошибки.

    Args:
        files: Список путей к файлам для проверки.

    Returns:
        Список кортежей (путь_к_файлу, сообщение_об_ошибке, номер_строки).
    """
    errors = []

    for py_file in files:
        try:
            content = py_file.read_text(encoding="utf-8")
            ast.parse(content, filename=str(py_file))
        except SyntaxError as e:
            error_msg = f"SyntaxError: {e.msg}" if e.msg else "SyntaxError"
            line_num = e.lineno if e.lineno else 0
            errors.append((py_file, error_msg, line_num))
        except Exception as e:
            errors.append((py_file, f"Error reading file: {str(e)}", 0))

    return errors


def format_file_list(files: List[Path], max_files: int = 5) -> str:
    """
    Форматирует список файлов для отображения в сообщении об ошибке.

    Args:
        files: Список путей к файлам.
        max_files: Максимальное количество файлов для отображения.

    Returns:
        Отформатированная строка со списком файлов.
    """
    if not files:
        return ""

    displayed = files[:max_files]
    result = "\n".join(f"  - {f}" for f in displayed)

    if len(files) > max_files:
        result += f"\n  ... и ещё {len(files) - max_files} файлов(а)"

    return result


# =============================================================================
# ТЕСТЫ
# =============================================================================


class TestRuffFormatting:
    """Тесты для проверки форматирования ruff."""

    @pytest.mark.formatting
    def test_ruff_formatting_all_files(self):
        """
        Тест 1: Проверка ruff format ВСЕХ файлов в parser_2gis/.

        Запускает ruff format --check.
        Проверяет что ВСЕ Python файлы отформатированы согласно ruff.

        Raises:
            pytest.skip: Если ruff не установлен.
            AssertionError: Если файлы требуют форматирования.
        """
        python_files = get_all_python_files()

        returncode, stdout, stderr = run_ruff_format_check(python_files)

        # Проверяем что ruff установлен
        if returncode == 127 or "not found" in stderr or "No module named ruff" in stderr:
            pytest.skip("ruff не установлен. Установите: pip install ruff")

        # Если ruff обнаружил проблемы
        if returncode == 1:
            error_message = (
                f"ruff format обнаружил файлы, требующие форматирования:\n\n"
                f"{stdout}\n{stderr}\n\n"
                f"Для автоматического форматирования выполните:\n"
                f"  ruff format ."
            )
            pytest.fail(error_message)

        # Тест проходит
        assert returncode == 0, f"ruff format завершил работу с кодом {returncode}: {stderr}"

    @pytest.mark.formatting
    def test_ruff_formatting_detailed_report(self):
        """
        Тест 2: Детальный отчет о форматировании ruff.

        Проверяет каждый файл индивидуально и предоставляет детальный отчет.
        """
        python_files = get_all_python_files()
        unformatted_files = []

        for py_file in python_files:
            returncode, stdout, stderr = run_ruff_format_check([py_file])

            if returncode == 127 or "not found" in stderr:
                pytest.skip("ruff не установлен")

            if returncode == 1:
                unformatted_files.append(py_file)

        if unformatted_files:
            error_message = (
                f"Следующие файлы требуют форматирования ruff:\n\n"
                f"{format_file_list(unformatted_files, max_files=10)}\n\n"
                f"Всего файлов с нарушениями: {len(unformatted_files)} из {len(python_files)}\n\n"
                f"Для исправления выполните:\n"
                f"  ruff format {' '.join(str(f) for f in unformatted_files[:5])}"
            )
            pytest.fail(error_message)


class TestIsortImports:
    """Тесты для проверки сортировки импортов isort."""

    @pytest.mark.formatting
    def test_isort_imports_all_files(self):
        """
        Тест 3: Проверка isort сортировки ВСЕХ импортов в parser_2gis/.

        Запускает isort --check-only с profile=black и line-length=100.
        Проверяет что ВСЕ импорты отсортированы.

        Raises:
            pytest.skip: Если isort не установлен.
            AssertionError: Если импорты не отсортированы.
        """
        python_files = get_all_python_files()

        returncode, stdout, stderr = run_isort_check(python_files)

        # Проверяем что isort установлен
        if returncode == 127 or "not found" in stderr or "No module named isort" in stderr:
            pytest.skip("isort не установлен. Установите: pip install isort")

        # Если isort обнаружил проблемы
        if returncode == 1:
            # Пытаемся извлечь список файлов из вывода isort
            problematic_files = []
            for line in stdout.split("\n"):
                line = line.strip()
                if line.endswith("would be reordered"):
                    file_path = line.replace("would be reordered", "").strip()
                    if file_path:
                        problematic_files.append(Path(file_path))
                elif line.startswith("ERROR ") and line.endswith(".py"):
                    parts = line.split()
                    if parts and parts[-1].endswith(".py"):
                        problematic_files.append(Path(parts[-1]))

            # Если не удалось извлечь файлы, используем все файлы
            if not problematic_files:
                problematic_files = python_files

            error_message = (
                f"isort обнаружил файлы с неотсортированными импортами "
                f"(profile=black, line-length=100):\n\n"
                f"{format_file_list(problematic_files)}\n\n"
                f"Вывод isort:\n{stdout}\n{stderr}\n\n"
                f"Для автоматической сортировки выполните:\n"
                f"  isort --profile=black --line-length=100 parser_2gis/"
            )
            pytest.fail(error_message)

        # Тест проходит
        assert returncode == 0, f"isort завершил работу с кодом {returncode}: {stderr}"

    @pytest.mark.formatting
    def test_isort_imports_detailed_report(self):
        """
        Тест 4: Детальный отчет о сортировке импортов isort.

        Проверяет каждый файл индивидуально и предоставляет детальный отчет.
        """
        python_files = get_all_python_files()
        unsorted_files = []

        for py_file in python_files:
            returncode, stdout, stderr = run_isort_check([py_file])

            if returncode == 127 or "not found" in stderr:
                pytest.skip("isort не установлен")

            if returncode == 1:
                unsorted_files.append(py_file)

        if unsorted_files:
            error_message = (
                f"Следующие файлы имеют неотсортированные импорты "
                f"(profile=black, line-length=100):\n\n"
                f"{format_file_list(unsorted_files, max_files=10)}\n\n"
                f"Всего файлов с нарушениями: {len(unsorted_files)} из {len(python_files)}\n\n"
                f"Для исправления выполните:\n"
                f"  isort --profile=black --line-length=100 {' '.join(str(f) for f in unsorted_files[:5])}"
            )
            pytest.fail(error_message)


class TestAutoflakeUnusedImports:
    """Тесты для проверки неиспользуемых импортов."""

    @pytest.mark.formatting
    def test_autoflake_no_unused_imports(self):
        """
        Тест 5: Проверка отсутствия неиспользуемых импортов.

        Запускает autoflake --check с --remove-all-unused-imports.
        Проверяет что ВСЕ импорты в parser_2gis/ используются.

        Raises:
            pytest.skip: Если autoflake не установлен.
            AssertionError: Если есть неиспользуемые импорты.
        """
        python_files = get_all_python_files()

        returncode, stdout, stderr = run_autoflake_check(python_files)

        # Проверяем что autoflake установлен
        if returncode == 127 or "not found" in stderr or "No module named autoflake" in stderr:
            pytest.skip("autoflake не установлен. Установите: pip install autoflake")

        # Если autoflake обнаружил проблемы
        if returncode == 1:
            # Пытаемся извлечь информацию о проблемах
            error_lines = []
            for line in stdout.split("\n"):
                line = line.strip()
                if line and not line.startswith("+++ "):
                    error_lines.append(line)

            error_message = (
                f"autoflake обнаружил неиспользуемые импорты:\n\n"
                f"Вывод autoflake:\n{stdout}\n{stderr}\n\n"
                f"Найденные проблемы:\n"
                + "\n".join(f"  {line}" for line in error_lines[:20])
                + "\n\nДля автоматического удаления выполните:\n"
                "  autoflake --remove-all-unused-imports -r parser_2gis/"
            )
            pytest.fail(error_message)

        # Тест проходит
        assert returncode == 0, f"autoflake завершил работу с кодом {returncode}: {stderr}"


class TestSyntaxErrors:
    """Тесты для проверки синтаксических ошибок."""

    @pytest.mark.formatting
    def test_no_syntax_errors_in_all_files(self):
        """
        Тест 6: Проверка отсутствия синтаксических ошибок во ВСЕХ файлах parser_2gis/.

        Использует ast.parse для проверки синтаксиса.
        Проверяет ВСЕ Python файлы в parser_2gis/.

        Raises:
            AssertionError: Если найдены синтаксические ошибки.
        """
        python_files = get_all_python_files()

        syntax_errors = check_syntax_errors(python_files)

        if syntax_errors:
            error_message = "Обнаружены синтаксические ошибки в Python файлах:\n\n"

            for file_path, error_msg, line_num in syntax_errors:
                error_message += f"  {file_path}:{line_num} - {error_msg}\n"

            error_message += (
                f"\nВсего ошибок: {len(syntax_errors)}\n\n"
                f"Проверьте указанные файлы и исправьте синтаксические ошибки."
            )
            pytest.fail(error_message)

        # Тест проходит
        assert len(syntax_errors) == 0, "Синтаксические ошибки не найдены"

    @pytest.mark.formatting
    def test_syntax_errors_detailed_report(self):
        """
        Тест 7: Детальный отчет о синтаксических ошибках.

        Проверяет каждый файл индивидуально и предоставляет детальный отчет.
        """
        python_files = get_all_python_files()
        files_with_errors = []

        for py_file in python_files:
            try:
                content = py_file.read_text(encoding="utf-8")
                ast.parse(content, filename=str(py_file))
            except SyntaxError as e:
                error_msg = f"SyntaxError: {e.msg}" if e.msg else "SyntaxError"
                line_num = e.lineno if e.lineno else 0
                files_with_errors.append((py_file, error_msg, line_num))
            except Exception as e:
                files_with_errors.append((py_file, f"Error: {str(e)}", 0))

        if files_with_errors:
            error_message = (
                f"Следующие файлы содержат синтаксические ошибки:\n\n"
                f"{format_file_list([f[0] for f in files_with_errors], max_files=10)}\n\n"
                f"Детали ошибок:\n"
            )

            for file_path, error_msg, line_num in files_with_errors[:10]:
                error_message += f"  {file_path}:{line_num} - {error_msg}\n"

            if len(files_with_errors) > 10:
                error_message += f"  ... и ещё {len(files_with_errors) - 10} ошибок\n"

            pytest.fail(error_message)


# =============================================================================
# ЗАПУСК ТЕСТОВ
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
