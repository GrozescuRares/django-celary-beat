from typing import Any

from django.db import transaction
from django.db.transaction import on_commit
from rest_framework import viewsets, mixins, status
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from tasks.models import Task
from tasks.serializers import TaskSerializer

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
        if task.result is not None:
            raise ValidationError("Cannot delete a task that already has a result.")
        task.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
