"""
Тесты для валидации JavaScript кода.

Тестируют рефакторированную функцию _validate_js_code и её подфункции.
ИСПРАВЛЕНИЕ P0-1: Рефакторинг функции валидации JS (сложность 39 -> <10)

Файлы: parser_2gis/chrome/remote.py
"""

import os
import sys

from parser_2gis.chrome.js_executor import (
    _check_array_and_regexp,
    _check_base64_functions,
    _check_bracket_access,
    _check_concatenation_bypass,
    _check_dangerous_constructors,
    _check_dangerous_encoding,
    _check_js_length,
    _check_obfuscation_patterns,
    _check_prototype_pollution,
    _check_reflect_and_apply,
    _check_string_conversion_functions,
    _validate_js_code,
)

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestValidateJsCode:
    """Тесты для основной функции валидации JavaScript."""

    def test_validate_valid_js_code(self) -> None:
        """Тест валидации безопасного JavaScript кода."""
        valid_js = """
            document.querySelector('.organization-name');
            window.scrollTo(0, 100);
            const data = { name: 'test', value: 123 };
        """
        is_valid, _error = _validate_js_code(valid_js)
        assert is_valid is True
        # error может быть None или пустой строкой для валидного кода

    def test_validate_none_js_code(self) -> None:
        """Тест валидации None JavaScript кода."""
        is_valid, error = _validate_js_code(None)  # type: ignore
        assert is_valid is False
        assert error is not None
        assert "JavaScript код не может быть None" in error

    def test_validate_js_with_comments(self) -> None:
        """Тест валидации JavaScript с комментариями."""
        js_with_comments = """
            // Это комментарий
            var x = 10;
            /* Многострочный комментарий */
            var y = 20;
        """
        is_valid, _error = _validate_js_code(js_with_comments)
        assert is_valid is True


class TestJsLengthCheck:
    """Тесты для проверки длины JavaScript кода."""

    def test_js_length_within_limit(self) -> None:
        """Тест JavaScript кода в пределах лимита длины."""
        js_code = "var x = 10;" * 100  # ~1300 символов
        is_valid, _error = _check_js_length(js_code, max_length=10000)
        assert is_valid is True

    def test_js_length_exceeds_limit(self) -> None:
        """Тест JavaScript кода, превышающего лимит длины."""
        js_code = "var x = 10;" * 10000  # ~130000 символов
        is_valid, error = _check_js_length(js_code, max_length=10000)
        assert is_valid is False
        assert error is not None
        assert "превышает максимальную длину" in error.lower()

    def test_js_length_just_over_limit(self) -> None:
        """Тест JavaScript кода чуть выше лимита длины."""
        js_code = "x" * 1001
        is_valid, error = _check_js_length(js_code, max_length=1000)
        assert is_valid is False
        assert error is not None


class TestDangerousEncodingCheck:
    """Тесты для проверки опасных кодировок."""

    def test_no_dangerous_encoding(self) -> None:
        """Тест отсутствия опасных кодировок."""
        js_code = "var str = 'normal string';"
        is_valid, _error = _check_dangerous_encoding(js_code)
        assert is_valid is True

    def test_atob_function_detected(self) -> None:
        """Тест обнаружения функции atob (base64 decode)."""
        js_code = "var decoded = atob('SGVsbG8=');"
        is_valid, error = _check_base64_functions(js_code)
        assert is_valid is False
        assert error is not None

    def test_btoa_function_detected(self) -> None:
        """Тест обнаружения функции btoa (base64 encode)."""
        js_code = "var encoded = btoa('Hello');"
        is_valid, error = _check_base64_functions(js_code)
        assert is_valid is False
        assert error is not None


class TestBase64FunctionsCheck:
    """Тесты для проверки base64 функций."""

    def test_no_base64_functions(self) -> None:
        """Тест отсутствия base64 функций."""
        js_code = "var x = 10; console.log(x);"
        is_valid, _error = _check_base64_functions(js_code)
        assert is_valid is True

    def test_fromcharcode_detected(self) -> None:
        """Тест обнаружения String.fromCharCode."""
        js_code = "var str = String.fromCharCode(72, 101, 108, 108, 111);"
        is_valid, error = _check_string_conversion_functions(js_code)
        assert is_valid is False
        assert error is not None


class TestStringConversionFunctionsCheck:
    """Тесты для проверки функций преобразования строк."""

    def test_no_string_conversion(self) -> None:
        """Тест отсутствия функций преобразования строк."""
        js_code = "var x = 10; var y = 20;"
        is_valid, _error = _check_string_conversion_functions(js_code)
        assert is_valid is True

    def test_charcode_in_nested_function(self) -> None:
        """Тест обнаружения fromCharCode во вложенной функции."""
        js_code = "function decode() { return String.fromCharCode(65, 66, 67); }"
        is_valid, error = _check_string_conversion_functions(js_code)
        assert is_valid is False
        assert error is not None


class TestConcatenationBypassCheck:
    """Тесты для проверки обхода конкатенацией."""

    def test_no_concatenation_bypass(self) -> None:
        """Тест отсутствия обхода конкатенацией."""
        js_code = "var str = 'hello' + 'world';"
        is_valid, _error = _check_concatenation_bypass(js_code)
        assert is_valid is True

    def test_suspicious_concatenation(self) -> None:
        """Тест подозрительной конкатенации с eval."""
        js_code = "var fn = 'ev' + 'al'; window[fn]('alert(1)');"
        is_valid, error = _check_concatenation_bypass(js_code)
        assert is_valid is False
        assert error is not None


