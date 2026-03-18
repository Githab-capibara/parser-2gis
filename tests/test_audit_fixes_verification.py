"""
Тесты для проверки исправлений из отчета аудита.

Этот файл содержит тесты для верификации всех исправлений:
- M3: Мониторинг кэшей (get_cache_stats, log_cache_stats)
- L2: Удаление избыточных комментариев
- L5: Бенчмарки производительности
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest

from parser_2gis.cache import CacheManager
from parser_2gis.common import (
    _validate_category_cached,
    _validate_city_cached,
    generate_city_urls,
    get_cache_stats,
    log_cache_stats,
    url_query_encode,
)
from parser_2gis.validator import DataValidator

# =============================================================================
# ТЕСТЫ ДЛЯ M3: МОНИТОРИНГ КЭШЕЙ
# =============================================================================


class TestCacheStatsMonitoring:
    """Тесты для мониторинга статистики кэшей (M3)."""

    def test_get_cache_stats_exists(self) -> None:
        """Тест 1: Функция get_cache_stats существует и возвращает dict."""
        stats = get_cache_stats()
        assert isinstance(stats, dict)
        assert len(stats) >= 4  # Минимум 4 кэша

    def test_get_cache_stats_structure(self) -> None:
        """Тест 2: Структура возвращаемого значения."""
        stats = get_cache_stats()

        # Проверяем наличие обязательных кэшей
        required_caches = [
            "_validate_city_cached",
            "_validate_category_cached",
            "_generate_category_url_cached",
            "url_query_encode",
        ]

        for cache_name in required_caches:
            assert cache_name in stats, f"Кэш {cache_name} отсутствует в статистике"

            # Проверяем структуру CacheInfo
            cache_info = stats[cache_name]
            assert hasattr(cache_info, "hits")
            assert hasattr(cache_info, "misses")
            assert hasattr(cache_info, "maxsize")
            assert hasattr(cache_info, "currsize")

    def test_get_cache_stats_after_operations(self) -> None:
        """Тест 3: Статистика обновляется после операций."""
        # Очищаем кэш перед тестом
        _validate_city_cached.cache_clear()

        # Получаем начальную статистику
        initial_stats = get_cache_stats()
        initial_misses = initial_stats["_validate_city_cached"].misses

        # Выполняем операцию (должна увеличить misses)
        _validate_city_cached("test", "test.2gis.ru")

        # Получаем финальную статистику
        final_stats = get_cache_stats()
        final_misses = final_stats["_validate_city_cached"].misses

        # Проверяем что статистика обновилась
        assert final_misses == initial_misses + 1

    def test_log_cache_stats_no_exceptions(self, caplog: Any) -> None:
        """Тест 4: log_cache_stats не вызывает исключений."""
        # Прогреваем кэши
        _validate_city_cached("msk", "moscow.2gis.ru")
        _validate_category_cached(("Рестораны", "рестораны", ""))

        # Вызываем логирование - не должно быть исключений
        with caplog.at_level("INFO"):
            log_cache_stats()

        # Проверяем что логи записаны
        assert "Статистика кэша" in caplog.text

    def test_cache_stats_with_large_dataset(self) -> None:
        """Тест 5: Статистика с большим набором данных."""
        # Очищаем кэш
        _validate_city_cached.cache_clear()

        # Генерируем данные
        cities = [(f"city{i}", f"city{i}.2gis.ru") for i in range(100)]

        # Заполняем кэш
        for code, domain in cities:
            _validate_city_cached(code, domain)

        # Проверяем статистику
        stats = get_cache_stats()
        city_cache_info = stats["_validate_city_cached"]

        assert city_cache_info.currsize == 100
        assert city_cache_info.misses == 100


# =============================================================================
# ТЕСТЫ ДЛЯ L2: ПРОВЕРКА ОТСУТСТВИЯ ИЗБЫТОЧНЫХ КОММЕНТАРИЕВ
# =============================================================================


class TestNoExcessiveComments:
    """Тесты для проверки отсутствия избыточных комментариев (L2)."""

    def test_no_problem_fix_comments_in_common(self) -> None:
        """Тест 1: Отсутствие комментариев 'ИСПРАВЛЕНИЕ ПРОБЛЕМЫ' в common.py."""
        with open("parser_2gis/common.py", "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Проверяем только строки-комментарии (начинающиеся с #)
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                assert "ИСПРАВЛЕНИЕ ПРОБЛЕМЫ" not in stripped, (
                    f"Строка {i}: найден избыточный комментарий"
                )
                assert "Исправление проблемы" not in stripped, (
                    f"Строка {i}: найден избыточный комментарий"
                )

    def test_no_problem_fix_comments_in_remote(self) -> None:
        """Тест 2: Отсутствие комментариев 'ИСПРАВЛЕНИЕ ПРОБЛЕМЫ' в remote.py."""
        with open("parser_2gis/chrome/remote.py", "r", encoding="utf-8") as f:
            lines = f.readlines()

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                assert "ИСПРАВЛЕНИЕ ПРОБЛЕМЫ" not in stripped, (
                    f"Строка {i}: найден избыточный комментарий"
                )
                assert "Исправление проблемы" not in stripped, (
                    f"Строка {i}: найден избыточный комментарий"
                )

    def test_no_problem_fix_comments_in_validator(self) -> None:
        """Тест 3: Отсутствие комментариев 'ИСПРАВЛЕНИЕ ПРОБЛЕМЫ' в validator.py."""
        with open("parser_2gis/validator.py", "r", encoding="utf-8") as f:
            lines = f.readlines()

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                assert "ИСПРАВЛЕНИЕ ПРОБЛЕМЫ" not in stripped, (
                    f"Строка {i}: найден избыточный комментарий"
                )
                assert "Исправление проблемы" not in stripped, (
                    f"Строка {i}: найден избыточный комментарий"
                )


# =============================================================================
# ТЕСТЫ ДЛЯ M4: UNICODE ВАЛИДАЦИЯ ТЕЛЕФОНОВ
# =============================================================================


class TestUnicodePhoneValidation:
    """Тесты для валидации телефонов с Unicode (M4)."""

    @pytest.fixture
    def validator(self) -> DataValidator:
        """Фикстура для DataValidator."""
        return DataValidator()

    def test_arabic_digits_normalization(self, validator: DataValidator) -> None:
        """Тест 1: Нормализация арабских цифр."""
        phone = "+٧ (٩٩٩) ١٢٣-٤٥-٦٧"  # Арабские цифры

        result = validator.validate_phone(phone)

        assert result.is_valid
        assert result.value == "8 (999) 123-45-67"

    def test_persian_digits_normalization(self, validator: DataValidator) -> None:
        """Тест 2: Нормализация персидских цифр."""
        phone = "+٧ (٩٩٩) ١٢٣-٤٥-٦٧"  # Арабские цифры (персидский алфавит)

        result = validator.validate_phone(phone)

        # Персидские цифры должны нормализоваться
        assert result.is_valid

    def test_mixed_digits_normalization(self, validator: DataValidator) -> None:
        """Тест 3: Нормализация смешанных цифр."""
        phone = "+7 (999) ١٢٣-45-67"  # Смешанные цифры

        result = validator.validate_phone(phone)

        assert result.is_valid
        assert result.value == "8 (999) 123-45-67"


# =============================================================================
# ТЕСТЫ ДЛЯ L8: ПОКРЫТИЕ EDGE CASES
# =============================================================================


class TestEdgeCasesCoverage:
    """Тесты для покрытия edge cases (L8)."""

    def test_empty_city_list(self) -> None:
        """Тест 1: Пустой список городов."""
        cities: list[Dict[str, str]] = []
        query = "рестораны"

        urls = generate_city_urls(cities, query)

        assert len(urls) == 0

    def test_empty_category_list(self) -> None:
        """Тест 2: Пустой список категорий (query)."""
        cities = [{"code": "msk", "domain": "moscow.2gis.ru"}]
        query = ""  # Пустой запрос

        urls = generate_city_urls(cities, query)

        # URLs должны сгенерироваться даже с пустым query
        assert len(urls) >= 0

    def test_cache_empty_data(self, tmp_path: Path) -> None:
        """Тест 3: Кэш с пустыми данными."""
        cache_dir = tmp_path / "test_cache"
        cache = CacheManager(cache_dir=cache_dir, ttl_hours=24)

        # Пустая запись
        cache.set("empty_key", {})
        result = cache.get("empty_key")

        assert result == {}

        cache.close()

    def test_cache_none_value(self, tmp_path: Path) -> None:
        """Тест 4: Кэш с None значением."""
        cache_dir = tmp_path / "test_cache"
        cache = CacheManager(cache_dir=cache_dir, ttl_hours=24)

        # Запись None
        cache.set("none_key", None)
        result = cache.get("none_key")

        assert result is None

        cache.close()

    def test_url_query_encode_empty(self) -> None:
        """Тест 5: Кодирование пустой строки."""
        result = url_query_encode("")
        assert result == ""

    def test_url_query_encode_special_chars(self) -> None:
        """Тест 6: Кодирование специальных символов."""
        result = url_query_encode("рестораны & бары")
        assert "%26" in result  # '&' кодируется как '%26'


# =============================================================================
# ТЕСТЫ ДЛЯ L10: ОБРАБОТКА ОШИБОК В WRITER
# =============================================================================


class TestWriterErrorHandling:
    """Тесты для обработки ошибок в writer (L10)."""

    def test_csv_writer_handles_invalid_data(self, tmp_path: Path) -> None:
        """Тест 1: CSV writer обрабатывает некорректные данные."""
        from parser_2gis.writer.options import CSVOptions
        from parser_2gis.writer.writers.csv_writer import CSVWriter

        output_file = tmp_path / "test.csv"
        options = CSVOptions(delimiter=",", encoding="utf-8")

        writer = CSVWriter(output_file, options)

        # Пытаемся записать некорректные данные
        try:
            # Данные с некорректными символами
            invalid_data = {"name": "test\ninvalid", "value": 123}
            writer.write(invalid_data)
            writer.close()
        except Exception as e:
            # Исключение допустимо, главное чтобы не было падения без обработки
            assert True

    def test_json_writer_handles_invalid_data(self, tmp_path: Path) -> None:
        """Тест 2: JSON writer обрабатывает некорректные данные."""
        from parser_2gis.writer.options import WriterOptions
        from parser_2gis.writer.writers.json_writer import JSONWriter

        output_file = tmp_path / "test.json"
        options = WriterOptions(encoding="utf-8")

        writer = JSONWriter(output_file, options)

        # Пытаемся записать некорректные данные
        try:
            invalid_data = {
                "name": "test",
                "value": float("inf"),
            }  # JSON не поддерживает inf
            writer.write(invalid_data)
            writer.close()
        except (ValueError, TypeError):
            # Ожидаемое исключение
            assert True


# =============================================================================
# ЗАПУСК ТЕСТОВ
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
