"""Загрузчик городов для парсера.

Модуль предоставляет функции для загрузки и валидации городов из JSON файла.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from parser_2gis.constants import MAX_CITIES_COUNT, MAX_CITIES_FILE_SIZE, MMAP_CITIES_THRESHOLD
from parser_2gis.logger import logger


@lru_cache(maxsize=16)
def load_cities_json(cities_path_str: str) -> list[dict[str, Any]]:
    """Загружает JSON файл с городами с оптимизированной загрузкой.

    C019: Кэширование через lru_cache для снижения повторных загрузок.

    Args:
        cities_path_str: Путь к файлу cities.json как строка.

    Returns:
        Список городов из JSON файла.

    Raises:
        FileNotFoundError: Если файл не найден.
        ValueError: Если файл повреждён или содержит некорректные данные.
        OSError: Если произошла ошибка операционной системы.

    """
    cities_path = Path(cities_path_str)

    if not cities_path.is_file():
        logger.error("Файл городов не найден: %s", cities_path)
        raise FileNotFoundError(f"Файл {cities_path} не найден")

    try:
        file_size = cities_path.stat().st_size
        if file_size == 0:
            logger.error("Файл городов пуст: %s", cities_path)
            raise ValueError(f"Файл {cities_path} пуст")

        if file_size > MAX_CITIES_FILE_SIZE:
            logger.error(
                "Файл городов слишком большой: %d байт (макс: %d байт)",
                file_size,
                MAX_CITIES_FILE_SIZE,
            )
            raise ValueError(
                f"Файл {cities_path} слишком большой ({file_size} > {MAX_CITIES_FILE_SIZE} байт)"
            )

        logger.debug("Размер файла городов: %d байт", file_size)
    except OSError as stat_error:
        logger.error("Ошибка получения информации о файле: %s", stat_error)
        raise OSError(f"Не удалось получить информацию о файле: {stat_error}") from stat_error

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
            logger.error("Файл городов должен содержать список, а не %s", type(all_cities).__name__)
            raise ValueError(
                f"Файл городов должен содержать список, получен {type(all_cities).__name__}"
            )

        if len(all_cities) > MAX_CITIES_COUNT:
            logger.error("Слишком много городов: %d (макс: %d)", len(all_cities), MAX_CITIES_COUNT)
            raise ValueError(
                f"Слишком много городов в файле: {len(all_cities)} > {MAX_CITIES_COUNT}"
            )

        for i, city in enumerate(all_cities):
            if not isinstance(city, dict):
                logger.error("Город %d должен быть словарём, а не %s", i, type(city).__name__)
                raise ValueError("Город %d должен быть словарём")

            # Проверяем name, code, domain
            if "name" not in city or "code" not in city or "domain" not in city:
                logger.error("Город %d должен содержать поля 'name', 'code' и 'domain'", i)
                raise ValueError("Город %d должен содержать поля 'name', 'code' и 'domain'")

            if (
                not isinstance(city["name"], str)
                or not isinstance(city["code"], str)
                or not isinstance(city["domain"], str)
            ):
                logger.error("Поля 'name', 'code' и 'domain' города %d должны быть строками", i)
                raise ValueError(f"Поля 'name', 'code' и 'domain' города {i} должны быть строками")

            # Опционально: проверяем country_code если есть
            if "country_code" in city and not isinstance(city["country_code"], str):
                logger.error("Поле 'country_code' города %d должно быть строкой", i)
                raise ValueError(f"Поле 'country_code' города {i} должно быть строкой")

        logger.debug("Файл городов валидирован: %d городов", len(all_cities))
        return all_cities

    except json.JSONDecodeError as e:
        logger.error("Ошибка парсинга JSON в файле городов: %s", e)
        raise ValueError(f"Некорректный формат JSON в файле городов: {e}") from e
    except OSError as e:
        logger.error("Ошибка ОС при чтении файла городов: %s", e)
        raise OSError(f"Не удалось прочитать файл городов: {e}") from e


def load_cities_json_lazy(cities_path_str: str):
    """Генератор для lazy loading городов.

    C019: Lazy loading через генератор для снижения потребления памяти.

    Args:
        cities_path_str: Путь к файлу cities.json как строка.

    Yields:
        Словари городов.

    """
    cities_path = Path(cities_path_str)

    if not cities_path.is_file():
        logger.error("Файл городов не найден: %s", cities_path)
        raise FileNotFoundError(f"Файл {cities_path} не найден")

    # C019: Используем mmap для больших файлов
    try:
        file_size = cities_path.stat().st_size
        use_mmap = file_size > MMAP_CITIES_THRESHOLD

        if use_mmap:
            import mmap as mmap_module

            with open(cities_path, "rb") as f:
                mmapped_file = mmap_module.mmap(f.fileno(), 0, access=mmap_module.ACCESS_READ)
                try:
                    json_data = mmapped_file.read().decode("utf-8")
                    all_cities = json.loads(json_data)
                    for city in all_cities:
                        yield city
                finally:
                    mmapped_file.close()
        else:
            with open(cities_path, encoding="utf-8") as f:
                all_cities = json.load(f)
                for city in all_cities:
                    yield city
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Ошибка при lazy loading городов: %s", e)
        raise


__all__ = ["load_cities_json", "load_cities_json_lazy"]
