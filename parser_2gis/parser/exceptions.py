import inspect


class ParserException(Exception):
    """Базовое исключение парсера.

    Добавляет контекстную информацию об ошибке:
    - Имя функции, где произошла ошибка
    - Номер строки
    - Имя файла
    """

    def __init__(self, message: str = "", **kwargs) -> None:
        # Получаем информацию о вызове
        frame = inspect.currentframe()
        if frame and frame.f_back:
            self.function_name = frame.f_back.f_code.co_name
            self.line_number = frame.f_back.f_lineno
            self.filename = frame.f_back.f_code.co_filename
        else:
            self.function_name = "unknown"
            self.line_number = 0
            self.filename = "unknown"

        # Формируем полное сообщение с контекстом
        full_message = (
            f"{message}. "
            f"Функция: {self.function_name}, "
            f"Строка: {self.line_number}, "
            f"Файл: {self.filename}"
        )
        super().__init__(full_message, **kwargs)


__all__ = [
    "ParserException",
]
