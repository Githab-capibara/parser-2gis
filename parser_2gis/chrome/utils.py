"""Утилиты для работы с Chrome.

Предоставляет функции для:
- Поиска пути к исполняемому файлу Chrome
- Получения свободного порта для подключения
"""

from __future__ import annotations

import functools
import os
import socket
import subprocess
import time


@functools.lru_cache()
def locate_chrome_path() -> str | None:
    """Определяет путь к исполняемому файлу Chrome для Linux Ubuntu.

    Returns:
        Путь к исполняемому файлу Chrome или None, если браузер не найден.

    Примечание:
        Поиск выполняется в стандартных директориях Linux:
        - /usr/bin, /usr/sbin, /usr/local/bin, /usr/local/sbin
        - /opt/google/chrome
        - /snap/bin (для Snap-версий Chromium)
        Также используется команда 'which' для поиска.
    """
    # Стандартные пути для Chrome на Linux Ubuntu
    app_dirs = [
        "/usr/bin",
        "/usr/sbin",
        "/usr/local/bin",
        "/usr/local/sbin",
        "/sbin",
        "/opt/google/chrome",
        "/snap/bin",
    ]
    browser_executables = [
        "google-chrome",
        "chrome",
        "chrome-browser",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
    ]

    # Поиск в стандартных директориях
    for d in app_dirs:
        for f in browser_executables:
            binary_path = os.path.join(d, f)
            if os.path.isfile(binary_path):
                # Валидация пути через realpath для предотвращения атак
                return os.path.realpath(binary_path)

    # Использование команды 'which' для поиска исполняемого файла Chrome
    for f in browser_executables:
        try:
            ret_output = subprocess.check_output(["which", f])
            binary_path = ret_output.decode("utf-8").strip()
            if os.path.isfile(binary_path):
                # Валидация пути через realpath для предотвращения атак
                return os.path.realpath(binary_path)

        except subprocess.CalledProcessError:
            # Binary не найден в PATH, продолжаем поиск
            pass

    return None


def free_port() -> int:
    """Получает свободный порт с помощью сокетов.

    Returns:
        Номер свободного порта на localhost.

    Примечание:
        Порт выбирается автоматически операционной системой.
        Сокет закрывается после выбора порта, порт остаётся свободным для использования.
        ИСПРАВЛЕНИЕ: Добавлена опция SO_REUSEADDR для предотвращения проблем с занятостью порта.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as free_socket:
        # ИСПРАВЛЕНИЕ: Устанавливаем SO_REUSEADDR для предотвращения проблем с занятостью порта
        free_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        free_socket.bind(("127.0.0.1", 0))
        free_socket.listen(5)
        port = free_socket.getsockname()[1]
    # Сокет закрывается в конце контекстного менеджера
    # Небольшая задержка для гарантии освобождения порта
    time.sleep(0.01)
    return port
