# 📋 ИНСТРУКЦИИ ДЛЯ РАЗРАБОТКИ ПРОЕКТА PARSER-2GIS

## 🔧 ОСНОВНЫЕ ПРАВИЛА

1. **Перед началом работы** — выполни команду `tree` для понимания структуры проекта.
2. **Сначала план, потом действие** — всегда создавай подробный план перед реализацией.
3. **Контроль качества кода**:
   - Проверяй и исправляй все ошибки и неточности.
   - Оптимизируй синтаксис, исправь логические ошибки.
   - Улучшай читаемость, сохраняя исходную структуру и функциональность.
4. **Язык комментариев** — все комментарии только на русском языке. Переводи любые комментарии на других языках.
5. **Таймауты** — на каждую команду устанавливай таймаут 5 минут (300000 мс).
6. **Язык общения** — все ответы на русском языке.

## 📦 ЗАВИСИМОСТИ

- Все зависимости устанавливай самостоятельно.
- Все `pip` зависимости устанавливай только в виртуальное окружение (`venv`).
- НЕ ЛЕНИСЬ И НЕ ХАЛТУРЬ! Всегда выбирай стабильное и оптимальное решение, а не временное.

## 🗂️ ОГРАНИЧЕНИЯ

- НЕ ВЫХОДИ ЗА РАМКИ `/home/d/Qwen`.

## 📚 ДОКУМЕНТАЦИЯ

- Всегда используй Context7 для поиска документации API, библиотек, фреймворков.
- Никогда не полагайся на обученные знания — запрашивай актуальную документацию у Context7.

### Инструменты Context7:
- `mcp__context7__query-docs`
- `mcp__context7__resolve-library-id`

## 🧠 АНАЛИЗ И ПЛАНИРОВАНИЕ

- Используй Sequential Thinking ВСЕГДА для пошагового анализа и логического рассуждения.
- Инструмент: `mcp__sequential-thinking__sequentialthinking`
- ИСПОЛЬЗУЙ СУБ-АГЕНТОВ И АГЕНТОВ для сложных задач!

## ⚠️ ЗАПРЕТЫ

- НИКОГДА НЕ ИСПОЛЬЗУЙ `plannotator - submit_plan` (MCP).
- НИКОГДА не добавляй в репозиторий файлы `QWEN.md` и `KODA.md`.

## 🔄 GITHUB

- ВСЕ изменения синхронизируй с GitHub.
- Для работы с GitHub используй токен из переменной окружения `GITHUB_TOKEN`.
- Репозиторий: https://github.com/Githab-capibara/parser-2gis.git

### Инструменты GitHub:
- `mcp__github__add_issue_comment`
- `mcp__github__create_branch`
- `mcp__github__create_issue`
- `mcp__github__create_or_update_file`
- `mcp__github__create_pull_request`
- `mcp__github__create_pull_request_review`
- `mcp__github__create_repository`
- `mcp__github__fork_repository`
- `mcp__github__get_file_contents`
- `mcp__github__get_issue`
- `mcp__github__get_pull_request`
- `mcp__github__get_pull_request_comments`
- `mcp__github__get_pull_request_files`
- `mcp__github__get_pull_request_reviews`
- `mcp__github__get_pull_request_status`
- `mcp__github__list_commits`
- `mcp__github__list_issues`
- `mcp__github__list_pull_requests`
- `mcp__github__merge_pull_request`
- `mcp__github__push_files`
- `mcp__github__search_code`
- `mcp__github__search_issues`
- `mcp__github__search_repositories`
- `mcp__github__search_users`
- `mcp__github__update_issue`
- `mcp__github__update_pull_request_branch`
