"""Модуль выполнения и валидации JavaScript кода.

Предоставляет функции для безопасной валидации и выполнения JavaScript:
- _validate_js_code - Валидация JS кода на безопасность
- _sanitize_js_string - Санитизация строк для JS
- Функции проверок безопасности (_check_*)
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable

from parser_2gis.logger.logger import logger as app_logger

from .constants import MAX_JS_CODE_LENGTH

# =============================================================================
# КОНФИГУРАЦИЯ ПРОВЕРОК БЕЗОПАСНОСТИ JS КОДА
# =============================================================================

# Опасные конкатенации для проверки на обход фильтров
_DANGEROUS_CONCAT_LIST = [
    "eval",
    "function",
    "settimeout",
    "setinterval",
    "fromcharcode",
    "newfunction",
    "document",
    "window",
    "prototype",
    "constructor",
    "__proto__",
]

# Максимальное соотношение escape-последовательностей для обфускации
_MAX_ESCAPE_RATIO = 0.3

# Максимальное соотношение специальных символов для обфускации
_MAX_SPECIAL_CHARS_RATIO = 0.7

# Минимальная длина кода для проверок обфускации
_MIN_CODE_LENGTH_FOR_OBFUSCATION_CHECK = 100


# =============================================================================
# СКОМПИЛИРОВАННЫЕ REGEX ПАТТЕРНЫ
# =============================================================================

# ISSUE-053: Переименовано из _DANGEROUS_JS_PATTERNS в DANGEROUS_JS_PATTERNS
# Оптимизация: скомпилированные паттерны вместо компиляции при каждом вызове
DANGEROUS_JS_PATTERNS = [
    (re.compile(r"\beval\s*\("), "eval() запрещён"),
    (re.compile(r"(?<![\w])Function\s*\("), "конструктор Function запрещён"),
    (re.compile(r"\bsetTimeout\s*\([^,]*,\s*[\"']"), "setTimeout с строковым кодом запрещён"),
    (re.compile(r"\bsetInterval\s*\([^,]*,\s*[\"']"), "setInterval с строковым кодом запрещён"),
    (re.compile(r"\bdocument\.write\s*\("), "document.write() запрещён"),
    (re.compile(r"\.innerHTML\s*="), "прямая установка innerHTML запрещена"),
    (re.compile(r"\.outerHTML\s*="), "прямая установка outerHTML запрещена"),
    (
        re.compile(r"document\s*\.\s*createElement\s*\(\s*[\"']script[\"']"),
        "создание script элемента запрещено",
    ),
    (re.compile(r"\bimport\s*\("), "динамический import запрещён"),
    (re.compile(r"\bWebSocket\s*\("), "WebSocket соединение запрещено"),
    (re.compile(r"\bfetch\s*\([^)]*\)\s*\.then"), "fetch с обработкой .then() запрещён"),
    (re.compile(r"\bfetch\s*\([^)]*\)\s*\.catch"), "fetch с обработкой .catch() запрещён"),
    (re.compile(r"\bXMLHttpRequest\s*\("), "XMLHttpRequest запрещён"),
    (re.compile(r"\.src\s*=\s*[\"']http"), "установка src с http запрещена"),
    # Дополнительные паттерны для обнаружения обфускации
    (re.compile(r"\[\s*[\"']eval[\"']\s*\]"), "обфускация eval через массив"),
    (re.compile(r"window\s*\[\s*[\"']eval[\"']\s*\]"), "доступ к eval через window[]"),
    (re.compile(r"this\s*\[\s*[\"']eval[\"']\s*\]"), "доступ к eval через this[]"),
    (re.compile(r"global\s*\[\s*[\"']eval[\"']\s*\]"), "доступ к eval через global[]"),
    (re.compile(r"self\s*\[\s*[\"']eval[\"']\s*\]"), "доступ к eval через self[]"),
]


# =============================================================================
# ФУНКЦИИ ПРОВЕРКИ JS КОДА (ТАБЛИЧНО-ОРИЕНТИРОВАННЫЙ ПОДХОД)
# =============================================================================


def _check_js_length(code: str, max_length: int) -> tuple[bool, str | None]:
    """Проверяет длину JavaScript кода.

    Args:
        code: JavaScript код для проверки.
        max_length: Максимальная допустимая длина.

    Returns:
        Кортеж (is_valid, error_message):
        - is_valid: True если длина в норме, False иначе
        - error_message: Сообщение об ошибке или None

    """
    if len(code) > max_length:
        return (
            False,
            f"JavaScript код превышает максимальную длину ({len(code)} > {max_length} символов)",
        )
    return True, None


# ISSUE-003-#14: Скомпилированные паттерны для проверки опасных кодировок
# Вынесены на уровень модуля для компиляции один раз
_ENCODING_CHECK_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"\\u00[0-9a-fA-F]{2}", re.IGNORECASE),
        "Обнаружена попытка обхода через Unicode кодировку",
    ),
    (
        re.compile(r"\\u\{[0-9a-fA-F]+\}", re.IGNORECASE),
        "Обнаружена попытка обхода через расширенную Unicode кодировку",
    ),
    (
        re.compile(r"&#x[0-9a-fA-F]+;|&#\d+;", re.IGNORECASE),
        "Обнаружена попытка обхода через HTML entity кодировку",
    ),
    (re.compile(r"\\0[0-7]{2,3}"), "Обнаружена попытка обхода через Octal кодировку"),
    (
        re.compile(r"\\x[0-9a-fA-F]{2}", re.IGNORECASE),
        "Обнаружена попытка обхода через Hex кодировку",
    ),
]


def _check_dangerous_encoding(code: str) -> tuple[bool, str | None]:
    """Проверяет код на опасные кодировки (Unicode, HTML entities, octal, hex).

    ISSUE-003-#14: Использует скомпилированные паттерны для снижения
    сложности с O(n*k) до O(n).

    Args:
        code: JavaScript код для проверки.

    Returns:
        Кортеж (is_valid, error_message):
        - is_valid: True если кодировки безопасны, False иначе
        - error_message: Сообщение об ошибке или None

    """
    for pattern, message in _ENCODING_CHECK_PATTERNS:
        if pattern.search(code):
            return False, message

    return True, None


def _check_base64_functions(code: str) -> tuple[bool, str | None]:
    """Проверяет код на использование base64 функций (atob, btoa, Buffer.from).

    Args:
        code: JavaScript код для проверки.

    Returns:
        Кортеж (is_valid, error_message):
        - is_valid: True если base64 функции отсутствуют, False иначе
        - error_message: Сообщение об ошибке или None

    """
    # atob() - декодирование base64
    if re.search(r"\batob\s*\(\s*[^)]+\)", code, re.IGNORECASE):
        return False, "Функция atob() запрещена (может скрывать опасный код)"

    # btoa() - кодирование в base64
    if re.search(r"\bbtoa\s*\(\s*[^)]+\)", code, re.IGNORECASE):
        return False, "Функция btoa() запрещена (может скрывать опасный код)"

    # Проверка на Buffer.from с base64
    if re.search(r'Buffer\s*\.\s*from\s*\([^,]+,\s*["\']base64["\']', code, re.IGNORECASE):
        return False, "Buffer.from с base64 запрещён (может скрывать опасный код)"

    return True, None


def _check_string_conversion_functions(code: str) -> tuple[bool, str | None]:
    """Проверяет код на использование String.fromCharCode и аналогов.

    Args:
        code: JavaScript код для проверки.

    Returns:
        Кортеж (is_valid, error_message):
        - is_valid: True если функции отсутствуют, False иначе
        - error_message: Сообщение об ошибке или None

    """
    if re.search(r"String\s*\.\s*fromCharCode\s*\(", code, re.IGNORECASE):
        return False, "String.fromCharCode() запрещён (может использоваться для обхода)"

    if re.search(r"String\s*\.\s*fromCodePoint\s*\(", code, re.IGNORECASE):
        return False, "String.fromCodePoint() запрещён (может использоваться для обхода)"

    if re.search(r"Character\s*\.\s*fromCharCode\s*\(", code, re.IGNORECASE):
        return False, "Character.fromCharCode() запрещён (может использоваться для обхода)"

    return True, None


def _check_concatenation_bypass(code: str) -> tuple[bool, str | None]:
    """Проверяет код на конкатенацию строк для обхода фильтров.

    Args:
        code: JavaScript код для проверки.

    Returns:
        Кортеж (is_valid, error_message):
        - is_valid: True если конкатенация безопасна, False иначе
        - error_message: Сообщение об ошибке или None

    """
    if "+" not in code or ('"' not in code and "'" not in code):
        return True, None

    # ИСПРАВЛЕНИЕ: Проверяем именно подозрительные паттерны конкатенации,
    # а не просто наличие слов в коде.
    # Паттерн: строка + строка, где при соединении получается опасное слово
    for dangerous in _DANGEROUS_CONCAT_LIST:
        # Строим паттерн для поиска разбитого опасного слова
        # Например: "ev" + "al" или 'func' + 'tion'
        dangerous_pattern = r'["\']([^"\']*)["\']\s*\+\s*["\']([^"\']*)["\']'
        matches = re.findall(dangerous_pattern, code, re.IGNORECASE)

        for match in matches:
            # Проверяем, образует ли конкатенация опасное слово
            concatenated = "".join(match).lower()
            # Дополнительная проверка: это действительно обход или легитимный код?
            # Если опасное слово не является полным словом в конкатенации - пропускаем
            if dangerous in concatenated and (
                concatenated == dangerous or dangerous in concatenated.split(dangerous)
            ):
                return False, f"Обнаружена подозрительная конкатенация строк с {dangerous}"

    # Дополнительная проверка на конкатенацию с array join
    if re.search(r'\[\s*["\'][^"\']*["\']\s*\]\s*\.\s*join\s*\(', code, re.IGNORECASE):
        return False, "Обнаружена подозрительная конкатенация через array.join()"

    return True, None


def _check_obfuscation_patterns(code: str) -> tuple[bool, str | None]:
    """Проверяет код на паттерны обфускации.

    Args:
        code: JavaScript код для проверки.

    Returns:
        Кортеж (is_valid, error_message):
        - is_valid: True если обфускация отсутствует, False иначе
        - error_message: Сообщение об ошибке или None

    """
    # Проверка на split('').reverse().join() - техника обфускации
    if re.search(
        r'split\s*\(\s*["\"]["\"]\s*\)\s*\.reverse\s*\(\)\s*\.join\s*\(', code, re.IGNORECASE,
    ):
        return False, "Обнаружена обфускация через split().reverse().join()"

    # Проверка на обфускацию через множественные escape-последовательности
    escape_count = len(re.findall(r"\\[uUxX0-9]", code))
    if (
        len(code) > _MIN_CODE_LENGTH_FOR_OBFUSCATION_CHECK
        and escape_count / len(code) > _MAX_ESCAPE_RATIO
    ):
        return (
            False,
            "Обнаружена подозрительная обфускация кода (множественные escape-последовательности)",
        )

    # Проверка на чрезмерное использование специальных символов
    special_chars = re.findall(r'[^a-zA-Z0-9\s_$.(){}[\],;:\'"`=+\-*/<>!&|]', code)
    if (
        len(code) > _MIN_CODE_LENGTH_FOR_OBFUSCATION_CHECK
        and len(special_chars) / len(code) > _MAX_SPECIAL_CHARS_RATIO
    ):
        return (
            False,
            "Обнаружена подозрительная обфускация кода "
            "(чрезмерное использование специальных символов)",
        )

    # Проверка на подозрительные переменные с именами типа _0x1234
    if re.search(r"var\s+_[0-9a-fA-F]{4,}\s*=", code) or re.search(
        r"let\s+_[0-9a-fA-F]{4,}\s*=", code,
    ):
        return False, "Обнаружена обфускация кода (подозрительные имена переменных)"

    return True, None


def _check_prototype_pollution(code: str) -> tuple[bool, str | None]:
    """Проверяет код на попытки prototype pollution.

    Args:
        code: JavaScript код для проверки.

    Returns:
        Кортеж (is_valid, error_message):
        - is_valid: True если prototype pollution отсутствует, False иначе
        - error_message: Сообщение об ошибке или None

    """
    # Проверка на использование Object.prototype.constructor
    if re.search(r"Object\s*\.\s*prototype\s*\.\s*constructor", code, re.IGNORECASE):
        return False, "Object.prototype.constructor запрещён (попытка обхода)"

    # Проверка на использование constructor.constructor
    if re.search(r"constructor\s*\.\s*constructor", code, re.IGNORECASE):
        return False, "constructor.constructor запрещён (попытка обхода)"

    return True, None


def _check_dangerous_constructors(code: str) -> tuple[bool, str | None]:
    """Проверяет код на опасные конструкторы (new Function, eval).

    Args:
        code: JavaScript код для проверки.

    Returns:
        Кортеж (is_valid, error_message):
        - is_valid: True если конструкторы безопасны, False иначе
        - error_message: Сообщение об ошибке или None

    """
    # Проверяем на eval()
    if re.search(r"\beval\s*\(", code, re.IGNORECASE):
        return False, "Функция eval() запрещена"

    # Проверяем на new Function()
    if re.search(r"new\s+Function\s*\(", code, re.IGNORECASE):
        return False, "Конструктор 'new Function()' запрещён"

    # Проверяем на присваивание eval переменной
    if re.search(r"\b\s*\w+\s*=\s*eval\s*;", code):
        return False, "Присваивание eval переменной запрещено (попытка обхода)"

    # Проверка на присваивание Function переменной
    if re.search(r"\b\s*\w+\s*=\s*Function\s*;", code):
        return False, "Присваивание Function переменной запрещено (попытка обхода)"

    return True, None


def _check_bracket_access(code: str) -> tuple[bool, str | None]:
    """Проверяет код на доступ через квадратные скобки (eval["..."]).

    Args:
        code: JavaScript код для проверки.

    Returns:
        Кортеж (is_valid, error_message):
        - is_valid: True если доступ безопасен, False иначе
        - error_message: Сообщение об ошибке или None

    """
    # Проверка на доступ к eval через квадратные скобки
    if re.search(r'\beval\s*\[\s*["\'][a-zA-Z]+["\']\s*\]', code):
        return False, "Доступ к eval через квадратные скобки запрещён"

    # Проверка на доступ к Function через квадратные скобки
    if re.search(r'\bFunction\s*\[\s*["\'][a-zA-Z]+["\']\s*\]', code):
        return False, "Доступ к Function через квадратные скобки запрещён"

    # Проверка на window['eval'] и window['Function']
    if re.search(r"window\s*\[\s*['\"](?:eval|Function)['\"]\s*\]", code, re.IGNORECASE):
        return False, "Доступ window['eval'] или window['Function'] запрещён"

    return True, None


def _check_reflect_and_apply(code: str) -> tuple[bool, str | None]:
    """Проверяет код на Reflect/apply/call с умной проверкой.

    Блокирует только подозрительные случаи:
    1. Reflect.* (любой доступ к Reflect)
    2. apply/call с eval/Function (попытка выполнения кода)
    3. apply/call в контексте обхода проверок

    Args:
        code: JavaScript код для проверки.

    Returns:
        Кортеж (is_valid, error_message)

    """
    # Проверка на использование Reflect - блокируем всё
    if re.search(r"Reflect\s*\.", code, re.IGNORECASE):
        return False, "Reflect запрещён (может использоваться для обхода)"

    # Проверка на apply/call ТОЛЬКО в подозрительных контекстах
    # 1. apply/call с eval или Function
    if re.search(r"\.\s*(?:apply|call)\s*\([^)]*(?:eval|Function)[^)]*\)", code, re.IGNORECASE):
        return False, "apply/call с eval/Function запрещён"

    # 2. apply/call для выполнения кода через Function.prototype
    if re.search(r"Function\s*\.\s*prototype\s*\.\s*(?:apply|call)", code, re.IGNORECASE):
        return False, "Function.prototype.apply/call запрещён"

    # 3. apply/call с аргументами, которые могут быть кодом
    # Проверяем, содержит ли массив строки с кодом
    if re.search(
        r"\.\s*(?:apply|call)\s*\(\s*this\s*,\s*\[\s*['\"]", code, re.IGNORECASE,
    ) and re.search(r"\.\s*(?:apply|call)\s*\(\s*this\s*,\s*\[", code, re.IGNORECASE):
        return False, "apply/call с строковыми аргументами запрещён"

    return True, None


def _check_array_and_regexp(code: str) -> tuple[bool, str | None]:
    """Проверяет код на Array.from и RegExp с eval/Function.

    Args:
        code: JavaScript код для проверки.

    Returns:
        Кортеж (is_valid, error_message):
        - is_valid: True если функции безопасны, False иначе
        - error_message: Сообщение об ошибке или None

    """
    # Проверка на Array.from с подозрительными аргументами
    if re.search(r'Array\s*\.\s*from\s*\(\s*["\'][^"\']*["\']', code, re.IGNORECASE):
        return False, "Array.from со строкой запрещён (может использоваться для обхода)"

    # Проверка на скомпилированный RegExp с eval/Function
    if re.search(r"new\s+RegExp\s*\([^)]*(?:eval|Function)[^)]*\)", code, re.IGNORECASE):
        return False, "RegExp с eval/Function запрещён (попытка обхода)"

    return True, None


# Таблица проверок безопасности JS кода
_JS_SECURITY_CHECKS: list[tuple[Callable[[str], tuple[bool, str | None]], str]] = [
    (_check_dangerous_encoding, "Обнаружены опасные кодировки"),
    (_check_base64_functions, "Обнаружены base64 функции"),
    (_check_string_conversion_functions, "Обнаружены функции конвертации строк"),
    (_check_concatenation_bypass, "Обнаружен обход через конкатенацию"),
    (_check_obfuscation_patterns, "Обнаружены паттерны обфускации"),
    (_check_prototype_pollution, "Обнаружена попытка prototype pollution"),
    (_check_dangerous_constructors, "Обнаружены опасные конструкторы"),
    (_check_bracket_access, "Обнаружен доступ через квадратные скобки"),
    (_check_reflect_and_apply, "Обнаружены Reflect/apply/call"),
    (_check_array_and_regexp, "Обнаружены Array.from/RegExp"),
]


def _validate_js_code(code: str, max_length: int = MAX_JS_CODE_LENGTH) -> tuple[bool, str]:
    """Валидирует JavaScript код на безопасность.

    Использует таблично-ориентированный подход для проверок безопасности.
    Каждая проверка выделена в отдельную функцию для снижения сложности.

    Args:
        code: JavaScript код для валидации.
        max_length: Максимальная допустимая длина кода.

    Returns:
        Кортеж (is_valid, error_message):
        - is_valid: True если код безопасен, False иначе
        - error_message: Сообщение об ошибке или пустая строка

    Примечание:
        Проверки включают:
        - Проверка на None и пустую строку
        - Проверка максимальной длины
        - Проверка типа данных
        - Таблица проверок безопасности (10 функций)
        - Проверка на опасные паттерны из DANGEROUS_JS_PATTERNS
        - Нормализация Unicode (NFKC) для предотвращения обходов через Unicode эскейпы

    """
    if code is None:
        return False, "JavaScript код не может быть None"

    # Проверка типа
    if not isinstance(code, str):
        return (False, f"JavaScript код должен быть строкой, получен {type(code).__name__}")

    # ИСПРАВЛЕНИЕ 5: Нормализуем Unicode для предотвращения обходов через Unicode эскейпы
    # Только NFKC нормализация — безопасное преобразование без изменения легитимного кода
    normalized_code = unicodedata.normalize("NFKC", code)

    # ISSUE-003-#8: Убрано unicode_escape декодирование, так как оно может
    # изменить легитимный JavaScript код (например, строки с \n, \t внутри).
    # Обнаружение обходов через Unicode-эскейпы выполняется в _check_dangerous_encoding
    # через regex-паттерны (\uXXXX, \xXX, octal и т.д.)

    # Проверка на None и пустую строку после нормализации
    if not normalized_code:
        return False, "JavaScript код не может быть пустым"

    # Проверка типа после нормализации
    if not isinstance(normalized_code, str):
        return (
            False,
            f"JavaScript код должен быть строкой, получен {type(normalized_code).__name__}",
        )

    # Проверка на пустую строку
    if not normalized_code.strip():
        return False, "JavaScript код не может быть пустым"

    # D016: Дополнительная проверка на base64 кодировки для обхода фильтров
    # Обнаруживает длинные последовательности base64-символов (50+ символов),
    # которые могут использоваться для сокрытия вредоносного JavaScript-кода
    # путём кодирования в base64 и последующего декодирования через atob().

    # Проверка на потенциальные base64 строки (длинные последовательности base64 символов)
    base64_pattern = re.compile(r"[A-Za-z0-9+/]{50,}={0,2}")
    # Проверяем не является ли это легитимными данными (например, image data)
    if base64_pattern.search(normalized_code) and (
        "atob" in normalized_code.lower() or "btoa" in normalized_code.lower()
    ):
        return False, "Обнаружено использование base64 с функциями atob/btoa"

    # Проверка максимальной длины
    is_length_valid, length_error = _check_js_length(normalized_code, max_length)
    if not is_length_valid:
        return False, length_error or ""

    # Выполняем все проверки безопасности из таблицы
    for check_func, error_prefix in _JS_SECURITY_CHECKS:
        is_valid, error = check_func(normalized_code)
        if not is_valid:
            return False, error or error_prefix

    # Проверка на опасные паттерны с использованием скомпилированных regex
    for pattern, description in DANGEROUS_JS_PATTERNS:
        if pattern.search(normalized_code):
            return False, f"Обнаружен опасный паттерн в JavaScript коде: {description}"

    # Проверяем на попытки использования setTimeout/setInterval с функцией
    if re.search(r"setTimeout\s*\(\s*function\s*\(", normalized_code, re.IGNORECASE):
        # Это допустимо, но логируем для аудита
        app_logger.debug("Обнаружен setTimeout с function - допустимо")

    # Проверка на self-executing функции с обфускацией
    if re.search(
        r"\(function\s*\([^)]*\)\s*\{[^}]*\}\s*\)\.call\s*\(", normalized_code, re.IGNORECASE,
    ):
        app_logger.debug("Обнаружена self-executing функция с .call() - допустимо")

    return True, ""


def _sanitize_js_string(value: str) -> str:
    r"""Санитизирует строку для безопасного использования в JavaScript.

    Args:
        value: Исходная строка.

    Returns:
        Санитизированная строка с экранированными специальными символами.

    Примечание:
        Экранирует следующие символы:
        - Обратные кавычки (`)
        - Обратные слеши (\\)
        - Доллар ($) для предотвращения инъекций в template literals

    """
    if not isinstance(value, str):
        value = str(value)

    # Экранируем обратные слеши в первую очередь
    value = value.replace("\\", "\\\\")
    # Экранируем обратные кавычки
    value = value.replace("`", "\\`")
    # Экранируем доллар для предотвращения инъекций
    value = value.replace("$", "\\$")
    # Экранируем кавычки
    value = value.replace("'", "\\'")
    return value.replace('"', '\\"')
