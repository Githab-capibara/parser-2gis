#!/usr/bin/env python3
"""
Тесты для проверки валидации max_workers в параллельном парсере.

Этот модуль тестирует корректность валидации параметра max_workers:
1. Что max_workers=40 работает (ранее вызывало ошибку при лимите 15)
2. Что ENV переменная PARSER_MAX_WORKERS работает для переопределения лимита
3. Что превышение лимита в 100 (максимальное значение) вызывает ошибку
4. Что значения меньше 1 вызывают ошибку
5. Что некорректное значение ENV переменной (не число) вызывает ошибку
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

import pytest


def check_constant_value(const_name: str, expected_value: int) -> bool:
    """
    Проверяет значение константы в отдельном процессе.

    Args:
        const_name: Имя константы для проверки.
        expected_value: Ожидаемое значение константы.

    Returns:
        bool: True если значение совпадает с ожидаемым.
    """
    code = f"""
from parser_2gis.constants import {const_name}
print({const_name})
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(Path(__file__).parent.parent),
    )

    if result.returncode != 0:
        return False

    try:
        actual_value = int(result.stdout.strip())
        return actual_value == expected_value
    except ValueError:
        return False


@pytest.fixture
def sample_cities() -> list[Dict[str, str]]:
    """Фикстура для примера списка городов."""
    return [{"name": "Москва", "url": "https://2gis.ru/moscow", "code": "moscow"}]


@pytest.fixture
def sample_categories() -> list[Dict[str, Any]]:
    """Фикстура для примера списка категорий."""
    return [{"name": "Кафе", "query": "Кафе", "rubric_code": "161"}]


@pytest.fixture
def sample_config() -> Any:
    """Фикстура для примера конфигурации."""
    from parser_2gis.config import Configuration

    return Configuration()


class TestMaxWorkersBasicValidation:
    """Тесты базовой валидации параметра max_workers."""

    def test_max_workers_40_works(
        self, tmp_path: Any, sample_cities: list, sample_categories: list, sample_config: Any
    ) -> None:
        """
        Тест 1: Проверка что max_workers=40 работает корректно.

        ИСТОРИЯ: Ранее max_workers был ограничен значением 15,
        что не позволяло использовать высокую степень параллелизма.
        Теперь лимит увеличен до 100 для поддержки 40+ параллельных браузеров.
        """
        from parser_2gis.parallel import ParallelCityParser

        output_dir = str(tmp_path / "output")

        # Создаём парсер с max_workers=40
        parser = ParallelCityParser(
            cities=sample_cities,
            categories=sample_categories,
            output_dir=output_dir,
            config=sample_config,
            max_workers=40,
        )

        # Проверяем что парсер создан с правильным значением
        assert parser is not None
        assert parser.max_workers == 40, "max_workers должен быть равен 40"

    def test_max_workers_50_works(
        self, tmp_path: Any, sample_cities: list, sample_categories: list, sample_config: Any
    ) -> None:
        """Проверка что max_workers=50 (значение по умолчанию) работает."""
        from parser_2gis.parallel import ParallelCityParser

        output_dir = str(tmp_path / "output")

        parser = ParallelCityParser(
            cities=sample_cities,
            categories=sample_categories,
            output_dir=output_dir,
            config=sample_config,
            max_workers=50,
        )

        assert parser.max_workers == 50

    def test_max_workers_1_works(
        self, tmp_path: Any, sample_cities: list, sample_categories: list, sample_config: Any
    ) -> None:
        """Проверка что max_workers=1 (минимальное значение) работает."""
        from parser_2gis.parallel import ParallelCityParser

        output_dir = str(tmp_path / "output")

        parser = ParallelCityParser(
            cities=sample_cities,
            categories=sample_categories,
            output_dir=output_dir,
            config=sample_config,
            max_workers=1,
        )

        assert parser.max_workers == 1


class TestMaxWorkersLimitExceeded:
    """Тесты превышения максимального лимита max_workers."""

    def test_max_workers_101_raises_error(
        self, tmp_path: Any, sample_cities: list, sample_categories: list, sample_config: Any
    ) -> None:
        """
        Тест 3: Проверка что max_workers=101 вызывает ошибку.

        Максимальное допустимое значение: 50 (по умолчанию).
        Значения больше 50 вызывают ValueError.
        """
        from parser_2gis.parallel import ParallelCityParser

        output_dir = str(tmp_path / "output")

        with pytest.raises(ValueError) as exc_info:
            ParallelCityParser(
                cities=sample_cities,
                categories=sample_categories,
                output_dir=output_dir,
                config=sample_config,
                max_workers=101,
            )

        assert "max_workers слишком большой" in str(exc_info.value)
        assert "101" in str(exc_info.value)
        assert "50" in str(exc_info.value)

    def test_max_workers_150_raises_error(
        self, tmp_path: Any, sample_cities: list, sample_categories: list, sample_config: Any
    ) -> None:
        """Проверка что max_workers=150 вызывает ошибку."""
        from parser_2gis.parallel import ParallelCityParser

        output_dir = str(tmp_path / "output")

        with pytest.raises(ValueError) as exc_info:
            ParallelCityParser(
                cities=sample_cities,
                categories=sample_categories,
                output_dir=output_dir,
                config=sample_config,
                max_workers=150,
            )

        assert "max_workers слишком большой" in str(exc_info.value)

    def test_max_workers_1000_raises_error(
        self, tmp_path: Any, sample_cities: list, sample_categories: list, sample_config: Any
    ) -> None:
        """Проверка что max_workers=1000 вызывает ошибку."""
        from parser_2gis.parallel import ParallelCityParser

        output_dir = str(tmp_path / "output")

        with pytest.raises(ValueError) as exc_info:
            ParallelCityParser(
                cities=sample_cities,
                categories=sample_categories,
                output_dir=output_dir,
                config=sample_config,
                max_workers=1000,
            )

        assert "max_workers слишком большой" in str(exc_info.value)


