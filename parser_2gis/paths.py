from __future__ import annotations

import base64
import functools
import os
import pathlib

from .common import running_mac, running_windows

# Константа для максимальной длины пути
MAX_PATH_LENGTH = 1024


def data_path() -> pathlib.Path:
    """Получает путь к данным пакета."""
    if '_MEIPASS2' in os.environ:
        here = os.environ['_MEIPASS2']
    else:
        here = os.path.dirname(os.path.abspath(__file__))

    path = os.path.join(here, 'data')
    return pathlib.Path(path)


def user_path(is_config: bool = True) -> pathlib.Path:
    """Получает пользовательский путь в зависимости от ОС.

    Примечание:
        Возможное расположение пути в зависимости от ОС:
        * Unix: ~/.config/parser-2gis или ~/.local/share/parser-2gis (зависит от флага `is_config`)
        * Mac: ~/Library/Application Support/parser-2gis/
        * Win: C:\\Users\\%USERPROFILE%\\AppData\\Local\\parser-2gis
    """
    if running_windows():
        import ctypes

        CSIDL_LOCAL_APPDATA = 28
        buf = ctypes.create_unicode_buffer(MAX_PATH_LENGTH)
        ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_LOCAL_APPDATA, None, 0, buf)  # type: ignore
        path = buf.value
    elif running_mac():
        path = os.path.expanduser('~/Library/Application Support')
    else:
        if is_config:
            path = os.getenv('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
        else:
            path = os.getenv('XDG_DATA_HOME', os.path.expanduser('~/.local/share'))

    path = os.path.join(path, 'parser-2gis')
    return pathlib.Path(path)


@functools.lru_cache()
def image_path(basename: str, ext: str | None = None) -> str:
    """Получает путь к изображению `basename`.`ext`.
    Расширение игнорируется, если `ext` установлен в `None`.

    Args:
        basename: Базовое имя изображения.
        ext: Расширение изображения.

    Returns:
        Путь к изображению.
        
    Raises:
        ValueError: Если basename содержит недопустимые символы.
        FileNotFoundError: Если изображение не найдено.
    """
    # Валидация basename для предотвращения directory traversal
    if '/' in basename or '\\' in basename or '..' in basename:
        raise ValueError(f'Недопустимое имя файла: {basename}')

    images_dir = data_path() / 'images'

    # Оптимизированный поиск: сразу формируем ожидаемое имя файла
    if ext is not None:
        img_name = f'{basename}.{ext}'
        img_path = images_dir / img_name
        if img_path.exists():
            return os.path.abspath(img_path)
        raise FileNotFoundError(f'Изображение {basename}.{ext} не найдено')
    else:
        # Если расширение не указано, ищем любой файл с таким basename
        for img_name in os.listdir(images_dir):
            img_basename, img_ext = os.path.splitext(img_name)
            if img_basename == basename:
                return os.path.abspath(images_dir / img_name)
        raise FileNotFoundError(f'Изображение {basename} не найдено')


@functools.lru_cache()
def image_data(basename: str, ext: str | None = None) -> bytes:
    """Получает данные изображения `basename`.`ext`.
    Расширение игнорируется, если `ext` установлен в `None`.

    Args:
        basename: Базовое имя изображения.
        ext: Расширение изображения.

    Returns:
        Данные изображения.
    """
    img_path = image_path(basename, ext)
    try:
        with open(img_path, 'rb') as f_img:
            return base64.b64encode(f_img.read())
    except (IOError, OSError) as e:
        # Файл не может быть прочитан - ошибка логируется и пробрасывается дальше
        raise
