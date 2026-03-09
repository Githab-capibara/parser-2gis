# Инструкция по синхронизации с GitHub

## Проблема

GitHub блокирует `git push` из-за обнаруженного токена GitHub в файле `KODA.md`, который был закоммичен в коммите `db3a26c`.

## Решение

### Вариант 1: Очистка истории коммитов (рекомендуется)

```bash
# 1. Найти коммит с токеном
git log --all --grep="токен" --oneline

# 2. Сделать interactive rebase для удаления коммита с токеном
git rebase -i db3a26c^

# В редакторе удалить строку с коммитом, содержащим токен, или изменить её на 'drop'

# 3. После rebase сделать force push
git push origin main --force-with-lease
```

### Вариант 2: Создание нового коммита с исправлениями

```bash
# 1. Убедиться, что KODA.md в .gitignore
echo "KODA.md" >> .gitignore

# 2. Удалить KODA.md из tracked файлов
git rm --cached KODA.md

# 3. Закоммитить изменения
git add .gitignore
git commit -m "chore: Удаление KODA.md из репозитория"

# 4. Попытаться сделать push
git push origin main
```

### Вариант 3: Использование GitHub UI

1. Перейти на https://github.com/Githab-capibara/parser-2gis
2. Скачать локальные изменения вручную через веб-интерфейс
3. Или разблокировать токен по ссылке из ошибки:
   https://github.com/Githab-capibara/parser-2gis/security/secret-scanning/unblock-secret/3AhARFW4u2wLkD7vexYwfkrP5sj

### Вариант 4: Сброс токена (если есть доступ к настройкам GitHub)

1. Перейти в https://github.com/settings/tokens
2. Отозвать текущий токен `[REDACTED]`
3. Создать новый токен
4. Обновить токен в локальных настройках (не в репозитории!)

## Текущий статус

- ✅ README.md обновлен и содержит всю актуальную информацию
- ✅ KODA.md добавлен в `.gitignore`
- ✅ KODA.md удален из tracked файлов
- ⚠️ Требуется ручное вмешательство для push в GitHub

## Содержимое README.md

Новый README.md содержит:
- Объединенную документацию из всех .md файлов проекта
- Информацию о функциях v2.0 и v2.1
- Актуальную статистику тестов (269 passed)
- Code quality score (95/100)
- Полную структуру проекта
- Примеры использования
- FAQ и поддержку

## Следующие шаги

1. Разрешить проблему с токеном через GitHub UI
2. Сделать `git push origin main`
3. Проверить, что README.md обновился на GitHub

---

**Дата создания:** 2026-03-09
**Статус:** Ожидает разрешения проблемы с токеном
