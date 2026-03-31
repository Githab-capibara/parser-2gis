"""
Модуль для управления браузером Chrome с временным профилем.

Предоставляет класс ChromeBrowser для запуска и управления браузером Chrome
с временным профилем, который автоматически удаляется после закрытия.

Особенности:
- Автоматическое создание и удаление временного профиля
- Проверка возраста профиля для предотвращения использования старых данных
- Очистка orphaned профилей
- Безопасное завершение работы браузера

Пример использования:
    >>> from .browser import ChromeBrowser
    >>> from .options import ChromeOptions
    >>> options = ChromeOptions()
    >>> browser = ChromeBrowser(options)
    >>> browser.init()
    >>> # ... работа с браузером ...
    >>> browser.close()
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
import weakref
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from parser_2gis.logger.logger import logger as app_logger

from .constants import SECONDS_PER_HOUR
from .exceptions import ChromePathNotFound
from .utils import free_port, locate_chrome_path

if TYPE_CHECKING:
    from .options import ChromeOptions


# =============================================================================
# КЛАСС 1: BrowserPathResolver - Поиск и валидация пути к браузеру
# =============================================================================


class BrowserPathResolver:
    """
    Класс для поиска и валидации пути к браузеру Chrome.

    Отвечает за:
    - Поиск пути к браузеру (автоматически или заданный вручную)
    - Валидацию пути (существование, исполняемость)
    - Нормализацию пути (разрешение symlink)

    Пример использования:
        >>> resolver = BrowserPathResolver()
        >>> path = resolver.resolve_path(chrome_options)
    """

    def resolve_path(self, chrome_options: ChromeOptions) -> str:
        """
        Получает и валидирует путь к браузеру.

        Args:
            chrome_options: Опции Chrome для получения пути.

        Returns:
            Валидированный путь к браузеру.

        Raises:
            ChromePathNotFound: Если путь к Chrome не найден.
            ValueError: Если путь некорректен.
            FileNotFoundError: Если файл не существует.
            PermissionError: Если файл не исполняемый.
        """
        binary_path: str | None = None

        if chrome_options.binary_path:
            # Конвертируем Path в str если необходимо
            if isinstance(chrome_options.binary_path, Path):
                binary_path = str(chrome_options.binary_path)
            else:
                binary_path = chrome_options.binary_path
        else:
            binary_path = locate_chrome_path()

        if not binary_path:
            app_logger.error("Путь к Chrome браузеру не найден")
            raise ChromePathNotFound

        # Проверка и нормализация пути для предотвращения symlink атак
        if os.path.islink(binary_path):
            app_logger.warning(
                "Путь к браузеру содержит символическую ссылку: %s. "
                "Это может быть потенциально опасно (symlink атака). "
                "Путь будет нормализован через realpath.",
                binary_path,
            )

        # Нормализация пути через realpath
        original_binary_path = binary_path
        binary_path = os.path.realpath(binary_path)

        if original_binary_path != binary_path:
            app_logger.debug(
                "Путь к браузеру нормализован: %s → %s", original_binary_path, binary_path
            )

        app_logger.debug("Повторная валидация пути к браузеру после нормализации: %s", binary_path)
        self._validate_binary_path(binary_path)
        app_logger.debug("Запуск Chrome браузера по пути: %s", binary_path)

        return binary_path

    def _validate_binary_path(self, binary_path: str) -> None:
        """
        Валидирует путь к исполняемому файлу браузера.

        Args:
            binary_path: Путь к браузеру для валидации.

        Raises:
            ValueError: Если путь не абсолютный или указывает на директорию.
            FileNotFoundError: Если файл не существует.
            PermissionError: Если файл не исполняемый (для Unix).
        """
        # Проверка на абсолютный путь
        if not os.path.isabs(binary_path):
            raise ValueError(f"Путь к браузеру должен быть абсолютным: {binary_path}")

        # Проверка существования файла
        if not os.path.exists(binary_path):
            raise FileNotFoundError(f"Путь к браузеру не существует: {binary_path}")

        # Проверка, что это файл (не директория)
        if not os.path.isfile(binary_path):
            raise ValueError(f"Путь к браузеру должен указывать на файл: {binary_path}")

        # Проверка на исполняемость (только для Linux/Unix)
        # ВАЖНО: Выбрасываем PermissionError вместо простого логирования
        # Это предотвращает запуск браузера с некорректными правами
        if not os.access(binary_path, os.X_OK):
            error_msg = f"Файл браузера не имеет прав на выполнение: {binary_path}"
            app_logger.error(error_msg)
            raise PermissionError(error_msg)


# =============================================================================
# КЛАСС 2: ProfileManager - Управление профилем Chrome
# =============================================================================


class ProfileManager:
    """
    Класс для управления временным профилем Chrome.

    Отвечает за:
    - Создание временной директории профиля
    - Управление правами доступа к профилю
    - Очистку профиля после использования

    Пример использования:
        >>> manager = ProfileManager()
        >>> profile_path = manager.create_profile()
        >>> manager.cleanup_profile(profile_path)
    """

    def __init__(self) -> None:
        """Инициализирует менеджер профиля."""
        self._profile_tempdir: Optional[tempfile.TemporaryDirectory] = None
        self._profile_path: Optional[str] = None

    def create_profile(self) -> tuple[tempfile.TemporaryDirectory, str]:
        """
        Создаёт временную директорию профиля.

        Returns:
            Кортеж (TemporaryDirectory, путь к профилю).

        Raises:
            OSError: Если не удалось создать директорию.
        """
        self._profile_tempdir = tempfile.TemporaryDirectory(prefix="chrome_profile_")
        self._profile_path = self._profile_tempdir.name

        # Устанавливаем restrictive права на директорию профиля (0o700)
        try:
            os.chmod(self._profile_path, 0o700)
        except OSError as chmod_error:
            app_logger.warning(
                "Не удалось установить права 0o700 на профиль %s: %s. "
                "Профиль будет автоматически удалён при закрытии.",
                self._profile_path,
                chmod_error,
            )

        return self._profile_tempdir, self._profile_path

    def cleanup_profile(self) -> None:
        """
        Очищает временный профиль Chrome.

        Использует TemporaryDirectory.cleanup() с fallback на shutil.rmtree().
        """
        profile_cleanup_error: Optional[Exception] = None

        try:
            if self._profile_tempdir is not None:
                self._profile_tempdir.cleanup()
                app_logger.debug(
                    "Временный профиль Chrome удалён через TemporaryDirectory.cleanup()"
                )
        except (OSError, IOError) as profile_error:
            app_logger.error(
                "Ошибка ОС/IO при удалении профиля через TemporaryDirectory: %s",
                profile_error,
                exc_info=True,
            )
            profile_cleanup_error = profile_error
        except (RuntimeError, AttributeError, ValueError) as profile_error:
            app_logger.error(
                "Непредвиденная ошибка при удалении профиля через TemporaryDirectory: %s",
                profile_error,
                exc_info=True,
            )
            profile_cleanup_error = profile_error
        finally:
            # Fallback очистка через shutil.rmtree() если TemporaryDirectory не удался
            if profile_cleanup_error is not None and self._profile_path:
                try:
                    shutil.rmtree(self._profile_path, ignore_errors=True)
                    app_logger.debug("Профиль удалён через fallback shutil.rmtree()")
                except (OSError, IOError) as fallback_error:
                    app_logger.error(
                        "Ошибка ОС/IO при fallback очистке профиля: %s",
                        fallback_error,
                        exc_info=True,
                    )
                except (RuntimeError, AttributeError, ValueError) as fallback_error:
                    app_logger.error(
                        "Непредвиденная ошибка при fallback очистке профиля: %s",
                        fallback_error,
                        exc_info=True,
                    )

    @property
    def profile_path(self) -> Optional[str]:
        """Возвращает путь к профилю."""
        return self._profile_path

    @property
    def profile_tempdir(self) -> Optional[tempfile.TemporaryDirectory]:
        """Возвращает TemporaryDirectory профиля."""
        return self._profile_tempdir


# =============================================================================
# КЛАСС 3: ProcessManager - Управление процессом Chrome
# =============================================================================


class ProcessManager:
    """
    Класс для управления процессом Chrome.

    Отвечает за:
    - Запуск процесса Chrome
    - Завершение процесса (graceful и forceful)
    - Мониторинг состояния процесса

    Пример использования:
        >>> manager = ProcessManager()
        >>> proc = manager.launch_process(chrome_cmd, profile_path, options)
        >>> manager.terminate_process(proc.pid)
    """

    def __init__(self) -> None:
        """Инициализирует менеджер процесса."""
        self._proc: Optional[subprocess.Popen] = None
        self._start_time: float = 0.0

    def launch_process(
        self, chrome_cmd: list[str], profile_path: str, chrome_options: ChromeOptions
    ) -> subprocess.Popen:
        """
        Запускает процесс Chrome.

        Args:
            chrome_cmd: Команда запуска Chrome.
            profile_path: Путь к профилю.
            chrome_options: Опции Chrome.

        Returns:
            Процесс Chrome.

        Raises:
            ValueError: Если chrome_cmd пуст или некорректен.
            Exception: При ошибке запуска.
        """
        # Валидация аргументов перед запуском subprocess
        if not chrome_cmd:
            app_logger.error("chrome_cmd не может быть пустым")
            raise ValueError("chrome_cmd не может быть пустым")

        if not isinstance(chrome_cmd, list):
            app_logger.error("chrome_cmd должен быть списком")
            raise TypeError("chrome_cmd должен быть списком")

        if any(arg is None for arg in chrome_cmd):
            app_logger.error("chrome_cmd содержит None значения")
            raise TypeError("chrome_cmd не должен содержать None значения")

        self._start_time = time.time()

        try:
            if chrome_options.silent_browser:
                app_logger.debug("В Chrome отключён вывод отладочной информации.")
                proc = subprocess.Popen(
                    chrome_cmd, shell=False, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL
                )
            else:
                proc = subprocess.Popen(chrome_cmd, shell=False)

            self._proc = proc
            app_logger.debug("Chrome браузер запущен с PID: %d", proc.pid)
            return proc

        except (subprocess.SubprocessError, OSError, FileNotFoundError, ValueError, TypeError) as e:
            app_logger.error("Ошибка при запуске Chrome браузера: %s", e)
            # Очистка профиля при ошибке запуска
            try:
                shutil.rmtree(profile_path, ignore_errors=True)
            except (OSError, IOError) as cleanup_error:
                app_logger.debug("Не удалось удалить профиль при ошибке запуска: %s", cleanup_error)
            raise

    def terminate(self, process_pid: int, timeout: int = 5) -> tuple[bool, str]:
        """
        Завершает процесс через terminate() (graceful shutdown).

        H2: Упрощённый метод для корректного завершения процесса.
        Объединяет логику terminate_process_graceful.

        Args:
            process_pid: PID процесса для завершения.
            timeout: Таймаут ожидания завершения в секундах.

        Returns:
            Кортеж (process_closed, process_status):
            - process_closed: True если процесс завершён
            - process_status: Статус завершения процесса
        """
        if self._proc is None:
            app_logger.debug("Процесс не инициализирован (PID: %s)", process_pid)
            return False, "no_process"

        try:
            app_logger.debug("Отправка SIGTERM процессу %d", process_pid)
            self._proc.terminate()

            # Проверка poll() для обнаружения завершения процесса
            poll_result = self._proc.poll()
            if poll_result is not None:
                process_status = f"terminated (exit code: {poll_result})"
                app_logger.info(
                    "Chrome браузер корректно завершён (PID: %d, exit code: %d, время жизни: %.1f сек)",
                    process_pid,
                    poll_result,
                    time.time() - self._start_time,
                )
                return True, process_status
            else:
                # Процесс ещё работает, ждём завершения с timeout
                try:
                    self._proc.wait(timeout=timeout)
                    app_logger.info(
                        "Chrome браузер корректно завершён (PID: %d, время ожидания: %d сек)",
                        process_pid,
                        timeout,
                    )
                    return True, "terminated"
                except subprocess.TimeoutExpired:
                    app_logger.warning(
                        "Таймаут (%d сек) при завершении Chrome PID %d", timeout, process_pid
                    )
                    return False, "terminate_timeout"

        except ProcessLookupError as proc_error:
            app_logger.debug("Процесс уже завершён: %s", proc_error)
            return True, "already_terminated"
        except PermissionError as perm_error:
            app_logger.error("Нет прав на завершение процесса: %s", perm_error)
            return False, "permission_denied"
        except (OSError, subprocess.SubprocessError, ValueError) as terminate_error:
            app_logger.warning(
                "Ошибка при завершении Chrome (PID %d): %s (тип: %s)",
                process_pid,
                terminate_error,
                type(terminate_error).__name__,
            )
            return False, "terminate_error"

    def kill(self, process_pid: int, timeout: int = 10) -> tuple[bool, str]:
        """
        Принудительно завершает процесс через kill() (forceful shutdown).

        H2: Упрощённый метод для принудительного завершения процесса.
        Объединяет логику terminate_process_forceful.

        Args:
            process_pid: PID процесса для завершения.
            timeout: Таймаут ожидания завершения в секундах.

        Returns:
            Кортеж (process_closed, process_status):
            - process_closed: True если процесс завершён
            - process_status: Статус завершения процесса
        """
        if self._proc is None:
            app_logger.debug("Процесс не инициализирован (PID: %s)", process_pid)
            return False, "no_process"

        try:
            app_logger.warning("Отправка SIGKILL процессу %d", process_pid)
            self._proc.kill()

            # Проверка poll() после kill()
            poll_result = self._proc.poll()
            if poll_result is not None:
                process_status = f"killed (exit code: {poll_result})"
                app_logger.info(
                    "Chrome браузер принудительно завершён (PID: %d, exit code: %d, время жизни: %.1f сек)",
                    process_pid,
                    poll_result,
                    time.time() - self._start_time,
                )
                return True, process_status
            else:
                # Процесс всё ещё работает после kill(), ждём с timeout
                try:
                    self._proc.wait(timeout=timeout)
                    app_logger.info(
                        "Chrome браузер принудительно завершён (PID: %d, время ожидания: %d сек)",
                        process_pid,
                        timeout,
                    )
                    return True, "killed"
                except subprocess.TimeoutExpired:
                    app_logger.error(
                        "Таймаут (%d сек) после SIGKILL для PID %d - возможна утечка процесса",
                        timeout,
                        process_pid,
                    )
                    return False, "kill_timeout"

        except ProcessLookupError as proc_error:
            app_logger.debug("Процесс уже завершён (kill): %s", proc_error)
            return True, "already_killed"
        except PermissionError as perm_error:
            app_logger.error("Нет прав на принудительное завершение: %s", perm_error)
            return False, "kill_permission_denied"
        except (OSError, subprocess.SubprocessError, ValueError) as kill_error:
            app_logger.error(
                "Ошибка при принудительном закрытии Chrome (PID %d): %s (тип: %s)",
                process_pid,
                kill_error,
                type(kill_error).__name__,
            )
            return False, "kill_error"

    @property
    def process(self) -> Optional[subprocess.Popen]:
        """Возвращает процесс."""
        return self._proc

    @property
    def pid(self) -> Optional[int]:
        """Возвращает PID процесса."""
        return self._proc.pid if self._proc else None

    def is_running(self) -> bool:
        """Проверяет, запущен ли процесс."""
        if self._proc is None:
            return False
        return self._proc.poll() is None

    # ==========================================================================
    # АЛИАСЫ ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ
    # ==========================================================================
    # Эти методы предоставлены для обратной совместимости со старыми тестами.
    # Они вызывают новые методы terminate() и kill().
    # ==========================================================================

    def terminate_process_graceful(self, process_pid: int, timeout: int = 5) -> tuple[bool, str]:
        """
        Алиас для метода terminate() для обратной совместимости.

        Завершает процесс через terminate() (graceful shutdown).

        Args:
            process_pid: PID процесса для завершения.
            timeout: Таймаут ожидания завершения в секундах.

        Returns:
            Кортеж (process_closed, process_status):
            - process_closed: True если процесс завершён
            - process_status: Статус завершения процесса
        """
        return self.terminate(process_pid, timeout)

    def terminate_process_forceful(self, process_pid: int, timeout: int = 10) -> tuple[bool, str]:
        """
        Алиас для метода kill() для обратной совместимости.

        Принудительно завершает процесс через kill() (forceful shutdown).

        Args:
            process_pid: PID процесса для завершения.
            timeout: Таймаут ожидания завершения в секундах.

        Returns:
            Кортеж (process_closed, process_status):
            - process_closed: True если процесс завершён
            - process_status: Статус завершения процесса
        """
        return self.kill(process_pid, timeout)


# =============================================================================
# КЛАСС 4: BrowserLifecycleManager - Координация жизненного цикла браузера
# =============================================================================


class BrowserLifecycleManager:
    """
    Основной класс, координирующий работу остальных компонентов.

    Отвечает за:
    - Инициализацию всех компонентов
    - Координацию запуска браузера
    - Управление жизненным циклом
    - Гарантированную очистку ресурсов

    Пример использования:
        >>> manager = BrowserLifecycleManager(chrome_options)
        >>> manager.init()
        >>> # ... работа с браузером ...
        >>> manager.close()
    """

    def __init__(self, chrome_options: ChromeOptions) -> None:
        """
        Инициализирует менеджер жизненного цикла браузера.

        Args:
            chrome_options: Опции для настройки браузера Chrome.
        """
        self._chrome_options = chrome_options
        self._path_resolver = BrowserPathResolver()
        self._profile_manager = ProfileManager()
        self._process_manager = ProcessManager()
        self._remote_port: Optional[int] = None
        self._chrome_cmd: Optional[list[str]] = None
        self._closed: bool = False

        # weakref.finalize() для гарантированной очистки
        self._finalizer = weakref.finalize(
            self,
            self._cleanup_from_finalizer,
            self._process_manager.process,
            self._profile_manager.profile_tempdir,
            self._profile_manager.profile_path,
        )
        self._finalizer.atexit = False

    def init(self) -> int:
        """
        Инициализирует браузер Chrome.

        Returns:
            Порт remote debugging.

        Raises:
            ChromeException: При ошибке инициализации браузера.
            FileNotFoundError: Если браузер не найден.
            PermissionError: Если браузер не имеет прав на выполнение.
        """
        try:
            # Получаем и валидируем путь к браузеру
            binary_path = self._path_resolver.resolve_path(self._chrome_options)

            # Создаём временную директорию профиля
            _, profile_path = self._profile_manager.create_profile()

            # Получаем свободный порт
            self._remote_port = free_port()

            # Формируем команду запуска
            self._chrome_cmd = self._build_chrome_cmd(
                binary_path, profile_path, self._remote_port, self._chrome_options
            )

            # Запускаем процесс Chrome
            self._process_manager.launch_process(
                self._chrome_cmd, profile_path, self._chrome_options
            )

            app_logger.info(
                "Chrome браузер инициализирован (PID: %s, порт: %s)",
                self._process_manager.pid,
                self._remote_port,
            )

        except (subprocess.SubprocessError, OSError, FileNotFoundError, ValueError, TypeError) as e:
            app_logger.error("Ошибка инициализации Chrome: %s", e)
            # Очистка профиля при ошибке
            try:
                self._profile_manager.cleanup_profile()
                app_logger.debug("Профиль Chrome очищен при ошибке инициализации")
            except (OSError, IOError) as cleanup_error:
                app_logger.debug("Ошибка при очистке профиля: %s", cleanup_error)
            raise

        return self._remote_port  # type: ignore[return-value]

    def _build_chrome_cmd(
        self, binary_path: str, profile_path: str, remote_port: int, chrome_options: ChromeOptions
    ) -> list[str]:
        """
        Формирует команду запуска Chrome.

        Args:
            binary_path: Путь к браузеру.
            profile_path: Путь к профилю.
            remote_port: Порт отладки.
            chrome_options: Опции Chrome.

        Returns:
            Список аргументов командной строки.
        """
        # Валидация memory_limit перед формированием команды
        memory_limit = (
            chrome_options.memory_limit if chrome_options.memory_limit is not None else 2048
        )

        # Формирование команды запуска
        chrome_cmd = [
            binary_path,
            f"--remote-debugging-port={remote_port}",
            f"--user-data-dir={profile_path}",
            "--no-default-browser-check",
            "--no-first-run",
            "--no-sandbox",
            "--disable-fre",
            # Ограничиваем remote-allow-origins для безопасности
            "--remote-allow-origins=http://127.0.0.1:*",
            "--js-flags=--expose-gc",
            f"--max-old-space-size={memory_limit}",
        ]

        # Дополнительные опции
        if chrome_options.start_maximized:
            chrome_cmd.append("--start-maximized")

        if chrome_options.headless:
            app_logger.debug("В Chrome установлен скрытый режим (headless).")
            chrome_cmd.append("--headless")
            chrome_cmd.append("--disable-gpu")

        if chrome_options.disable_images:
            app_logger.debug("В Chrome отключены изображения.")
            chrome_cmd.append("--blink-settings=imagesEnabled=false")

        return chrome_cmd

    def close(self) -> None:
        """
        Закрывает браузер и удаляет временный профиль.

        H2: Использует упрощённые методы terminate() и kill().

        Примечание:
            ИСПРАВЛЕНИЕ CRITICAL 8: Обернуто в try/finally для гарантии выполнения
            Функция гарантирует попытку закрытия даже при ошибках.
            Используется двухуровневая стратегия завершения:
            1. Корректное завершение через terminate() + wait(timeout=5)
            2. Принудительное завершение через kill() + wait(timeout=10)
        """
        # Проверка на повторное закрытие
        if self._closed:
            app_logger.debug("Браузер уже закрыт, повторный вызов игнорируется")
            return

        self._closed = True

        process_pid = self._process_manager.pid
        app_logger.debug("Closing Chrome browser (PID: %s)", process_pid)

        try:
            # Завершаем процесс безопасно (H2: используем упрощённые методы)
            if process_pid is not None:
                # Сначала пытаемся завершить корректно
                success, status = self._process_manager.terminate(process_pid, timeout=5)

                # Если не удалось, пробуем принудительно
                if not success:
                    self._process_manager.kill(process_pid, timeout=10)

        except Exception as e:
            app_logger.error(f"Error closing browser: {e}")
        finally:
            # ИСПРАВЛЕНИЕ CRITICAL 8: Гарантированная очистка профиля в finally
            try:
                self._profile_manager.cleanup_profile()
            except Exception as cleanup_error:
                app_logger.error(f"Error cleaning up profile in finally: {cleanup_error}")

    @staticmethod
    def _cleanup_from_finalizer(
        proc: Optional[subprocess.Popen],
        profile_tempdir: Optional[tempfile.TemporaryDirectory],
        profile_path: Optional[str],
    ) -> None:
        """
        Гарантированная очистка ресурсов через weakref.finalize().

        Args:
            proc: Процесс браузера.
            profile_tempdir: Временная директория профиля.
            profile_path: Путь к профилю.
        """
        try:
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)

            if profile_tempdir is not None:
                profile_tempdir.cleanup()
        except (subprocess.SubprocessError, OSError, RuntimeError) as finalizer_error:
            app_logger.debug("Ошибка в weakref.finalize(): %s", finalizer_error)

    @property
    def remote_port(self) -> Optional[int]:
        """Порт отладки."""
        return self._remote_port

    @property
    def process(self) -> Optional[subprocess.Popen]:
        """Процесс браузера."""
        return self._process_manager.process

    @property
    def profile_path(self) -> Optional[str]:
        """Путь к профилю."""
        return self._profile_manager.profile_path

    def __repr__(self) -> str:
        """Возвращает строковое представление объекта."""
        classname = self.__class__.__name__
        return f"{classname}(arguments={self._chrome_cmd!r})"

    def __enter__(self) -> "BrowserLifecycleManager":
        """Возвращает экземпляр для использования в контекстном менеджере."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Закрывает браузер при выходе из контекста."""
        self.close()

    def __del__(self) -> None:
        """Деструктор объекта."""
        try:
            if hasattr(self, "_finalizer") and self._finalizer is not None:
                if self._finalizer.detach():
                    self._cleanup_from_finalizer(
                        self._process_manager.process,
                        self._profile_manager.profile_tempdir,
                        self._profile_manager.profile_path,
                    )
                return

            if not self._closed and self._process_manager.is_running():
                app_logger.warning(
                    "BrowserLifecycleManager уничтожается без явного закрытия. "
                    "Всегда вызывайте close() явно."
                )
        except (OSError, IOError, RuntimeError, AttributeError) as del_error:
            app_logger.debug("BrowserLifecycleManager.__del__: ошибка: %s", del_error)


