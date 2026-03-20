"""
Модуль путей к ресурсам парсера.

Предоставляет функции для получения путей к данным, изображениям
и пользовательским директориям.
"""

from __future__ import annotations

import base64
import functools
import os
import pathlib

# Константа для максимальной длины пути
MAX_PATH_LENGTH = 1024


def data_path() -> pathlib.Path:
    """Получает путь к данным пакета."""
    if "_MEIPASS2" in os.environ:
        here = os.environ["_MEIPASS2"]
    else:
        here = os.path.dirname(os.path.abspath(__file__))

    path = os.path.join(here, "data")
    return pathlib.Path(path)


def user_path(is_config: bool = True) -> pathlib.Path:
    """Получает пользовательский путь для Linux Ubuntu.

    Примечание:
        Расположение пути для Linux Ubuntu:
        * ~/.config/parser-2gis (для конфигурации)
        * ~/.local/share/parser-2gis (для данных)

    Args:
        is_config: Если True, возвращает путь к конфигурации, иначе к данным.

    Returns:
        Путь к пользовательской директории.
    """
    if is_config:
        path = os.getenv("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    else:
        path = os.getenv("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))

    path = os.path.join(path, "parser-2gis")
    return pathlib.Path(path)


@functools.lru_cache()
def image_path(basename: str, ext: str | None = None) -> str:
    """Получает путь к изображению `basename`.`ext`.
    Расширение игнорируется, если `ext` установлен в `None`.

    Args:
        basename: Базовое имя изображения.
        ext: Расширение изображения (опционально).

    Returns:
        Абсолютный путь к изображению.

    Raises:
        ValueError: Если basename содержит недопустимые символы.
        FileNotFoundError: Если изображение не найдено.
    """
    # Валидация basename для предотвращения directory traversal
    if "/" in basename or "\\" in basename or ".." in basename:
        raise ValueError(f"Недопустимое имя файла: {basename}")

    images_dir = data_path() / "images"

    # Оптимизированный поиск: сразу формируем ожидаемое имя файла
    if ext is not None:
        img_name = f"{basename}.{ext}"
        img_path = images_dir / img_name
        if img_path.exists():
            return os.path.abspath(img_path)
        raise FileNotFoundError(f"Изображение {basename}.{ext} не найдено")

    # Если расширение не указано, ищем любой файл с таким basename
    for img_name in os.listdir(images_dir):
        img_basename, _ = os.path.splitext(img_name)
        if img_basename == basename:
            return os.path.abspath(images_dir / img_name)
    raise FileNotFoundError(f"Изображение {basename} не найдено")


@functools.lru_cache()
def image_data(basename: str, ext: str | None = None) -> bytes:
    """Получает данные изображения `basename`.`ext`.
    Расширение игнорируется, если `ext` установлен в `None`.

    Args:
        basename: Базовое имя изображения.
        ext: Расширение изображения (опционально).

    Returns:
        Данные изображения в кодировке base64.

    Raises:
        FileNotFoundError: Если изображение не найдено.
        IOError: Если файл не может быть прочитан.
    """
    img_path = image_path(basename, ext)
    try:
        with open(img_path, "rb") as f_img:
            return base64.b64encode(f_img.read())
    except (IOError, OSError):
        # Файл не может быть прочитан - ошибка логируется и пробрасывается дальше
        raise


@functools.lru_cache()
def cache_path() -> pathlib.Path:
    """Получает путь к директории кэша для Linux Ubuntu.

    Примечание:
        Расположение пути для Linux Ubuntu:
        * ~/.cache/parser-2gis (для кэша)

    Returns:
        Путь к директории кэша.
    """
    path = os.getenv("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))
    path = os.path.join(path, "parser-2gis")
    return pathlib.Path(path)
