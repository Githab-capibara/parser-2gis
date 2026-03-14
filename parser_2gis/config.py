from __future__ import annotations

import json
import pathlib
import shutil
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, ValidationError

from .chrome import ChromeOptions
from .common import report_from_validation_error
from .logger import LogOptions, logger
from .parser import ParserOptions
from .paths import user_path
from .version import config_version
from .writer import WriterOptions


class Configuration(BaseModel):
    """Модель конфигурации."""

    model_config = ConfigDict(validate_assignment=True)

    log: LogOptions = LogOptions()
    writer: WriterOptions = WriterOptions()
    chrome: ChromeOptions = ChromeOptions()
    parser: ParserOptions = ParserOptions()
    path: Optional[pathlib.Path] = None
    version: str = config_version

    def merge_with(self, other_config: Configuration) -> None:
        """Объединяет конфигурацию с другой.

        Рекурсивно обновляет поля текущей конфигурации значениями из other_config.
        Используются только явно установленные поля (model_fields_set / __fields_set__).

        Args:
            other_config: Конфигурация для объединения.

        Raises:
            ValueError: Если возникает конфликт типов при объединении.
            RecursionError: При превышении максимальной глубины рекурсии.
        """

        def assign_attributes(
            model_source: BaseModel,
            model_target: BaseModel,
            max_depth: int = 10,
            current_depth: int = 0,
            visited: Optional[set] = None,
        ) -> None:
            """Рекурсивно присваивает новые атрибуты к существующей конфигурации.

            Использует model_fields_set для получения набора установленных полей (Pydantic v2).
            Использует набор visited для предотвращения циклических ссылок.

            Args:
                model_source: Исходная модель.
                model_target: Целевая модель.
                max_depth: Максимальная глубина рекурсии (по умолчанию 10).
                current_depth: Текущая глубина рекурсии.
                visited: Набор посещённых объектов для предотвращения циклических ссылок.

            Raises:
                RecursionError: При превышении максимальной глубины рекурсии.
            """
            # Инициализируем набор посещённых объектов
            if visited is None:
                visited = set()

            # Проверка на циклические ссылки
            source_id = id(model_source)
            if source_id in visited:
                logger.warning("Обнаружена циклическая ссылка при объединении конфигурации")
                return

            visited.add(source_id)

            try:
                # Проверка глубины рекурсии
                if current_depth >= max_depth:
                    raise RecursionError(
                        f"Превышена максимальная глубина рекурсии ({max_depth}) при объединении конфигурации"
                    )

                # Определяем набор установленных полей (Pydantic v2)
                fields_set: Optional[set[str]] = model_source.model_fields_set  # type: ignore[attr-defined]

                if not fields_set:
                    fields_set = set()

                for field in fields_set:
                    try:
                        source_attr = getattr(model_source, field)

                        if not isinstance(source_attr, BaseModel):
                            # Присваиваем простое значение
                            setattr(model_target, field, source_attr)
                        else:
                            # Рекурсивно объединяем вложенные модели
                            target_attr = getattr(model_target, field, None)
                            if target_attr is None:
                                # Если целевой атрибут не существует, создаём копию
                                from copy import deepcopy
                                setattr(model_target, field, deepcopy(source_attr))
                            else:
                                assign_attributes(
                                    source_attr, target_attr, max_depth, current_depth + 1, visited
                                )

                    except (AttributeError, TypeError) as e:
                        logger.warning("Ошибка при объединении поля %s: %s", field, e)
                        raise
                    except Exception as e:
                        logger.error(
                            "Непредвиденная ошибка при объединении поля %s: %s", field, e
                        )
                        raise
            finally:
                # Удаляем из набора после обработки
                visited.discard(source_id)

        try:
            assign_attributes(other_config, self)
        except Exception as e:
            logger.error("Критическая ошибка при объединении конфигураций: %s", e)
            raise

    def save_config(self) -> None:
        """Сохраняет конфигурацию, если она была загружена из пути.

        Raises:
            OSError: Если не удалось сохранить файл конфигурации.
            TypeError: Если ошибка сериализации JSON.
            ValueError: Если ошибка валидации данных.
        """
        if not self.path:
            logger.warning("Путь для сохранения конфигурации не указан")
            return

        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)

            # Сериализация конфигурации в словарь (Pydantic v2)
            config_dict: Dict[str, Any] = self.model_dump(exclude={"path"})  # type: ignore[attr-defined]

            json_str = json.dumps(config_dict, ensure_ascii=False, indent=4)

            # Записываем конфигурацию в файл с кодировкой UTF-8
            with open(self.path, "w", encoding="utf-8") as f:
                f.write(json_str)

            logger.debug("Конфигурация сохранена: %s", self.path)

        except OSError as e:
            logger.error("Ошибка при создании директории для конфигурации: %s", e)
            raise
        except (TypeError, ValueError) as e:
            logger.error("Ошибка при сериализации конфигурации в JSON: %s", e)
            raise
        except Exception as e:
            logger.error("Непредвиденная ошибка при сохранении конфигурации: %s", e)
            raise

    @classmethod
    def load_config(
        cls, config_path: Optional[pathlib.Path] = None, auto_create: bool = True
    ) -> Configuration:
        """Загружает конфигурацию из пути. Если путь не указан,
        конфигурация загружается из пользовательского пути конфигурации.
        При возникновении ошибок во время загрузки метод возвращается к
        конфигурации по умолчанию.

        Примечание:
            Пользовательский путь конфигурации в зависимости от ОС:
            * Unix: ~/.config/parser-2gis/parser-2gis.config
            * Mac: ~/Library/Application Support/parser-2gis/parser-2gis.config
            * Win: C:\\Users\\%USERPROFILE%\\AppData\\Local\\parser-2gis/parser-2gis.config

        Args:
            config_path: Путь к файлу конфигурации. Если не указан, загружается пользовательская конфигурация.
            auto_create: Создать конфигурацию, если она не существует.

        Returns:
            Конфигурация.

        Raises:
            OSError: Если не удалось создать файл конфигурации.
        """
        if not config_path:
            user_config_path = user_path()
            if user_config_path is None:
                logger.warning(
                    "Не удалось определить пользовательский путь конфигурации, используется путь по умолчанию"
                )
                config_path = pathlib.Path.home() / ".config" / "parser-2gis"
            else:
                config_path = user_config_path / "parser-2gis.config"

        # Обработка случая когда файл не существует
        if not config_path.is_file():
            if auto_create:
                config = cls(path=config_path)
                config.save_config()
                logger.debug("Создан файл конфигурации: %s", config_path)
            else:
                logger.info("Файл конфигурации не найден, используется конфигурация по умолчанию")
                config = cls()
            return config

        # Загружаем существующий файл конфигурации
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = f.read()
        except (FileNotFoundError, PermissionError, OSError) as file_error:
            logger.error("Ошибка чтения файла конфигурации: %s", file_error)
            return cls()

        # Парсим конфигурацию
        try:
            config = cls.model_validate_json(config_data)  # type: ignore[attr-defined]
            config.path = config_path
            return config

        except (json.JSONDecodeError, ValueError) as json_error:
            logger.error("Повреждённый JSON в конфигурации: %s", json_error)
            return cls()
        except ValidationError as e:
            logger.warning("Ошибка валидации конфигурации")
            cls._backup_corrupted_config(config_path)
            cls._log_validation_errors(e)
            return cls()

        except Exception as e:
            logger.error("Непредвиденная ошибка при загрузке конфигурации: %s", e, exc_info=e)
            return cls()

        # Возвращаем конфигурацию по умолчанию при любой ошибке
        return cls()

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
                logger.warning("Оригинальный файл переименован: %s -> %s", config_path, renamed_path)
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
