"""Сервисы конфигурации парсера.

Предоставляет сервисы для работы с конфигурацией:
- ConfigMerger - объединение конфигураций
- ConfigValidator - валидация конфигураций

Пример использования:
    >>> from parser_2gis.config_services import ConfigMerger, ConfigValidator
    >>> merger = ConfigMerger()
    >>> merger.merge(config1, config2)
"""

from parser_2gis.config_services.config_merger import ConfigMerger
from parser_2gis.config_services.config_validator import ConfigValidator

__all__ = ["ConfigMerger", "ConfigValidator"]
