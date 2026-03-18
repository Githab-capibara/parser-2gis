from __future__ import annotations

import json
import pathlib
import shutil
from copy import deepcopy
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, ConfigDict, ValidationError

from .chrome import ChromeOptions
from .common import report_from_validation_error
from .logger import LogOptions, logger
from .parser import ParserOptions
from .paths import user_path
from .pydantic_compat import (
    get_model_dump,
    get_model_fields_set,
    model_validate_json_class,
)
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

    def merge_with(self, other_config: Configuration, max_depth: int = 50) -> None:
        """Объединяет конфигурацию с другой.

        Рекурсивно обновляет поля текущей конфигурации значениями из other_config.
        Используются только явно установленные поля (model_fields_set / __fields_set__).

        Args:
            other_config: Конфигурация для объединения.
            max_depth: Максимальная глубина рекурсии при объединении (по умолчанию 50).
                      Увеличьте если конфигурация имеет глубокую вложенность.

        Raises:
            ValueError: Если возникает конфликт типов при объединении.
            RecursionWarning: При приближении к лимиту глубины (80% от max_depth).

        Example:
            >>> config = Configuration()
            >>> other = Configuration(chrome=ChromeOptions(headless=True))
            >>> config.merge_with(other)  # Обновляет только chrome.headless
            >>> config.merge_with(other, max_depth=100)  # С увеличенной глубиной
        """
        self._merge_models_iterative(
            source=other_config,
            target=self,
            max_depth=max_depth,
        )

    @staticmethod
    def _merge_models_iterative(
        source: BaseModel,
        target: BaseModel,
        max_depth: int = 50,
    ) -> None:
        """Итеративно объединяет две Pydantic модели без рекурсии.

        Использует стек для обработки вложенных моделей, что предотвращает
        RecursionError при глубокой вложенности.

        Алгоритм работы:
            1. Инициализируем стек кортежем (source, target, depth=0)
            2. Пока стек не пуст, извлекаем текущую пару моделей
            3. Проверяем на циклические ссылки и превышение глубины
            4. Для каждого поля source:
               - Если простое значение → копируем в target
               - Если вложенная модель → добавляем в стек для обработки
            5. Повторяем пока стек не опустеет

        Args:
            source: Исходная модель для чтения значений.
            target: Целевая модель для обновления.
            max_depth: Максимальная глубина обработки (по умолчанию 50).

        Raises:
            RecursionError: При превышении максимальной глубины.

        Note:
            При достижении 80% от max_depth выводится предупреждение в лог.
        """
        # Инициализируем константы для контроля глубины
        warning_threshold: int = int(
            max_depth * 0.8
        )  # 80% от лимита для предупреждения
        warning_shown: bool = False

        # Стек содержит кортежи: (source_model, target_model, current_depth)
        # Используем стек вместо рекурсии для предотвращения RecursionError
        stack: List[tuple[BaseModel, BaseModel, int]] = [(source, target, 0)]

        # Набор для отслеживания посещённых объектов (предотвращение циклических ссылок)
        visited: Set[int] = set()

        while stack:
            # Извлекаем текущую пару моделей из стека
            current_source, current_target, current_depth = stack.pop()

            # Проверка на циклические ссылки
            if Configuration._is_cyclic_reference(current_source, visited):
                logger.warning(
                    "Обнаружена циклическая ссылка при объединении конфигурации"
                )
                continue

            # Проверка и обновление порога предупреждения о глубине
            warning_shown = Configuration._check_depth_limit(
                current_depth=current_depth,
                max_depth=max_depth,
                warning_threshold=warning_threshold,
                warning_shown=warning_shown,
            )

            # Получаем набор установленных полей исходной модели
            fields_set = Configuration._get_fields_set(current_source)

            # Обрабатываем каждое поле
            Configuration._process_fields(
                source=current_source,
                target=current_target,
                fields_set=fields_set,
                stack=stack,
                current_depth=current_depth,
            )

            # Удаляем из посещённых после успешной обработки
            visited.discard(id(current_source))

    @staticmethod
    def _is_cyclic_reference(model: BaseModel, visited: Set[int]) -> bool:
        """Проверяет модель на наличие циклических ссылок.

        Args:
            model: Pydantic модель для проверки.
            visited: Множество уже посещённых ID объектов.

        Returns:
            True если модель уже была посещена (циклическая ссылка), False иначе.
        """
        model_id = id(model)
        if model_id in visited:
            return True
        visited.add(model_id)
        return False

    @staticmethod
    def _check_depth_limit(
        current_depth: int,
        max_depth: int,
        warning_threshold: int,
        warning_shown: bool,
    ) -> bool:
        """Проверяет лимит глубины и выводит предупреждение при необходимости.

        Args:
            current_depth: Текущая глубина обработки.
            max_depth: Максимально разрешённая глубина.
            warning_threshold: Порог для вывода предупреждения (80% от max_depth).
            warning_shown: Флаг, было ли уже показано предупреждение.

        Returns:
            Обновлённый флаг warning_shown.

        Raises:
            RecursionError: Если текущая глубина превышает max_depth.
        """
        # Проверка на превышение максимальной глубины
        if current_depth >= max_depth:
            raise RecursionError(
                f"Превышена максимальная глубина обработки ({max_depth}) при объединении конфигурации"
            )

        # Вывод предупреждения при приближении к лимиту
        if current_depth >= warning_threshold and not warning_shown:
            logger.warning(
                "Внимание: глубина обработки достигла %d/%d (80%% от лимита). "
                "Возможна сложная вложенность конфигурации.",
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
        """Обрабатывает поля исходной модели и обновляет целевую модель.

        Для простых значений выполняется прямое присваивание.
        Для вложенных моделей - добавление в стек для последующей обработки.

        Args:
            source: Исходная модель для чтения значений.
            target: Целевая модель для обновления.
            fields_set: Набор имён полей для обработки.
            stack: Стек для обработки вложенных моделей.
            current_depth: Текущая глубина обработки.

        Raises:
            AttributeError: При ошибке доступа к полю.
            TypeError: При конфликте типов данных.
            Exception: При непредвиденных ошибках.
        """
        for field in fields_set:
            try:
                source_value = getattr(source, field)

                if not isinstance(source_value, BaseModel):
                    # Простое значение (строка, число, булево и т.д.) - прямое присваивание
                    setattr(target, field, source_value)
                else:
                    # Вложенная модель - рекурсивная обработка через стек
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
            except Exception as e:
                logger.error(
                    "Непредвиденная ошибка при объединении поля %s: %s", field, e
                )
                raise

    @staticmethod
    def _handle_nested_model(
        source_value: BaseModel,
        target: BaseModel,
        field: str,
        stack: List[tuple[BaseModel, BaseModel, int]],
        current_depth: int,
    ) -> None:
        """Обрабатывает вложенную модель при объединении.

        Если целевое поле отсутствует - создаётся копия.
        Если целевое поле существует - добавляется в стек для обработки.

        Args:
            source_value: Вложенная модель из источника.
            target: Целевая модель для обновления.
            field: Имя поля вложенной модели.
            stack: Стек для обработки вложенных моделей.
            current_depth: Текущая глубина обработки.
        """
        target_value = getattr(target, field, None)

        if target_value is None:
            # Целевой атрибут не существует - создаём глубокую копию
            setattr(target, field, deepcopy(source_value))
        else:
            # Целевой атрибут существует - добавляем в стек для рекурсивной обработки
            # Увеличиваем глубину на 1 для отслеживания вложенности
            stack.append((source_value, target_value, current_depth + 1))

    @staticmethod
    def _get_fields_set(model: BaseModel) -> Set[str]:
        """Получает набор установленных полей модели.

        Args:
            model: Pydantic модель.

        Returns:
            Набор имён установленных полей.
        """
        fields_set: Optional[Set[str]] = get_model_fields_set(model)
        return fields_set if fields_set else set()

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

            # Сериализация конфигурации в словарь (поддержка Pydantic v1 и v2)
            config_dict: Dict[str, Any] = get_model_dump(self, exclude={"path"})

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
                logger.info(
                    "Файл конфигурации не найден, используется конфигурация по умолчанию"
                )
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
            config = model_validate_json_class(cls, config_data)
            config.path = config_path  # type: ignore[assignment]
            return config  # type: ignore[return-value]

        except (json.JSONDecodeError, ValueError) as json_error:
            logger.error("Повреждённый JSON в конфигурации: %s", json_error)
            return cls()
        except ValidationError as e:
            logger.warning("Ошибка валидации конфигурации")
            cls._backup_corrupted_config(config_path)
            cls._log_validation_errors(e)
            return cls()

        except Exception as e:
            logger.error(
                "Непредвиденная ошибка при загрузке конфигурации: %s", e, exc_info=e
            )
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
                logger.warning(
                    "Создана резервная копия повреждённой конфигурации: %s", backup_path
                )
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
                logger.warning("Не удалось создать резервную копию: %s", backup_path)
        except OSError as copy_err:
            logger.warning(
                "Ошибка при создании резервной копии конфигурации: %s", copy_err
            )

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
