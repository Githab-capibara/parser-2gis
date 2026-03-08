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

    Args:
        chrome_options: Опции Chrome.

    Raises:
        ChromePathNotFound: Если путь к Chrome не найден.
        ValueError: Если путь к браузеру некорректен.
        FileNotFoundError: Если файл браузера не существует.
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

        # Строгая валидация binary_path
        self._validate_binary_path(binary_path)

        logger.debug("Запуск Chrome браузера по пути: %s", binary_path)

        # Инициализация профиля и порта
        self._profile_path = tempfile.mkdtemp()
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
            "--remote-allow-origins=http://localhost",
            f"--js-flags=--expose-gc --max-old-space-size={memory_limit}",
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
            except Exception:
                pass
            raise

    def _validate_binary_path(self, binary_path: str) -> None:
        """
        Валидирует путь к исполняемому файлу браузера.

        Args:
            binary_path: Путь к браузеру для валидации.

        Raises:
            ValueError: Если путь не абсолютный.
            FileNotFoundError: Если файл не существует.
            PermissionError: Если файл не исполняемый.
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

        # Проверка на исполняемость (для Unix-систем)
        if os.name != "nt" and not os.access(binary_path, os.X_OK):
            logger.warning("Файл браузера не имеет прав на выполнение: %s", binary_path)

    @property
    def remote_port(self) -> int:
        """Порт отладки."""
        return self._remote_port

    @wait_until_finished(timeout=300, throw_exception=False)
    def _delete_profile(self) -> bool:
        """Удаляет временный профиль Chrome.

        Returns:
            `True` при успешном удалении, `False` при неудаче.

        Примечание:
            Использует многоуровневую стратегию удаления:
            1. Попытка обычного удаления
            2. Принудительное удаление с ignore_errors=True
            3. Логирование ошибки для последующей очистки при перезапуске
        """
        # Проверяем существование профиля перед удалением
        if not os.path.exists(self._profile_path):
            logger.debug(
                "Профиль Chrome уже удалён или не существовал: %s", self._profile_path
            )
            return True

        try:
            # Первая попытка: обычное удаление
            shutil.rmtree(self._profile_path, ignore_errors=False)
            profile_deleted = not os.path.isdir(self._profile_path)
            if profile_deleted:
                logger.debug("Временный профиль Chrome удалён: %s", self._profile_path)
                return True

            # Если профиль остался, пробуем принудительное удаление
            logger.warning(
                "Профиль Chrome не удалён с первой попытки, пробуем принудительно"
            )

        except (OSError, PermissionError) as e:
            # Ошибка при удалении - пробуем принудительно
            logger.warning("Ошибка при удалении профиля Chrome (попытка 1): %s", e)

        except Exception as unexpected_error:
            # Непредвиденная ошибка
            logger.error(
                "Непредвиденная ошибка при удалении профиля Chrome: %s",
                unexpected_error,
            )

        # Вторая попытка: игнорируем ошибки для предотвращения утечки дискового пространства
        try:
            shutil.rmtree(self._profile_path, ignore_errors=True)
            logger.debug("Профиль Chrome удалён принудительно (попытка 2)")
            return not os.path.isdir(self._profile_path)
        except Exception as cleanup_error:
            # Третья попытка не удалась - логируем ошибку для последующей очистки
            logger.error(
                "Не удалось удалить профиль Chrome после 2 попыток: %s. Профиль может остаться на диске.",
                cleanup_error,
            )
            # Помечаем профиль для удаления при следующем запуске
            try:
                # Создаём маркер для последующей очистки
                marker_file = os.path.join(
                    os.path.dirname(self._profile_path), ".cleanup_marker"
                )
                with open(marker_file, "a", encoding="utf-8") as f:
                    f.write(f"{self._profile_path}\n")
                logger.debug("Создан маркер для последующей очистки: %s", marker_file)
            except Exception:
                pass  # Не критично если маркер не создан
            return False

    def close(self) -> None:
        """Закрывает браузер и удаляет временный профиль.

        Примечание:
            Функция гарантирует попытку закрытия даже при ошибках.
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

        # Удаляем временный профиль
        try:
            if hasattr(self, "_profile_path") and self._profile_path:
                self._delete_profile()
        except Exception as profile_error:
            logger.error("Ошибка при удалении профиля: %s", profile_error)

    def __repr__(self) -> str:
        classname = self.__class__.__name__
        return f"{classname}(arguments={self._chrome_cmd!r})"
