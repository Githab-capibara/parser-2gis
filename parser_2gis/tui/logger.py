"""
TUI логгер для Parser2GIS.

Предоставляет логгер, который отправляет логи одновременно:
- В TUI панель (в реальном времени)
- В файл (подробный лог)
"""

from __future__ import annotations

import logging
import queue
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from rich.console import Console

if TYPE_CHECKING:
    from .components import LogPanel


class TUIHandler(logging.Handler):
    """
    Обработчик логов для TUI.

    Отправляет логи в панель логов TUI интерфейса.
    """

    def __init__(self, log_panel: LogPanel, console: Optional[Console] = None) -> None:
        """
        Инициализация обработчика.

        Args:
            log_panel: Панель логов для отображения
            console: Консоль для вывода (опционально)
        """
        super().__init__()
        self._log_panel = log_panel
        self._console = console or Console()
        self._log_queue: queue.Queue[tuple[str, str, str]] = queue.Queue()

    def emit(self, record: logging.LogRecord) -> None:
        """
        Эмит записи лога.

        Args:
            record: Запись лога
            
        Raises:
            Exception: При ошибке обработки записи лога.
        """
        try:
            msg = self.format(record)
            level = record.levelname

            # Добавляем в панель логов с обработкой ошибок
            try:
                self._log_panel.add_log(msg, level)
            except Exception as e:
                # Если не удалось добавить в панель, логируем ошибку
                sys.stderr.write(
                    f"Ошибка добавления лога в панель: {e}. "
                    f"Функция: {self.emit.__name__}, "
                    f"Уровень: {level}, "
                    f"Сообщение: {msg}\n"
                )

            # Также выводим в консоль с цветом
            level_colors = {
                "INFO": "cyan",
                "DEBUG": "dim white",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold red",
                "SUCCESS": "green",
            }
            color = level_colors.get(level, "white")
            self._console.print(f"[{color}]{msg}[/{color}]")

        except (KeyboardInterrupt, SystemExit):
            # Прерывание работы - не логируем, просто пробрасываем дальше
            raise
        except Exception as e:
            # Обрабатываем ошибку с полным контекстом
            error_details = (
                f"Ошибка в TUI обработчике логов: {e}. "
                f"Функция: {self.emit.__name__}, "
                f"Логгер: {getattr(record, 'name', 'unknown')}, "
                f"Уровень: {getattr(record, 'levelname', 'unknown')}, "
                f"Строка: {getattr(record, 'lineno', 'unknown')}, "
                f"Функция вызова: {getattr(record, 'funcName', 'unknown')}"
            )
            # Используем sys.stderr для вывода ошибки логирования
            sys.stderr.write(error_details + "\n")
            # Пробрасываем ошибку дальше через handleError
            self.handleError(record)


