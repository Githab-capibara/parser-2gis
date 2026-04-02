"""Модуль для файлового логирования.

Предоставляет функциональность для записи логов в файл с поддержкой вращения логов.
Автоматически создаёт файлы с timestamp в названии для каждой сессии.

Этот модуль выделен в отдельный пакет logging для устранения циклической
зависимости между logger и chrome модулями.
"""

import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path


class FileLogger:
    """Логгер с поддержкой записи в файл.

    Этот класс предоставляет возможность логирования работы парсера в файл
    для отладки и мониторинга. Поддерживает вращение логов (log rotation)
    для экономии дискового пространства.

    Автоматически создаёт новую сессию логирования для каждого запуска:
    - Файлы создаются в папке logs/
    - Имя файла: parser_YYYY-MM-DD_HH-MM-SS.log
    - Каждая сессия записывается в отдельный файл

    Attributes:
        _log_file: Путь к файлу логов
        _log_level: Уровень логирования
        _max_bytes: Максимальный размер файла в байтах
        _backup_count: Количество резервных копий
        _file_handler: Обработчик файла для логирования
        _log_dir: Директория для логов

    Пример использования:
        >>> logger = FileLogger(log_dir=Path('logs'), log_level='DEBUG')
        >>> logger.setup_logger(logging.getLogger('parser-2gis'))

    """

    def __init__(
        self,
        log_file: Path | None = None,
        log_dir: Path | None = None,
        log_level: str = "DEBUG",
        max_bytes: int = 10 * 1024 * 1024,  # 10 MB
        backup_count: int = 5,
        auto_session: bool = True,
    ):
        """Инициализация файлового логгера.

        Args:
            log_file: Путь к файлу логов. Если None и auto_session=True,
                файл создаётся автоматически.
            log_dir: Директория для логов (по умолчанию: logs/).
                Используется если auto_session=True.
            log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL).
            max_bytes: Максимальный размер файла в байтах перед вращением.
            backup_count: Количество резервных копий логов.
            auto_session: Автоматически создавать новую сессию с timestamp в имени файла.

        Raises:
            ValueError: Если log_level имеет некорректное значение.

        """
        self._log_file = log_file
        self._log_dir = log_dir or Path("logs")
        self._auto_session = auto_session

        # Валидация уровня логирования
        try:
            self._log_level = getattr(logging, log_level.upper())
        except AttributeError as err:
            raise ValueError(f"Некорректный уровень логирования: {log_level}") from err

        self._max_bytes = max_bytes
        self._backup_count = backup_count
        self._file_handler: RotatingFileHandler | None = None

        # Если включён автоматический режим сессий, генерируем имя файла
        if auto_session and log_file is None:
            self._log_file = self._generate_session_log_file()

        # Если указан файл логов, настраиваем обработчик
        if self._log_file:
            try:
                self._setup_file_handler()
            except OSError as e:
                # ID:137: Обрабатываем ошибку создания директории
                import sys

                sys.stderr.write(
                    f"Не удалось инициализировать файловый логгер: {e}. Файл: {self._log_file}\n"
                )
                # Не пробрасываем ошибку дальше, чтобы приложение могло работать без файлового логгера
                self._log_file = None

    def _generate_session_log_file(self) -> Path:
        """Сгенерировать имя файла лога для новой сессии.

        Returns:
            Путь к файлу лога с timestamp в названии

        """
        # Создаём директорию для логов
        self._log_dir.mkdir(parents=True, exist_ok=True)

        # Генерируем имя файла с датой и временем
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return self._log_dir / f"parser_{timestamp}.log"

    def _setup_file_handler(self) -> None:
        """Настройка обработчика файла для логирования.

        Создает директорию для логов если она не существует,
        и настраивает RotatingFileHandler для автоматического
        вращения логов при достижении максимального размера.
        Добавляет запись о начале новой сессии.

        Raises:
            OSError: При ошибке создания директории для логов.
            IOError: При ошибке создания файлового обработчика.

        """
        # ID:138: Используем try/finally для закрытия handler при ошибке
        handler_created = False

        try:
            # Создаём директорию для логов, если её нет
            if self._log_file:
                try:
                    self._log_file.parent.mkdir(parents=True, exist_ok=True)
                except OSError as e:
                    raise OSError(
                        f"Не удалось создать директорию для логов: {self._log_file.parent}. "
                        f"Ошибка: {e}. "
                        f"Функция: {self._setup_file_handler.__name__}"
                    ) from e

            # Создаём rotating file handler
            try:
                self._file_handler = RotatingFileHandler(
                    filename=str(self._log_file),
                    maxBytes=self._max_bytes,
                    backupCount=self._backup_count,
                    encoding="utf-8",
                )
                handler_created = True
            except OSError as e:
                raise OSError(
                    f"Ошибка создания RotatingFileHandler: {e}. "
                    f"Файл: {self._log_file}. "
                    f"Функция: {self._setup_file_handler.__name__}"
                ) from e

            # Форматирование логов с детальной информацией
            formatter = logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | "
                "%(funcName)s:%(lineno)d | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            self._file_handler.setFormatter(formatter)
            self._file_handler.setLevel(self._log_level)

            # Логируем начало сессии
            session_logger = logging.getLogger("parser-2gis")
            session_logger.info("=" * 80)
            session_logger.info("НАЧАЛО НОВОЙ СЕССИИ")
            session_logger.info(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            # Проверяем, что файл лога существует перед вызовом absolute()
            if self._log_file:
                session_logger.info(f"Файл лога: {self._log_file.absolute()}")
            session_logger.info("=" * 80)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            # ID:138: Закрываем handler если он был создан но настройка не удалась
            if handler_created and self._file_handler is not None:
                try:
                    self._file_handler.close()
                except Exception:
                    pass  # Игнорируем ошибку закрытия
                self._file_handler = None
            # Логируем ошибку в stderr
            import sys

            sys.stderr.write(
                f"Критическая ошибка при настройке файлового обработчика: {e}. "
                f"Функция: {self._setup_file_handler.__name__}, "
                f"Файл: {self._log_file}\n"
            )
            raise

    def setup_logger(self, logger: logging.Logger) -> None:
        """Настройка логгера для записи в файл.

        Добавляет файловый обработчик к указанному логгеру.
        Проверяет, не был ли handler уже добавлен.

        Args:
            logger: Логгер для настройки (экземпляр logging.Logger).

        Raises:
            RuntimeError: При ошибке добавления обработчика.

        """
        try:
            if self._file_handler:
                # ID:139: Проверяем, не был ли handler уже добавлен
                if self._file_handler in logger.handlers:
                    logger.debug("Файловый обработчик уже добавлен к логгеру %s", logger.name)
                    return

                logger.addHandler(self._file_handler)
                # Устанавливаем минимальный уровень логирования
                if logger.level == 0 or logger.level > self._log_level:
                    logger.setLevel(self._log_level)
        except Exception as e:
            raise RuntimeError(
                f"Ошибка добавления файлового обработчика к логгеру: {e}. "
                f"Функция: {self.setup_logger.__name__}, "
                f"Логгер: {logger.name}"
            ) from e

    def close(self) -> None:
        """Закрытие обработчика файла.

        Корректно закрывает файловый обработчик и освобождает ресурсы.
        Добавляет запись о завершении сессии.
        Должен вызываться при завершении работы программы.

        Raises:
            Exception: При ошибке закрытия обработчика.

        """
        try:
            if self._file_handler:
                # Логируем завершение сессии
                session_logger = logging.getLogger("parser-2gis")
                session_logger.info("=" * 80)
                session_logger.info("ЗАВЕРШЕНИЕ СЕССИИ")
                session_logger.info(
                    f"Время завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                session_logger.info("=" * 80)

                try:
                    self._file_handler.close()
                except Exception as e:
                    session_logger.error(
                        f"Ошибка закрытия файлового обработчика: {e}. "
                        f"Функция: {self.close.__name__}"
                    )
                finally:
                    self._file_handler = None
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            import sys

            sys.stderr.write(
                f"Ошибка при закрытии файлового логгера: {e}. Функция: {self.close.__name__}\n"
            )
            # Не пробрасываем ошибку, чтобы не нарушить завершение работы

    def __enter__(self) -> "FileLogger":
        """Контекстный менеджер для автоматического закрытия.

        Returns:
            Экземпляр FileLogger для использования в with-блоке.

        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Автоматическое закрытие при выходе из контекста."""
        self.close()

    @property
    def log_file(self) -> Path | None:
        """Путь к файлу логов.

        Returns:
            Путь к файлу логов или None, если логирование в файл отключено.

        """
        return self._log_file

    @property
    def is_enabled(self) -> bool:
        """Проверка, включено ли логирование в файл.

        Returns:
            True, если логирование в файл включено, иначе False.

        """
        return self._file_handler is not None
