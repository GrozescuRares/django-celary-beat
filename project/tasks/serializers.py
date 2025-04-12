import random
from typing import Self

from rest_framework import serializers

from tasks.models import Task, TaskSchedule


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = "__all__"
        read_only_fields = (
            "task_id",
            "status",
            "result",
            "created_at",
            "task_schedule",
        )

    priority = serializers.IntegerField(
        required=False,
        allow_null=True,
        validators=Task._meta.get_field("priority").validators,
    )

    def create(self, validated_data: dict) -> Self:
        if validated_data.get("priority") is None:
            validated_data["priority"] = random.randint(0, 9)

        return super().create(validated_data)


class TaskScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskSchedule
        fields = "__all__"
        read_only_fields = ("task_schedule_id",)

    every_x_days = serializers.IntegerField(required=False, allow_null=True)
    every_x_hours = serializers.IntegerField(required=False, allow_null=True)
    tasks = TaskSerializer(
        many=True, read_only=True
    )  # Nested serializer for related tasks

    def validate(self, data):
        if not data.get("every_x_days") and not data.get("every_x_hours"):
            raise serializers.ValidationError(
                "At least one of 'every_x_days' or 'every_x_hours' must have a value."
            )

        return data
