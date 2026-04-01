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
from .cli.config_service import ConfigService
from .logger.logger import logger, logger as app_logger
from .logger import LogOptions
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
        # HIGH 7: Отслеживание посещённых объектов через id() для предотвращения циклических зависимостей
        visited_objects: set[int] = set()
        self._merge_models_recursive(
            source=other_config,
            target=self,
            current_depth=0,
            max_depth=max_depth,
            visited_objects=visited_objects,
            warning_shown=False,
        )

    @staticmethod
    def _merge_models_recursive(
        source: BaseModel,
        target: BaseModel,
        current_depth: int,
        max_depth: int,
        visited_objects: set[int],
        warning_shown: bool = False,
    ) -> bool:
        """Рекурсивно объединяет две Pydantic модели.

        Args:
            source: Исходная модель.
            target: Целевая модель.
            current_depth: Текущая глубина рекурсии.
            max_depth: Максимальная глубина.
            visited_objects: Множество id посещённых объектов для предотвращения циклов.
            warning_shown: Флаг показа предупреждения.

        Returns:
            Флаг показа предупреждения.

        Raises:
            RecursionError: При превышении максимальной глубины.
            ValueError: При обнаружении циклической ссылки.
        """
        warning_threshold = int(max_depth * 0.8)

        if current_depth >= max_depth:
            raise RecursionError(f"Превышена максимальная глубина обработки ({max_depth})")

        # HIGH 7: Проверка на циклические зависимости через id()
        source_id = id(source)
        if source_id in visited_objects:
            app_logger.warning(
                "Обнаружена циклическая ссылка на объект %s (id=%d). Пропускаем.",
                type(source).__name__,
                source_id,
            )
            return warning_shown

        visited_objects.add(source_id)

        if current_depth >= warning_threshold and not warning_shown:
            logger.warning(
                "Внимание: глубина обработки достигла %d/%d (80%% от лимита)",
                current_depth,
                max_depth,
            )
            warning_shown = True

        fields_set = Configuration._get_fields_set(source)

        for field in fields_set:
            try:
                source_value = getattr(source, field)

                if not isinstance(source_value, BaseModel):
                    setattr(target, field, source_value)
                else:
                    target_value = getattr(target, field, None)
                    if target_value is None:
                        setattr(target, field, deepcopy(source_value))
                    else:
                        warning_shown = Configuration._merge_models_recursive(
                            source=source_value,
                            target=target_value,
                            current_depth=current_depth + 1,
                            max_depth=max_depth,
                            visited_objects=visited_objects,
                            warning_shown=warning_shown,
                        )

            except (AttributeError, TypeError) as e:
                logger.warning("Ошибка при объединении поля %s: %s", field, e)
                raise
            except (ValueError, RuntimeError, OSError) as e:
                logger.error("Непредвиденная ошибка при объединении поля %s: %s", field, e)
                raise

        # HIGH 7: Удаляем объект из посещённых после обработки
        visited_objects.remove(source_id)
        return warning_shown

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
