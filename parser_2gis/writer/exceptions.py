class WriterUnknownFileFormat(Exception):
    """Выбрасывается, когда пользователь указал неизвестный формат выходного файла."""

    pass


__all__ = [
    "WriterUnknownFileFormat",
]
