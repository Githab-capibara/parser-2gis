"""Парсер для фирм 2GIS.

Предоставляет класс FirmParser для парсинга страниц организаций:
- URL-паттерн: /firm/<firm_id>
- Извлечение данных из window.initialState
- Валидация структуры initialState на безопасность
"""

from __future__ import annotations

import re
import sys
from typing import TYPE_CHECKING

from parser_2gis.constants import (
    MAX_INITIAL_STATE_DEPTH,
    MAX_INITIAL_STATE_SIZE,
    MAX_ITEMS_IN_COLLECTION,
)
from parser_2gis.logger import logger

from .main import MainParser

if TYPE_CHECKING:
    from parser_2gis.writer import FileWriter

# Рекурсивный тип для валидации данных initialState
# Может быть dict, list, str, int, float, bool или None
type InitialStateData = (
    "dict[str, InitialStateData] | list[InitialStateData] | str | int | float | bool | None"
)

_ALLOWED_KEYS: set[str] = {
    "data",
    "entity",
    "profile",
    "id",
    "name",
    "name_ex",
    "address",
    "phone",
    "phone_unformatted",
    "url",
    "email",
    "lat",
    "lon",
    "city_id",
    "rubric_id",
    "rubric_ids",
    "adm_div",
    "city",
    "building_id",
    "warehouse_id",
    "is_chain",
    "chain_id",
    "schedules",
    "links",
    "attributes",
    "files",
    "specifications",
    "ads",
    "antiad",
    "reviews",
    "statistics",
    "meta",
    "type",
    "type_id",
    "source",
    "import_ver",
    "import_hash",
    "mod_revision",
    "created_at",
    "updated_at",
}

# Скомпилированные regex паттерны для валидации HTML/XSS данных (Оптимизация: кэширование)
# ISSUE-053: Переименовано из _DANGEROUS_JS_PATTERNS в DANGEROUS_HTML_PATTERNS
# D013: Паттерны покрывают onerror=, onload= и другие обработчики БЕЗ пробелов
# Примечание: это HTML/XSS паттерны, не путать с DANGEROUS_JS_PATTERNS из chrome/js_executor.py
DANGEROUS_HTML_PATTERNS = [
    (re.compile(r"<script", re.IGNORECASE), "тег <script>"),
    (re.compile(r"javascript:", re.IGNORECASE), "протокол javascript:"),
    # D013: Исправление - \s* покрывает onerror=, onerror =, onerror  = и т.д.
    (re.compile(r"onerror\s*=", re.IGNORECASE), "обработчик onerror"),
    (re.compile(r"onload\s*=", re.IGNORECASE), "обработчик onload"),
    (re.compile(r"onclick\s*=", re.IGNORECASE), "обработчик onclick"),
    (re.compile(r"onmouseover\s*=", re.IGNORECASE), "обработчик onmouseover"),
    (re.compile(r"onfocus\s*=", re.IGNORECASE), "обработчик onfocus"),
    (re.compile(r"onblur\s*=", re.IGNORECASE), "обработчик onblur"),
    (re.compile(r"onchange\s*=", re.IGNORECASE), "обработчик onchange"),
    (re.compile(r"onsubmit\s*=", re.IGNORECASE), "обработчик onsubmit"),
    (re.compile(r"onkeydown\s*=", re.IGNORECASE), "обработчик onkeydown"),
    (re.compile(r"onkeyup\s*=", re.IGNORECASE), "обработчик onkeyup"),
    (re.compile(r"onkeypress\s*=", re.IGNORECASE), "обработчик onkeypress"),
    # D013: Общий паттерн для всех on* обработчиков
    (re.compile(r"\bon\w+\s*=", re.IGNORECASE), "on* обработчик событий"),
    (re.compile(r"eval\s*\(", re.IGNORECASE), "функция eval()"),
    (re.compile(r"Function\s*\(", re.IGNORECASE), "конструктор Function"),
    (re.compile(r"document\.cookie", re.IGNORECASE), "доступ к document.cookie"),
    (re.compile(r"localStorage", re.IGNORECASE), "доступ к localStorage"),
    (re.compile(r"sessionStorage", re.IGNORECASE), "доступ к sessionStorage"),
    (re.compile(r"XMLHttpRequest", re.IGNORECASE), "XMLHttpRequest"),
    (re.compile(r"fetch\s*\(", re.IGNORECASE), "функция fetch()"),
    (re.compile(r"alert\s*\(", re.IGNORECASE), "функция alert()"),
    (re.compile(r"confirm\s*\(", re.IGNORECASE), "функция confirm()"),
    (re.compile(r"prompt\s*\(", re.IGNORECASE), "функция prompt()"),
    (re.compile(r"window\.location", re.IGNORECASE), "доступ к window.location"),
    (re.compile(r"document\.write", re.IGNORECASE), "метод document.write"),
    (re.compile(r"document\.writeln", re.IGNORECASE), "метод document.writeln"),
    (re.compile(r"\.innerHTML\s*=", re.IGNORECASE), "свойство innerHTML"),
    (re.compile(r"\.outerHTML\s*=", re.IGNORECASE), "свойство outerHTML"),
    (re.compile(r"\.insertAdjacentHTML", re.IGNORECASE), "метод insertAdjacentHTML"),
]

