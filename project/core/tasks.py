import time

from celery.utils.log import get_task_logger
from django.core.management import call_command

from core.celery import app

logger = get_task_logger(__name__)


@app.task
def process_task(task_id: int) -> None:
    from tasks.models import Task, TaskStatus

    time.sleep(
        10
    )  # Add sleep to simulate complex computation which can also lead to a race condition if the task is deleted in the meantime

    try:
        task = Task.objects.get(task_id=task_id)
    except Task.DoesNotExist:
        logger.error(f"Task with id {task_id} was deleted in the meantime.")
        return

    task.status = TaskStatus.STARTED
    task.save()
    logger.info(
        f"Start processing task with id: {task_id} which has priority: {task.priority}"
    )

    try:
        operands = task.operation.split("+")
        result = sum(float(operand) for operand in operands)

        task.result = result
        task.status = TaskStatus.SUCCESS
        logger.info(f"Task {task_id} completed successfully with result: {result}")
    except Exception as e:
        task.status = TaskStatus.ERROR
        logger.error(f"Error processing task {task_id}: {e}")
    finally:
        task.save()


@app.task
def schedule_tasks() -> None:
    call_command(
        "process_task_schedules",
    )