class TUILogger:
    """
    TUI логгер с поддержкой вывода в файл.

    Этот класс объединяет:
    - Визуальный вывод в TUI интерфейс
    - Подробное логирование в файл
    """

    def __init__(
        self,
        log_panel: LogPanel,
        log_dir: Optional[Path] = None,
        log_level: str = "DEBUG",
    ) -> None:
        """
        Инициализация TUI логгера.

        Args:
            log_panel: Панель логов для отображения
            log_dir: Директория для логов (по умолчанию: logs/)
            log_level: Уровень логирования
        """
        self._log_panel = log_panel
        self._log_dir = log_dir or Path("logs")
        self._log_level = getattr(logging, log_level.upper(), logging.DEBUG)
        self._log_file: Optional[Path] = None
        self._file_handler: Optional[logging.FileHandler] = None
        self._tui_handler: Optional[TUIHandler] = None
        self._logger: Optional[logging.Logger] = None

    def setup(self, logger_name: str = "parser-2gis") -> logging.Logger:
        """
        Настройка логгера.

        Args:
            logger_name: Имя логгера

        Returns:
            Настроенный логгер
            
        Raises:
            OSError: При ошибке создания директории для логов.
            IOError: При ошибке создания файлового обработчика.
            Exception: При других ошибках настройки логгера.
        """
        try:
            # Создаём директорию для логов с обработкой ошибок
            try:
                self._log_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise OSError(
                    f"Не удалось создать директорию для логов: {self._log_dir}. "
                    f"Ошибка: {e}. "
                    f"Функция: {self.setup.__name__}"
                ) from e

            # Генерируем имя файла с датой и временем
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            self._log_file = self._log_dir / f"parser_{timestamp}.log"

            # Получаем логгер
            self._logger = logging.getLogger(logger_name)
            self._logger.setLevel(self._log_level)

            # Очищаем старые обработчики
            self._logger.handlers.clear()

            # Настраиваем TUI обработчик с обработкой ошибок
            try:
                console = Console()
                self._tui_handler = TUIHandler(self._log_panel, console)
                tui_format = logging.Formatter("%(levelname)s: %(message)s")
                self._tui_handler.setFormatter(tui_format)
                self._tui_handler.setLevel(logging.INFO)
                self._logger.addHandler(self._tui_handler)
            except Exception as e:
                raise RuntimeError(
                    f"Ошибка настройки TUI обработчика: {e}. "
                    f"Функция: {self.setup.__name__}"
                ) from e

            # Настраиваем файловый обработчик (максимально подробный)
            try:
                self._file_handler = logging.FileHandler(
                    filename=str(self._log_file),
                    encoding="utf-8",
                )
                file_format = logging.Formatter(
                    fmt="%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
                self._file_handler.setFormatter(file_format)
                self._file_handler.setLevel(self._log_level)
                self._logger.addHandler(self._file_handler)
            except IOError as e:
                raise IOError(
                    f"Ошибка создания файлового обработчика: {e}. "
                    f"Файл: {self._log_file}. "
                    f"Функция: {self.setup.__name__}"
                ) from e

            # Логируем начало сессии
            self._logger.info("=" * 80)
            self._logger.info("НАЧАЛО СЕССИИ PARSER2GIS")
            self._logger.info(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self._logger.info(f"Файл лога: {self._log_file.absolute()}")
            self._logger.info("=" * 80)

            return self._logger
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            # Логируем ошибку в stderr, так как логгер ещё не настроен
            sys.stderr.write(
                f"Критическая ошибка при настройке TUI логгера: {e}. "
                f"Функция: {self.setup.__name__}, "
                f"Директория: {self._log_dir}\n"
            )
            raise

    def close(self) -> None:
        """Закрыть логгер и освободить ресурсы.
        
        Raises:
            Exception: При ошибке закрытия обработчиков.
        """
        try:
            if self._logger:
                self._logger.info("=" * 80)
                self._logger.info("ЗАВЕРШЕНИЕ СЕССИИ")
                self._logger.info(f"Время завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                self._logger.info("=" * 80)

                # Закрываем обработчики с обработкой ошибок
                for handler in self._logger.handlers:
                    try:
                        handler.close()
                    except Exception as e:
                        sys.stderr.write(
                            f"Ошибка закрытия обработчика логов: {e}. "
                            f"Функция: {self.close.__name__}, "
                            f"Обработчик: {handler.__class__.__name__}\n"
                        )
                self._logger.handlers.clear()
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            sys.stderr.write(
                f"Ошибка при закрытии TUI логгера: {e}. "
                f"Функция: {self.close.__name__}\n"
            )
            # Не пробрасываем ошибку дальше, чтобы не нарушить завершение работы

    @property
    def log_file(self) -> Optional[Path]:
        """Путь к файлу лога."""
        return self._log_file

    @property
    def logger(self) -> Optional[logging.Logger]:
        """Логгер."""
        return self._logger


def setup_tui_logger(
    log_panel: LogPanel,
    log_dir: Optional[Path] = None,
    log_level: str = "DEBUG",
) -> tuple[logging.Logger, TUILogger]:
    """
    Настроить TUI логгер.

    Args:
        log_panel: Панель логов для отображения
        log_dir: Директория для логов
        log_level: Уровень логирования

    Returns:
        Кортеж (логгер, TUILogger)
    """
    tui_logger = TUILogger(log_panel, log_dir, log_level)
    logger = tui_logger.setup()
    return logger, tui_logger