# C017: Опасные ключи которые не должны присутствовать в initialState
_DANGEROUS_KEYS = {
    "__proto__",
    "constructor",
    "prototype",
    "__defineGetter__",
    "__defineSetter__",
    "__lookupGetter__",
    "__lookupSetter__",
}

# D013: Дополнительные паттерны для санитизации строк
_HTML_ESCAPE_TABLE = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#x27;",
    "`": "&#x60;",
}


def _sanitize_string_value(value: str) -> str:
    """D013: Санитизирует строковое значение для предотвращения XSS.

    Args:
        value: Исходная строка.

    Returns:
        Санитизированная строка с экранированными HTML символами.

    """
    if not isinstance(value, str):
        return value

    # Экранируем HTML символы
    for char, escape in _HTML_ESCAPE_TABLE.items():
        value = value.replace(char, escape)

    return value


def _validate_initial_state(
    data: InitialStateData,
    depth: int = 0,
    item_count: int = 0,
) -> tuple[bool, int]:
    """Рекурсивно валидирует структуру initialState на безопасность.

    ISSUE-076, ISSUE-077: Добавлена валидация depth и item_count.

    Args:
        data: Данные для валидации.
        depth: Текущая глубина вложенности.
        item_count: Счётчик обработанных элементов.

    Returns:
        Кортеж (is_valid, item_count) - валидны ли данные и общее количество элементов.

    Raises:
        ValueError: Если depth отрицательный или item_count переполнен.

    """
    # ISSUE-076: Валидация depth на отрицательное значение
    if depth < 0:
        logger.warning("Отрицательная глубина вложенности initialState: %d", depth)
        msg = f"depth не может быть отрицательным: {depth}"
        raise ValueError(msg)

    # ISSUE-077: Валидация item_count на переполнение
    if item_count < 0:
        logger.warning("Отрицательный счётчик элементов initialState: %d", item_count)
        msg = f"item_count не может быть отрицательным: {item_count}"
        raise ValueError(msg)

    # Защита от переполнения item_count (максимум 2^31 - 1)
    max_item_count = 2_147_483_647
    if item_count > max_item_count:
        logger.warning("Переполнение счётчика элементов initialState: %d", item_count)
        return False, item_count

    if depth > MAX_INITIAL_STATE_DEPTH:
        logger.warning("Превышена максимальная глубина вложенности initialState: %d", depth)
        return False, item_count

    if data is None:
        return True, item_count

    if isinstance(data, bool):
        return True, item_count

    if isinstance(data, (int, float)):
        import math

        if isinstance(data, float) and (math.isnan(data) or math.isinf(data)):
            logger.warning("Обнаружено NaN/Infinity в initialState")
            return False, item_count
        return True, item_count

    if isinstance(data, str):
        # Проверка на опасные JS конструкции с использованием скомпилированных паттернов
        for pattern, description in DANGEROUS_HTML_PATTERNS:
            if pattern.search(data):
                logger.warning("Обнаружена опасная конструкция в initialState: %s", description)
                return False, item_count

        if len(data) > MAX_INITIAL_STATE_SIZE:
            logger.warning("Строка в initialState превышает максимальный размер: %d", len(data))
            return False, item_count
        return True, item_count

    if isinstance(data, dict) and len(data) > MAX_ITEMS_IN_COLLECTION:
        logger.warning(
            "Словарь в initialState превышает максимальное количество элементов: %d",
            len(data),
        )
        return False, item_count

    if isinstance(data, dict):
        for key, value in data.items():
            if not isinstance(key, str):
                logger.warning("Некорректный тип ключа в initialState")
                return False, item_count
            # C017: Проверка на опасные ключи
            if key in _DANGEROUS_KEYS:
                logger.warning("Обнаружен опасный ключ в initialState: %s", key)
                return False, item_count
            valid, item_count = _validate_initial_state(value, depth + 1, item_count + 1)
            if not valid:
                return False, item_count
        return True, item_count

    if isinstance(data, list) and len(data) > MAX_ITEMS_IN_COLLECTION:
        logger.warning(
            "Список в initialState превышает максимальное количество элементов: %d",
            len(data),
        )
        return False, item_count

    if isinstance(data, list):
        for item in data:
            valid, item_count = _validate_initial_state(item, depth + 1, item_count + 1)
            if not valid:
                return False, item_count
        return True, item_count

    logger.warning("Недопустимый тип данных в initialState: %s", type(data).__name__)
    return False, item_count


