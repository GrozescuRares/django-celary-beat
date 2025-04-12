from celery import group
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F
from django.db.transaction import on_commit
from django.utils.timezone import now

from tasks.handlers import task_creation_check_chain
from tasks.models import Task, TaskSchedule

from core.tasks import process_task


class Command(BaseCommand):
    help = "Process task schedules and create tasks if conditions are met."

    def handle(self, *args, **kwargs):
        # Make sure that the schedules that are currently processed don't get deleted in the meantime
        task_schedules = (
            TaskSchedule.objects.select_for_update(skip_locked=True)
            .filter(schedule_x_times__gt=0)
            .order_by("checked_scheduling_at")[:100]
        )
        new_tasks = []

        with transaction.atomic():
            for schedule in task_schedules:
                # Get the last created task for the schedule
                last_task = (
                    Task.objects.filter(task_schedule=schedule)
                    .order_by("-created_at")
                    .first()
                )

                if task_creation_check_chain.handle(schedule, last_task) is False:
                    continue

                new_task = Task.objects.create(
                    operation=schedule.operation,
                    priority=schedule.priority,
                    task_schedule=schedule,
                )
                new_tasks.append(new_task)

                # Update the schedule by decreasing schedule_x_times and
                # updating checked_scheduling_data to ensure that other schedules will be fetched next
                schedule.schedule_x_times = F("schedule_x_times") - 1
                schedule.checked_scheduling_at = now()
                schedule.save()

            # send group to broker after db commit
            task_group = group(
                process_task.s(task.task_id).set(priority=task.priority)
                for task in new_tasks
            )
            on_commit(task_group.apply_async)

        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {len(task_schedules)} schedules and created {len(new_tasks)} tasks."
            )
        )
