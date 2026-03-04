# JSON Schemas

Этот документ определяет JSON схемы, используемые skill-creator.

---

## evals.json

Определяет evals для скилла. Расположен в `evals/evals.json` внутри директории скилла.

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "Пример запроса пользователя",
      "expected_output": "Описание ожидаемого результата",
      "files": ["evals/files/sample1.pdf"],
      "expectations": [
        "Вывод включает X",
        "Скилл использовал скрипт Y"
      ]
    }
  ]
}
```

**Поля:**
- `skill_name`: Имя, совпадающее с frontmatter скилла
- `evals[].id`: Уникальный целочисленный идентификатор
- `evals[].prompt`: Задача для выполнения
- `evals[].expected_output`: Читаемое человеком описание успеха
- `evals[].files`: Опциональный список путей входных файлов (относительно корня скилла)
- `evals[].expectations`: Список проверяемых утверждений

---

## history.json

Отслеживает прогресс версий в режиме Improve. Расположен в корне workspace.

```json
{
  "started_at": "2026-01-15T10:30:00Z",
  "skill_name": "pdf",
  "current_best": "v2",
  "iterations": [
    {
      "version": "v0",
      "parent": null,
      "expectation_pass_rate": 0.65,
      "grading_result": "baseline",
      "is_current_best": false
    },
    {
      "version": "v1",
      "parent": "v0",
      "expectation_pass_rate": 0.75,
      "grading_result": "won",
      "is_current_best": false
    },
    {
      "version": "v2",
      "parent": "v1",
      "expectation_pass_rate": 0.85,
      "grading_result": "won",
      "is_current_best": true
    }
  ]
}
```

**Поля:**
- `started_at`: ISO timestamp начала улучшения
- `skill_name`: Имя улучшаемого скилла
- `current_best`: Идентификатор версии лучшего исполнителя
- `iterations[].version`: Идентификатор версии (v0, v1, ...)
- `iterations[].parent`: Родительская версия, от которой это было получено
- `iterations[].expectation_pass_rate`: Процент прохождения из оценки
- `iterations[].grading_result`: "baseline", "won", "lost" или "tie"
- `iterations[].is_current_best`: Является ли это текущей лучшей версией

---

## grading.json

Вывод от агента-оценщика. Расположен в `/grading.json`.

```json
{
  "expectations": [
    {
      "text": "Вывод включает имя 'John Smith'",
      "passed": true,
      "evidence": "Найдено в транскрипте Шаг 3: 'Извлечённые имена: John Smith, Sarah Johnson'"
    },
    {
      "text": "Таблица имеет формулу SUM в ячейке B10",
      "passed": false,
      "evidence": "Таблица не была создана. Вывод был текстовым файлом."
    }
  ],
  "summary": {
    "passed": 2,
    "failed": 1,
    "total": 3,
    "pass_rate": 0.67
  },
  "execution_metrics": {
    "tool_calls": {
      "Read": 5,
      "Write": 2,
      "Bash": 8
    },
    "total_tool_calls": 15,
    "total_steps": 6,
    "errors_encountered": 0,
    "output_chars": 12450,
    "transcript_chars": 3200
  },
  "timing": {
    "executor_duration_seconds": 165.0,
    "grader_duration_seconds": 26.0,
    "total_duration_seconds": 191.0
  },
  "claims": [
    {
      "claim": "Форма имеет 12 заполняемых полей",
      "type": "factual",
      "verified": true,
      "evidence": "Посчитано 12 полей в field_info.json"
    }
  ],
  "user_notes_summary": {
    "uncertainties": ["Использовал данные 2023, могут быть устаревшими"],
    "needs_review": [],
    "workarounds": ["Использовал текстовое наложение для незаполняемых полей"]
  },
  "eval_feedback": {
    "suggestions": [
      {
        "assertion": "Вывод включает имя 'John Smith'",
        "reason": "Галлюцинированный документ, упоминающий имя, также прошёл бы"
      }
    ],
    "overall": "Утверждения проверяют наличие, но не правильность."
  }
}
```

**Поля:**
- `expectations[]`: Оценённые ожидания с доказательствами
- `summary`: Агрегированные количества pass/fail
- `execution_metrics`: Использование инструментов и размер вывода (из executor's metrics.json)
- `timing`: Время wall clock (из timing.json)
- `claims`: Извлечённые и проверенные утверждения из вывода
- `user_notes_summary`: Проблемы, отмеченные исполнителем
- `eval_feedback`: (опционально) Предложения по улучшению для evals, присутствуют только когда оценщик определяет проблемы, достойные поднятия

---

## metrics.json

Вывод от агента-исполнителя. Расположен в `/outputs/metrics.json`.

```json
{
  "tool_calls": {
    "Read": 5,
    "Write": 2,
    "Bash": 8,
    "Edit": 1,
    "Glob": 2,
    "Grep": 0
  },
  "total_tool_calls": 18,
  "total_steps": 6,
  "files_created": ["filled_form.pdf", "field_values.json"],
  "errors_encountered": 0,
  "output_chars": 12450,
  "transcript_chars": 3200
}
```

**Поля:**
- `tool_calls`: Количество по типу инструмента
- `total_tool_calls`: Сумма всех вызовов инструментов
- `total_steps`: Количество основных шагов выполнения
- `files_created`: Список созданных файлов вывода
- `errors_encountered`: Количество ошибок во время выполнения
- `output_chars`: Общее количество символов файлов вывода
- `transcript_chars`: Количество символов транскрипта

---

## timing.json

Время wall clock для запуска. Расположен в `/timing.json`.

**Как захватить:** Когда задача субагента завершается, уведомление о задаче включает `total_tokens` и `duration_ms`. Сохраните их немедленно — они не сохраняются в другом месте и не могут быть восстановлены после факта.

```json
{
  "total_tokens": 84852,
  "duration_ms": 23332,
  "total_duration_seconds": 23.3,
  "executor_start": "2026-01-15T10:30:00Z",
  "executor_end": "2026-01-15T10:32:45Z",
  "executor_duration_seconds": 165.0,
  "grader_start": "2026-01-15T10:32:46Z",
  "grader_end": "2026-01-15T10:33:12Z",
  "grader_duration_seconds": 26.0
}
```

---

## benchmark.json

Вывод из режима Benchmark. Расположен в `benchmarks/<timestamp>/benchmark.json`.

```json
{
  "metadata": {
    "skill_name": "pdf",
    "skill_path": "/path/to/pdf",
    "executor_model": "claude-sonnet-4-20250514",
    "analyzer_model": "most-capable-model",
    "timestamp": "2026-01-15T10:30:00Z",
    "evals_run": [1, 2, 3],
    "runs_per_configuration": 3
  },
  "runs": [
    {
      "eval_id": 1,
      "eval_name": "Ocean",
      "configuration": "with_skill",
      "run_number": 1,
      "result": {
        "pass_rate": 0.85,
        "passed": 6,
        "failed": 1,
        "total": 7,
        "time_seconds": 42.5,
        "tokens": 3800,
        "tool_calls": 18,
        "errors": 0
      },
      "expectations": [
        {"text": "...", "passed": true, "evidence": "..."}
      ],
      "notes": [
        "Использовал данные 2023, могут быть устаревшими",
        "Использовал текстовое наложение для незаполняемых полей"
      ]
    }
  ],
  "run_summary": {
    "with_skill": {
      "pass_rate": {"mean": 0.85, "stddev": 0.05, "min": 0.80, "max": 0.90},
      "time_seconds": {"mean": 45.0, "stddev": 12.0, "min": 32.0, "max": 58.0},
      "tokens": {"mean": 3800, "stddev": 400, "min": 3200, "max": 4100}
    },
    "without_skill": {
      "pass_rate": {"mean": 0.35, "stddev": 0.08, "min": 0.28, "max": 0.45},
      "time_seconds": {"mean": 32.0, "stddev": 8.0, "min": 24.0, "max": 42.0},
      "tokens": {"mean": 2100, "stddev": 300, "min": 1800, "max": 2500}
    },
    "delta": {
      "pass_rate": "+0.50",
      "time_seconds": "+13.0",
      "tokens": "+1700"
    }
  },
  "notes": [
    "Утверждение 'Вывод является PDF файлом' проходит 100% в обеих конфигурациях — может не дифференцировать ценность скилла",
    "Eval 3 показывает высокую вариативность (50% ± 40%) — может быть ненадёжным или зависимым от модели",
    "Запуски without_skill последовательно проваливаются на ожиданиях извлечения таблиц",
    "Скилл добавляет 13с среднего времени выполнения, но улучшает pass rate на 50%"
  ]
}
```

**Поля:**
- `metadata`: Информация о запуске бенчмарка
- `skill_name`: Имя скилла
- `timestamp`: Когда был запущен бенчмарк
- `evals_run`: Список имён или ID evals
- `runs_per_configuration`: Количество запусков на конфигурацию (например, 3)
- `runs[]`: Индивидуальные результаты запусков
- `eval_id`: Числовой идентификатор eval
- `eval_name`: Читаемое человеком имя eval (используется как заголовок секции в просмотрщике)
- `configuration`: Должно быть `"with_skill"` или `"without_skill"` (просмотрщик использует это точное строковое значение для группировки и цветовой кодировки)
- `run_number`: Целочисленный номер запуска (1, 2, 3...)
- `result`: Вложенный объект с `pass_rate`, `passed`, `total`, `time_seconds`, `tokens`, `errors`
- `run_summary`: Статистические агрегаты на конфигурацию
- `with_skill` / `without_skill`: Каждый содержит объекты `pass_rate`, `time_seconds`, `tokens` с полями `mean` и `stddev`
- `delta`: Строки разницы, такие как `"+0.50"`, `"+13.0"`, `"+1700"`
- `notes`: Свободные наблюдения от аналитика

**Важно:** Просмотрщик читает эти имена полей точно. Использование `config` вместо `configuration`, или размещение `pass_rate` на верхнем уровне запуска вместо вложенного под `result`, приведёт к тому, что просмотрщик покажет пустые/нулевые значения. Всегда ссылайтесь на эту схему при генерации benchmark.json вручную.

---

## comparison.json

Вывод от слепого сравнителя. Расположен в `/comparison-N.json`.

```json
{
  "winner": "A",
  "reasoning": "Вывод A предоставляет полное решение с правильным форматированием и всеми требуемыми полями. Вывод B пропускает поле даты и имеет несоответствия форматирования.",
  "rubric": {
    "A": {
      "content": {
        "correctness": 5,
        "completeness": 5,
        "accuracy": 4
      },
      "structure": {
        "organization": 4,
        "formatting": 5,
        "usability": 4
      },
      "content_score": 4.7,
      "structure_score": 4.3,
      "overall_score": 9.0
    },
    "B": {
      "content": {
        "correctness": 3,
        "completeness": 2,
        "accuracy": 3
      },
      "structure": {
        "organization": 3,
        "formatting": 2,
        "usability": 3
      },
      "content_score": 2.7,
      "structure_score": 2.7,
      "overall_score": 5.4
    }
  },
  "output_quality": {
    "A": {
      "score": 9,
      "strengths": ["Полное решение", "Хорошо отформатировано", "Все поля присутствуют"],
      "weaknesses": ["Незначительное несоответствие стиля в заголовке"]
    },
    "B": {
      "score": 5,
      "strengths": ["Читаемый вывод", "Правильная базовая структура"],
      "weaknesses": ["Пропущено поле даты", "Несоответствия форматирования", "Частичное извлечение данных"]
    }
  },
  "expectation_results": {
    "A": {
      "passed": 4,
      "total": 5,
      "pass_rate": 0.80,
      "details": [
        {"text": "Вывод включает имя", "passed": true}
      ]
    },
    "B": {
      "passed": 3,
      "total": 5,
      "pass_rate": 0.60,
      "details": [
        {"text": "Вывод включает имя", "passed": true}
      ]
    }
  }
}
```

---

## analysis.json

Вывод от пост-фактум аналитика. Расположен в `/analysis.json`.

```json
{
  "comparison_summary": {
    "winner": "A",
    "winner_skill": "path/to/winner/skill",
    "loser_skill": "path/to/loser/skill",
    "comparator_reasoning": "Краткое резюме того, почему компаратор выбрал победителя"
  },
  "winner_strengths": [
    "Чёткие пошаговые инструкции для обработки многостраничных документов",
    "Включённый скрипт валидации, который ловил ошибки форматирования"
  ],
  "loser_weaknesses": [
    "Расплывчатая инструкция 'обработать документ соответственно' привела к непоследовательному поведению",
    "Нет скрипта для валидации, агент должен был импровизировать"
  ],
  "instruction_following": {
    "winner": {
      "score": 9,
      "issues": ["Незначительно: пропустил опциональный шаг логирования"]
    },
    "loser": {
      "score": 6,
      "issues": [
        "Не использовал шаблон форматирования скилла",
        "Изобрёл собственный подход вместо следования шагу 3"
      ]
    }
  },
  "improvement_suggestions": [
    {
      "priority": "high",
      "category": "instructions",
      "suggestion": "Замените 'обработать документ соответственно' на явные шаги",
      "expected_impact": "Устранило бы неоднозначность, которая вызвала непоследовательное поведение"
    }
  ],
  "transcript_insights": {
    "winner_execution_pattern": "Прочитал скилл -> Следовал 5-шаговому процессу -> Использовал скрипт валидации",
    "loser_execution_pattern": "Прочитал скилл -> Неясен подход -> Попробовал 3 разных метода"
  }
}
```

---
