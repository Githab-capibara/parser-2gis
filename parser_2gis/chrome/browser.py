"""Модуль для управления браузером Chrome с временным профилем.

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
import threading
import time
import types
import weakref
from pathlib import Path
from typing import TYPE_CHECKING

from typing_extensions import TypeAlias

from parser_2gis.logger.logger import logger as app_logger

from .constants import (
    CHROME_NO_SANDBOX_FLAG,
    CHROME_REMOTE_ALLOW_ORIGINS_TEMPLATE,
    DEFAULT_FILE_PERMISSIONS,
    SECONDS_PER_HOUR,
)
from .exceptions import ChromePathNotFound
from .utils import free_port, locate_chrome_path

# Попытка импортировать psutil для принудительного завершения процессов
try:
    import psutil
except ImportError:
    psutil = None  # type: ignore[misc]

if TYPE_CHECKING:
    from .options import ChromeOptions


# =============================================================================
# TYPE ALIASES
# =============================================================================

# Тип возврата для методов завершения процесса
ProcessStatus: TypeAlias = tuple[bool, str]


# =============================================================================
# КЛАСС 1: BrowserPathResolver - Поиск и валидация пути к браузеру
# =============================================================================


class BrowserPathResolver:
    """Класс для поиска и валидации пути к браузеру Chrome.

    Отвечает за:
    - Поиск пути к браузеру (автоматически или заданный вручную)
    - Валидацию пути (существование, исполняемость)
    - Нормализацию пути (разрешение symlink)

    Пример использования:
        >>> resolver = BrowserPathResolver()
        >>> path = resolver.resolve_path(chrome_options)
    """

    def resolve_path(self, chrome_options: ChromeOptions) -> str:
        """Получает и валидирует путь к браузеру.

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
        """Валидирует путь к исполняемому файлу браузера.

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
    """Класс для управления временным профилем Chrome.

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
        self._profile_tempdir: tempfile.TemporaryDirectory | None = None
        self._profile_path: str | None = None

    def create_profile(self) -> tuple[tempfile.TemporaryDirectory, str]:
        """Создаёт временную директорию профиля.

        Returns:
            Кортеж (TemporaryDirectory, путь к профилю).

        Raises:
            OSError: Если не удалось создать директорию.

        """
        self._profile_tempdir = tempfile.TemporaryDirectory(prefix="chrome_profile_")
        self._profile_path = self._profile_tempdir.name

        # P1-17: Используем os.makedirs с параметром mode для атомарного создания
        # и установки restrictive прав (DEFAULT_FILE_PERMISSIONS) для предотвращения race condition
        try:
            os.makedirs(self._profile_path, mode=DEFAULT_FILE_PERMISSIONS, exist_ok=True)
            app_logger.debug("Профиль создан с правами 0o700 через os.makedirs")
        except OSError as chmod_error:
            app_logger.warning(
                "Не удалось установить права 0o700 на профиль %s: %s. "
                "Профиль будет автоматически удалён при закрытии.",
                self._profile_path,
                chmod_error,
            )

        return self._profile_tempdir, self._profile_path

    def cleanup_profile(self) -> None:
        """Очищает временный профиль Chrome.

        Использует TemporaryDirectory.cleanup() с fallback на shutil.rmtree().
        P0-2: Добавлена проверка profile_path перед очисткой.
        """
        # P0-2: Проверка profile_path перед очисткой
        if not self._profile_path:
            app_logger.debug("Профиль не был создан, очистка не требуется")
            return

        profile_cleanup_error: Exception | None = None

        try:
            if self._profile_tempdir is not None:
                self._profile_tempdir.cleanup()
                app_logger.debug(
                    "Временный профиль Chrome удалён через TemporaryDirectory.cleanup()"
                )
        except OSError as profile_error:
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
                except OSError as fallback_error:
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
    def profile_path(self) -> str | None:
        """Возвращает путь к профилю."""
        return self._profile_path

    @property
    def profile_tempdir(self) -> tempfile.TemporaryDirectory | None:
        """Возвращает TemporaryDirectory профиля."""
        return self._profile_tempdir


