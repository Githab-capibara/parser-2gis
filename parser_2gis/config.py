"""Модуль конфигурации парсера.

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
from typing import TypeAlias

from .chrome import ChromeOptions
from .cli.config_service import ConfigService
from .logger import LogOptions

# Убран прямой импорт logger для устранения циклической зависимости (A011)
# Используется lazy import внутри методов
from .parallel import ParallelOptions
from .parser import ParserOptions
from .version import config_version
from .writer import WriterOptions

# =============================================================================
# TYPE ALIASES FOR COMPLEX TYPES
# =============================================================================

ConfigFieldsSet: TypeAlias = set[str]


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

    def merge_with(self, other_config: Configuration, max_depth: int = 20) -> None:
        """Объединяет конфигурацию с другой.

        Рекурсивно обновляет поля текущей конфигурации значениями из other_config.
        Используются только явно установленные поля (model_fields_set / __fields_set__).

        ISSUE-058: Уменьшена максимальная глубина рекурсии с 50 до 20.

        Args:
            other_config: Конфигурация для объединения.
            max_depth: Максимальная глубина рекурсии при объединении (по умолчанию 20).

        Raises:
            RecursionError: При превышении максимальной глубины.
            ValueError: При конфликте типов.

        Note:
            При достижении 80% от max_depth выводится предупреждение.

        """
        visited_objects: set[int] = set()
        self._merge_recursive_safe(
            source=other_config,
            target=self,
            current_depth=0,
            max_depth=max_depth,
            visited_objects=visited_objects,
        )

    def _check_recursion_depth(self, current_depth: int, max_depth: int) -> None:
        """Проверяет глубину рекурсии при объединении конфигураций.

        ISSUE-056: Добавлен подробный docstring.

        Args:
            current_depth: Текущая глубина рекурсии.
            max_depth: Максимально допустимая глубина рекурсии.

        Raises:
            RecursionError: При превышении максимальной глубины обработки.

        Example:
            >>> config = Configuration()
            >>> config._check_recursion_depth(10, 50)  # Не вызывает исключений
            >>> config._check_recursion_depth(60, 50)  # Вызывает RecursionError

        """
        if current_depth >= max_depth:
            raise RecursionError(f"Превышена максимальная глубина обработки ({max_depth})")

    def _check_circular_reference(self, source: BaseModel, visited_objects: set[int]) -> bool:
        """Проверяет наличие циклических ссылок в объектах конфигурации.

        ISSUE-057: Добавлен подробный docstring.

        Args:
            source: Исходный объект Pydantic BaseModel для проверки.
            visited_objects: Множество ID уже посещённых объектов для обнаружения циклов.

        Returns:
            True если обнаружена циклическая ссылка, False иначе.

        Note:
            При обнаружении циклической ссылки выводится предупреждение в лог
            и ссылка пропускается для предотвращения бесконечной рекурсии.

        Example:
            >>> config = Configuration()
            >>> visited: set[int] = set()
            >>> config._check_circular_reference(some_model, visited)
            False

        """
        source_id = id(source)
        if source_id in visited_objects:
            # Lazy import для устранения циклической зависимости (A011)
            from .logger.logger import logger as lazy_logger

            lazy_logger.warning(
                "Обнаружена циклическая ссылка на объект %s (id=%d). Пропускаем.",
                type(source).__name__,
                source_id,
            )
            return True
        visited_objects.add(source_id)
        return False

    def _log_depth_warning(self, current_depth: int, max_depth: int) -> bool:
        """Выводит предупреждение о глубине рекурсии."""
        warning_threshold = int(max_depth * 0.8)
        if current_depth >= warning_threshold:
            # Lazy import для устранения циклической зависимости (A011)
            from .logger.logger import logger as lazy_logger

            lazy_logger.warning(
                "Внимание: глубина обработки достигла %d/%d (80%% от лимита)",
                current_depth,
                max_depth,
            )
            return True
        return False

    def _merge_primitive_field(self, target: BaseModel, field: str, source: BaseModel) -> None:
        """Объединяет примитивное поле."""
        source_value = getattr(source, field)
        setattr(target, field, source_value)

    def _merge_nested_model(
        self,
        target: BaseModel,
        field: str,
        source: BaseModel,
        current_depth: int,
        max_depth: int,
        visited_objects: set[int],
    ) -> None:
        """Объединяет вложенную модель."""
        source_value = getattr(source, field)
        target_value = getattr(target, field, None)

        if target_value is None:
            setattr(target, field, deepcopy(source_value))
        else:
            self._merge_recursive_safe(
                source=source_value,
                target=target_value,
                current_depth=current_depth + 1,
                max_depth=max_depth,
                visited_objects=visited_objects,
            )

    def _merge_recursive_safe(
        self,
        source: BaseModel,
        target: BaseModel,
        current_depth: int,
        max_depth: int,
        visited_objects: set[int],
    ) -> None:
        """Безопасно объединяет две Pydantic модели рекурсивно с итеративным подходом.

        ISSUE-048: Удалена неиспользуемая переменная warning_shown.
        """
        # Проверка глубины рекурсии
        self._check_recursion_depth(current_depth, max_depth)

        # Проверка на циклические ссылки
        if self._check_circular_reference(source, visited_objects):
            return

        # Предупреждение о глубине
        self._log_depth_warning(current_depth, max_depth)

        # Получаем установленные поля
        fields_set = self._get_fields_set(source)

        # Обрабатываем каждое поле итеративно
        for field in fields_set:
            source_value = getattr(source, field, None)

            if not isinstance(source_value, BaseModel):
                # Примитивное поле
                self._merge_primitive_field(target, field, source)
            else:
                # Вложенная модель
                self._merge_nested_model(
                    target=target,
                    field=field,
                    source=source,
                    current_depth=current_depth,
                    max_depth=max_depth,
                    visited_objects=visited_objects,
                )

        # Удаляем объект из посещённых после обработки
        visited_objects.discard(id(source))

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
            # Lazy import для устранения циклической зависимости (A011)
            from .logger.logger import logger as lazy_logger

            lazy_logger.warning("Путь для сохранения конфигурации не указан")

    @classmethod
    def load_config(
        cls, config_path: pathlib.Path | None = None, auto_create: bool = True
    ) -> Configuration:
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

        # Lazy import для устранения циклической зависимости (A011)
        from .logger.logger import logger as lazy_logger

        errors = []
        errors_report = report_from_validation_error(ex)
        for attr_path, error in errors_report.items():
            error_msg = error.get("error_message", "неизвестная ошибка")
            errors.append(f"атрибут {attr_path} ({error_msg})")

        if errors:
            lazy_logger.warning("Ошибки валидации: %s", ", ".join(errors))
        else:
            lazy_logger.warning("Неизвестные ошибки валидации")
