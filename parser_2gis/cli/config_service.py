"""Сервис для операций с конфигурацией.

Предоставляет класс ConfigService для сохранения и загрузки конфигураций.
Выделен из config.py для соблюдения принципа единственной ответственности (SRP).

Назначение класса:
    ConfigService существует для разделения ответственности между:
    1. Configuration (модель данных) - хранение и валидация настроек
    2. ConfigService (сервис) - операции сохранения/загрузки из файла

    Это следует паттерну Service Layer и предотвращает нарушение SRP
    в классе Configuration.

Ответственность ConfigService:
    - Сохранение конфигурации в JSON файл
    - Загрузка конфигурации из JSON файла
    - Создание резервных копий при повреждении
    - Логирование операций с конфигурацией

    ConfigService НЕ должен:
    - Содержать бизнес-логику конфигурации
    - Модифицировать данные конфигурации
    - Зависеть от конкретных реализаций Configuration

Примечание:
    Логика merge_configs перемещена в класс Configuration для устранения
    нарушения Middle Man. Этот класс оставлен только для операций save/load.

Пример использования:
    >>> from parser_2gis.cli.config_service import ConfigService
    >>> from parser_2gis.config import Configuration
    >>> from pathlib import Path
    >>> config = Configuration()
    >>> ConfigService.save_config(config, Path("./config.json"))
    >>> loaded = ConfigService.load_config(Configuration, Path("./config.json"))
"""

from __future__ import annotations

import json
import pathlib
import shutil
from typing import Any

from pydantic import BaseModel, ValidationError

from parser_2gis.logger import logger
from parser_2gis.pydantic_compat import get_model_dump, model_validate_json
from parser_2gis.utils import report_from_validation_error
from parser_2gis.utils.paths import user_path


class ConfigService:
    """Сервис для операций с конфигурацией.

    Предоставляет статические методы для:
    - Сохранения конфигурации в файл
    - Загрузки конфигурации из файла
    - Создания резервных копий

    Этот класс реализует паттерн Service Layer для операций с конфигурацией.
    Все методы статические, так как сервис не хранит состояние.

    Принцип работы:
        1. save_config() - сериализует pydantic модель в JSON и сохраняет в файл
        2. load_config() - читает JSON из файла, валидирует и возвращает модель
        3. При ошибке валидации создаётся резервная копия повреждённого файла

    Обработка ошибок:
        - FileNotFoundError: создаётся конфигурация по умолчанию
        - ValidationError: создаётся резервная копия, возвращается default
        - JSONDecodeError: создаётся резервная копия, возвращается default
        - OSError: пробрасывается дальше для обработки вызывающим кодом

    Example:
        >>> from parser_2gis.cli.config_service import ConfigService
        >>> from parser_2gis.config import Configuration
        >>> config = Configuration()
        >>> ConfigService.save_config(config, Path("./config.json"))
        >>> loaded = ConfigService.load_config(Configuration, Path("./config.json"))

    Примечание:
        Методы merge_configs, _merge_models_iterative и связанные методы
        перемещены в класс Configuration для устранения Middle Man.

    """

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
            MemoryError: Если не хватает памяти для сериализации.

        """
        if not path:
            logger.warning("Путь для сохранения конфигурации не указан")
            return

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            config_dict: dict[str, Any] = get_model_dump(config, exclude={"path"})

            # ID:059: Обрабатываем MemoryError при json.dumps
            try:
                json_str = json.dumps(config_dict, ensure_ascii=False, indent=4)
            except MemoryError as mem_error:
                logger.error("Недостаточно памяти для сериализации конфигурации: %s", mem_error)
                raise

            with open(path, "w", encoding="utf-8") as f:
                f.write(json_str)

            logger.debug("Конфигурация сохранена: %s", path)

        except OSError as e:
            logger.error("Ошибка при создании директории для конфигурации: %s", e)
            raise OSError(f"Не удалось создать директорию: {path.parent}") from e
        except (TypeError, ValueError) as e:
            logger.error("Ошибка при сериализации конфигурации в JSON: %s", e)
            raise TypeError(f"Ошибка сериализации конфигурации: {e}") from e
        except (MemoryError, KeyboardInterrupt, SystemExit) as e:
            logger.error("Критическая ошибка при сохранении конфигурации: %s", e)
            raise
        except RuntimeError as e:
            logger.error("Непредвиденная ошибка при сохранении конфигурации: %s", e)
            raise RuntimeError(f"Непредвиденная ошибка при сохранении: {e}") from e

    @staticmethod
    def load_config(
        config_cls: type[BaseModel],
        config_path: pathlib.Path | None = None,
        *,
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

        if not config_path.is_file() and auto_create:
            config = config_cls(path=config_path)  # type: ignore[call-arg]
            ConfigService.save_config(config, config_path)
            logger.debug("Создан файл конфигурации: %s", config_path)
            return config
        elif not config_path.is_file():
            logger.info("Файл конфигурации не найден, используется конфигурация по умолчанию")
            return config_cls()  # type: ignore[call-arg]

        try:
            with open(config_path, encoding="utf-8") as f:
                config_data = f.read()
        except (FileNotFoundError, PermissionError, OSError) as file_error:
            logger.error("Ошибка чтения файла конфигурации: %s", file_error)
            return config_cls()  # type: ignore[call-arg]

        try:
            config = model_validate_json(config_data, config_cls)
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
            return config_cls()

    @staticmethod
    def _backup_corrupted_config(config_path: pathlib.Path) -> None:
        """Создаёт резервную копию повреждённого файла конфигурации.

        ID:061: Упрощённая логика без дублирования ConfigValidator.
        """
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
                    "Оригинальный файл переименован: %s -> %s", config_path, renamed_path,
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