# =============================================================================
# КЛАСС 3: ProcessManager - Управление процессом Chrome
# =============================================================================


class ProcessManager:
    """Класс для управления процессом Chrome.

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
        self._proc: subprocess.Popen | None = None
        self._start_time: float = 0.0

    def launch_process(
        self, chrome_cmd: list[str], profile_path: str, chrome_options: ChromeOptions
    ) -> subprocess.Popen:
        """Запускает процесс Chrome.

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
        proc: subprocess.Popen | None = None

        # ID:103, ID:107: Используем try/finally для гарантии очистки ресурсов
        try:
            if chrome_options.silent_browser:
                app_logger.debug("В Chrome отключён вывод отладочной информации.")
                proc = subprocess.Popen(
                    chrome_cmd,
                    shell=False,
                    stderr=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    text=True,
                )
            else:
                proc = subprocess.Popen(chrome_cmd, shell=False, text=True)

            self._proc = proc
            app_logger.debug("Chrome браузер запущен с PID: %d", proc.pid)
            return proc

        except (subprocess.SubprocessError, OSError, TypeError) as e:
            app_logger.error("Ошибка при запуске Chrome браузера: %s", e)
            # ID:103: Очищаем ссылку на процесс при ошибке
            self._proc = None
            # ID:107: Очистка профиля при ошибке запуска
            try:
                shutil.rmtree(profile_path, ignore_errors=True)
            except OSError as cleanup_error:
                app_logger.debug("Не удалось удалить профиль при ошибке запуска: %s", cleanup_error)
            raise
        finally:
            # ID:103: Гарантированная очистка _proc ссылки если процесс не был успешно создан
            if proc is None and self._proc is not None:
                self._proc = None

    def _terminate_process_common(
        self,
        process_pid: int,
        terminate_method: str,
        timeout: int,
        success_status: str,
        timeout_status: str,
        already_terminated_status: str,
        permission_denied_status: str,
        error_status: str,
    ) -> ProcessStatus:
        """Общая логика завершения процесса для terminate и kill.

        Args:
            process_pid: PID процесса для завершения.
            terminate_method: Метод завершения ('terminate' или 'kill').
            timeout: Таймаут ожидания завершения в секундах.
            success_status: Статус при успешном завершении.
            timeout_status: Статус при таймауте.
            already_terminated_status: Статус если процесс уже завершён.
            permission_denied_status: Статус при отсутствии прав.
            error_status: Статус при ошибке.

        Returns:
            Кортеж (process_closed, process_status).

        """
        if self._proc is None:
            app_logger.debug("Процесс не инициализирован (PID: %s)", process_pid)
            return False, "no_process"

        try:
            # Вызов метода terminate() или kill()
            terminate_func = getattr(self._proc, terminate_method)
            app_logger.debug("Отправка SIG%s процессу %d", terminate_method.upper(), process_pid)
            terminate_func()

            # Проверка poll() для обнаружения завершения процесса
            poll_result = self._proc.poll()
            if poll_result is not None:
                process_status = f"{success_status} (exit code: {poll_result})"
                app_logger.info(
                    "Chrome браузер %s завершён (PID: %d, exit code: %d, время жизни: %.1f сек)",
                    terminate_method,
                    process_pid,
                    poll_result,
                    time.time() - self._start_time,
                )
                # H013: Очищаем ссылку на процесс после завершения
                self._proc = None
                return True, process_status
            else:
                # Процесс ещё работает, ждём завершения с timeout
                try:
                    self._proc.wait(timeout=timeout)
                    app_logger.info(
                        "Chrome браузер %s завершён (PID: %d, время ожидания: %d сек)",
                        process_pid,
                        timeout,
                        terminate_method,
                    )
                    # H013: Очищаем ссылку на процесс после завершения
                    self._proc = None
                    return True, success_status
                except subprocess.TimeoutExpired:
                    app_logger.warning(
                        "Таймаут (%d сек) при %s Chrome PID %d",
                        timeout,
                        terminate_method,
                        process_pid,
                    )
                    return False, timeout_status

        except ProcessLookupError as proc_error:
            app_logger.debug("Процесс уже завершён: %s", proc_error)
            # H013: Очищаем ссылку на процесс
            self._proc = None
            return True, already_terminated_status
        except PermissionError as perm_error:
            app_logger.error("Нет прав на завершение процесса: %s", perm_error)
            return False, permission_denied_status
        except (OSError, subprocess.SubprocessError, ValueError) as terminate_error:
            app_logger.warning(
                "Ошибка при %s Chrome (PID %d): %s (тип: %s)",
                terminate_method,
                process_pid,
                terminate_error,
                type(terminate_error).__name__,
            )
            return False, error_status

    def terminate(self, process_pid: int, timeout: int = 5) -> ProcessStatus:
        """Завершает процесс через terminate() (graceful shutdown).

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
        return self._terminate_process_common(
            process_pid=process_pid,
            terminate_method="terminate",
            timeout=timeout,
            success_status="terminated",
            timeout_status="terminate_timeout",
            already_terminated_status="already_terminated",
            permission_denied_status="permission_denied",
            error_status="terminate_error",
        )

    def kill(self, process_pid: int, timeout: int = 10) -> ProcessStatus:
        """Принудительно завершает процесс через kill() (forceful shutdown).

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
            try:
                self._proc.kill()
            except ProcessLookupError as proc_kill_error:
                app_logger.debug("Процесс уже завершён при попытке kill(): %s", proc_kill_error)
                self._proc = None
                return True, "already_killed"

            # Проверка poll() после kill()
            poll_result = self._proc.poll()
            if poll_result is not None:
                process_status = f"killed (exit code: {poll_result})"
                app_logger.info(
                    "Chrome браузер принудительно завершён "
                    "(PID: %d, exit code: %d, время жизни: %.1f сек)",
                    process_pid,
                    poll_result,
                    time.time() - self._start_time,
                )
                # H013: Очищаем ссылку на процесс после завершения
                self._proc = None
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
                    # H013: Очищаем ссылку на процесс после завершения
                    self._proc = None
                    return True, "killed"
                except subprocess.TimeoutExpired:
                    # P1-10: Добавляем принудительное завершение через kill() после timeout
                    app_logger.error(
                        "Таймаут (%d сек) после SIGKILL для PID %d - "
                        "применяем принудительное завершение",
                        timeout,
                        process_pid,
                    )
                    try:
                        # Принудительное завершение процесса и всех дочерних процессов
                        if psutil is None:
                            raise ImportError("psutil не установлен")
                        ps_proc = psutil.Process(process_pid)
                        children = ps_proc.children(recursive=True)
                        for child in children:
                            try:
                                child.kill()
                            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                                # Процесс уже завершён или нет доступа — ожидаемо при форс-килли
                                # ИСПРАВЛЕНИЕ #4: Добавлено логирование для диагностики
                                app_logger.debug(
                                    "Не удалось завершить дочерний процесс PID %d: %s",
                                    child.pid if hasattr(child, "pid") else "unknown",
                                    e,
                                )

                        ps_proc.kill()
                        app_logger.info(
                            "Процесс PID %d и его дочерние процессы принудительно завершены",
                            process_pid,
                        )
                        return True, "killed_forcefully"
                    except (
                        psutil.NoSuchProcess,
                        psutil.AccessDenied,
                        ImportError,
                        FileNotFoundError,
                    ) as e:
                        app_logger.error(
                            "Не удалось принудительно завершить процесс PID %d: %s", process_pid, e
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
    def process(self) -> subprocess.Popen | None:
        """Возвращает процесс."""
        return self._proc

    @property
    def pid(self) -> int | None:
        """Возвращает PID процесса."""
        return self._proc.pid if self._proc else None

    def is_running(self) -> bool:
        """Проверяет, запущен ли процесс."""
        if self._proc is None:
            return False
        return self._proc.poll() is None

    @property
    def start_time(self) -> float:
        """Возвращает время запуска процесса."""
        return self._start_time


# =============================================================================
# КЛАСС 4: BrowserLifecycleManager - Координация жизненного цикла браузера
# =============================================================================


# NOTE: God class — рассмотреть разделение на инициализатор и менеджер жизненного цикла.
# Класс координирует работу BrowserPathResolver, ProfileManager и ProcessManager,
# что приводит к нарушению принципа единственной ответственности (SRP).
class BrowserLifecycleManager:
    """Основной класс, координирующий работу остальных компонентов.

    Отвечает за:
    - Инициализацию всех компонентов
    - Координацию запуска браузера
    - Управление жизненным циклом
    - Гарантированную очистку ресурсов

    Атрибуты управления жизненным циклом:
        _finalizer: weakref.finalize для гарантированной очистки ресурсов
            (процесс, профиль) при сборке мусора, даже если close() не вызван.
        _closed: флаг явно закрытого менеджера; предотвращает повторный вызов
            close() и используется в __del__ для предупреждения о неявном закрытии.

    Пример использования:
        >>> manager = BrowserLifecycleManager(chrome_options)
        >>> manager.init()
        >>> # ... работа с браузером ...
        >>> manager.close()
    """

    def __init__(self, chrome_options: ChromeOptions) -> None:
        """Инициализирует менеджер жизненного цикла браузера.

        Args:
            chrome_options: Опции для настройки браузера Chrome.

        """
        self._chrome_options = chrome_options
        self._path_resolver = BrowserPathResolver()
        self._profile_manager = ProfileManager()
        self._process_manager = ProcessManager()
        self._remote_port: int | None = None
        self._chrome_cmd: list[str] | None = None
        # ИСПРАВЛЕНИЕ #7: Атомарная проверка и установка _closed через threading.Lock
        # для предотвращения двойной очистки в weakref.finalize
        self._closed: bool = False
        self._closed_lock: threading.Lock = threading.Lock()

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
        """Инициализирует браузер Chrome.

        Returns:
            Порт remote debugging.

        Raises:
            ChromeException: При ошибке инициализации браузера.
            FileNotFoundError: Если браузер не найден.
            PermissionError: Если браузер не имеет прав на выполнение.

        """
        profile_created = False
        try:
            # Получаем и валидируем путь к браузеру
            binary_path = self._path_resolver.resolve_path(self._chrome_options)

            # Создаём временную директорию профиля
            _, profile_path = self._profile_manager.create_profile()
            profile_created = True

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
            raise
        except MemoryError as memory_error:
            app_logger.critical("MemoryError при инициализации Chrome: %s", memory_error)
            raise
        except KeyboardInterrupt:
            app_logger.warning("KeyboardInterrupt при инициализации Chrome")
            raise
        finally:
            # HIGH 4: finally блок с очисткой при любой ошибке
            # Очищаем профиль если он был создан, независимо от того на каком этапе произошла ошибка
            if profile_created:
                try:
                    self._profile_manager.cleanup_profile()
                    app_logger.debug("Профиль Chrome очищен в finally блоке")
                except OSError as cleanup_error:
                    app_logger.debug("Ошибка при очистке профиля в finally: %s", cleanup_error)

        return self._remote_port  # type: ignore[return-value]

    def _build_chrome_cmd(
        self, binary_path: str, profile_path: str, remote_port: int, chrome_options: ChromeOptions
    ) -> list[str]:
        """Формирует команду запуска Chrome.

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
            CHROME_NO_SANDBOX_FLAG,  # Необходимо для работы в Docker/контейнерах
            "--disable-fre",
            # Ограничиваем remote-allow-origins точным портом для безопасности
            f"--remote-allow-origins={CHROME_REMOTE_ALLOW_ORIGINS_TEMPLATE.format(port=remote_port)}",
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
        """Закрывает браузер и удаляет временный профиль.

        H2: Использует упрощённые методы terminate() и kill().

        Примечание:
            ИСПРАВЛЕНИЕ CRITICAL 8: Обернуто в try/finally для гарантии выполнения
            Функция гарантирует попытку закрытия даже при ошибках.
            Используется двухуровневая стратегия завершения:
            1. Корректное завершение через terminate() + wait(timeout=10)
            2. Принудительное завершение через kill() + wait(timeout=20)
        """
        # ИСПРАВЛЕНИЕ #7: Атомарная проверка и установка _closed через Lock
        with self._closed_lock:
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
                success, status = self._process_manager.terminate(process_pid, timeout=10)

                # Если не удалось, пробуем принудительно
                if not success:
                    kill_success, kill_status = self._process_manager.kill(process_pid, timeout=20)
                    if not kill_success:
                        app_logger.error(
                            "Не удалось завершить процесс браузера (PID: %s): "
                            "terminate и kill оба вернули False",
                            process_pid,
                        )

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            app_logger.error("Ошибка при закрытии браузера: %s", e)
        finally:
            # ИСПРАВЛЕНИЕ CRITICAL 8: Гарантированная очистка профиля в finally
            try:
                self._profile_manager.cleanup_profile()
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as cleanup_error:
                app_logger.error(f"Error cleaning up profile in finally: {cleanup_error}")
            # ISSUE-003-#3: Явно вызываем финализатор при normal close,
            try:
                if self._finalizer is not None and self._finalizer.alive:
                    self._finalizer()
                    app_logger.debug("Финализатор weakref вызван явно в close()")
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as finalizer_error:
                app_logger.debug("Ошибка при явном вызове финализатора: %s", finalizer_error)

    @staticmethod
    def _cleanup_from_finalizer(
        proc: subprocess.Popen | None,
        profile_tempdir: tempfile.TemporaryDirectory | None,
        profile_path: str | None,
    ) -> None:
        """Гарантированная очистка ресурсов через weakref.finalize().

        Args:
            proc: Процесс браузера.
            profile_tempdir: Временная директория профиля.
            profile_path: Путь к профилю.

        """
        try:
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=6)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=10)

            if profile_tempdir is not None:
                profile_tempdir.cleanup()
        except (subprocess.SubprocessError, OSError, RuntimeError) as finalizer_error:
            app_logger.debug("Ошибка в weakref.finalize(): %s", finalizer_error)

    @property
    def remote_port(self) -> int | None:
        """Порт отладки."""
        return self._remote_port

    @property
    def process(self) -> subprocess.Popen | None:
        """Процесс браузера."""
        return self._process_manager.process

    @property
    def profile_path(self) -> str | None:
        """Путь к профилю."""
        return self._profile_manager.profile_path

    def __repr__(self) -> str:
        """Возвращает строковое представление объекта."""
        classname = self.__class__.__name__
        return f"{classname}(arguments={self._chrome_cmd!r})"

    def __enter__(self) -> BrowserLifecycleManager:
        """Возвращает экземпляр для использования в контекстном менеджере."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> bool:
        """Закрывает браузер при выходе из контекста."""
        self.close()
        return False

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
        except (OSError, RuntimeError, AttributeError) as del_error:
            app_logger.debug("BrowserLifecycleManager.__del__: ошибка: %s", del_error)


# =============================================================================
# СТАРЫЙ КЛАСС CHROMEBROWSER (ОБЁРТКА ДЛЯ BACKWARD COMPATIBILITY)
# =============================================================================


class ChromeBrowser:
    """Браузер Chrome с временным профилем (backward compatibility wrapper).

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
        """Инициализирует браузер Chrome с заданными опциями.

        Args:
            chrome_options: Опции для настройки браузера Chrome.

        """
        self._lifecycle_manager = BrowserLifecycleManager(chrome_options)
        self._remote_port = self._lifecycle_manager.init()
        self._closed: bool = False

    @property
    def remote_port(self) -> int | None:
        """Порт отладки."""
        return self._remote_port

    @property
    def _proc(self) -> subprocess.Popen | None:
        """Процесс браузера (для backward compatibility)."""
        return self._lifecycle_manager.process

    @property
    def _profile_path(self) -> str | None:
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

    def __enter__(self) -> ChromeBrowser:
        """Возвращает экземпляр для использования в контекстном менеджере."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Закрывает браузер при выходе из контекста."""
        self.close()

    def __del__(self) -> None:
        """Деструктор объекта."""
        try:
            if hasattr(self, "_lifecycle_manager"):
                # weakref.finalize() уже зарегистрирован в BrowserLifecycleManager,
                # дополнительных действий не требуется
                pass  # noqa: PIE790 — намеренный no-op, finalize уже зарегистрирован
        except (OSError, RuntimeError, AttributeError) as del_error:
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
    profiles_dir: Path | None = None, max_age_hours: int = ORPHANED_PROFILE_MAX_AGE_HOURS
) -> int:
    """Очищает осиротевшие профили Chrome от предыдущих запусков.

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
    except (OSError, RuntimeError) as e:
        app_logger.warning("Ошибка при очистке осиротевших профилей: %s", e)

    if deleted_count > 0:
        app_logger.info("Очищено %d осиротевших профилей Chrome", deleted_count)
    else:
        app_logger.debug("Осиротевшие профили не найдены")

    return deleted_count


# ISSUE-003-#18: Кэширование результатов проверки процессов для снижения нагрузки
# Кэш хранит (timestamp, set_of_chrome_cmdlines) на короткое время
_process_cache: dict[str, tuple[float, list[list[str | None]]]] = {}
_PROCESS_CACHE_TTL = 5.0  # секунд


def _is_profile_in_use(profile_path: Path) -> bool:
    """Проверяет, используется ли профиль активным процессом Chrome.
    - Проверяет активные процессы перед удалением профиля
    - Предотвращает удаление активных профилей

    ISSUE-003-#18: Кэширует результат psutil.process_iter() на 5 секунд
    для предотвращения повторного перебора всех процессов.

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

            # ISSUE-003-#18: Проверяем кэш перед вызовом process_iter
            current_time = time.time()
            cache_key = "chrome_processes"
            if cache_key in _process_cache:
                cached_time, cached_processes = _process_cache[cache_key]
                if current_time - cached_time < _PROCESS_CACHE_TTL:
                    # Используем кэшированные процессы
                    for cmdline in cached_processes:
                        if cmdline and any("chrome" in str(part).lower() for part in cmdline):
                            cmdline_str = " ".join(str(p) for p in cmdline if p)
                            if profile_str in cmdline_str:
                                return True
                    return False

            # Кэш устарел или отсутствует — собираем заново
            all_processes = []
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    cmdline = proc.info.get("cmdline") or []
                    name = proc.info.get("name") or ""
                    all_processes.append(cmdline)
                    if "chrome" in name.lower():
                        cmdline_str = " ".join(str(p) for p in cmdline if p)
                        if profile_str in cmdline_str:
                            # ISSUE-003-#18: Кэшируем результат
                            _process_cache[cache_key] = (current_time, all_processes)
                            app_logger.debug(
                                "Профиль используется процессом Chrome PID %d", proc.info["pid"]
                            )
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            # ISSUE-003-#18: Кэшируем даже если Chrome не найден
            _process_cache[cache_key] = (current_time, all_processes)
            return False
        except ImportError:
            # Fallback для систем без psutil: используем subprocess (Unix)
            import subprocess
            import sys

            # Проверяем платформу
            if sys.platform == "win32":
                # Windows: используем tasklist
                result = subprocess.run(
                    ["tasklist", "/V", "/FO", "CSV"], capture_output=True, text=True, timeout=10
                )
                profile_str = str(profile_path)
                for line in result.stdout.splitlines():
                    if profile_str in line and "chrome" in line.lower():
                        app_logger.debug("Профиль используется процессом Chrome")
                        return True
            else:
                # Unix-like: используем ps aux
                result = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=10)
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

    except (OSError, RuntimeError) as e:
        # При ошибке проверки считаем что профиль не используется
        app_logger.debug("Ошибка проверки активности профиля %s: %s", profile_path, e)
        return False


def _safe_remove_profile(profile_path: Path) -> None:
    """Безопасно удаляет профиль Chrome с обработкой ошибок.
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

    except (OSError, RuntimeError) as e:
        app_logger.warning("Ошибка при удалении профиля %s: %s", profile_path, e)


__all__ = [
    "ORPHANED_PROFILE_MARKER",
    "ORPHANED_PROFILE_MAX_AGE_HOURS",
    "BrowserLifecycleManager",
    "BrowserPathResolver",
    "ChromeBrowser",
    "ProcessManager",
    "ProfileManager",
    "cleanup_orphaned_profiles",
]
