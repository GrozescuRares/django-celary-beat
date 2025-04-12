from typing import Any

from celery import group
from django.db import transaction
from django.db.transaction import on_commit
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from tasks.models import Task, TaskSchedule, TaskStatus
from tasks.serializers import TaskSerializer, TaskScheduleSerializer

from core.tasks import process_task


class TaskViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer

    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            task = serializer.save()
            on_commit(
                lambda: process_task.apply_async(
                    args=[task.task_id], priority=task.priority
                )
            )

        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)

    def destroy(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        task = self.get_object()
        if task.status != TaskStatus.PENDING:
            raise ValidationError("Cannot delete a task which is processed.")
        task.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema(
        operation_summary="Batch create tasks",
        operation_description=(
            "Creates multiple tasks (up to 100) and triggers their processing. "
            "Each task must include an operation and an optional priority."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "operation": openapi.Schema(
                        type=openapi.TYPE_STRING, description="Mathematical operation"
                    ),
                    "priority": openapi.Schema(
                        type=openapi.TYPE_INTEGER,
                        description="Task priority (optional)",
                    ),
                },
                required=["operation"],
            ),
        ),
        responses={
            202: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "tasks": openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(type=openapi.TYPE_OBJECT),
                    )
                },
            ),
            400: "Bad Request",
        },
    )
    @action(detail=False, methods=["post"], url_path="batch-request")
    def batch_request(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        tasks_data = request.data
        if not isinstance(tasks_data, list) or len(tasks_data) > 100:
            raise ValidationError("Request body must be a list of up to 100 tasks.")

        created_tasks = []
        with transaction.atomic():
            """
            Creates tasks in a batch and triggers their processing as a group.

            - Validates and saves each task from the provided data.
            - Ensures atomicity, so either all tasks are created or none.
            - Groups the tasks for asynchronous processing using Celery.
            """
            for task_data in tasks_data:
                serializer = self.get_serializer(data=task_data)
                serializer.is_valid(raise_exception=True)
                task = serializer.save()
                created_tasks.append(task)

            task_group = group(
                process_task.s(task.task_id).set(priority=task.priority)
                for task in created_tasks
            )
            on_commit(task_group.apply_async)

        serialized_tasks = self.get_serializer(created_tasks, many=True)

        return Response(
            {"tasks": serialized_tasks.data}, status=status.HTTP_202_ACCEPTED
        )


class TaskScheduleViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = TaskSchedule.objects.all()
    serializer_class = TaskScheduleSerializer

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task_schedule = serializer.save()
        return Response(
            self.get_serializer(task_schedule).data,
            status=status.HTTP_202_ACCEPTED,
        )
