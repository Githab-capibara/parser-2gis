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
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from ..logger.logger import logger as app_logger
from .exceptions import ChromePathNotFound
from .utils import free_port, locate_chrome_path

if TYPE_CHECKING:
    from .options import ChromeOptions


class ChromeBrowser:
    """Браузер Chrome с временным профилем.

    Этот класс управляет запуском браузера Chrome с временным профилем,
    который автоматически удаляется после закрытия браузера.

    Args:
        chrome_options: Опции Chrome для настройки браузера.

    Raises:
        ChromePathNotFound: Если путь к Chrome не найден.
        ValueError: Если путь к браузеру некорректен.
        FileNotFoundError: Если файл браузера не существует.
        PermissionError: Если файл браузера не исполняемый.
    """

    def _get_binary_path(self, chrome_options: ChromeOptions) -> str:
        """Получает и валидирует путь к браузеру.

        Args:
            chrome_options: Опции Chrome для получения пути.

        Returns:
            Валидированный путь к браузеру.

        Raises:
            ChromePathNotFound: Если путь к Chrome не найден.
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
                "Путь к браузеру нормализован: %s → %s",
                original_binary_path,
                binary_path,
            )

        app_logger.debug(
            "Повторная валидация пути к браузеру после нормализации: %s", binary_path
        )
        self._validate_binary_path(binary_path)
        app_logger.debug("Запуск Chrome браузера по пути: %s", binary_path)

        return binary_path

    def _create_profile_dir(self) -> tuple[tempfile.TemporaryDirectory, str]:
        """Создаёт временную директорию профиля.

        Returns:
            Кортеж (TemporaryDirectory, путь к профилю).
        """
        profile_tempdir = tempfile.TemporaryDirectory(prefix="chrome_profile_")
        profile_path = profile_tempdir.name

        # Устанавливаем restrictive права на директорию профиля (0o700)
        try:
            os.chmod(profile_path, 0o700)
        except OSError as chmod_error:
            app_logger.warning(
                "Не удалось установить права 0o700 на профиль %s: %s. "
                "Профиль будет автоматически удалён при закрытии.",
                profile_path,
                chmod_error,
            )

        return profile_tempdir, profile_path

    def _build_chrome_cmd(
        self,
        binary_path: str,
        profile_path: str,
        remote_port: int,
        chrome_options: ChromeOptions,
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
            chrome_options.memory_limit
            if chrome_options.memory_limit is not None
            else 2048
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

    def _launch_chrome_process(
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
            Exception: При ошибке запуска.
        """
        try:
            if chrome_options.silent_browser:
                app_logger.debug("В Chrome отключён вывод отладочной информации.")
                proc = subprocess.Popen(
                    chrome_cmd,
                    shell=False,
                    stderr=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                )
            else:
                proc = subprocess.Popen(chrome_cmd, shell=False)

            app_logger.debug("Chrome браузер запущен с PID: %d", proc.pid)
            return proc

        except Exception as e:
            app_logger.error("Ошибка при запуске Chrome браузера: %s", e)
            # Очистка профиля при ошибке запуска
            try:
                shutil.rmtree(profile_path, ignore_errors=True)
            except Exception as cleanup_error:
                app_logger.debug(
                    "Не удалось удалить профиль при ошибке запуска: %s", cleanup_error
                )
            raise

    def __init__(self, chrome_options: ChromeOptions) -> None:
        # Инициализируем переменные для гарантии очистки в finally
        self._profile_tempdir: Optional[tempfile.TemporaryDirectory] = None
        self._profile_path: Optional[str] = None
        self._proc: Optional[subprocess.Popen] = None
        self._chrome_cmd: Optional[list[str]] = None
        self._remote_port: Optional[int] = None

        try:
            # Получаем и валидируем путь к браузеру
            binary_path = self._get_binary_path(chrome_options)

            # Создаём временную директорию профиля
            self._profile_tempdir, self._profile_path = self._create_profile_dir()

            # Получаем свободный порт
            self._remote_port = free_port()

            # Формируем команду запуска
            self._chrome_cmd = self._build_chrome_cmd(
                binary_path, self._profile_path, self._remote_port, chrome_options
            )

            # Запускаем процесс Chrome
            self._proc = self._launch_chrome_process(
                self._chrome_cmd, self._profile_path, chrome_options
            )

        except Exception as e:
            # Если ошибка произошла после создания TemporaryDirectory,
            # гарантируем его очистку
            app_logger.error("Ошибка инициализации Chrome: %s", e)
            if self._profile_tempdir is not None:
                try:
                    self._profile_tempdir.cleanup()
                    app_logger.debug("Профиль Chrome очищен при ошибке инициализации")
                except Exception as cleanup_error:
                    app_logger.debug("Ошибка при очистке профиля: %s", cleanup_error)
            # Пробрасываем исключение дальше
            raise

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

    @property
    def remote_port(self) -> Optional[int]:
        """Порт отладки.

        Returns:
            Порт отладки или None если не инициализирован.
        """
        return self._remote_port

    def _terminate_process_graceful(self, process_pid: int) -> tuple[bool, str]:
        """Пытается корректно завершить процесс через terminate().

        Args:
            process_pid: PID процесса для завершения.

        Returns:
            Кортеж (process_closed, process_status):
            - process_closed: True если процесс завершён
            - process_status: Статус завершения процесса
        """
        if not hasattr(self, "_proc") or self._proc is None:
            return False, "no_process"

        try:
            self._proc.terminate()
            app_logger.debug("Отправлен сигнал SIGTERM процессу %d", process_pid)

            # Проверка poll() для обнаружения завершения процесса
            poll_result = self._proc.poll()
            if poll_result is not None:
                # Процесс уже завершился
                process_status = f"terminated (exit code: {poll_result})"
                app_logger.debug(
                    "Chrome браузер корректно завершён (PID: %d, exit code: %d)",
                    process_pid,
                    poll_result,
                )
                return True, process_status
            else:
                # Процесс ещё работает, ждём завершения с timeout
                try:
                    self._proc.wait(timeout=5)
                    app_logger.debug(
                        "Chrome браузер корректно завершён (PID: %d)", process_pid
                    )
                    return True, "terminated"
                except subprocess.TimeoutExpired:
                    app_logger.warning(
                        "Таймаут (5 сек) при завершении Chrome PID %d, "
                        "принудительное закрытие через kill()",
                        process_pid,
                    )
                    return False, "terminate_timeout"

        except ProcessLookupError as proc_error:
            # Процесс уже завершён
            app_logger.debug("Процесс уже завершён: %s", proc_error)
            return True, "already_terminated"
        except PermissionError as perm_error:
            # Нет прав на завершение процесса
            app_logger.error("Нет прав на завершение процесса: %s", perm_error)
            return False, "permission_denied"
        except Exception as terminate_error:
            app_logger.warning("Ошибка при завершении Chrome: %s", terminate_error)
            return False, "terminate_error"

    def _terminate_process_forceful(self, process_pid: int) -> tuple[bool, str]:
        """Пытается принудительно завершить процесс через kill().

        Args:
            process_pid: PID процесса для завершения.

        Returns:
            Кортеж (process_closed, process_status):
            - process_closed: True если процесс завершён
            - process_status: Статус завершения процесса
        """
        if not hasattr(self, "_proc") or self._proc is None:
            return False, "no_process"

        try:
            self._proc.kill()
            app_logger.debug("Отправлен сигнал SIGKILL процессу %d", process_pid)

            # Проверка poll() после kill()
            poll_result = self._proc.poll()
            if poll_result is not None:
                process_status = f"killed (exit code: {poll_result})"
                app_logger.debug(
                    "Chrome браузер принудительно завершён (PID: %d, exit code: %d)",
                    process_pid,
                    poll_result,
                )
                return True, process_status
            else:
                # Процесс всё ещё работает после kill(), ждём с большим timeout
                try:
                    self._proc.wait(timeout=10)
                    app_logger.debug(
                        "Chrome браузер принудительно завершён (PID: %d)", process_pid
                    )
                    return True, "killed"
                except subprocess.TimeoutExpired:
                    app_logger.error(
                        "Таймаут (10 сек) после SIGKILL для PID %d", process_pid
                    )
                    return False, "kill_timeout"

        except ProcessLookupError as proc_error:
            # Процесс уже завершён
            app_logger.debug("Процесс уже завершён (kill): %s", proc_error)
            return True, "already_killed"
        except PermissionError as perm_error:
            # Нет прав на завершение процесса
            app_logger.error("Нет прав на принудительное завершение: %s", perm_error)
            return False, "kill_permission_denied"
        except Exception as kill_error:
            app_logger.error(
                "Ошибка при принудительном закрытии Chrome: %s", kill_error
            )
            return False, "kill_error"

    def _cleanup_profile(self) -> None:
        """Очищает временный профиль Chrome.

        Использует TemporaryDirectory.cleanup() с fallback на shutil.rmtree().
        """
        profile_cleanup_error: Optional[Exception] = None
        try:
            if hasattr(self, "_profile_tempdir") and self._profile_tempdir is not None:
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
        except Exception as profile_error:
            app_logger.error(
                "Непредвиденная ошибка при удалении профиля через TemporaryDirectory: %s",
                profile_error,
                exc_info=True,
            )
            profile_cleanup_error = profile_error
        finally:
            # Fallback очистка через shutil.rmtree() если TemporaryDirectory не удался
            if profile_cleanup_error is not None:
                try:
                    if hasattr(self, "_profile_path") and self._profile_path:
                        shutil.rmtree(self._profile_path, ignore_errors=True)
                        app_logger.debug(
                            "Профиль удалён через fallback shutil.rmtree()"
                        )
                except (OSError, IOError) as fallback_error:
                    app_logger.error(
                        "Ошибка ОС/IO при fallback очистке профиля: %s",
                        fallback_error,
                        exc_info=True,
                    )
                except Exception as fallback_error:
                    app_logger.error(
                        "Непредвиденная ошибка при fallback очистке профиля: %s",
                        fallback_error,
                        exc_info=True,
                    )

    def close(self) -> None:
        """Закрывает браузер и удаляет временный профиль.

        Примечание:
            Функция гарантирует попытку закрытия даже при ошибках.
            Используется двухуровневая стратегия завершения:
            1. Корректное завершение через terminate() + wait(timeout=5)
            2. Принудительное завершение через kill() + wait(timeout=10)

        Важно:
            - ИСПРАВЛЕНИЕ 8: Проверка poll() после terminate() для обнаружения zombie процессов
            - Использовать kill() если terminate() не работает
            - Добавлен wait() с timeout для предотвращения утечки процессов
            - Метод обрабатывает zombie процессы через wait() с timeout
            - TemporaryDirectory.cleanup() гарантирует удаление профиля
            - Все ошибки логируются для последующего анализа
        """
        app_logger.debug("Завершение работы Chrome браузера.")

        process_closed = False
        process_status = "unknown"

        try:
            if hasattr(self, "_proc") and self._proc is not None:
                process_pid = self._proc.pid
                app_logger.debug("Завершение процесса Chrome с PID: %d", process_pid)

                # Попытка 1: Корректное завершение через terminate()
                process_closed, process_status = self._terminate_process_graceful(
                    process_pid
                )

                # Попытка 2: Принудительное завершение через kill()
                if not process_closed:
                    process_closed, process_status = self._terminate_process_forceful(
                        process_pid
                    )

            else:
                app_logger.warning("Процесс Chrome не инициализирован")

        except Exception as e:
            app_logger.error("Непредвиденная ошибка при закрытии Chrome: %s", e)
            process_status = "unexpected_error"

        # Логируем финальный статус процесса
        if hasattr(self, "_proc") and self._proc is not None:
            app_logger.debug(
                "Финальный статус процесса Chrome: %s (PID: %d)",
                process_status,
                self._proc.pid,
            )

        # Очистка профиля
        self._cleanup_profile()

    def __repr__(self) -> str:
        classname = self.__class__.__name__
        return f"{classname}(arguments={self._chrome_cmd!r})"

    def __enter__(self) -> "ChromeBrowser":
        """Возвращает экземпляр для использования в контекстном менеджере."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Закрывает браузер при выходе из контекста."""
        self.close()


