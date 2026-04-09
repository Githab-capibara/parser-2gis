"""Модуль конфигурации парсера.

Предоставляет класс Configuration для хранения настроек парсера.
Делегирует операции merge, validation и save/load специализированным сервисам.

Примечание:
    ISSUE-001: Конфигурация разделена на отдельные модули для соблюдения SRP:
    - Configuration (данные) - этот модуль
    - ConfigMerger (объединение) - config.config_merger
    - ConfigValidator (валидация) - config.config_validator
    - ConfigService (save/load) - cli.config_service

Пример использования:
    >>> from parser_2gis.config import Configuration
    >>> config = Configuration()
    >>> config.merge_with(other_config)
"""

from __future__ import annotations

import pathlib
from typing import TypeAlias

from pydantic import BaseModel, ConfigDict, ValidationError

from .chrome import ChromeOptions
from .cli.config_service import ConfigService
from .logger import LogOptions
from .parallel import ParallelOptions
from .parser import ParserOptions
from .version import config_version
from .writer import WriterOptions

# =============================================================================
# TYPE ALIASES FOR COMPLEX TYPES
# =============================================================================

ConfigFieldsSet: TypeAlias = set[str]


class Configuration(BaseModel):
    """Модель конфигурации парсера.

    Хранит настройки парсера и делегирует операции специализированным сервисам.
    Следует принципу единственной ответственности (SRP).

    Attributes:
        log: Настройки логирования.
        writer: Настройки вывода данных.
        chrome: Настройки браузера Chrome.
        parser: Настройки парсера.
        parallel: Настройки параллельного парсинга.
        path: Путь к файлу конфигурации.
        version: Версия конфигурации.

    Example:
        >>> config = Configuration()
        >>> config.merge_with(other_config)
        >>> config.save_config()

    """

    model_config = ConfigDict(validate_assignment=True)

    log: LogOptions = LogOptions()
    writer: WriterOptions = WriterOptions()
    chrome: ChromeOptions = ChromeOptions()
    parser: ParserOptions = ParserOptions()
    parallel: ParallelOptions = ParallelOptions()
    path: pathlib.Path | None = None
    version: str = config_version

    def merge_with(self, other_config: Configuration, max_depth: int = 20) -> None:
        """Объединяет конфигурацию с другой.

        Делегирует логику объединения классу ConfigMerger.

        Args:
            other_config: Конфигурация для объединения.
            max_depth: Максимальная глубина рекурсии (по умолчанию 20).

        Example:
            >>> config1 = Configuration()
            >>> config2 = Configuration()
            >>> config1.merge_with(config2)

        """
        from .config_services import ConfigMerger

        ConfigMerger.merge(self, other_config, max_depth=max_depth)

    def save_config(self) -> None:
        """Сохраняет конфигурацию в файл.

        Делегирует операцию классу ConfigService.

        Raises:
            OSError: При ошибке записи файла.

        """
        if self.path:
            ConfigService.save_config(config=self, path=self.path)
        else:
            from .logger.logger import logger as lazy_logger

            lazy_logger.warning("Путь для сохранения конфигурации не указан")

    @classmethod
    def load_config(
        cls, config_path: pathlib.Path | None = None, auto_create: bool = True
    ) -> Configuration:
        """Загружает конфигурацию из файла.

        Делегирует операцию классу ConfigService.

        Args:
            config_path: Путь к файлу конфигурации.
            auto_create: Создать файл если не существует.

        Returns:
            Загруженная конфигурация.

        """
        result = ConfigService.load_config(
            config_cls=cls, config_path=config_path, auto_create=auto_create
        )
        # ConfigService.load_config возвращает ConfigService.T, который связан с cls
        # mypy не может вывести что T == Configuration, но это гарантировано логикой
        from typing import cast

        return cast(Configuration, result)

    def validate(self) -> tuple[bool, list[str]]:  # pylint: disable=arguments-renamed
        """Валидирует конфигурацию.

        Делегирует операцию классу ConfigValidator.

        Returns:
            Кортеж (валидность, список ошибок).

        """
        from .config_services import ConfigValidator

        validator = ConfigValidator()
        return validator.validate(self)

    @staticmethod
    def format_validation_errors(ex: ValidationError) -> list[str]:
        """Форматирует ошибки валидации.

        Args:
            ex: Исключение валидации.

        Returns:
            Список строк с описанием ошибок.

        """
        from .config_services import ConfigValidator

        return ConfigValidator.format_validation_errors(ex)

    @staticmethod
    def log_validation_errors(ex: ValidationError) -> None:
        """Логирует ошибки валидации.

        Args:
            ex: Исключение валидации.

        """
        from .config_services import ConfigValidator

        ConfigValidator.log_validation_errors(ex)

    @staticmethod
    def backup_corrupted_config(config_path: pathlib.Path) -> None:
        """Создаёт резервную копию повреждённого файла конфигурации.

        Args:
            config_path: Путь к файлу конфигурации.

        """
        from .config_services import ConfigValidator

        ConfigValidator.backup_corrupted_config(config_path)
