import time

from celery.utils.log import get_task_logger

from core.celery import app

logger = get_task_logger(__name__)


@app.task
def process_task(task_id: int) -> None:
    from tasks.models import Task, TaskStatus
    # TODO should this be wrapped into an atomic transaction?
    task = Task.objects.get(task_id=task_id)
    task.status = TaskStatus.STARTED
    task.save()
    logger.info(f"Start processing task with id: {task_id} which has priority: {task.priority}")

    time.sleep(20)

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
