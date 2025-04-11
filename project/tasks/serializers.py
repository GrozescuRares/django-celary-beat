import random
from typing import Self

from rest_framework import serializers

from tasks.models import Task


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = "__all__"
        read_only_fields = ("task_id", "status", "result", "created_at", "task_schedule")

    priority = serializers.IntegerField(
        required=False, allow_null=True, validators=Task._meta.get_field("priority").validators
    )

    def create(self, validated_data: dict) -> Self:
        if validated_data.get('priority') is None:
            validated_data['priority'] = random.randint(0, 9)

        return super().create(validated_data)