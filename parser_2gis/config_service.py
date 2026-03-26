"""
Сервис для операций с конфигурацией.

Предоставляет класс ConfigService для сохранения, загрузки и объединения конфигураций.
Выделен из config.py для соблюдения принципа единственной ответственности (SRP).
"""

from __future__ import annotations

import json
import pathlib
import shutil
from copy import deepcopy
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, ValidationError

from .logger import logger
from .paths import user_path
from .pydantic_compat import get_model_dump, get_model_fields_set, model_validate_json_class
from .utils import report_from_validation_error


class ConfigService:
    """Сервис для операций с конфигурацией.

    Предоставляет статические методы для:
    - Сохранения конфигурации в файл
    - Загрузки конфигурации из файла
    - Объединения конфигураций
    - Создания резервных копий

    Example:
        >>> from parser_2gis.config_service import ConfigService
        >>> config = Configuration()
        >>> ConfigService.save_config(config, Path("./config.json"))
        >>> loaded = ConfigService.load_config(Path("./config.json"))
        >>> ConfigService.merge_configs(source, target)
    """

    @staticmethod
    def merge_configs(source: BaseModel, target: BaseModel, max_depth: int = 50) -> None:
        """Объединяет две конфигурации.

        Рекурсивно обновляет поля target значениями из source.
        Используются только явно установленные поля (model_fields_set).

        Args:
            source: Исходная конфигурация для чтения значений.
            target: Целевая конфигурация для обновления.
            max_depth: Максимальная глубина рекурсии (по умолчанию 50).

        Raises:
            RecursionError: При превышении максимальной глубины.
            ValueError: При конфликте типов.

        Note:
            При достижении 80% от max_depth выводится предупреждение.
        """
        ConfigService._merge_models_iterative(source=source, target=target, max_depth=max_depth)

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
        stack: List[tuple[BaseModel, BaseModel, int]] = [(source, target, 0)]
        visited: Set[int] = set()

        while stack:
            current_source, current_target, current_depth = stack.pop()

            if ConfigService._is_cyclic_reference(current_source, visited):
                logger.warning("Обнаружена циклическая ссылка при объединении конфигурации")
                continue

            warning_shown = ConfigService._check_depth_limit(
                current_depth=current_depth,
                max_depth=max_depth,
                warning_threshold=warning_threshold,
                warning_shown=warning_shown,
            )

            fields_set = ConfigService._get_fields_set(current_source)
            ConfigService._process_fields(
                source=current_source,
                target=current_target,
                fields_set=fields_set,
                stack=stack,
                current_depth=current_depth,
            )

            visited.discard(id(current_source))

    @staticmethod
    def _is_cyclic_reference(model: BaseModel, visited: Set[int]) -> bool:
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
        fields_set: Set[str],
        stack: List[tuple[BaseModel, BaseModel, int]],
        current_depth: int,
    ) -> None:
        """Обрабатывает поля исходной модели."""
        for field in fields_set:
            try:
                source_value = getattr(source, field)

                if not isinstance(source_value, BaseModel):
                    setattr(target, field, source_value)
                else:
                    ConfigService._handle_nested_model(
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
        stack: List[tuple[BaseModel, BaseModel, int]],
        current_depth: int,
    ) -> None:
        """Обрабатывает вложенную модель."""
        target_value = getattr(target, field, None)

        if target_value is None:
            setattr(target, field, deepcopy(source_value))
        else:
            stack.append((source_value, target_value, current_depth + 1))

    @staticmethod
    def _get_fields_set(model: BaseModel) -> Set[str]:
        """Получает набор установленных полей модели."""
        fields_set: Optional[Set[str]] = get_model_fields_set(model)
        return fields_set if fields_set else set()

    @staticmethod
    def save_config(config: BaseModel, path: pathlib.Path) -> None:
        """Сохраняет конфигурацию в файл.

        Args:
            config: Конфигурация для сохранения.
            path: Путь к файлу конфигурации.

        Raises:
            OSError: Если не удалось создать директорию или записать файл.
            TypeError: Если ошибка сериализации JSON.
            ValueError: Если ошибка валидации данных.
        """
        if not path:
            logger.warning("Путь для сохранения конфигурации не указан")
            return

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            config_dict: Dict[str, Any] = get_model_dump(config, exclude={"path"})
            json_str = json.dumps(config_dict, ensure_ascii=False, indent=4)

            with open(path, "w", encoding="utf-8") as f:
                f.write(json_str)

            logger.debug("Конфигурация сохранена: %s", path)

        except OSError as e:
            logger.error("Ошибка при создании директории для конфигурации: %s", e)
            raise
        except (TypeError, ValueError) as e:
            logger.error("Ошибка при сериализации конфигурации в JSON: %s", e)
            raise
        except (RuntimeError, MemoryError, KeyboardInterrupt, SystemExit) as e:
            logger.error("Непредвиденная ошибка при сохранении конфигурации: %s", e)
            raise

    @staticmethod
    def load_config(
        config_cls: type[BaseModel],
        config_path: Optional[pathlib.Path] = None,
        auto_create: bool = True,
    ) -> BaseModel:
        """Загружает конфигурацию из файла.

        Args:
            config_cls: Класс конфигурации для загрузки.
            config_path: Путь к файлу конфигурации.
            auto_create: Создать конфигурацию если она не существует.

        Returns:
            Загруженная конфигурация.

        Raises:
            OSError: Если не удалось создать файл конфигурации.
        """
        if not config_path:
            user_config_path = user_path()
            if user_config_path is None:
                logger.warning("Не удалось определить пользовательский путь конфигурации")
                config_path = pathlib.Path.home() / ".config" / "parser-2gis"
            else:
                config_path = user_config_path / "parser-2gis.config"

        if not config_path.is_file():
            if auto_create:
                config = config_cls(path=config_path)  # type: ignore[call-arg]
                ConfigService.save_config(config, config_path)
                logger.debug("Создан файл конфигурации: %s", config_path)
            else:
                logger.info("Файл конфигурации не найден, используется конфигурация по умолчанию")
                config = config_cls()  # type: ignore[call-arg]
            return config

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = f.read()
        except (FileNotFoundError, PermissionError, OSError) as file_error:
            logger.error("Ошибка чтения файла конфигурации: %s", file_error)
            return config_cls()  # type: ignore[call-arg]

        try:
            config = model_validate_json_class(config_cls, config_data)
            config.path = config_path  # type: ignore[attr-defined]
            return config  # type: ignore[return-value]

        except ValidationError as e:
            logger.warning("Ошибка валидации конфигурации")
            ConfigService._backup_corrupted_config(config_path)
            ConfigService._log_validation_errors(e)
            return config_cls()  # type: ignore[call-arg]
        except (json.JSONDecodeError, ValueError) as json_error:
            logger.error("Повреждённый JSON в конфигурации: %s", json_error)
            return config_cls()  # type: ignore[call-arg]
        except (OSError, RuntimeError, TypeError) as e:
            logger.error("Непредвиденная ошибка при загрузке конфигурации: %s", e, exc_info=e)
            return config_cls()  # type: ignore[call-arg]

        return config_cls()  # type: ignore[call-arg]

    @staticmethod
    def _backup_corrupted_config(config_path: pathlib.Path) -> None:
        """Создаёт резервную копию повреждённого файла конфигурации."""
        if not config_path.is_file():
            return

        backup_path = config_path.with_suffix(config_path.suffix + ".bak")
        try:
            shutil.copy2(config_path, backup_path)
            if backup_path.exists():
                logger.warning("Создана резервная копия повреждённой конфигурации: %s", backup_path)
                renamed_path = config_path.with_suffix(config_path.suffix + ".corrupted")
                config_path.rename(renamed_path)
                logger.warning(
                    "Оригинальный файл переименован: %s -> %s", config_path, renamed_path
                )
            else:
                logger.warning("Не удалось создать резервную копию: %s", backup_path)
        except OSError as copy_err:
            logger.warning("Ошибка при создании резервной копии конфигурации: %s", copy_err)

    @staticmethod
    def _log_validation_errors(ex: ValidationError) -> None:
        """Формирует детальное сообщение об ошибках валидации."""
        errors = []
        errors_report = report_from_validation_error(ex)
        for attr_path, error in errors_report.items():
            error_msg = error.get("error_message", "неизвестная ошибка")
            errors.append(f"атрибут {attr_path} ({error_msg})")

        if errors:
            logger.warning("Ошибки валидации: %s", ", ".join(errors))
        else:
            logger.warning("Неизвестные ошибки валидации")


__all__ = ["ConfigService"]
