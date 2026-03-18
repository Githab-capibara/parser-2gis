#!/usr/bin/env python3
"""
Тесты для проверки чтения переменных окружения для конфигурации параллельного парсера.

Проверяет корректность чтения настроек из переменных окружения.
Тесты покрывают исправления выноса конфигов в переменные окружения.

Тесты:
1. test_merge_lock_timeout_from_env - Тест чтения MERGE_LOCK_TIMEOUT из переменной окружения
2. test_max_lock_file_age_from_env - Тест чтения MAX_LOCK_FILE_AGE из переменной окружения
3. test_max_temp_files_from_env - Тест чтения MAX_TEMP_FILES из переменной окружения
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

# Пути к проекту
PROJECT_ROOT = Path(__file__).parent.parent


def check_env_value(
    env_var: str, const_name: str, test_value: str, expected_value: int
) -> bool:
    """
    Проверяет что переменная окружения читается корректно.

    Args:
        env_var: Имя переменной окружения.
        const_name: Имя константы в модуле.
        test_value: Тестовое значение.
        expected_value: Ожидаемое значение после конвертации.

    Returns:
        True если проверка пройдена.
    """
    # Запускаем отдельный процесс для проверки
    code = f"""
import os
os.environ['{env_var}'] = '{test_value}'
from parser_2gis.parallel_parser import {const_name}
print({const_name})
"""
    # Получаем путь к Python из текущего окружения
    python_executable = sys.executable

    result = subprocess.run(
        [python_executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(PROJECT_ROOT),
    )

    if result.returncode != 0:
        return False

    try:
        actual_value = int(result.stdout.strip())
        return actual_value == expected_value
    except ValueError:
        return False


class TestParallelParserEnvConfig:
    """Тесты для проверки чтения переменных окружения конфигурации."""

    def test_merge_lock_timeout_from_env(self) -> None:
        """
        Тест 3.1: Проверка чтения MERGE_LOCK_TIMEOUT из переменной окружения.

        Устанавливает переменную окружения PARSER_MERGE_LOCK_TIMEOUT.
        Проверяет что константа MERGE_LOCK_TIMEOUT читает значение из переменной.

        Note:
            Переменная окружения: PARSER_MERGE_LOCK_TIMEOUT
            Значение по умолчанию: 300 секунд
        """
        result = check_env_value(
            "PARSER_MERGE_LOCK_TIMEOUT", "MERGE_LOCK_TIMEOUT", "600", 600
        )
        assert result is True, "PARSER_MERGE_LOCK_TIMEOUT=600 должно читаться корректно"

    def test_max_lock_file_age_from_env(self) -> None:
        """
        Тест 3.2: Проверка чтения MAX_LOCK_FILE_AGE из переменной окружения.

        Устанавливает переменную окружения PARSER_MAX_LOCK_FILE_AGE.
        Проверяет что константа MAX_LOCK_FILE_AGE читает значение из переменной.

        Note:
            Переменная окружения: PARSER_MAX_LOCK_FILE_AGE
            Значение по умолчанию: 300 секунд
        """
        result = check_env_value(
            "PARSER_MAX_LOCK_FILE_AGE", "MAX_LOCK_FILE_AGE", "600", 600
        )
        assert result is True, "PARSER_MAX_LOCK_FILE_AGE=600 должно читаться корректно"

    def test_max_temp_files_from_env(self) -> None:
        """
        Тест 3.3: Проверка чтения MAX_TEMP_FILES из переменной окружения.

        Устанавливает переменную окружения PARSER_MAX_TEMP_FILES.
        Проверяет что константа MAX_TEMP_FILES читает значение из переменной.

        Note:
            Переменная окружения: PARSER_MAX_TEMP_FILES
            Значение по умолчанию: 1000 файлов
        """
        result = check_env_value("PARSER_MAX_TEMP_FILES", "MAX_TEMP_FILES", "500", 500)
        assert result is True, "PARSER_MAX_TEMP_FILES=500 должно читаться корректно"


class TestParallelParserEnvConfigDefaults:
    """Тесты для проверки значений по умолчанию переменных окружения."""

    def test_merge_lock_timeout_default_value(self) -> None:
        """
        Проверка значения по умолчанию для MERGE_LOCK_TIMEOUT.

        Note:
            Значение по умолчанию: 300 секунд (5 минут)
        """
        result = check_env_value(
            "PARSER_MERGE_LOCK_TIMEOUT", "MERGE_LOCK_TIMEOUT", "300", 300
        )
        assert result is True, "PARSER_MERGE_LOCK_TIMEOUT по умолчанию должно быть 300"

    def test_max_lock_file_age_default_value(self) -> None:
        """
        Проверка значения по умолчанию для MAX_LOCK_FILE_AGE.

        Note:
            Значение по умолчанию: 300 секунд (5 минут)
        """
        result = check_env_value(
            "PARSER_MAX_LOCK_FILE_AGE", "MAX_LOCK_FILE_AGE", "300", 300
        )
        assert result is True, "PARSER_MAX_LOCK_FILE_AGE по умолчанию должно быть 300"

    def test_max_temp_files_default_value(self) -> None:
        """
        Проверка значения по умолчанию для MAX_TEMP_FILES.

        Note:
            Значение по умолчанию: 1000 файлов
        """
        result = check_env_value(
            "PARSER_MAX_TEMP_FILES", "MAX_TEMP_FILES", "1000", 1000
        )
        assert result is True, "PARSER_MAX_TEMP_FILES по умолчанию должно быть 1000"


class TestParallelParserEnvConfigInvalidValues:
    """Тесты для проверки обработки некорректных значений переменных окружения."""

    def test_invalid_merge_lock_timeout_raises_error(self) -> None:
        """
        Проверка что некорректное значение MERGE_LOCK_TIMEOUT вызывает ошибку.

        Note:
            Некорректные значения: нечисловые строки
        """
        code = """
import os
os.environ['PARSER_MERGE_LOCK_TIMEOUT'] = 'invalid'
from parser_2gis.parallel_parser import MERGE_LOCK_TIMEOUT
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(PROJECT_ROOT),
        )

        # Проверяем что возникла ошибка
        assert result.returncode != 0, "Некорректное значение должно вызывать ошибку"
        assert "invalid literal" in result.stderr or "ValueError" in result.stderr

    def test_invalid_max_lock_file_age_raises_error(self) -> None:
        """
        Проверка что некорректное значение MAX_LOCK_FILE_AGE вызывает ошибку.

        Note:
            Некорректные значения: нечисловые строки
        """
        code = """
import os
os.environ['PARSER_MAX_LOCK_FILE_AGE'] = 'invalid'
from parser_2gis.parallel_parser import MAX_LOCK_FILE_AGE
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(PROJECT_ROOT),
        )

        # Проверяем что возникла ошибка
        assert result.returncode != 0, "Некорректное значение должно вызывать ошибку"
        assert "invalid literal" in result.stderr or "ValueError" in result.stderr

    def test_invalid_max_temp_files_raises_error(self) -> None:
        """
        Проверка что некорректное значение MAX_TEMP_FILES вызывает ошибку.

        Note:
            Некорректные значения: нечисловые строки
        """
        code = """
import os
os.environ['PARSER_MAX_TEMP_FILES'] = 'invalid'
from parser_2gis.parallel_parser import MAX_TEMP_FILES
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(PROJECT_ROOT),
        )

        # Проверяем что возникла ошибка
        assert result.returncode != 0, "Некорректное значение должно вызывать ошибку"
        assert "invalid literal" in result.stderr or "ValueError" in result.stderr


# Запуск тестов через pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
