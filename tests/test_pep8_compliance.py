#!/usr/bin/env python3
"""
Тесты для проверки соответствия кода стандарту PEP 8.

Проверяет отсутствие нарушений форматирования кода.
Тесты покрывают исправления автоматического форматирования PEP 8.

Тесты:
1. test_no_e302_violations - Тест отсутствия нарушений E302 (2 пустые строки)
2. test_no_e305_violations - Тест отсутствия нарушений E305 (после класса/функции)
3. test_no_w293_violations - Тест отсутствия whitespace в пустых строках
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

import pytest

# Пути к исходным файлам проекта
PROJECT_ROOT = Path(__file__).parent.parent
SOURCE_DIRS = [
    PROJECT_ROOT / "parser_2gis",
    PROJECT_ROOT / "tests",
]

# Исключаемые файлы и директории
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
    "htmlcov",
    ".benchmarks",
    ".pytest_cache",
]


def get_python_files() -> List[Path]:
    """
    Получает список всех Python файлов в проекте.

    Returns:
        Список путей к Python файлам.
    """
    python_files = []

    for source_dir in SOURCE_DIRS:
        if not source_dir.exists():
            continue

        for py_file in source_dir.rglob("*.py"):
            # Проверяем на исключения
            excluded = False
            for pattern in EXCLUDE_PATTERNS:
                if pattern in str(py_file):
                    excluded = True
                    break

            if not excluded:
                python_files.append(py_file)

    return python_files


def run_flake8_check(file_path: Path) -> Tuple[int, str, str]:
    """
    Запускает проверку flake8 для файла.

    Args:
        file_path: Путь к файлу для проверки.

    Returns:
        Кортеж (return_code, stdout, stderr).
    """
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "flake8",
            "--select=E302,E305,W293",
            "--show-source",
            str(file_path),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )

    return result.returncode, result.stdout, result.stderr


class TestPEP8Compliance:
    """Тесты для проверки соответствия кода стандарту PEP 8."""

    def test_no_e302_violations(self) -> None:
        """
        Тест 5.1: Проверка отсутствия нарушений E302 (2 пустые строки).

        E302: expected 2 blank lines, found 0
        E302: expected 2 blank lines, found 1

        Проверяет ключевые Python файлы проекта на отсутствие нарушений E302.
        """
        # Проверяем только ключевые файлы проекта
        key_files = [
            PROJECT_ROOT / "parser_2gis" / "main.py",
            PROJECT_ROOT / "parser_2gis" / "parallel_parser.py",
            PROJECT_ROOT / "parser_2gis" / "validation.py",
            PROJECT_ROOT / "parser_2gis" / "config.py",
        ]
        violations = []

        for py_file in key_files:
            if not py_file.exists():
                continue
            returncode, stdout, stderr = run_flake8_check(py_file)

            if returncode != 0:
                # Фильтруем только E302 нарушения
                for line in stdout.splitlines():
                    if "E302" in line:
                        violations.append(f"{py_file}: {line}")

        assert len(violations) == 0, f"Обнаружены нарушения E302 (2 пустые строки):\n" + "\n".join(
            violations[:10]
        )

    def test_no_e305_violations(self) -> None:
        """
        Тест 5.2: Проверка отсутствия нарушений E305 (после класса/функции).

        E305: expected 2 blank lines after end of function or class

        Проверяет ключевые Python файлы проекта на отсутствие нарушений E305.
        """
        # Проверяем только ключевые файлы проекта
        key_files = [
            PROJECT_ROOT / "parser_2gis" / "main.py",
            PROJECT_ROOT / "parser_2gis" / "parallel_parser.py",
            PROJECT_ROOT / "parser_2gis" / "validation.py",
            PROJECT_ROOT / "parser_2gis" / "config.py",
        ]
        violations = []

        for py_file in key_files:
            if not py_file.exists():
                continue
            returncode, stdout, stderr = run_flake8_check(py_file)

            if returncode != 0:
                # Фильтруем только E305 нарушения
                for line in stdout.splitlines():
                    if "E305" in line:
                        violations.append(f"{py_file}: {line}")

        assert (
            len(violations) == 0
        ), f"Обнаружены нарушения E305 (2 пустые строки после класса/функции):\n" + "\n".join(
            violations[:10]
        )

    def test_no_w293_violations(self) -> None:
        """
        Тест 5.3: Проверка отсутствия whitespace в пустых строках.

        W293: blank line contains whitespace

        Проверяет ключевые Python файлы проекта на отсутствие пробелов в пустых строках.
        """
        # Проверяем только ключевые файлы проекта
        key_files = [
            PROJECT_ROOT / "parser_2gis" / "main.py",
            PROJECT_ROOT / "parser_2gis" / "parallel_parser.py",
            PROJECT_ROOT / "parser_2gis" / "validation.py",
            PROJECT_ROOT / "parser_2gis" / "config.py",
        ]
        violations = []

        for py_file in key_files:
            if not py_file.exists():
                continue
            returncode, stdout, stderr = run_flake8_check(py_file)

            if returncode != 0:
                # Фильтруем только W293 нарушения
                for line in stdout.splitlines():
                    if "W293" in line:
                        violations.append(f"{py_file}: {line}")

        assert (
            len(violations) == 0
        ), f"Обнаружены нарушения W293 (whitespace в пустых строках):\n" + "\n".join(
            violations[:10]
        )


class TestPEP8ComplianceSpecificFiles:
    """Тесты для проверки конкретных файлов проекта."""

    @pytest.mark.parametrize(
        "file_path",
        [
            "parser_2gis/main.py",
            "parser_2gis/parallel_parser.py",
            "parser_2gis/validation.py",
            "parser_2gis/config.py",
        ],
    )
    def test_critical_files_pep8_compliance(self, file_path: str) -> None:
        """
        Проверка соответствия PEP 8 для критических файлов проекта.

        Args:
            file_path: Путь к файлу относительно корня проекта.
        """
        full_path = PROJECT_ROOT / file_path

        if not full_path.exists():
            pytest.skip(f"Файл {file_path} не найден")

        returncode, stdout, stderr = run_flake8_check(full_path)

        # Фильтруем только интересующие нас нарушения
        relevant_violations = []
        for line in stdout.splitlines():
            if any(code in line for code in ["E302", "E305", "W293"]):
                relevant_violations.append(line)

        assert (
            len(relevant_violations) == 0
        ), f"Обнаружены нарушения PEP 8 в {file_path}:\n" + "\n".join(relevant_violations)


class TestPEP8ComplianceDetailed:
    """Детальные тесты для проверки конкретных нарушений PEP 8."""

    def test_no_trailing_whitespace_in_code(self) -> None:
        """
        Проверка отсутствия пробелов в конце строк кода.

        Note:
            W291: trailing whitespace
            W293: blank line contains whitespace
        """
        # Проверяем только ключевые файлы проекта
        key_files = [
            PROJECT_ROOT / "parser_2gis" / "main.py",
            PROJECT_ROOT / "parser_2gis" / "parallel_parser.py",
            PROJECT_ROOT / "parser_2gis" / "validation.py",
            PROJECT_ROOT / "parser_2gis" / "config.py",
        ]
        violations = []

        for py_file in key_files:
            if not py_file.exists():
                continue
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        # Проверяем на пробелы в конце строки (перед newline)
                        if line.rstrip("\n\r") != line.rstrip():
                            violations.append(f"{py_file}:{line_num}: trailing whitespace")
            except Exception as e:
                # Пропускаем файлы которые не удалось прочитать
                pass

        assert len(violations) == 0, f"Обнаружены пробелы в конце строк:\n" + "\n".join(
            violations[:10]
        )

    def test_blank_lines_after_function(self) -> None:
        """
        Проверка что после определения функции есть 2 пустые строки.

        Note:
            E302: expected 2 blank lines, found 0
            E305: expected 2 blank lines after end of function or class
        """
        python_files = get_python_files()
        violations = []

        for py_file in python_files:
            returncode, stdout, stderr = run_flake8_check(py_file)

            if returncode != 0:
                for line in stdout.splitlines():
                    if "E302" in line or "E305" in line:
                        violations.append(f"{py_file}: {line}")

        assert len(violations) == 0, (
            f"Обнаружены нарушения количества пустых строк:\n"
            + "\n".join(violations[:10])
            + (f"\n... и ещё {len(violations) - 10}" if len(violations) > 10 else "")
        )

    def test_mixed_tabs_and_spaces(self) -> None:
        """
        Проверка отсутствия смешанных табуляций и пробелов.

        Note:
            E101: indentation contains mixed spaces and tabs
        """
        python_files = get_python_files()
        violations = []

        for py_file in python_files:
            try:
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "flake8",
                        "--select=E101",
                        "--show-source",
                        str(py_file),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if result.returncode != 0:
                    for line in result.stdout.splitlines():
                        violations.append(f"{py_file}: {line}")
            except Exception:
                pass

        assert len(violations) == 0, (
            f"Обнаружены смешанные табуляции и пробелы:\n"
            + "\n".join(violations[:10])
            + (f"\n... и ещё {len(violations) - 10}" if len(violations) > 10 else "")
        )


class TestPEP8ComplianceConfiguration:
    """Тесты для проверки конфигурации PEP 8."""

    def test_flake8_config_exists(self) -> None:
        """
        Проверка что конфигурация flake8 существует.

        Note:
            Проверяет наличие setup.cfg или .flake8
        """
        config_files = [
            PROJECT_ROOT / "setup.cfg",
            PROJECT_ROOT / ".flake8",
            PROJECT_ROOT / "tox.ini",
        ]

        config_exists = any(config.exists() for config in config_files)

        assert config_exists, (
            "Конфигурация flake8 не найдена. " "Создайте setup.cfg или .flake8 в корне проекта"
        )

    def test_setup_cfg_has_flake8_section(self) -> None:
        """
        Проверка что setup.cfg содержит секцию flake8.

        Note:
            Проверяет наличие [flake8] секции
        """
        setup_cfg = PROJECT_ROOT / "setup.cfg"

        if not setup_cfg.exists():
            pytest.skip("setup.cfg не найден")

        with open(setup_cfg, "r", encoding="utf-8") as f:
            content = f.read()

        assert "[flake8]" in content, "setup.cfg должен содержать секцию [flake8]"


# Запуск тестов через pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
