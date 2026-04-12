"""Модуль валидации конфигураций.

Предоставляет класс ConfigValidator для валидации конфигураций
и формирования подробных отчётов об ошибках.

Пример использования:
    >>> from parser_2gis.config import Configuration
    >>> from parser_2gis.config.config_validator import ConfigValidator
    >>> validator = ConfigValidator()
    >>> validator.validate(config)
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ValidationError


class ConfigValidator:
    """Валидатор конфигураций.

    Предоставляет методы для валидации конфигураций и обработки ошибок.
    Следует принципу единственной ответственности (SRP).

    Example:
        >>> validator = ConfigValidator()
        >>> if validator.validate(config):
        ...     print("Конфигурация валидна")

    """

    def validate(self, config: BaseModel) -> tuple[bool, list[str]]:
        """Валидирует конфигурацию.

        Args:
            config: Конфигурация для валидации.

        Returns:
            Кортеж (валидность, список ошибок).

        """
        if config is None:
            return False, ["Конфигурация не может быть None"]
        if not isinstance(config, BaseModel):
            return False, ["Конфигурация должна быть экземпляром Pydantic BaseModel"]
        # Pydantic валидирует автоматически при присваивании
        # Дополнительная явная валидация через model_validate
        try:
            type(config).model_validate(config.model_dump())
            return True, []
        except ValidationError as ex:
            return False, self.format_validation_errors(ex)

    @staticmethod
    def format_validation_errors(ex: ValidationError) -> list[str]:
        """Форматирует ошибки валидации в читаемый формат.

        Args:
            ex: Исключение валидации.

        Returns:
            Список строк с описанием ошибок.

        """
        from parser_2gis.utils import report_from_validation_error

        errors: list[str] = []
        errors_report = report_from_validation_error(ex)

        for attr_path, error in errors_report.items():
            error_msg = error.get("error_message", "неизвестная ошибка")
            errors.append(f"атрибут {attr_path} ({error_msg})")

        return errors

    @staticmethod
    def log_validation_errors(ex: ValidationError) -> None:
        """Логирует ошибки валидации.

        Args:
            ex: Исключение валидации.

        """
        from parser_2gis.logger.logger import logger as lazy_logger

        errors = ConfigValidator.format_validation_errors(ex)

        if errors:
            lazy_logger.warning("Ошибки валидации: %s", ", ".join(errors))
        else:
            lazy_logger.warning("Неизвестные ошибки валидации")

    @staticmethod
    def backup_corrupted_config(config_path: Path) -> None:
        """Создаёт резервную копию повреждённого файла конфигурации.

        Args:
            config_path: Путь к файлу конфигурации.

        """
        import shutil

        if not config_path.is_file():
            return

        backup_path = config_path.with_suffix(config_path.suffix + ".bak")
        try:
            shutil.copy2(config_path, backup_path)
            if backup_path.exists():
                from parser_2gis.logger.logger import logger as lazy_logger

                lazy_logger.warning(
                    "Создана резервная копия повреждённой конфигурации: %s", backup_path,
                )
                renamed_path = config_path.with_suffix(config_path.suffix + ".corrupted")
                config_path.rename(renamed_path)
                lazy_logger.warning(
                    "Оригинальный файл переименован: %s -> %s", config_path, renamed_path,
                )
            else:
                from parser_2gis.logger.logger import logger as lazy_logger

                lazy_logger.warning("Не удалось создать резервную копию: %s", backup_path)
        except OSError as copy_err:
            from parser_2gis.logger.logger import logger as lazy_logger

            lazy_logger.warning("Ошибка при создании резервной копии конфигурации: %s", copy_err)


__all__ = ["ConfigValidator"]
