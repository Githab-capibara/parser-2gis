"""
Модуль конфигурации парсера.

Предоставляет классы и функции для работы с конфигурацией,
включая валидацию, загрузку и сохранение настроек.

Примечание:
    Логика merge_configs перемещена из ConfigService в Configuration
    для устранения нарушения Middle Man (SRP).
    ConfigService оставлен только для операций save/load.
"""

from __future__ import annotations

import pathlib
from copy import deepcopy

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

    def merge_with(self, other_config: "Configuration", max_depth: int = 50) -> None:
        """Объединяет конфигурацию с другой.

        Рекурсивно обновляет поля текущей конфигурации значениями из other_config.
        Используются только явно установленные поля (model_fields_set / __fields_set__).

        Args:
            other_config: Конфигурация для объединения.
            max_depth: Максимальная глубина рекурсии при объединении (по умолчанию 50).

        Raises:
            RecursionError: При превышении максимальной глубины.
            ValueError: При конфликте типов.

        Note:
            При достижении 80% от max_depth выводится предупреждение.
        """
        self._merge_models_iterative(source=other_config, target=self, max_depth=max_depth)

    @staticmethod
    def _merge_models_iterative(source: BaseModel, target: BaseModel, max_depth: int = 50) -> None:
        """Итеративно объединяет две Pydantic модели без рекурсии.

        Использует стек вместо рекурсии для предотвращения RecursionError.

        Args:
            source: Исходная модель.
            target: Целевая модель.
            max_depth: Максимальная глубина.
        """
        warning_threshold: int = int(max_depth * 0.8)
        warning_shown: bool = False
        stack: list[tuple[BaseModel, BaseModel, int]] = [(source, target, 0)]
        visited: set[int] = set()

        while stack:
            current_source, current_target, current_depth = stack.pop()

            if Configuration._is_cyclic_reference(current_source, visited):
                logger.warning("Обнаружена циклическая ссылка при объединении конфигурации")
                continue

            warning_shown = Configuration._check_depth_limit(
                current_depth=current_depth,
                max_depth=max_depth,
                warning_threshold=warning_threshold,
                warning_shown=warning_shown,
            )

            fields_set = Configuration._get_fields_set(current_source)
            Configuration._process_fields(
                source=current_source,
                target=current_target,
                fields_set=fields_set,
                stack=stack,
                current_depth=current_depth,
            )

            visited.discard(id(current_source))

    @staticmethod
    def _is_cyclic_reference(model: BaseModel, visited: set[int]) -> bool:
        """Проверяет модель на циклические ссылки."""
        model_id = id(model)
        if model_id in visited:
            return True
        visited.add(model_id)
        return False

    @staticmethod
    def _check_depth_limit(
        current_depth: int, max_depth: int, warning_threshold: int, warning_shown: bool
    ) -> bool:
        """Проверяет лимит глубины и выводит предупреждение."""
        if current_depth >= max_depth:
            raise RecursionError(f"Превышена максимальная глубина обработки ({max_depth})")

        if current_depth >= warning_threshold and not warning_shown:
            logger.warning(
                "Внимание: глубина обработки достигла %d/%d (80%% от лимита)",
                current_depth,
                max_depth,
            )
            warning_shown = True

        return warning_shown

    @staticmethod
    def _process_fields(
        source: BaseModel,
        target: BaseModel,
        fields_set: set[str],
        stack: list[tuple[BaseModel, BaseModel, int]],
        current_depth: int,
    ) -> None:
        """Обрабатывает поля исходной модели."""

        for field in fields_set:
            try:
                source_value = getattr(source, field)

                if not isinstance(source_value, BaseModel):
                    setattr(target, field, source_value)
                else:
                    Configuration._handle_nested_model(
                        source_value=source_value,
                        target=target,
                        field=field,
                        stack=stack,
                        current_depth=current_depth,
                    )

            except (AttributeError, TypeError) as e:
                logger.warning("Ошибка при объединении поля %s: %s", field, e)
                raise
            except (ValueError, RuntimeError, OSError) as e:
                logger.error("Непредвиденная ошибка при объединении поля %s: %s", field, e)
                raise

    @staticmethod
    def _handle_nested_model(
        source_value: BaseModel,
        target: BaseModel,
        field: str,
        stack: list[tuple[BaseModel, BaseModel, int]],
        current_depth: int,
    ) -> None:
        """Обрабатывает вложенную модель."""
        target_value = getattr(target, field, None)

        if target_value is None:
            setattr(target, field, deepcopy(source_value))
        else:
            stack.append((source_value, target_value, current_depth + 1))

    @staticmethod
    def _get_fields_set(model: BaseModel) -> set[str]:
        """Получает набор установленных полей модели."""
        from parser_2gis.pydantic_compat import get_model_fields_set

        fields_set: set[str] | None = get_model_fields_set(model)
        return fields_set if fields_set else set()

    def save_config(self) -> None:
        """Сохраняет конфигурацию, если она была загружена из пути."""
        if self.path:
            ConfigService.save_config(config=self, path=self.path)
        else:
            logger.warning("Путь для сохранения конфигурации не указан")

    @classmethod
    def load_config(
        cls, config_path: pathlib.Path | None = None, auto_create: bool = True
    ) -> "Configuration":
        """Загружает конфигурацию из файла.

        Делегирует к ConfigService для операций save/load.
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
        from parser_2gis.utils import report_from_validation_error

        errors = []
        errors_report = report_from_validation_error(ex)
        for attr_path, error in errors_report.items():
            error_msg = error.get("error_message", "неизвестная ошибка")
            errors.append(f"атрибут {attr_path} ({error_msg})")

        if errors:
            logger.warning("Ошибки валидации: %s", ", ".join(errors))
        else:
            logger.warning("Неизвестные ошибки валидации")