class TestMaxWorkersBelowMinimum:
    """Тесты значений max_workers меньше минимального."""

    def test_max_workers_0_raises_error(
        self, tmp_path: Any, sample_cities: list, sample_categories: list, sample_config: Any
    ) -> None:
        """
        Тест 4: Проверка что max_workers=0 вызывает ошибку.

        Минимальное допустимое значение: 1.
        """
        from parser_2gis.parallel import ParallelCityParser

        output_dir = str(tmp_path / "output")

        with pytest.raises(ValueError) as exc_info:
            ParallelCityParser(
                cities=sample_cities,
                categories=sample_categories,
                output_dir=output_dir,
                config=sample_config,
                max_workers=0,
            )

        assert "max_workers должен быть не менее" in str(exc_info.value)
        assert "1" in str(exc_info.value)

    def test_max_workers_negative_raises_error(
        self, tmp_path: Any, sample_cities: list, sample_categories: list, sample_config: Any
    ) -> None:
        """Проверка что отрицательный max_workers вызывает ошибку."""
        from parser_2gis.parallel import ParallelCityParser

        output_dir = str(tmp_path / "output")

        with pytest.raises(ValueError) as exc_info:
            ParallelCityParser(
                cities=sample_cities,
                categories=sample_categories,
                output_dir=output_dir,
                config=sample_config,
                max_workers=-5,
            )

        assert "max_workers должен быть не менее" in str(exc_info.value)


class TestMaxWorkersEnvVariable:
    """Тесты переменной окружения PARSER_MAX_WORKERS."""

    def test_env_max_workers_40(self) -> None:
        """
        Тест 2: Проверка что ENV переменная PARSER_MAX_WORKERS=40 работает.
        """
        code = """
import os
os.environ['PARSER_MAX_WORKERS'] = '40'
from parser_2gis.constants.env_config import get_env_config
config = get_env_config()
print(config.max_workers)
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(Path(__file__).parent.parent),
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert result.stdout.strip() == "40", "PARSER_MAX_WORKERS=40 должно читаться корректно"

    def test_env_max_workers_80(self) -> None:
        """Проверка что ENV переменная PARSER_MAX_WORKERS=80 работает."""
        code = """
import os
os.environ['PARSER_MAX_WORKERS'] = '80'
from parser_2gis.constants.env_config import get_env_config
config = get_env_config()
print(config.max_workers)
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(Path(__file__).parent.parent),
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert result.stdout.strip() == "80", "PARSER_MAX_WORKERS=80 должно читаться корректно"

    def test_env_max_workers_100(self) -> None:
        """Проверка что ENV переменная PARSER_MAX_WORKERS=100 работает."""
        code = """
import os
os.environ['PARSER_MAX_WORKERS'] = '100'
from parser_2gis.constants.env_config import get_env_config
config = get_env_config()
print(config.max_workers)
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(Path(__file__).parent.parent),
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert result.stdout.strip() == "100", "PARSER_MAX_WORKERS=100 должно читаться корректно"

    def test_env_max_workers_default_50(self) -> None:
        """
        Проверка значения по умолчанию MAX_WORKERS=50.
        """
        if "PARSER_MAX_WORKERS" in os.environ:
            del os.environ["PARSER_MAX_WORKERS"]

        code = """
import os
if 'PARSER_MAX_WORKERS' in os.environ:
    del os.environ['PARSER_MAX_WORKERS']
from parser_2gis.constants.env_config import get_env_config
config = get_env_config()
print(config.max_workers)
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(Path(__file__).parent.parent),
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert result.stdout.strip() == "50", "MAX_WORKERS по умолчанию должно быть 50"


class TestMaxWorkersEnvInvalidValues:
    """Тесты некорректных значений ENV переменной PARSER_MAX_WORKERS."""

    def test_env_max_workers_invalid_string(self) -> None:
        """
        Тест 5: Проверка что некорректное значение ENV (не число) вызывает ошибку.
        """
        code = """
import os
os.environ['PARSER_MAX_WORKERS'] = 'invalid'
from parser_2gis.constants.env_config import get_env_config
config = get_env_config()
print(config.max_workers)
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(Path(__file__).parent.parent),
        )

        # При некорректном значении должен быть ненулевой код возврата
        assert result.returncode != 0, "Некорректное значение должно вызывать ошибку"

    def test_env_max_workers_float_string(self) -> None:
        """Проверка что строка с float значением вызывает ошибку."""
        code = """
import os
os.environ['PARSER_MAX_WORKERS'] = '40.5'
from parser_2gis.constants.env_config import get_env_config
config = get_env_config()
print(config.max_workers)
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(Path(__file__).parent.parent),
        )

        # При некорректном значении должен быть ненулевой код возврата
        assert result.returncode != 0, "Строка с float должна вызывать ошибку"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
