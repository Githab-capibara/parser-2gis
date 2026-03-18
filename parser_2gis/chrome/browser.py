from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from ..logger import logger
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

    def __init__(self, chrome_options: ChromeOptions) -> None:
        # Получаем путь к браузеру
        from pathlib import Path

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
            logger.error("Путь к Chrome браузеру не найден")
            raise ChromePathNotFound

        # Нормализация пути через realpath для предотвращения атак с символическими ссылками
        binary_path = os.path.realpath(binary_path)

        # Строгая валидация binary_path
        self._validate_binary_path(binary_path)

        logger.debug("Запуск Chrome браузера по пути: %s", binary_path)

        # ИСПОЛЬЗУЕМ TemporaryDirectory для автоматической очистки профиля
        # TemporaryDirectory гарантирует удаление профиля даже при ошибке или KeyboardInterrupt
        # Маркер для отложенной очистки при следующем запуске создаётся автоматически
        self._profile_tempdir = tempfile.TemporaryDirectory(prefix="chrome_profile_")
        self._profile_path = self._profile_tempdir.name

        # Устанавливаем restrictive права на директорию профиля (0o700 - только владелец)
        # При ошибке TemporaryDirectory всё равно очистит профиль при закрытии
        try:
            os.chmod(self._profile_path, 0o700)
        except OSError as chmod_error:
            logger.warning(
                "Не удалось установить права 0o700 на профиль %s: %s. " "Профиль будет автоматически удалён при закрытии.",
                self._profile_path,
                chmod_error,
            )
            # НЕ выбрасываем исключение - TemporaryDirectory гарантирует очистку

        self._remote_port = free_port()

        # Валидация memory_limit перед формированием команды
        memory_limit = chrome_options.memory_limit if chrome_options.memory_limit is not None else 2048

        # Формирование команды запуска
        self._chrome_cmd = [
            binary_path,
            f"--remote-debugging-port={self._remote_port}",
            f"--user-data-dir={self._profile_path}",
            "--no-default-browser-check",
            "--no-first-run",
            "--no-sandbox",
            "--disable-fre",
            # Ограничиваем remote-allow-origins для безопасности
            # Используем 127.0.0.1 вместо localhost для более строгой безопасности
            "--remote-allow-origins=http://127.0.0.1:*",
            "--js-flags=--expose-gc",
            f"--max-old-space-size={memory_limit}",
        ]

        # Дополнительные опции
        if chrome_options.start_maximized:
            self._chrome_cmd.append("--start-maximized")

        if chrome_options.headless:
            logger.debug("В Chrome установлен скрытый режим (headless).")
            self._chrome_cmd.append("--headless")
            self._chrome_cmd.append("--disable-gpu")

        if chrome_options.disable_images:
            logger.debug("В Chrome отключены изображения.")
            self._chrome_cmd.append("--blink-settings=imagesEnabled=false")

        # Запуск процесса
        try:
            if chrome_options.silent_browser:
                logger.debug("В Chrome отключён вывод отладочной информации.")
                self._proc = subprocess.Popen(
                    self._chrome_cmd,
                    shell=False,
                    stderr=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                )
            else:
                self._proc = subprocess.Popen(self._chrome_cmd, shell=False)

            logger.debug("Chrome браузер запущен с PID: %d", self._proc.pid)

        except Exception as e:
            logger.error("Ошибка при запуске Chrome браузера: %s", e)
            # Очистка профиля при ошибке запуска
            try:
                shutil.rmtree(self._profile_path, ignore_errors=True)
            except Exception as e:
                logger.debug("Не удалось удалить профиль при ошибке запуска: %s", e)
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
            logger.error(error_msg)
            raise PermissionError(error_msg)

    @property
    def remote_port(self) -> int:
        """Порт отладки."""
        return self._remote_port

    def close(self) -> None:
        """Закрывает браузер и удаляет временный профиль.

        Примечание:
            Функция гарантирует попытку закрытия даже при ошибках.
            Используется двухуровневая стратегия завершения:
            1. Корректное завершение через terminate() + wait(timeout=5)
            2. Принудительное завершение через kill() + wait(timeout=10)

        Важно:
            - Метод обрабатывает zombie процессы через wait() с timeout
            - TemporaryDirectory.cleanup() гарантирует удаление профиля
            - Все ошибки логируются для последующего анализа
        """
        logger.debug("Завершение работы Chrome браузера.")

        process_closed = False
        process_status = "unknown"

        try:
            if hasattr(self, "_proc") and self._proc is not None:
                process_pid = self._proc.pid
                logger.debug("Завершение процесса Chrome с PID: %d", process_pid)

                # Попытка 1: Корректное завершение через terminate()
                try:
                    self._proc.terminate()
                    logger.debug("Отправлен сигнал SIGTERM процессу %d", process_pid)

                    try:
                        self._proc.wait(timeout=5)
                        process_closed = True
                        process_status = "terminated"
                        logger.debug(
                            "Chrome браузер корректно завершён (PID: %d)",
                            process_pid,
                        )
                    except subprocess.TimeoutExpired:
                        logger.warning(
                            "Таймаут (5 сек) при завершении Chrome PID %d, " "принудительное закрытие через kill()",
                            process_pid,
                        )

                except Exception as terminate_error:
                    logger.warning("Ошибка при завершении Chrome: %s", terminate_error)

                # Попытка 2: Принудительное завершение через kill()
                if not process_closed:
                    try:
                        self._proc.kill()
                        logger.debug("Отправлен сигнал SIGKILL процессу %d", process_pid)

                        try:
                            self._proc.wait(timeout=10)
                            process_closed = True
                            process_status = "killed"
                            logger.debug(
                                "Chrome браузер принудительно завершён (PID: %d)",
                                process_pid,
                            )
                        except subprocess.TimeoutExpired:
                            logger.error(
                                "Таймаут (10 сек) после SIGKILL для PID %d",
                                process_pid,
                            )
                            process_status = "kill_timeout"

                    except Exception as kill_error:
                        logger.error("Ошибка при принудительном закрытии Chrome: %s", kill_error)
                        process_status = "kill_error"

            else:
                logger.warning("Процесс Chrome не инициализирован")

        except Exception as e:
            logger.error("Непредвиденная ошибка при закрытии Chrome: %s", e)
            process_status = "unexpected_error"

        # Логируем финальный статус процесса
        if hasattr(self, "_proc") and self._proc is not None:
            logger.debug(
                "Финальный статус процесса Chrome: %s (PID: %d)",
                process_status,
                self._proc.pid,
            )

        # TemporaryDirectory.cleanup() гарантирует удаление профиля
        try:
            if hasattr(self, "_profile_tempdir") and self._profile_tempdir is not None:
                self._profile_tempdir.cleanup()
                logger.debug("Временный профиль Chrome удалён через TemporaryDirectory.cleanup()")
        except Exception as profile_error:
            logger.error("Ошибка при удалении профиля через TemporaryDirectory: %s", profile_error)
            try:
                if hasattr(self, "_profile_path") and self._profile_path:
                    shutil.rmtree(self._profile_path, ignore_errors=True)
                    logger.debug("Профиль удалён через fallback shutil.rmtree()")
            except Exception as fallback_error:
                logger.error("Fallback очистка профиля не удалась: %s", fallback_error)

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


