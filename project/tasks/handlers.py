from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Optional

from django.utils.timezone import now
from tasks.models import Task, TaskSchedule


class TaskCreationHandler(ABC):
    def __init__(self, next_handler: Optional["TaskCreationHandler"] = None):
        self.next_handler = next_handler

    @abstractmethod
    def handle(self, schedule: TaskSchedule, last_task: Task | None) -> bool:
        pass


class DaysCheckHandler(TaskCreationHandler):
    def handle(self, schedule: TaskSchedule, last_task: Task | None) -> bool:
        if (
            schedule.every_x_days is None
            or last_task is None
            or last_task.created_at <= now() - timedelta(days=schedule.every_x_days)
        ):
            return (
                self.next_handler.handle(schedule, last_task)
                if self.next_handler
                else True
            )
        return False


class HoursCheckHandler(TaskCreationHandler):
    def handle(self, schedule: TaskSchedule, last_task: Task | None) -> bool:
        if (
            schedule.every_x_hours is None
            or last_task is None
            or last_task.created_at <= now() - timedelta(hours=schedule.every_x_hours)
        ):
            return (
                self.next_handler.handle(schedule, last_task)
                if self.next_handler
                else True
            )
        return False


class TaskCountCheckHandler(TaskCreationHandler):
    def handle(self, schedule: TaskSchedule, last_task: Task | None) -> bool:
        if (
            Task.objects.filter(task_schedule=schedule).count()
            <= schedule.schedule_x_times
        ):
            return (
                self.next_handler.handle(schedule, last_task)
                if self.next_handler
                else True
            )
        return False


task_creation_check_chain = TaskCountCheckHandler(HoursCheckHandler(DaysCheckHandler()))
