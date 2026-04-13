"""CLI runner для запуска парсера в режиме командной строки.

Предоставляет класс CLIRunner для последовательной обработки URL:
- Запуск парсера для каждого URL
- Обработка ошибок и исключений
- Логирование результатов парсинга
"""

from __future__ import annotations

import time

from parser_2gis.chrome.exceptions import ChromeRuntimeException, ChromeUserAbortException
from parser_2gis.logger import log_parser_finish, logger
from parser_2gis.parser import get_parser
from parser_2gis.writer import get_writer

from .runner import AbstractRunner


class CLIRunner(AbstractRunner):
    """Запуск CLI парсера.

    Args:
        urls: URL 2GIS с элементами для сбора.
        output_path: Путь к результирующему файлу.
        output_format: Формат `csv`, `xlsx` или `json`.
        config: Конфигурация.

    """

    def start(self) -> None:
        """Запускает процесс парсинга в CLI режиме.

        Примечание:
            Метод последовательно обрабатывает все URL, используя
            writer для записи результатов и parser для извлечения данных.
        """
        start_time = time.time()
        total_urls = len(self._urls)
        parsed_count = 0
        error_count = 0

        logger.info("🚀 Начало парсинга %d URL...", total_urls)

        try:
            with get_writer(self._output_path, self._output_format, self._config.writer) as writer:
                for idx, url in enumerate(self._urls, 1):
                    logger.info("📄 [%d/%d] Парсинг ссылки: %s", idx, total_urls, url)
                    with get_parser(
                        url,
                        chrome_options=self._config.chrome,
                        parser_options=self._config.parser,
                    ) as parser:
                        try:
                            parser.parse(writer)
                            parsed_count += 1
                            logger.info("✅ [%d/%d] Ссылка успешно обработана", idx, total_urls)
                        except (ValueError, TypeError, RuntimeError) as parse_error:
                            error_count += 1
                            logger.error(
                                "❌ [%d/%d] Ошибка при парсинге ссылки: %s",
                                idx,
                                total_urls,
                                parse_error,
                            )
                            # Продолжаем парсинг следующих URL
                            continue
        except (KeyboardInterrupt, ChromeUserAbortException):
            logger.error("🛑 Работа парсера прервана пользователем.")
            log_parser_finish(
                success=False,
                stats={"Всего URL": total_urls, "Обработано": parsed_count, "Ошибки": error_count},
            )
            return
        except ConnectionError as e:
            # Ошибки сетевого соединения
            logger.error("❌ Ошибка сетевого соединения: %s", e)
            log_parser_finish(success=False)
            return
        except TimeoutError as e:
            # Таймаут операции
            logger.error("❌ Таймаут операции: %s", e)
            log_parser_finish(success=False)
            return
        except PermissionError as e:
            # Ошибка доступа к файлу
            logger.error("❌ Ошибка доступа к файлу: %s", e)
            log_parser_finish(success=False)
            return
        except OSError as e:
            # Ошибки файловой системы
            logger.error("❌ Ошибка файловой системы: %s", e)
            log_parser_finish(success=False)
            return
        except (TypeError, RuntimeError, ChromeRuntimeException) as e:
            if isinstance(e, ChromeRuntimeException) and str(e) == "Вкладка была остановлена":
                logger.error("❌ Вкладка браузера была закрыта.")
            else:
                logger.error("❌ Ошибка во время работы парсера.", exc_info=True)
            log_parser_finish(success=False)
            return
        finally:
            # Вычисляем длительность
            duration = time.time() - start_time
            duration_str = f"{duration:.2f} сек."

            # Финальная статистика
            stats = {
                "Всего URL": str(total_urls),
                "Успешно": str(parsed_count),
                "Ошибки": str(error_count),
            }

            logger.info("🏁 Парсинг завершён.")
            log_parser_finish(success=error_count == 0, stats=stats, duration=duration_str)

    def stop(self) -> None:
        """Останавливает процесс парсинга в CLI режиме.

        Примечание: В CLI режиме остановка не поддерживается, так как
        процесс выполняется синхронно. Для остановки необходимо
        использовать сочетание клавиш Ctrl+C.
        """
