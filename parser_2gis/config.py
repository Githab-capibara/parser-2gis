"""
Модуль конфигурации парсера.

Предоставляет классы и функции для работы с конфигурацией,
включая валидацию, загрузку и сохранение настроек.
"""

from __future__ import annotations

import pathlib

from pydantic import BaseModel, ConfigDict, ValidationError

from .chrome import ChromeOptions
from .config_service import ConfigService
from .logger import LogOptions, logger
from .parallel import ParallelOptions
from .parser import ParserOptions
from .version import config_version
from .writer import WriterOptions


class Configuration(BaseModel):
    """Модель конфигурации."""

    model_config = ConfigDict(validate_assignment=True)

    log: LogOptions = LogOptions()
    writer: WriterOptions = WriterOptions()
    chrome: ChromeOptions = ChromeOptions()
    parser: ParserOptions = ParserOptions()
    parallel: ParallelOptions = ParallelOptions()
    path: pathlib.Path | None = None
    version: str = config_version

    def merge_with(self, other_config: Configuration, max_depth: int = 50) -> None:
        """Объединяет конфигурацию с другой.

        Рекурсивно обновляет поля текущей конфигурации значениями из other_config.
        Используются только явно установленные поля (model_fields_set / __fields_set__).

        Args:
            other_config: Конфигурация для объединения.
            max_depth: Максимальная глубина рекурсии при объединении (по умолчанию 50).

        Raises:
            ValueError: Если возникает конфликт типов при объединении.
        """
        ConfigService.merge_configs(source=other_config, target=self, max_depth=max_depth)

    @staticmethod
    def _merge_models_iterative(source: BaseModel, target: BaseModel, max_depth: int = 50) -> None:
        """Итеративно объединяет две Pydantic модели без рекурсии.

        Делегирует к ConfigService для устранения дублирования.
        """
        ConfigService._merge_models_iterative(source=source, target=target, max_depth=max_depth)

    @staticmethod
    def _is_cyclic_reference(model: BaseModel, visited: set[int]) -> bool:
        """Проверяет модель на наличие циклических ссылок."""
        return ConfigService._is_cyclic_reference(model=model, visited=visited)

    @staticmethod
    def _check_depth_limit(
        current_depth: int, max_depth: int, warning_threshold: int, warning_shown: bool
    ) -> bool:
        """Проверяет лимит глубины и выводит предупреждение при необходимости."""
        return ConfigService._check_depth_limit(
            current_depth=current_depth,
            max_depth=max_depth,
            warning_threshold=warning_threshold,
            warning_shown=warning_shown,
        )

    @staticmethod
    def _process_fields(
        source: BaseModel,
        target: BaseModel,
        fields_set: set[str],
        stack: list[tuple[BaseModel, BaseModel, int]],
        current_depth: int,
    ) -> None:
        """Обрабатывает поля исходной модели и обновляет целевую модель."""
        ConfigService._process_fields(
            source=source,
            target=target,
            fields_set=fields_set,
            stack=stack,
            current_depth=current_depth,
        )

    @staticmethod
    def _handle_nested_model(
        source_value: BaseModel,
        target: BaseModel,
        field: str,
        stack: list[tuple[BaseModel, BaseModel, int]],
        current_depth: int,
    ) -> None:
        """Обрабатывает вложенную модель при объединении."""
        ConfigService._handle_nested_model(
            source_value=source_value,
            target=target,
            field=field,
            stack=stack,
            current_depth=current_depth,
        )

    @staticmethod
    def _get_fields_set(model: BaseModel) -> set[str]:
        """Получает набор установленных полей модели."""
        return ConfigService._get_fields_set(model=model)

    def save_config(self) -> None:
        """Сохраняет конфигурацию, если она была загружена из пути."""
        if self.path:
            ConfigService.save_config(config=self, path=self.path)
        else:
            logger.warning("Путь для сохранения конфигурации не указан")

    @classmethod
    def load_config(
        cls, config_path: pathlib.Path | None = None, auto_create: bool = True
    ) -> Configuration:
        """Загружает конфигурацию из файла.

        Делегирует к ConfigService для устранения дублирования.
        """
        return ConfigService.load_config(
            config_cls=cls, config_path=config_path, auto_create=auto_create
        )  # type: ignore[return-value]

    @staticmethod
    def _backup_corrupted_config(config_path: pathlib.Path) -> None:
        """Создаёт резервную копию повреждённого файла конфигурации."""
        ConfigService._backup_corrupted_config(config_path)

    @staticmethod
    def _log_validation_errors(ex: ValidationError) -> None:
        """Формирует детальное сообщение об ошибках валидации."""
        ConfigService._log_validation_errors(ex)
