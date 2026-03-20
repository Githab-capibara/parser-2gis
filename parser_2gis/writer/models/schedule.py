"""Модель расписания работы организации.

Предоставляет классы для представления расписания:
- WorkingHour - интервал работы (from/to)
- ScheduleDay - расписание на один день
- Schedule - недельное расписание с комментариями
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class WorkingHour(BaseModel):
    """Модель рабочего часа.

    Атрибуты:
        from_: Время начала работы в формате hh:mm.
        to: Время окончания работы в формате hh:mm.
    """

    # Значение в формате hh:mm
    from_: str = Field(..., alias="from")

    # Значение в формате hh:mm
    to: str


class ScheduleDay(BaseModel):
    """Модель расписания на один день.

    Атрибуты:
        working_hours: Список интервалов работы в течение дня.
    """

    # Часы работы
    working_hours: List[WorkingHour]


class Schedule(BaseModel):
    """Модель расписания работы организации.

    Атрибуты:
        Mon: Расписание на понедельник.
        Tue: Расписание на вторник.
        Wed: Расписание на среду.
        Thu: Расписание на четверг.
        Fri: Расписание на пятницу.
        Sat: Расписание на субботу.
        Sun: Расписание на воскресенье.
        is_24x7: Признак того, что организация работает круглосуточно 7 дней в неделю.
        description: Локализованное описание возможных изменений во времени работы.
        comment: Комментарий (например "Кругосуточно в праздничные дни").
        date_from: Дата начала изменений в расписании работы. Формат: "YYYY-MM-DD".
        date_to: Дата конца изменений в расписании работы. Формат: "YYYY-MM-DD".
    """

    # Понедельник
    Mon: Optional[ScheduleDay] = None

    # Вторник
    Tue: Optional[ScheduleDay] = None

    # Среда
    Wed: Optional[ScheduleDay] = None

    # Четверг
    Thu: Optional[ScheduleDay] = None

    # Пятница
    Fri: Optional[ScheduleDay] = None

    # Суббота
    Sat: Optional[ScheduleDay] = None

    # Воскресенье
    Sun: Optional[ScheduleDay] = None

    # Признак того, что организация работает круглосуточно 7 дней в неделю.
    # Если поле отсутствует, то организация не считается работающей круглосуточно.
    is_24x7: Optional[bool] = None

    # Локализованное описание возможных изменений во времени работы.
    # Применяется для праздников, временных ограничений и т.д.
    description: Optional[str] = None

    # Комментарий (например "Кругосуточно в праздничные дни")
    comment: Optional[str] = None

    # Дата начала изменений в расписании работы. Формат: "YYYY-MM-DD"
    date_from: Optional[str] = None

    # Дата конца изменений в расписании работы. Формат: "YYYY-MM-DD"
    date_to: Optional[str] = None

    def to_str(self, join_char: str, add_comment: bool = False) -> str:
        """Расписание как строка.

        Args:
            join_char: Символ для разделения дней.
            add_comment: Добавлять ли комментарий в конце.

        Returns:
            Расписание в виде строки.
        """
        # Явно указываем имена дней для совместимости с Pydantic v1 и v2
        days_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        days_mapping = dict(
            Mon="Пн", Tue="Вт", Wed="Ср", Thu="Чт", Fri="Пт", Sat="Сб", Sun="Вс"
        )

        slots_list = []
        for day_name in days_names:
            day_value = getattr(self, day_name)
            if not day_value:
                continue

            day_slot = f"{days_mapping[day_name]}: "
            for i, time_slot in enumerate(day_value.working_hours):
                if i > 0:
                    day_slot += ", "
                day_slot += f"{time_slot.from_}-{time_slot.to}"

            slots_list.append(day_slot)

        result = join_char.join(slots_list)
        if add_comment and self.comment:
            result += " (%s)" % self.comment

        return result
