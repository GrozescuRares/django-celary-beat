import re
from enum import StrEnum

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


def validate_addition_operation(value: str) -> None:
    if not re.fullmatch(r"\d+(\.\d+)?\+\d+(\.\d+)?", value):
        raise ValidationError(f'"{value}" is not a valid addition operation.')


class TaskSchedule(models.Model):
    task_schedule_id = models.AutoField(primary_key=True)
    operation = models.TextField(validators=[validate_addition_operation])
    priority = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(9)], null=True
    )
    every_x_days = models.PositiveIntegerField(
        validators=[MinValueValidator(1)], null=True
    )
    every_x_hours = models.PositiveIntegerField(
        validators=[MinValueValidator(1)], null=True
    )
    schedule_x_times = models.PositiveIntegerField(
        validators=[MinValueValidator(1)], default=1
    )  # Minimum value is 1
    checked_scheduling_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self) -> str:
        return f"TaskSchedule {self.task_schedule_id} - {self.operation}"


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"


class Task(models.Model):
    task_id = models.AutoField(primary_key=True)
    operation = models.TextField(validators=[validate_addition_operation])
    priority = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(9)]
    )
    status = models.CharField(
        max_length=10,
        choices=[(status.value, status.value) for status in TaskStatus],
        default=TaskStatus.PENDING,
    )
    result = models.FloatField(null=True, blank=True)
    task_schedule = models.ForeignKey(
        TaskSchedule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Task {self.task_id} - {self.operation}"