def _safe_extract_initial_state(
    raw_data: InitialStateData,
    required_keys: list[str],
) -> dict[str, InitialStateData] | None:
    """Безопасно извлекает данные из initialState с валидацией.

    Args:
        raw_data: Исходные данные из window.initialState.
        required_keys: Список обязательных ключей для извлечения.

    Returns:
        Валидированный словарь данных или None при ошибке.

    """
    if not isinstance(raw_data, dict):
        logger.warning("initialState не является словарём")
        return None

    data_size = sys.getsizeof(str(raw_data))
    if data_size > MAX_INITIAL_STATE_SIZE:
        logger.error("initialState превышает максимальный размер: %d байт", data_size)
        return None

    valid, _ = _validate_initial_state(raw_data)
    if not valid:
        logger.error("initialState содержит небезопасные данные")
        return None

    result = raw_data
    for key in required_keys:
        if not isinstance(result, dict):
            logger.warning("Ожидался словарь для ключа %s", key)
            return None
        result = result.get(key)
        if result is None:
            logger.warning("Ключ %s отсутствует в initialState", key)
            return None

    if not isinstance(result, dict):
        logger.warning("Итоговые данные не являются словарём")
        return None

    return result


class FirmParser(MainParser):
    """Парсер для фирм, предоставленных 2GIS.

    URL-паттерн для таких случаев: https://2gis.<domain>/<city_id>/firm/<firm_id>
    """

    @staticmethod
    def url_pattern() -> str:
        """Возвращает URL-паттерн для парсера фирм.

        Returns:
            Regex паттерн для匹配 URL фирм 2GIS.

        """
        return r"https?://2gis\.[^/]+(/[^/]+)?/firm/.*"

    def parse(self, writer: FileWriter) -> None:
        """Парсит URL с организацией.

        Args:
            writer: Целевой файловый писатель.

        Raises:
            MemoryError: При нехватке памяти.

        """
        try:
            # Переходим по URL с агрессивно ускоренным таймаутом для интенсивного парсинга
            self._chrome_remote.navigate(self._url, referer="https://google.com", timeout=15)

            # Документ загружен, получаем ответ
            responses = self._chrome_remote.get_responses()
            if not responses:
                logger.error("Ошибка получения ответа сервера.")
                return

            # Безопасное получение первого ответа
            try:
                document_response = responses[0]
            except (IndexError, KeyError):
                logger.error("Список ответов пуст или некорректен.")
                return

            # ISSUE-129: Явная проверка mimeType на None
            mime_type = document_response.get("mimeType")
            if mime_type is None:
                logger.error("MIME тип ответа отсутствует (None)")
                return

            if mime_type != "text/html":
                logger.error(
                    "Неверный тип MIME ответа: %s",
                    document_response.get("mimeType", "неизвестно"),
                )
                return

            if document_response.get("status") == 404:
                logger.warning('Сервер вернул сообщение "Организация не найдена".')

                if self._options.skip_404_response:
                    return

                # ISSUE-003-#13: Даже если skip_404_response=False, прекращаем парсинг
                # для несуществующих организаций
                logger.warning("Пропуск парсинга для несуществующей организации (404)")
                return

            # Ждём завершения всех запросов 2GIS
            self._wait_requests_finished()

            # Получаем ответ и собираем полезную нагрузку.
            try:
                initial_state = self._chrome_remote.execute_script("window.initialState")
                if not initial_state:
                    logger.warning("Данные организации не найдены (initialState отсутствует).")
                    return
                # D017: Дополнительная валидация window.initialState
                if not isinstance(initial_state, dict):
                    logger.error("window.initialState не является словарём")
                    return

                # Используем новую функцию валидации вместо ручной проверки
                required_keys = ["data", "entity", "profile"]
                profile_data = _safe_extract_initial_state(initial_state, required_keys)

                if not profile_data:
                    logger.warning("Данные организации не прошли валидацию.")
                    return

                # Извлекаем данные из валидированного профиля
                data = list(profile_data.values())
                if not data:
                    logger.warning("Данные организации не найдены (пустой профиль).")
                    return
                firm_data = data[0]

                # Проверяем, что firm_data — словарь для type-safe доступа
                if not isinstance(firm_data, dict):
                    logger.warning(
                        "Данные организации имеют неверный тип: %s", type(firm_data).__name__
                    )
                    return

                # D013: Санитизация строковых данных перед записью
                if "data" in firm_data and isinstance(firm_data.get("data"), dict):
                    for key, value in firm_data["data"].items():
                        if isinstance(value, str):
                            firm_data["data"][key] = _sanitize_string_value(value)
            except (KeyError, TypeError, AttributeError) as e:
                logger.error("Ошибка при получении данных организации: %s", e)
                return

            # Записываем API документ в файл
            writer.write(
                {"result": {"items": [firm_data["data"]]}, "meta": firm_data.get("meta", {})},
            )

        except MemoryError as memory_error:
            # ISSUE-128: Явная обработка MemoryError
            logger.error("MemoryError при парсинге фирмы: %s", memory_error)
            # Очищаем кэш и запускаем GC
            if hasattr(self, "_cache"):
                self._cache.clear()
            import gc

            gc.collect()
            raise
