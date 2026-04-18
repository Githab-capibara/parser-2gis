<!-- NOTE: переписано ИИ -->
# Вклад в проект

Спасибо за интерес к Parser2GIS!

## Как помочь

1. **Сообщить об ошибке** — создайте [Issue](https://github.com/Githab-capibara/parser-2gis/issues)
2. **Предложить улучшение** — открыйте Pull Request
3. **Улучшить документацию** — исправьте опечатки или добавьте примеры

## Руководство для разработчиков

### Настройка окружения

```bash
git clone https://github.com/Githab-capibara/parser-2gis.git
cd parser-2gis

# Создать виртуальное окружение
python -m venv .venv
source .venv/bin/activate

# Установить зависимости
pip install -e ".[dev]"
```

### Запуск тестов

```bash
pytest tests/ -v
```

### Проверка качества кода

Проект использует несколько инструментов:

```bash
ruff check .      # Линтер
mypy .          # Проверка типов
bandit -r parser_2gis  # Безопасность
```

### Стиль кода

- Python 3.10+ (PEP 604, структурное аннотирование)
- Русские комментарии в коде
- Одно имя — один импорт в `__all__`
- Типизация для открытых API

### Отправка изменений

1. Создайте ветку: `git checkout -b fix/description`
2. Внесите изменения
3. Добавьте тесты
4. Запушьте: `git push -u origin fix/description`
5. Откройте Pull Request

## Требования к PR

- Все тесты проходят
- Нет новых предупреждений линтеров
- Описаны изменения в коммите

## Вопросы

- Email: interlark@gmail.com
- GitHub Issues: https://github.com/Githab-capibara/parser-2gis/issues