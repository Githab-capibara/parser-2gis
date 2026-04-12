"""Кэш конфигураций для парсера.

Модуль предоставляет класс ConfigCache для кэширования конфигураций
городов и категорий с использованием lru_cache.

Пример использования:
    >>> from parser_2gis.cache.config_cache import ConfigCache
    >>> cache = ConfigCache()
    >>> cities = cache.load_cities("/path/to/cities.json")
    >>> categories = cache.get_categories()
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, TypedDict

from parser_2gis.constants import MAX_CITIES_COUNT, MAX_CITIES_FILE_SIZE, MMAP_CITIES_THRESHOLD
from parser_2gis.logger import logger

# Константа размера кэша городов
CITIES_CACHE_SIZE: int = 16


def _validate_city(city: dict[str, Any], index: int) -> None:
    """Валидирует отдельный город.

    Args:
        city: Словарь с данными города.
        index: Индекс города в списке (для сообщений об ошибках).

    Raises:
        ValueError: Если город некорректен.

    """
    if not isinstance(city, dict):
        logger.error("Город %d должен быть словарём, а не %s", index, type(city).__name__)
        error_msg = f"Город {index} должен быть словарём"
        raise TypeError(error_msg)

    # Проверяем name, code, domain
    if "name" not in city or "code" not in city or "domain" not in city:
        logger.error("Город %d должен содержать поля 'name', 'code' и 'domain'", index)
        error_msg = f"Город {index} должен содержать поля 'name', 'code' и 'domain'"
        raise ValueError(error_msg)

    if (
        not isinstance(city["name"], str)
        or not isinstance(city["code"], str)
        or not isinstance(city["domain"], str)
    ):
        logger.error("Поля 'name', 'code' и 'domain' города %d должны быть строками", index)
        error_msg = f"Поля 'name', 'code' и 'domain' города {index} должны быть строками"
        raise TypeError(error_msg)

    # Опционально: проверяем country_code если есть
    if "country_code" in city and not isinstance(city["country_code"], str):
        logger.error("Поле 'country_code' города %d должно быть строкой", index)
        error_msg = f"Поле 'country_code' города {index} должно быть строкой"
        raise TypeError(error_msg)


class CategoryDict(TypedDict):
    """Типизация словаря категории."""

    name: str
    query: str
    rubric_code: str | None


class ConfigCache:
    """Кэш для конфигураций городов и категорий.

    Использует lru_cache для кэширования загруженных данных
    и предотвращения повторных загрузок.

    Attributes:
        cities_cache_size: Максимальный размер кэша городов.
        categories_cache_size: Максимальный размер кэша категорий.

    Example:
        >>> cache = ConfigCache(cities_cache_size=16)
        >>> cities = cache.load_cities("/path/to/cities.json")
        >>> # Повторный вызов вернёт закэшированное значение
        >>> cities2 = cache.load_cities("/path/to/cities.json")

    """

    # ISSUE-087: Используем @lru_cache на методе класса вместо создания на экземпляре
    def __init__(
        self, cities_cache_size: int = CITIES_CACHE_SIZE, categories_cache_size: int = 4,
    ) -> None:
        """Инициализация кэша конфигураций.

        Args:
            cities_cache_size: Максимальный размер кэша городов.
            categories_cache_size: Максимальный размер кэша категорий.

        """
        self._cities_cache_size = cities_cache_size
        self._categories_cache_size = categories_cache_size

    @staticmethod
    @lru_cache(maxsize=16)
    def _load_cities_cached(cities_path_str: str) -> tuple[tuple[tuple[str, Any], ...], ...]:
        """Кэшированная загрузка городов.

        ISSUE-087: Используем @lru_cache на статическом методе вместо создания на экземпляре.

        Args:
            cities_path_str: Путь к файлу городов как строка.

        Returns:
            Кортеж кортежей (город, данные) для хэшируемости.

        """
        # Внутренняя функция для загрузки
        cities_path = Path(cities_path_str)

        if not cities_path.is_file():
            logger.error("Файл городов не найден: %s", cities_path)
            error_msg = f"Файл {cities_path} не найден"
            raise FileNotFoundError(error_msg)

        try:
            file_size = cities_path.stat().st_size
            if file_size == 0:
                logger.error("Файл городов пуст: %s", cities_path)
                error_msg = f"Файл {cities_path} пуст"
                raise ValueError(error_msg)

            if file_size > MAX_CITIES_FILE_SIZE:
                logger.error(
                    "Файл городов слишком большой: %d байт (макс: %d байт)",
                    file_size,
                    MAX_CITIES_FILE_SIZE,
                )
                error_msg = (
                    f"Файл {cities_path} слишком большой "
                    f"({file_size} > {MAX_CITIES_FILE_SIZE} байт)"
                )
                raise ValueError(error_msg)

            logger.debug("Размер файла городов: %d байт", file_size)
        except OSError as stat_error:
            logger.error("Ошибка получения информации о файле: %s", stat_error)
            error_msg = f"Не удалось получить информацию о файле: {stat_error}"
            raise OSError(error_msg) from stat_error

        all_cities: list[dict[str, Any]] | None = None

        try:
            use_mmap = file_size > MMAP_CITIES_THRESHOLD

            if use_mmap:
                logger.info(
                    "Файл городов большой (%.2f MB), используется mmap для чтения",
                    file_size / (1024 * 1024),
                )
                import mmap as mmap_module

                with open(cities_path, "rb") as f:
                    mmapped_file = mmap_module.mmap(f.fileno(), 0, access=mmap_module.ACCESS_READ)
                    try:
                        json_data = mmapped_file.read().decode("utf-8")
                        all_cities = json.loads(json_data)
                    finally:
                        mmapped_file.close()
            else:
                with open(cities_path, encoding="utf-8") as f:
                    all_cities = json.load(f)

            if not isinstance(all_cities, list):
                error_msg = (
                    f"Файл городов должен содержать список, получен {type(all_cities).__name__}"
                )
                logger.error(error_msg)
                raise TypeError(error_msg)

            if len(all_cities) > MAX_CITIES_COUNT:
                logger.error(
                    "Слишком много городов: %d (макс: %d)", len(all_cities), MAX_CITIES_COUNT,
                )
                error_msg = f"Слишком много городов в файле: {len(all_cities)} > {MAX_CITIES_COUNT}"
                raise ValueError(error_msg)

            for i, city in enumerate(all_cities):
                _validate_city(city, i)

            logger.debug("Файл городов валидирован: %d городов", len(all_cities))

            # Конвертируем в tuple для хэшируемости
            return tuple(tuple(sorted(city.items())) for city in all_cities)

        except UnicodeDecodeError as e:
            logger.error("Ошибка кодировки при чтении файла городов: %s", e)
            error_msg = f"Файл городов имеет некорректную кодировку (ожидалась UTF-8): {e}"
            raise ValueError(error_msg) from e
        except json.JSONDecodeError as e:
            logger.error("Ошибка парсинга JSON в файле городов: %s", e)
            error_msg = f"Некорректный формат JSON в файле городов: {e}"
            raise ValueError(error_msg) from e
        except OSError as e:
            logger.error("Ошибка ОС при чтении файла городов: %s", e)
            error_msg = f"Не удалось прочитать файл городов: {e}"
            raise OSError(error_msg) from e

    def load_cities(self, cities_path_str: str) -> list[dict[str, Any]]:
        """Загружает JSON файл с городами с кэшированием.

        ISSUE-087: Использует статический метод с @lru_cache.

        Args:
            cities_path_str: Путь к файлу cities.json как строка.

        Returns:
            Список городов из JSON файла.

        Raises:
            FileNotFoundError: Если файл не найден.
            ValueError: Если файл повреждён или содержит некорректные данные.
            OSError: Если произошла ошибка операционной системы.

        """
        cached_result = self._load_cities_cached(cities_path_str)
        # Конвертируем обратно в list[dict]
        return [dict(city_tuple) for city_tuple in cached_result]

    def clear_cities_cache(self) -> None:
        """Очищает кэш городов."""
        self._load_cities_cached.cache_clear()

    def cities_cache_info(self) -> dict[str, Any]:
        """Возвращает информацию о кэше городов.

        Returns:
            Словарь с информацией о кэше (hits, misses, size, maxsize).

        """
        cache_info = self._load_cities_cached.cache_info()
        return {
            "hits": cache_info.hits,
            "misses": cache_info.misses,
            "size": cache_info.currsize,
            "maxsize": cache_info.maxsize,
        }

    @staticmethod
    @lru_cache(maxsize=4)
    def get_categories() -> list[CategoryDict]:
        """Возвращает список категорий с кэшированием.

        Returns:
            Список из 93 категорий.

        """
        # Импортируем здесь для избежания циклической зависимости
        from parser_2gis.resources import CATEGORIES_93

        return CATEGORIES_93

    @staticmethod
    def clear_categories_cache() -> None:
        """Очищает кэш категорий."""
        ConfigCache.get_categories.cache_clear()


def get_config_cache() -> ConfigCache:
    """Получает singleton экземпляр ConfigCache (ленивая инициализация через замыкание).

    Returns:
        Singleton экземпляр ConfigCache.

    """
    if not hasattr(get_config_cache, "_instance"):
        get_config_cache._instance = ConfigCache()  # type: ignore[attr-defined]
    return get_config_cache._instance  # type: ignore[attr-defined,no-any-return]


__all__ = ["CategoryDict", "ConfigCache", "get_config_cache"]