class TestObfuscationPatternsCheck:
    """Тесты для проверки паттернов обфускации."""

    def test_no_obfuscation(self) -> None:
        """Тест отсутствия обфускации."""
        js_code = "var functionName = 'clear';"
        is_valid, _error = _check_obfuscation_patterns(js_code)
        assert is_valid is True

    def test_hex_escape_detected(self) -> None:
        """Тест обнаружения split().reverse().join() обфускации."""
        js_code = 'str.split("").reverse().join("");' + "x" * 100
        is_valid, error = _check_obfuscation_patterns(js_code)
        assert is_valid is False
        assert error is not None


class TestPrototypePollutionCheck:
    """Тесты для проверки prototype pollution."""

    def test_no_prototype_pollution(self) -> None:
        """Тест отсутствия prototype pollution."""
        js_code = "var obj = { name: 'test' };"
        is_valid, _error = _check_prototype_pollution(js_code)
        assert is_valid is True

    def test_proto_detected(self) -> None:
        """Тест обнаружения Object.prototype.constructor."""
        js_code = "Object.prototype.constructor.polluted = true;"
        is_valid, error = _check_prototype_pollution(js_code)
        assert is_valid is False
        assert error is not None

    def test_constructor_detected(self) -> None:
        """Тест обнаружения constructor.constructor."""
        js_code = "constructor.constructor.prototype.polluted = true;"
        is_valid, error = _check_prototype_pollution(js_code)
        assert is_valid is False
        assert error is not None


class TestDangerousConstructorsCheck:
    """Тесты для проверки опасных конструкторов."""

    def test_no_dangerous_constructors(self) -> None:
        """Тест отсутствия опасных конструкторов."""
        js_code = "var obj = new Object(); var arr = new Array();"
        is_valid, _error = _check_dangerous_constructors(js_code)
        assert is_valid is True

    def test_function_constructor_detected(self) -> None:
        """Тест обнаружения Function constructor."""
        js_code = "var fn = new Function('alert(1)');"
        is_valid, error = _check_dangerous_constructors(js_code)
        assert is_valid is False
        assert error is not None

    def test_eval_detected(self) -> None:
        """Тест обнаружения eval."""
        js_code = "eval('alert(1)');"
        is_valid, error = _check_dangerous_constructors(js_code)
        assert is_valid is False
        assert error is not None


class TestBracketAccessCheck:
    """Тесты для проверки доступа через скобки."""

    def test_no_suspicious_bracket_access(self) -> None:
        """Тест отсутствия подозрительного доступа через скобки."""
        js_code = "var value = obj['key'];"
        is_valid, _error = _check_bracket_access(js_code)
        assert is_valid is True

    def test_window_bracket_access_detected(self) -> None:
        """Тест обнаружения window['functionName']."""
        js_code = "window['eval']('alert(1)');"
        is_valid, error = _check_bracket_access(js_code)
        assert is_valid is False
        assert error is not None


class TestReflectAndApplyCheck:
    """Тесты для проверки Reflect и apply."""

    def test_no_reflect_apply(self) -> None:
        """Тест отсутствия Reflect и apply."""
        js_code = "var result = obj.method();"
        is_valid, _error = _check_reflect_and_apply(js_code)
        assert is_valid is True

    def test_reflect_detected(self) -> None:
        """Тест обнаружения Reflect."""
        js_code = "Reflect.get(obj, 'property');"
        is_valid, error = _check_reflect_and_apply(js_code)
        assert is_valid is False
        assert error is not None

    def test_apply_detected(self) -> None:
        """Тест обнаружения apply с eval."""
        js_code = "fn.apply(null, [eval(code)]);"
        is_valid, error = _check_reflect_and_apply(js_code)
        assert is_valid is False
        assert error is not None


class TestArrayAndRegexpCheck:
    """Тесты для проверки Array.from и RegExp."""

    def test_no_array_regexp(self) -> None:
        """Тест отсутствия Array.from и RegExp."""
        js_code = "var arr = [1, 2, 3]; var regex = /test/;"
        is_valid, _error = _check_array_and_regexp(js_code)
        assert is_valid is True

    def test_array_from_detected(self) -> None:
        """Тест обнаружения Array.from."""
        js_code = "var arr = Array.from('hello');"
        is_valid, error = _check_array_and_regexp(js_code)
        assert is_valid is False
        assert error is not None

    def test_regexp_constructor_detected(self) -> None:
        """Тест обнаружения RegExp constructor с eval."""
        js_code = "var regex = new RegExp('eval(\"alert(1)\")', 'i');"
        is_valid, error = _check_array_and_regexp(js_code)
        assert is_valid is False
        assert error is not None


class TestValidateJsCodeIntegration:
    """Интеграционные тесты для валидации JavaScript."""

    def test_validate_complex_safe_js(self) -> None:
        """Тест валидации сложного безопасного JavaScript."""
        complex_js = """
            (function() {
                var elements = document.querySelectorAll('.organization');
                elements.forEach(function(element) {
                    var name = element.querySelector('.name');
                    if (name) {
                        console.log(name.textContent);
                    }
                });
                return 'done';
            })();
        """
        is_valid, _error = _validate_js_code(complex_js)
        assert is_valid is True

    def test_validate_malicious_js(self) -> None:
        """Тест валидации вредоносного JavaScript."""
        malicious_js = """
            var fn = 'ev' + 'al';
            window[fn]('alert(1)');
            Object.prototype.constructor.polluted = true;
        """
        is_valid, error = _validate_js_code(malicious_js)
        assert is_valid is False
        assert error is not None

    def test_validate_obfuscated_js(self) -> None:
        """Тест валидации обфусцированного JavaScript."""
        obfuscated_js = """
            var _0x1234 = '\\x61\\x6c\\x65\\x72\\x74';
            var fn = String.fromCharCode(101, 118, 97, 108);
            eval(_0x1234);
        """
        is_valid, error = _validate_js_code(obfuscated_js)
        assert is_valid is False
        assert error is not None