# =============================================================================
# СТАРЫЙ КЛАСС CHROMEBROWSER (ОБЁРТКА ДЛЯ BACKWARD COMPATIBILITY)
# =============================================================================


class ChromeBrowser:
    """
    Браузер Chrome с временным профилем (backward compatibility wrapper).

    Этот класс является обёрткой над BrowserLifecycleManager для обеспечения
    обратной совместимости со старым кодом.

    Args:
        chrome_options: Опции Chrome для настройки браузера.

    Raises:
        ChromePathNotFound: Если путь к Chrome не найден.
        ValueError: Если путь к браузеру некорректен.
        FileNotFoundError: Если файл браузера не существует.
        PermissionError: Если файл браузера не исполняемый.
    """

    def __init__(self, chrome_options: ChromeOptions) -> None:
        """
        Инициализирует браузер Chrome с заданными опциями.

        Args:
            chrome_options: Опции для настройки браузера Chrome.
        """
        self._lifecycle_manager = BrowserLifecycleManager(chrome_options)
        self._remote_port = self._lifecycle_manager.init()
        self._closed: bool = False

    @property
    def remote_port(self) -> Optional[int]:
        """Порт отладки."""
        return self._remote_port

    @property
    def _proc(self) -> Optional[subprocess.Popen]:
        """Процесс браузера (для backward compatibility)."""
        return self._lifecycle_manager.process

    @property
    def _profile_path(self) -> Optional[str]:
        """Путь к профилю (для backward compatibility)."""
        return self._lifecycle_manager.profile_path

    @property
    def _closed(self) -> bool:
        """Статус закрытия браузера (для backward compatibility)."""
        return self._lifecycle_manager._closed

    @_closed.setter
    def _closed(self, value: bool) -> None:
        """Устанавливает статус закрытия браузера."""
        self._lifecycle_manager._closed = value

    def close(self) -> None:
        """Закрывает браузер и удаляет временный профиль."""
        self._lifecycle_manager.close()
        self._closed = True

    def __repr__(self) -> str:
        """Возвращает строковое представление объекта."""
        return repr(self._lifecycle_manager)

    def __enter__(self) -> "ChromeBrowser":
        """Возвращает экземпляр для использования в контекстном менеджере."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Закрывает браузер при выходе из контекста."""
        self.close()

    def __del__(self) -> None:
        """Деструктор объекта."""
        try:
            if hasattr(self, "_lifecycle_manager"):
                # weakref.finalize() уже зарегистрирован в BrowserLifecycleManager
                pass
        except (OSError, IOError, RuntimeError, AttributeError) as del_error:
            app_logger.debug("ChromeBrowser.__del__: ошибка: %s", del_error)


