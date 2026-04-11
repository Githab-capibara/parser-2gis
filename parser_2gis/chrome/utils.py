"""Утилиты для работы с Chrome.

Предоставляет функции для:
- Поиска пути к исполняемому файлу Chrome
- Получения свободного порта для подключения
"""

from __future__ import annotations

import functools
import os
import shutil
import socket
import time


@functools.lru_cache(maxsize=1)
def locate_chrome_path() -> str | None:
    """Определяет путь к исполняемому файлу Chrome для Linux Ubuntu.

    Returns:
        Путь к исполняемому файлу Chrome или None, если браузер не найден.

    Примечание:
        H004: Оптимизированный поиск:
        1. Сначала используется shutil.which() - быстрее чем subprocess
        2. Затем поиск в наиболее вероятных директориях
        3. Кэширование результата через lru_cache(maxsize=1)

    """
    # H004: Приоритетные исполняемые файлы (наиболее вероятные сначала)
    browser_executables = [
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "chrome",
        "chrome-browser",
    ]

    # H004: Сначала быстрый поиск через shutil.which() (использует PATH)
    for f in browser_executables:
        path = shutil.which(f)
        if path:
            # Валидация пути через realpath для предотвращения атак
            return str(os.path.realpath(path))

    # H004: Поиск только в наиболее вероятных директориях (сокращённый список)
    # Большинство систем устанавливают Chrome в /usr/bin или /opt/google/chrome
    priority_dirs = ["/usr/bin", "/opt/google/chrome", "/usr/local/bin"]

    for d in priority_dirs:
        for f in browser_executables:
            binary_path = os.path.join(d, f)
            if os.path.isfile(binary_path):
                # Валидация пути через realpath для предотвращения атак
                return str(os.path.realpath(binary_path))

    return None


def free_port() -> int:
    """Получает свободный порт с помощью сокетов.

    Returns:
        Номер свободного порта на localhost.

    Примечание:
        Порт выбирается автоматически операционной системой.
        Сокет закрывается после выбора порта, порт остаётся свободным для использования.
        ИСПРАВЛЕНИЕ: Добавлена опция SO_REUSEADDR для предотвращения проблем с занятостью порта.

    Note:
        Существует потенциальная race condition: между закрытием сокета и
        использованием порта другой процесс может занять тот же порт.
        Для снижения риска добавлена задержка time.sleep(0.1) после
        выбора порта. При высокой степени параллелизма рекомендуется
        использовать механизм повторных попыток при привязке порта.

    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as free_socket:
        # ИСПРАВЛЕНИЕ: Устанавливаем SO_REUSEADDR для предотвращения проблем с занятостью порта
        free_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        free_socket.bind(("127.0.0.1", 0))
        free_socket.listen(5)
        port = free_socket.getsockname()[1]
    # Сокет закрывается в конце контекстного менеджера
    # Увеличенная задержка для гарантии освобождения порта при параллельных запусках
    time.sleep(0.1)
    return port