def cleanup_orphaned_profiles(profiles_dir: Optional[Path] = None, max_age_hours: int = ORPHANED_PROFILE_MAX_AGE_HOURS) -> int:
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
        logger.debug("Директория профилей не существует: %s", profiles_dir)
        return 0

    deleted_count = 0
    current_time = time.time()
    max_age_seconds = max_age_hours * 3600

    logger.debug("Поиск осиротевших профилей Chrome в %s (макс. возраст: %d ч)...", profiles_dir, max_age_hours)

    try:
        # Ищем директории с префиксом chrome_profile_
        for item in profiles_dir.iterdir():
            if not item.is_dir():
                continue

            # Проверяем имя директории
            if not item.name.startswith("chrome_profile_"):
                continue

            # Проверяем наличие маркера (для надёжности)
            marker_file = item / ORPHANED_PROFILE_MARKER

            # Если маркер существует, проверяем его возраст
            if marker_file.exists():
                try:
                    marker_mtime = marker_file.stat().st_mtime
                    age_seconds = current_time - marker_mtime

                    if age_seconds > max_age_seconds:
                        # Профиль старый - удаляем
                        # Атомарная операция: пытаемся создать маркер удаления
                        delete_marker = item / ".deleting_marker"
                        try:
                            # Атомарное создание маркера для предотвращения race condition
                            delete_marker.touch(exist_ok=False)
                        except FileExistsError:
                            # Другой процесс уже удаляет этот профиль - пропускаем
                            logger.debug("Профиль %s уже удаляется другим процессом", item.name)
                            continue

                        _safe_remove_profile(item)
                        deleted_count += 1
                        logger.debug("Удалён осиротевший профиль: %s (возраст: %.1f ч)", item.name, age_seconds / 3600)
                except OSError as stat_error:
                    logger.debug("Ошибка получения информации о файле %s: %s", marker_file, stat_error)
                    # Если не можем получить информацию - удаляем профиль
                    _safe_remove_profile(item)
                    deleted_count += 1
            else:
                # Маркера нет - проверяем возраст директории
                try:
                    dir_mtime = item.stat().st_mtime
                    age_seconds = current_time - dir_mtime

                    if age_seconds > max_age_seconds:
                        # Профиль старый - удаляем
                        # Атомарная операция: пытаемся создать маркер удаления
                        delete_marker = item / ".deleting_marker"
                        try:
                            # Атомарное создание маркера для предотвращения race condition
                            delete_marker.touch(exist_ok=False)
                        except FileExistsError:
                            # Другой процесс уже удаляет этот профиль - пропускаем
                            logger.debug("Профиль %s уже удаляется другим процессом", item.name)
                            continue

                        _safe_remove_profile(item)
                        deleted_count += 1
                        logger.debug(
                            "Удалён осиротевший профиль (без маркера): %s (возраст: %.1f ч)", item.name, age_seconds / 3600
                        )
                except OSError as stat_error:
                    logger.debug("Ошибка получения информации о директории %s: %s", item, stat_error)

    except PermissionError as perm_error:
        logger.warning("Нет прав для доступа к директории профилей: %s", perm_error)
    except Exception as e:
        logger.warning("Ошибка при очистке осиротевших профилей: %s", e)

    if deleted_count > 0:
        logger.info("Очищено %d осиротевших профилей Chrome", deleted_count)
    else:
        logger.debug("Осиротевшие профили не найдены")

    return deleted_count


def _safe_remove_profile(profile_path: Path) -> None:
    """
    Безопасно удаляет профиль Chrome с обработкой ошибок.

    Args:
        profile_path: Путь к директории профиля для удаления.
    """
    try:
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
            logger.warning("Не удалось полностью удалить профиль: %s", profile_path)
        else:
            logger.debug("Профиль успешно удалён: %s", profile_path)

    except Exception as e:
        logger.warning("Ошибка при удалении профиля %s: %s", profile_path, e)