# =============================================================================
# ФУНКЦИИ ОЧИСТКИ ОСИРОВЕВШИХ ПРОФИЛЕЙ (ОСТАЮТСЯ БЕЗ ИЗМЕНЕНИЙ)
# =============================================================================


ORPHANED_PROFILE_MARKER = ".chrome_profile_marker"
ORPHANED_PROFILE_MAX_AGE_HOURS = 24  # Максимальный возраст профиля перед удалением


def _check_profile_age_and_delete(
    item: Path, marker_file: Path, current_time: float, max_age_seconds: float
) -> bool:
    """Проверяет возраст профиля по маркеру и удаляет если старый.

    Args:
        item: Путь к директории профиля.
        marker_file: Путь к файлу-маркеру.
        current_time: Текущее время.
        max_age_seconds: Максимальный возраст в секундах.

    Returns:
        True если профиль удалён, False иначе.
    """
    try:
        marker_mtime = marker_file.stat().st_mtime
        age_seconds = current_time - marker_mtime

        if age_seconds > max_age_seconds:
            # Профиль старый - удаляем
            delete_marker = item / ".deleting_marker"
            try:
                # Атомарное создание маркера для предотвращения race condition
                delete_marker.touch(exist_ok=False)
            except FileExistsError:
                # Другой процесс уже удаляет этот профиль
                app_logger.debug("Профиль %s уже удаляется другим процессом", item.name)
                return False

            _safe_remove_profile(item)
            app_logger.debug(
                "Удалён осиротевший профиль: %s (возраст: %.1f ч)",
                item.name,
                age_seconds / SECONDS_PER_HOUR,
            )
            return True
    except OSError as stat_error:
        app_logger.debug("Ошибка получения информации о файле %s: %s", marker_file, stat_error)
        # Если не можем получить информацию - удаляем профиль
        _safe_remove_profile(item)
        return True

    return False


