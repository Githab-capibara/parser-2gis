"""Информация о версии пакета parser-2gis.

Содержит константы с версией пакета и версией конфигурации.
Используется для отображения версии в CLI и логировании.

Пример использования:
    >>> from parser_2gis.version import VERSION, CONFIG_VERSION
    >>> print(f"Версия парсера: {VERSION}")
    Версия парсера: 2.1.12
    >>> print(f"Версия конфигурации: {CONFIG_VERSION}")
    Версия конфигурации: 0.1
"""

VERSION: str = "2.1.12"
CONFIG_VERSION: str = "0.1"

# Алиасы для обратной совместимости
version: str = "2.1.12"
config_version: str = CONFIG_VERSION

__all__ = ["CONFIG_VERSION", "VERSION", "config_version", "version"]
