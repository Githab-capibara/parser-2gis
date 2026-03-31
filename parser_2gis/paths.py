"""
Модуль путей к ресурсам парсера.

DEPRECATED: Этот модуль перемещён в parser_2gis.utils.paths
Используйте: from parser_2gis.utils.paths import data_path, resources_path, user_path, image_path, cache_path
"""

from parser_2gis.utils.paths import (
    cache_path,
    data_path,
    image_data,
    image_path,
    resources_path,
    user_path,
)

__all__ = ["data_path", "resources_path", "user_path", "image_path", "image_data", "cache_path"]
