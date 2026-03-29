"""Парсер для фирм 2GIS.

Предоставляет класс FirmParser для парсинга страниц организаций:
- URL-паттерн: /firm/<firm_id>
- Извлечение данных из window.initialState
- Валидация структуры initialState на безопасность
"""

from __future__ import annotations

import re
import sys
from typing import TYPE_CHECKING, Any, Dict, Optional, Set

from parser_2gis.logger import logger

from .main import MainParser

if TYPE_CHECKING:
    from parser_2gis.writer import FileWriter

MAX_INITIAL_STATE_DEPTH = 10
MAX_INITIAL_STATE_SIZE = 5 * 1024 * 1024
MAX_ITEMS_IN_COLLECTION = 10000

_ALLOWED_KEYS: Set[str] = {
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

# Скомпилированные regex паттерны для JS валидации (Оптимизация: кэширование)
_DANGEROUS_JS_PATTERNS = [
    (re.compile(r"<script", re.IGNORECASE), "тег <script>"),
    (re.compile(r"javascript:", re.IGNORECASE), "протокол javascript:"),
    (re.compile(r"onerror\s*=", re.IGNORECASE), "обработчик onerror"),
    (re.compile(r"onload\s*=", re.IGNORECASE), "обработчик onload"),
    (re.compile(r"eval\s*\(", re.IGNORECASE), "функция eval()"),
    (re.compile(r"Function\s*\(", re.IGNORECASE), "конструктор Function"),
    (re.compile(r"document\.cookie", re.IGNORECASE), "доступ к document.cookie"),
    (re.compile(r"localStorage", re.IGNORECASE), "доступ к localStorage"),
    (re.compile(r"sessionStorage", re.IGNORECASE), "доступ к sessionStorage"),
    (re.compile(r"XMLHttpRequest", re.IGNORECASE), "XMLHttpRequest"),
    (re.compile(r"fetch\s*\(", re.IGNORECASE), "функция fetch()"),
]


def _validate_initial_state(data: Any, depth: int = 0, item_count: int = 0) -> tuple[bool, int]:
    """Рекурсивно валидирует структуру initialState на безопасность.

    Args:
        data: Данные для валидации.
        depth: Текущая глубина вложенности.
        item_count: Счётчик обработанных элементов.

    Returns:
        Кортеж (is_valid, item_count) - валидны ли данные и общее количество элементов.
    """
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
        for pattern, description in _DANGEROUS_JS_PATTERNS:
            if pattern.search(data):
                logger.warning("Обнаружена опасная конструкция в initialState: %s", description)
                return False, item_count

        if len(data) > MAX_INITIAL_STATE_SIZE:
            logger.warning("Строка в initialState превышает максимальный размер: %d", len(data))
            return False, item_count
        return True, item_count

    if isinstance(data, dict):
        if len(data) > MAX_ITEMS_IN_COLLECTION:
            logger.warning(
                "Словарь в initialState превышает максимальное количество элементов: %d", len(data)
            )
            return False, item_count

        for key, value in data.items():
            if not isinstance(key, str):
                logger.warning("Некорректный тип ключа в initialState")
                return False, item_count
            valid, item_count = _validate_initial_state(value, depth + 1, item_count + 1)
            if not valid:
                return False, item_count
        return True, item_count

    if isinstance(data, list):
        if len(data) > MAX_ITEMS_IN_COLLECTION:
            logger.warning(
                "Список в initialState превышает максимальное количество элементов: %d", len(data)
            )
            return False, item_count

        for item in data:
            valid, item_count = _validate_initial_state(item, depth + 1, item_count + 1)
            if not valid:
                return False, item_count
        return True, item_count

    logger.warning("Недопустимый тип данных в initialState: %s", type(data).__name__)
    return False, item_count


def _safe_extract_initial_state(
    raw_data: Any, required_keys: list[str]
) -> Optional[Dict[str, Any]]:
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
    def url_pattern():
        """URL-паттерн для парсера."""
        return r"https?://2gis\.[^/]+(/[^/]+)?/firm/.*"

    def parse(self, writer: FileWriter) -> None:
        """Парсит URL с организацией.

        Args:
            writer: Целевой файловый писатель.
        """
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

        # Обработка 404
        if document_response.get("mimeType") != "text/html":
            logger.error(
                "Неверный тип MIME ответа: %s", document_response.get("mimeType", "неизвестно")
            )
            return

        if document_response.get("status") == 404:
            logger.warning('Сервер вернул сообщение "Организация не найдена".')

            if self._options.skip_404_response:
                return

        # Ждём завершения всех запросов 2GIS
        self._wait_requests_finished()

        # Получаем ответ и собираем полезную нагрузку.
        try:
            initial_state = self._chrome_remote.execute_script("window.initialState")
            if not initial_state:
                logger.warning("Данные организации не найдены (initialState отсутствует).")
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
            doc = data[0]
        except (KeyError, TypeError, AttributeError) as e:
            logger.error("Ошибка при получении данных организации: %s", e)
            return

        # Записываем API документ в файл
        writer.write({"result": {"items": [doc["data"]]}, "meta": doc.get("meta", {})})