def _check_profile_age_by_dir(item: Path, current_time: float, max_age_seconds: float) -> bool:
    """Проверяет возраст профиля по директории и удаляет если старый.

    Args:
        item: Путь к директории профиля.
        current_time: Текущее время.
        max_age_seconds: Максимальный возраст в секундах.

    Returns:
        True если профиль удалён, False иначе.
    """
    try:
        dir_mtime = item.stat().st_mtime
        age_seconds = current_time - dir_mtime

        if age_seconds > max_age_seconds:
            # Профиль старый - удаляем
            delete_marker = item / ".deleting_marker"
            try:
                # Атомарное создание маркера для предотвращения race condition
                delete_marker.touch(exist_ok=False)
            except FileExistsError:
                # Другой процесс уже удаляет этот профиль
                app_logger.debug("Профиль %s уже удаляется другим процессом", item.name)
                return False

            _safe_remove_profile(item)
            app_logger.debug(
                "Удалён осиротевший профиль (без маркера): %s (возраст: %.1f ч)",
                item.name,
                age_seconds / SECONDS_PER_HOUR,
            )
            return True
    except OSError as stat_error:
        app_logger.debug("Ошибка получения информации о директории %s: %s", item, stat_error)

    return False


def _process_orphaned_profile(item: Path, current_time: float, max_age_seconds: float) -> bool:
    """Обрабатывает один осиротевший профиль.

    Args:
        item: Путь к директории профиля.
        current_time: Текущее время.
        max_age_seconds: Максимальный возраст в секундах.

    Returns:
        True если профиль удалён, False иначе.
    """
    # Проверяем наличие маркера
    marker_file = item / ORPHANED_PROFILE_MARKER

    if marker_file.exists():
        return _check_profile_age_and_delete(item, marker_file, current_time, max_age_seconds)
    else:
        return _check_profile_age_by_dir(item, current_time, max_age_seconds)


