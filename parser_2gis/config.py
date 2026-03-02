from __future__ import annotations

import pathlib
import shutil
from json import JSONDecodeError
from typing import Optional

from pydantic import BaseModel, ConfigDict, ValidationError

from .chrome import ChromeOptions
from .common import report_from_validation_error
from .logger import LogOptions, logger
from .parser import ParserOptions
from .paths import user_path
from .version import config_version
from .writer import WriterOptions


class Configuration(BaseModel):
    """Configuration model."""
    model_config = ConfigDict(validate_assignment=True)
    
    log: LogOptions = LogOptions()
    writer: WriterOptions = WriterOptions()
    chrome: ChromeOptions = ChromeOptions()
    parser: ParserOptions = ParserOptions()
    path: Optional[pathlib.Path] = None
    version: str = config_version

    def merge_with(self, other_config: Configuration) -> None:
        """Объединяет конфигурацию с другой."""
        def assign_attributes(model_source: BaseModel,
                              model_target: BaseModel) -> None:
            """Рекурсивно присваивает новые атрибуты к существующей конфигурации."""
            # Используем model_fields_set для совместимости с Pydantic v2
            fields_set = getattr(model_source, 'model_fields_set', None)
            if fields_set is None:
                # Fallback для Pydantic v1
                fields_set = getattr(model_source, '__fields_set__', set())

            for field in fields_set:
                source_attr = getattr(model_source, field)
                if not isinstance(source_attr, BaseModel):
                    setattr(model_target, field, source_attr)
                else:
                    target_attr = getattr(model_target, field)
                    # Рекурсивно объединяем вложенные модели
                    assign_attributes(source_attr, target_attr)

        assign_attributes(other_config, self)

    def save_config(self) -> None:
        """Сохраняет конфигурацию, если она была загружена из пути."""
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            # Используем model_dump_json для совместимости с Pydantic v2
            import json
            if hasattr(self, 'model_dump_json'):
                json_str = self.model_dump_json(exclude={'path'}, ensure_ascii=False)
                # Форматируем JSON с отступами
                data = json.loads(json_str)
                json_str = json.dumps(data, ensure_ascii=False, indent=4)
            else:
                # Fallback для Pydantic v1
                json_str = self.json(exclude={'path'}, ensure_ascii=False, indent=4)
            with open(self.path, 'w', encoding='utf-8') as f:
                f.write(json_str)

    @classmethod
    def load_config(cls, config_path: pathlib.Path | None = None,
                    auto_create: bool = True) -> Configuration:
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
        """
        if not config_path:
            config_path = user_path() / 'parser-2gis.config'

        try:
            if not config_path.is_file():
                if auto_create:
                    config = cls(path=config_path)
                    config.save_config()
                    logger.debug('Создан файл конфигурации: %s', config_path)
                else:
                    config = cls()
            else:
                # Используем model_validate_json для совместимости с Pydantic v2
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = f.read()

                if hasattr(cls, 'model_validate_json'):
                    config = cls.model_validate_json(config_data)
                else:
                    # Fallback для Pydantic v1
                    from pydantic import parse_raw_as
                    config = parse_raw_as(cls, config_data)
                config.path = config_path
        except (JSONDecodeError, ValidationError) as e:
            # Создаём backup повреждённого файла конфигурации для отладки
            if config_path and config_path.is_file():
                backup_path = config_path.with_suffix(config_path.suffix + '.bak')
                try:
                    shutil.copy2(config_path, backup_path)
                    if backup_path.exists():
                        logger.warning('Создан backup повреждённой конфигурации: %s', backup_path)
                    else:
                        logger.warning('Не удалось создать backup: %s', backup_path)
                except OSError as copy_err:
                    logger.warning('Ошибка при создании backup конфигурации: %s', copy_err)

            warning_msg = 'Не удалось загрузить конфигурацию: '
            if isinstance(e, ValidationError):
                errors = []
                errors_report = report_from_validation_error(e)
                for attr_path, error in errors_report.items():
                    error_msg = error['error_message']
                    errors.append(f'атрибут {attr_path} ({error_msg})')

                warning_msg += ', '.join(errors)
            else:
                warning_msg += str(e)

            logger.warning(warning_msg)
            config = cls()

        return config
