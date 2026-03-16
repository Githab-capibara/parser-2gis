from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import TYPE_CHECKING

from ..common import wait_until_finished
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
                "Не удалось установить права 0o700 на профиль %s: %s. "
                "Профиль будет автоматически удалён при закрытии.",
                self._profile_path,
                chmod_error
            )
            # НЕ выбрасываем исключение - TemporaryDirectory гарантирует очистку

        self._remote_port = free_port()

        # Валидация memory_limit перед формированием команды
        memory_limit = (
            chrome_options.memory_limit
            if chrome_options.memory_limit is not None
            else 2048
        )

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
            "--remote-allow-origins=http://localhost:*",
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
        if not os.access(binary_path, os.X_OK):
            logger.warning("Файл браузера не имеет прав на выполнение: %s", binary_path)

    @property
    def remote_port(self) -> int:
        """Порт отладки."""
        return self._remote_port

    def close(self) -> None:
        """Закрывает браузер и удаляет временный профиль.

        Примечание:
            Функция гарантирует попытку закрытия даже при ошибках.
            Используется многоуровневая стратегия завершения:
            1. Корректное завершение через terminate()
            2. Принудительное завершение через kill()
            3. Удаление временного профиля через TemporaryDirectory.cleanup()
        """
        logger.debug("Завершение работы Chrome браузера.")

        # Закрываем браузер
        process_closed = False

        try:
            if hasattr(self, "_proc") and self._proc is not None:
                # Попытка корректного завершения
                try:
                    self._proc.terminate()
                    self._proc.wait(
                        timeout=30
                    )  # Уменьшенный таймаут для быстродействия
                    process_closed = True
                    logger.debug("Chrome браузер корректно завершён")
                except subprocess.TimeoutExpired:
                    logger.warning(
                        "Таймаут при завершении Chrome, принудительное закрытие"
                    )
                except Exception as terminate_error:
                    logger.warning("Ошибка при завершении Chrome: %s", terminate_error)

                # Принудительное завершение при необходимости
                if not process_closed:
                    try:
                        self._proc.kill()
                        self._proc.wait(timeout=60)
                        logger.debug("Chrome браузер принудительно завершён")
                    except Exception as kill_error:
                        logger.error(
                            "Ошибка при принудительном закрытии Chrome: %s", kill_error
                        )
            else:
                logger.warning("Процесс Chrome не инициализирован")

        except Exception as e:
            logger.error("Непредвиденная ошибка при закрытии Chrome: %s", e)

        # ВАЖНО: TemporaryDirectory.cleanup() гарантирует удаление профиля
        # даже при возникновении ошибок в предыдущем коде
        try:
            if hasattr(self, "_profile_tempdir") and self._profile_tempdir is not None:
                # cleanup() безопасен для повторного вызова
                self._profile_tempdir.cleanup()
                logger.debug("Временный профиль Chrome удалён через TemporaryDirectory.cleanup()")
        except Exception as profile_error:
            logger.error("Ошибка при удалении профиля через TemporaryDirectory: %s", profile_error)
            # Fallback: пытаемся удалить профиль напрямую
            try:
                if hasattr(self, "_profile_path") and self._profile_path:
                    shutil.rmtree(self._profile_path, ignore_errors=True)
                    logger.debug("Профиль удалён через fallback shutil.rmtree()")
            except Exception as fallback_error:
                logger.error("Fallback очистка профиля не удалась: %s", fallback_error)

    def __repr__(self) -> str:
        classname = self.__class__.__name__
        return f"{classname}(arguments={self._chrome_cmd!r})"