def cleanup_orphaned_profiles(
    profiles_dir: Optional[Path] = None, max_age_hours: int = ORPHANED_PROFILE_MAX_AGE_HOURS
) -> int:
    """
    Очищает осиротевшие профили Chrome от предыдущих запусков.

    Профили могут оставаться после аварийного завершения приложения (KeyboardInterrupt,
    сбой питания, падение процесса). Эта функция находит и удаляет такие профили.

    Args:
        profiles_dir: Директория для поиска профилей. Если None, используется временная
                     директория системы (tempfile.gettempdir()).
        max_age_hours: Максимальный возраст профиля в часах. Профили моложе этого
                      порога не удаляются для защиты активных сессий.

    Returns:
        Количество удалённых профилей.

    Примечание:
        - Функция безопасна - не удаляет профили моложе max_age_hours
        - Использует маркер-файл для идентификации профилей Chrome
        - Логирует все действия для отладки
        - Использует атомарные операции ФС для предотвращения race condition
    """
    if profiles_dir is None:
        profiles_dir = Path(tempfile.gettempdir())

    if not profiles_dir.exists():
        app_logger.debug("Директория профилей не существует: %s", profiles_dir)
        return 0

    deleted_count = 0
    current_time = time.time()
    max_age_seconds = max_age_hours * SECONDS_PER_HOUR

    app_logger.debug(
        "Поиск осиротевших профилей Chrome в %s (макс. возраст: %d ч)...",
        profiles_dir,
        max_age_hours,
    )

    try:
        # Ищем директории с префиксом chrome_profile_
        for item in profiles_dir.iterdir():
            if not item.is_dir():
                continue

            # Проверяем имя директории
            if not item.name.startswith("chrome_profile_"):
                continue

            # Обрабатываем профиль
            if _process_orphaned_profile(item, current_time, max_age_seconds):
                deleted_count += 1

    except PermissionError as perm_error:
        app_logger.warning("Нет прав для доступа к директории профилей: %s", perm_error)
    except (OSError, IOError, RuntimeError) as e:
        app_logger.warning("Ошибка при очистке осиротевших профилей: %s", e)

    if deleted_count > 0:
        app_logger.info("Очищено %d осиротевших профилей Chrome", deleted_count)
    else:
        app_logger.debug("Осиротевшие профили не найдены")

    return deleted_count


