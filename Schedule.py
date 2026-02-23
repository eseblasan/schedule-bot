from dataclasses import dataclass

@dataclass
class Lesson:
    start: str
    end: str
    subject: str
    lesson_type: str
    group: str | None

@dataclass
class ScheduleForDay:
    day: str
    lessons: list

class WeeklyPlan:
    week: int
    schedule: list[ScheduleForDay] | None

    def __init__(self, week: int, schedule: dict):
        self.week = week
        self.schedule = schedule

    def to_dict(self):
        pass

    def from_dict(self):
        pass