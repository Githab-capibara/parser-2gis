from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

from ...logger import logger
from .main import MainParser

if TYPE_CHECKING:
    from ...writer import FileWriter

# Константы для валидации initialState
MAX_INITIAL_STATE_DEPTH = 10  # Максимальная глубина вложенности данных


def _validate_initial_state(data: Any, depth: int = 0) -> bool:
    """Рекурсивно валидирует структуру initialState на безопасность.
    - Проверяет тип данных (только dict, list, str, int, float, bool, None)
    - Ограничивает глубину вложенности для предотвращения DoS
    - Проверяет строки на наличие опасных JS-конструкций

    Args:
        data: Данные для валидации.
        depth: Текущая глубина вложенности.

    Returns:
        True если данные безопасны, False иначе.
    """
    # Проверяем глубину вложенности
    if depth > MAX_INITIAL_STATE_DEPTH:
        logger.warning("Превышена максимальная глубина вложенности initialState")
        return False

    # Базовые типы
    if data is None:
        return True

    if isinstance(data, bool):
        return True

    if isinstance(data, (int, float)):
        # Проверяем на NaN и Infinity
        import math
        if isinstance(data, float) and (math.isnan(data) or math.isinf(data)):
            logger.warning("Обнаружено NaN/Infinity в initialState")
            return False
        return True

    if isinstance(data, str):
        # Проверяем строку на опасные JS-конструкции
        dangerous_patterns = [
            '<script', 'javascript:', 'onerror=', 'onload=',
            'eval(', 'Function(', 'document.cookie', 'localStorage',
            'sessionStorage', 'XMLHttpRequest', 'fetch('
        ]
        data_lower = data.lower()
        for pattern in dangerous_patterns:
            if pattern.lower() in data_lower:
                logger.warning(
                    "Обнаружена опасная конструкция в initialState: %s",
                    pattern
                )
                return False
        return True

    if isinstance(data, dict):
        # Рекурсивно проверяем все значения словаря
        for key, value in data.items():
            if not isinstance(key, str):
                logger.warning("Некорректный тип ключа в initialState")
                return False
            if not _validate_initial_state(value, depth + 1):
                return False
        return True

    if isinstance(data, list):
        # Рекурсивно проверяем все элементы списка
        for item in data:
            if not _validate_initial_state(item, depth + 1):
                return False
        return True

    # Недопустимый тип
    logger.warning(
        "Недопустимый тип данных в initialState: %s",
        type(data).__name__
    )
    return False


def _safe_extract_initial_state(
    raw_data: Any,
    required_keys: list[str]
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

    # Проверяем всю структуру на безопасность
    if not _validate_initial_state(raw_data):
        logger.error("initialState содержит небезопасные данные")
        return None

    # Последовательно извлекаем ключи
    result = raw_data
    for key in required_keys:
        if not isinstance(result, dict):
            logger.warning("Ожидался словарь для ключа %s", key)
            return None
        result = result.get(key)
        if result is None:
            logger.warning("Ключ %s отсутствует в initialState", key)
            return None

    # Финальная проверка типа
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
        # Переходим по URL с таймаутом 5 минут
        self._chrome_remote.navigate(
            self._url, referer="https://google.com", timeout=300
        )

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
                "Неверный тип MIME ответа: %s",
                document_response.get("mimeType", "неизвестно"),
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
                logger.warning(
                    "Данные организации не найдены (initialState отсутствует)."
                )
                return
            # Используем новую функцию валидации вместо ручной проверки
            required_keys = ["data", "entity", "profile"]
            profile_data = _safe_extract_initial_state(
                initial_state, required_keys
            )

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