def _is_profile_in_use(profile_path: Path) -> bool:
    """Проверяет, используется ли профиль активным процессом Chrome.
    - Проверяет активные процессы перед удалением профиля
    - Предотвращает удаление активных профилей

    Args:
        profile_path: Путь к директории профиля.

    Returns:
        True если профиль используется активным процессом, False иначе.
    """
    try:
        # Пытаемся использовать psutil для кроссплатформенной проверки
        try:
            import psutil

            profile_str = str(profile_path)
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    cmdline = proc.info.get("cmdline") or []
                    name = proc.info.get("name") or ""
                    if "chrome" in name.lower():
                        cmdline_str = " ".join(cmdline)
                        if profile_str in cmdline_str:
                            app_logger.debug(
                                "Профиль используется процессом Chrome PID %d", proc.info["pid"]
                            )
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return False
        except ImportError:
            # Fallback для систем без psutil: используем subprocess (Unix)
            import subprocess
            import sys

            # Проверяем платформу
            if sys.platform == "win32":
                # Windows: используем tasklist
                result = subprocess.run(
                    ["tasklist", "/V", "/FO", "CSV"], capture_output=True, text=True, timeout=5
                )
                profile_str = str(profile_path)
                for line in result.stdout.splitlines():
                    if profile_str in line and "chrome" in line.lower():
                        app_logger.debug("Профиль используется процессом Chrome")
                        return True
            else:
                # Unix-like: используем ps aux
                result = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
                profile_str = str(profile_path)
                for line in result.stdout.splitlines():
                    if profile_str in line and "chrome" in line.lower():
                        parts = line.split()
                        if len(parts) >= 2:
                            try:
                                pid = int(parts[1])
                                os.kill(pid, 0)
                                app_logger.debug(
                                    "Профиль используется процессом Chrome PID %d", pid
                                )
                                return True
                            except (ValueError, ProcessLookupError, PermissionError):
                                continue

            return False

    except (OSError, IOError, RuntimeError) as e:
        # При ошибке проверки считаем что профиль не используется
        app_logger.debug("Ошибка проверки активности профиля %s: %s", profile_path, e)
        return False


