from django.db import transaction
from rest_framework import viewsets, mixins, status
from rest_framework.request import Request
from rest_framework.response import Response

from tasks.models import Task
from tasks.serializers import TaskSerializer


class TaskViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer

    def perform_create(self, serializer) -> None:
        with transaction.atomic():
            serializer.save()

    def create(self, request: Request, *args, **kwargs) -> Response:
        response = super().create(request, *args, **kwargs)
        response.status_code = status.HTTP_202_ACCEPTED

        return response
