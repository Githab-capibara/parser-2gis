from __future__ import annotations

import json
import pathlib
import shutil
from typing import Any, Dict, Optional, Set

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
        """

        def assign_attributes(
            model_source: BaseModel,
            model_target: BaseModel,
            max_depth: int = 10,
            current_depth: int = 0,
        ) -> None:
            """Рекурсивно присваивает новые атрибуты к существующей конфигурации.

            Примечание:
                Корректно определяет версию Pydantic и получает набор установленных полей.
                Для Pydantic v2 используется model_fields_set, для v1 - __fields_set__.

            Args:
                model_source: Исходная модель.
                model_target: Целевая модель.
                max_depth: Максимальная глубина рекурсии (по умолчанию 10).
                current_depth: Текущая глубина рекурсии.

            Raises:
                RecursionError: При превышении максимальной глубины рекурсии.
            """
            # Проверка глубины рекурсии
            if current_depth >= max_depth:
                raise RecursionError(
                    f"Превышена максимальная глубина рекурсии ({max_depth}) при объединении конфигурации"
                )

            # Определяем версию Pydantic и получаем набор установленных полей
            if hasattr(model_source, "model_fields_set"):
                # Pydantic v2
                fields_set: Optional[Set[str]] = model_source.model_fields_set
            elif hasattr(model_source, "__fields_set__"):
                # Pydantic v1
                fields_set = model_source.__fields_set__
            else:
                # Неизвестная версия Pydantic
                fields_set = set()

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
                        target_attr = getattr(model_target, field)
                        assign_attributes(
                            source_attr, target_attr, max_depth, current_depth + 1
                        )

                except (AttributeError, TypeError) as e:
                    logger.warning("Ошибка при объединении поля %s: %s", field, e)
                    raise
                except Exception as e:
                    logger.error(
                        "Непредвиденная ошибка при объединении поля %s: %s", field, e
                    )
                    raise

        try:
            assign_attributes(other_config, self)
        except Exception as e:
            logger.error("Критическая ошибка при объединении конфигураций: %s", e)
            raise

    def save_config(self) -> None:
        """Сохраняет конфигурацию, если она была загружена из пути.

        Raises:
            OSError: Если не удалось сохранить файл конфигурации.
        """
        if not self.path:
            logger.warning("Путь для сохранения конфигурации не указан")
            return

        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)

            # Используем model_dump() для Pydantic v2 или dict() для v1
            if hasattr(self, "model_dump"):
                # Pydantic v2
                config_dict: Dict[str, Any] = self.model_dump(exclude={"path"})
            else:
                # Pydantic v1
                config_dict = self.dict(exclude={"path"})

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

        try:
            if not config_path.is_file():
                if auto_create:
                    config = cls(path=config_path)
                    config.save_config()
                    logger.debug("Создан файл конфигурации: %s", config_path)
                else:
                    logger.info(
                        "Файл конфигурации не найден, используется конфигурация по умолчанию"
                    )
                    config = cls()
            else:
                # Используем model_validate_json для совместимости с Pydantic v2
                with open(config_path, "r", encoding="utf-8") as f:
                    config_data = f.read()

                try:
                    if hasattr(cls, "model_validate_json"):
                        # Pydantic v2
                        config = cls.model_validate_json(config_data)
                    else:
                        # Запасной вариант для Pydantic v1
                        config = cls.parse_raw(config_data)  # type: ignore
                    config.path = config_path

                except (json.JSONDecodeError, ValueError) as json_error:
                    # Повреждённый JSON файл конфигурации
                    logger.error("Повреждённый JSON в конфигурации: %s", json_error)
                    config = cls()

        except FileNotFoundError:
            # Файл конфигурации не найден и auto_create=False
            logger.warning("Файл конфигурации не найден: %s", config_path)
            config = cls()

        except ValidationError as e:
            # Ошибка валидации Pydantic
            logger.warning("Ошибка валидации конфигурации")

            # Создаём backup повреждённого файла конфигурации для отладки
            if config_path and config_path.is_file():
                backup_path = config_path.with_suffix(config_path.suffix + ".bak")
                try:
                    shutil.copy2(config_path, backup_path)
                    if backup_path.exists():
                        logger.warning(
                            "Создан backup повреждённой конфигурации: %s", backup_path
                        )
                        # Переименовываем оригинальный файл, чтобы избежать перезаписи
                        renamed_path = config_path.with_suffix(
                            config_path.suffix + ".corrupted"
                        )
                        config_path.rename(renamed_path)
                        logger.warning(
                            "Оригинальный файл переименован: %s -> %s",
                            config_path,
                            renamed_path,
                        )
                    else:
                        logger.warning("Не удалось создать backup: %s", backup_path)
                except OSError as copy_err:
                    logger.warning(
                        "Ошибка при создании backup конфигурации: %s", copy_err
                    )

            # Формируем детальное сообщение об ошибках
            errors = []
            errors_report = report_from_validation_error(e)
            for attr_path, error in errors_report.items():
                error_msg = error.get("error_message", "неизвестная ошибка")
                errors.append(f"атрибут {attr_path} ({error_msg})")

            if errors:
                logger.warning("Ошибки валидации: %s", ", ".join(errors))
            else:
                logger.warning("Неизвестные ошибки валидации")

            config = cls()

        except OSError as e:
            # Ошибка доступа к файлу
            logger.error("Ошибка доступа к файлу конфигурации: %s", e)
            config = cls()

        except Exception as e:
            # Любая другая непредвиденная ошибка
            logger.error(
                "Непредвиденная ошибка при загрузке конфигурации: %s", e, exc_info=e
            )
            config = cls()

        return config