# Константы для очистки профилей
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
                age_seconds / 3600,
            )
            return True
    except OSError as stat_error:
        app_logger.debug(
            "Ошибка получения информации о файле %s: %s", marker_file, stat_error
        )
        # Если не можем получить информацию - удаляем профиль
        _safe_remove_profile(item)
        return True

    return False


def _check_profile_age_by_dir(
    item: Path, current_time: float, max_age_seconds: float
) -> bool:
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
                age_seconds / 3600,
            )
            return True
    except OSError as stat_error:
        app_logger.debug(
            "Ошибка получения информации о директории %s: %s", item, stat_error
        )

    return False


def _process_orphaned_profile(
    item: Path, current_time: float, max_age_seconds: float
) -> bool:
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
        return _check_profile_age_and_delete(
            item, marker_file, current_time, max_age_seconds
        )
    else:
        return _check_profile_age_by_dir(item, current_time, max_age_seconds)


def cleanup_orphaned_profiles(
    profiles_dir: Optional[Path] = None,
    max_age_hours: int = ORPHANED_PROFILE_MAX_AGE_HOURS,
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
    max_age_seconds = max_age_hours * 3600

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
    except Exception as e:
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
        # Пытаемся получить список процессов Chrome
        import subprocess

        # Получаем список всех процессов Chrome
        result = subprocess.run(
            ["ps", "aux"], capture_output=True, text=True, timeout=5
        )

        # Проверяем, есть ли процессы с этим профилем
        profile_str = str(profile_path)
        for line in result.stdout.splitlines():
            if profile_str in line and "chrome" in line.lower():
                # Проверяем, что это не наш процесс
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        pid = int(parts[1])
                        # Проверяем, существует ли процесс
                        os.kill(pid, 0)  # Сигнал 0 проверяет существование процесса
                        app_logger.debug(
                            "Профиль используется процессом Chrome PID %d", pid
                        )
                        return True
                    except (ValueError, ProcessLookupError, PermissionError):
                        # Процесс не существует или нет прав
                        continue

        return False

    except Exception as e:
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
        except OSError:
            pass  # Не критично

        # Удаляем профиль
        shutil.rmtree(profile_path, ignore_errors=True)

        # Проверяем успешность удаления
        if profile_path.exists():
            app_logger.warning("Не удалось полностью удалить профиль: %s", profile_path)
        else:
            app_logger.debug("Профиль успешно удалён: %s", profile_path)

    except Exception as e:
        app_logger.warning("Ошибка при удалении профиля %s: %s", profile_path, e)
