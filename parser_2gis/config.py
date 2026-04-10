"""Модуль конфигурации парсера.

Предоставляет класс Configuration для хранения настроек парсера.
Делегирует операции merge, validation и save/load специализированным сервисам.

Примечание:
    ISSUE-001: Конфигурация разделена на отдельные модули для соблюдения SRP:
    - Configuration (данные) - этот модуль
    - ConfigMerger (объединение) - config.config_merger
    - ConfigValidator (валидация) - config.config_validator
    - ConfigService (save/load) - cli.config_service

    ISSUE-027: Методы делегирования (merge_with, save_config, load_config, validate)
    оставлены для обратной совместимости, но вся логика вынесена в сервисы.

    ISSUE-035: Используется ленивый импорт ConfigService внутри методов
    вместо импорта на уровне модуля для устранения жёсткой зависимости.

    ISSUE-037: Вложенные модели опций используют default_factory через Field
    для ленивой инициализации при создании конфигурации.

Пример использования:
    >>> from parser_2gis.config import Configuration
    >>> config = Configuration()
    >>> config.merge_with(other_config)
"""

from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .version import config_version

if TYPE_CHECKING:
    from .chrome import ChromeOptions
    from .logger import LogOptions
    from .parallel import ParallelOptions
    from .parser import ParserOptions
    from .writer import WriterOptions

# =============================================================================
# PROTOCOL FOR CONFIG SERVICE (ISSUE-035)
# =============================================================================


@runtime_checkable
class ConfigServiceProtocol(Protocol):
    """Протокол сервиса конфигурации для устранения жёстких зависимостей.

    ISSUE-035: Определяет интерфейс ConfigService без прямого импорта.
    """

    @staticmethod
    def save_config(config: BaseModel, path: pathlib.Path) -> None:
        """Сохраняет конфигурацию в файл."""
        ...

    @staticmethod
    def load_config(
        config_cls: type[BaseModel], config_path: pathlib.Path | None = ..., auto_create: bool = ...,  # noqa: FBT001
    ) -> BaseModel:
        """Загружает конфигурацию из файла."""
        ...


# =============================================================================
# CONFIGURATION MODEL
# =============================================================================


class Configuration(BaseModel):
    """Модель конфигурации парсера.

    Хранит настройки парсера и делегирует операции специализированным сервисам.
    Следует принципу единственной ответственности (SRP).

    ISSUE-037: Вложенные модели опций создаются лениво через Field(default_factory=...)
    для предотвращения eager инициализации при импорте модуля.

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

    # ISSUE-037: Lazy creation через Field(default_factory=...)
    # Фабрики вызываются только при создании экземпляра, не при импорте
    log: LogOptions = Field(
        default_factory=lambda: __import__(
            "parser_2gis.logger", fromlist=["LogOptions"],
        ).LogOptions(),
    )
    writer: WriterOptions = Field(
        default_factory=lambda: __import__(
            "parser_2gis.writer", fromlist=["WriterOptions"],
        ).WriterOptions(),
    )
    chrome: ChromeOptions = Field(
        default_factory=lambda: __import__(
            "parser_2gis.chrome", fromlist=["ChromeOptions"],
        ).ChromeOptions(),
    )
    parser: ParserOptions = Field(
        default_factory=lambda: __import__(
            "parser_2gis.parser", fromlist=["ParserOptions"],
        ).ParserOptions(),
    )
    parallel: ParallelOptions = Field(
        default_factory=lambda: __import__(
            "parser_2gis.parallel", fromlist=["ParallelOptions"],
        ).ParallelOptions(),
    )
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

        ISSUE-035: Использует ленивый импорт внутри метода.

        Raises:
            OSError: При ошибке записи файла.

        """
        # ISSUE-035: Ленивый импорт ConfigService
        from .cli.config_service import ConfigService as _ConfigService

        if self.path:
            _ConfigService.save_config(config=self, path=self.path)
        else:
            from .logger.logger import logger as lazy_logger

            lazy_logger.warning("Путь для сохранения конфигурации не указан")

    @classmethod
    def load_config(
        cls, config_path: pathlib.Path | None = None, *, auto_create: bool = True,
    ) -> Configuration:
        """Загружает конфигурацию из файла.

        Делегирует операцию классу ConfigService.

        Args:
            config_path: Путь к файлу конфигурации.
            auto_create: Создать файл если не существует.

        Returns:
            Загруженная конфигурация.

        """
        # ISSUE-035: Ленивый импорт ConfigService
        from .cli.config_service import ConfigService as _ConfigService

        result = _ConfigService.load_config(
            config_cls=cls, config_path=config_path, auto_create=auto_create,
        )
        from typing import cast

        return cast("Configuration", result)

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


# Pydantic model rebuild для разрешения forward references
def _resolve_option_types() -> dict[str, type]:
    """Разрешает forward references для Pydantic."""
    from .chrome import ChromeOptions
    from .logger import LogOptions
    from .parallel import ParallelOptions
    from .parser import ParserOptions
    from .writer import WriterOptions

    return {
        "LogOptions": LogOptions,
        "WriterOptions": WriterOptions,
        "ChromeOptions": ChromeOptions,
        "ParserOptions": ParserOptions,
        "ParallelOptions": ParallelOptions,
    }


Configuration.model_rebuild(_types_namespace=_resolve_option_types(), raise_errors=True)