def _safe_remove_profile(profile_path: Path) -> None:
    """
    Безопасно удаляет профиль Chrome с обработкой ошибок.
    - Проверяет активные процессы перед удалением
    - Обрабатывает ошибки удаления файлов

    Args:
        profile_path: Путь к директории профиля для удаления.
    """
    try:
        if _is_profile_in_use(profile_path):
            app_logger.warning(
                "Профиль Chrome используется активным процессом, пропускаем удаление: %s",
                profile_path,
            )
            return

        # Создаём маркер удаления (для отладки)
        marker_file = profile_path / ".deleting_marker"
        try:
            marker_file.touch(exist_ok=True)
        except OSError as e:
            app_logger.debug(
                "Подавлено исключение при создании маркера удаления: %s", e
            )  # Не критично

        # Удаляем профиль
        shutil.rmtree(profile_path, ignore_errors=True)

        # Проверяем успешность удаления
        if profile_path.exists():
            app_logger.warning("Не удалось полностью удалить профиль: %s", profile_path)
        else:
            app_logger.debug("Профиль успешно удалён: %s", profile_path)

    except (OSError, IOError, RuntimeError) as e:
        app_logger.warning("Ошибка при удалении профиля %s: %s", profile_path, e)


__all__ = [
    "BrowserPathResolver",
    "ProfileManager",
    "ProcessManager",
    "BrowserLifecycleManager",
    "ChromeBrowser",
    "cleanup_orphaned_profiles",
    "ORPHANED_PROFILE_MARKER",
    "ORPHANED_PROFILE_MAX_AGE_HOURS",
]
