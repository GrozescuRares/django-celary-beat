from parameterized import parameterized
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from tasks.models import Task, TaskSchedule


class TaskViewSetTestCase(APITestCase):
    def test_create_task_happy(self) -> None:
        response = self.client.post(
            "/tasks/",
            {
                "operation": "1+1",
                "priority": 5,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(Task.objects.count(), 1)

        task = Task.objects.first()
        self.assertEqual(task.operation, "1+1")
        self.assertEqual(task.priority, 5)

    def test_create_task_without_priority(self) -> None:
        response = self.client.post(
            "/tasks/",
            {
                "operation": "1+1",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(Task.objects.count(), 1)

        task = Task.objects.first()
        self.assertEqual(task.operation, "1+1")
        self.assertTrue(0 <= task.priority <= 9)

    @parameterized.expand(
        [
            ({"operation": 1}, status.HTTP_400_BAD_REQUEST),
            ({"operation": "1+1", "priority": "high"}, status.HTTP_400_BAD_REQUEST),
        ]
    )
    def test_create_task_with_invalid_data(
        self, payload: dict, expected_status: int
    ) -> None:
        response = self.client.post("/tasks/", payload)
        self.assertEqual(response.status_code, expected_status)
        self.assertEqual(Task.objects.count(), 0)

    def test_retrieve_task_happy(self) -> None:
        task = Task.objects.create(
            operation="1+1",
            priority=5,
            status="PENDING",
            result=None,
        )

        response = self.client.get(reverse("task-detail", args=[task.task_id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["task_id"], task.task_id)
        self.assertEqual(response.data["status"], task.status)
        self.assertEqual(response.data["result"], task.result)

    def test_retrieve_task_not_found(self) -> None:
        response = self.client.get(reverse("task-detail", args=["nonexistent-task-id"]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_destroy_task_happy(self) -> None:
        task = Task.objects.create(
            operation="1+1",
            priority=5,
            status="PENDING",
            result=None,
        )

        response = self.client.delete(reverse("task-detail", args=[task.task_id]))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Task.objects.count(), 0)

    def test_destroy_task_with_result(self) -> None:
        task = Task.objects.create(
            operation="1+1",
            priority=5,
            status="SUCCESS",
            result="2",
        )

        response = self.client.delete(reverse("task-detail", args=[task.task_id]))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Task.objects.count(), 1)

    def test_destroy_task_not_found(self) -> None:
        response = self.client.delete(
            reverse("task-detail", args=["nonexistent-task-id"])
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_batch_request_happy(self) -> None:
        tasks_data = [
            {"operation": "1+1", "priority": 5},
            {"operation": "2+2", "priority": 3},
        ]

        response = self.client.post(
            reverse("task-batch-request"), tasks_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(Task.objects.count(), 2)

        task_1, task_2 = Task.objects.all()
        self.assertEqual(task_1.operation, "1+1")
        self.assertEqual(task_1.priority, 5)
        self.assertEqual(task_2.operation, "2+2")
        self.assertEqual(task_2.priority, 3)

    def test_batch_request_exceeds_limit(self) -> None:
        tasks_data = [{"operation": f"{i}+{i}"} for i in range(101)]

        response = self.client.post(
            reverse("task-batch-request"), tasks_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Task.objects.count(), 0)

    def test_batch_request_invalid_data(self) -> None:
        tasks_data = [
            {"operation": "1+1", "priority": "high"},  # Invalid priority
            {"operation": 123},  # Invalid operation
        ]

        response = self.client.post(
            reverse("task-batch-request"), tasks_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Task.objects.count(), 0)

    def test_batch_request_empty_list(self) -> None:
        response = self.client.post(reverse("task-batch-request"), [], format="json")

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(Task.objects.count(), 0)

    def test_batch_request_atomic_transaction(self) -> None:
        tasks_data = [
            {"operation": "1+1", "priority": 5},
            {"operation": "invalid_operation"},  # This will cause validation to fail
        ]

        response = self.client.post(
            reverse("task-batch-request"), tasks_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Task.objects.count(), 0)  # Ensure no tasks are created


class TaskScheduleViewSetTestCase(APITestCase):
    def test_create_task_schedule_happy(self) -> None:
        response = self.client.post(
            reverse("task-schedule-list"),
            {
                "operation": "1+1",
                "priority": 5,
                "every_x_days": 2,
                "schedule_x_times": 3,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(TaskSchedule.objects.count(), 1)

        task_schedule = TaskSchedule.objects.first()
        self.assertEqual(task_schedule.operation, "1+1")
        self.assertEqual(task_schedule.priority, 5)
        self.assertEqual(task_schedule.every_x_days, 2)
        self.assertEqual(task_schedule.schedule_x_times, 3)

    def test_create_task_schedule_without_priority(self) -> None:
        response = self.client.post(
            reverse("task-schedule-list"),
            {
                "operation": "1+1",
                "every_x_days": 2,
                "schedule_x_times": 3,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(TaskSchedule.objects.count(), 1)

        task_schedule = TaskSchedule.objects.first()
        self.assertEqual(task_schedule.operation, "1+1")
        self.assertEqual(task_schedule.priority, None)

    def test_create_task_schedule_invalid_data(self) -> None:
        response = self.client.post(
            reverse("task-schedule-list"),
            {
                "operation": "invalid_operation",
                "priority": 5,
                "every_x_days": 2,
                "schedule_x_times": 3,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(TaskSchedule.objects.count(), 0)

    def test_create_task_schedule_missing_every_x_fields(self) -> None:
        response = self.client.post(
            reverse("task-schedule-list"),
            {
                "operation": "1+1",
                "priority": 5,
                "schedule_x_times": 3,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(TaskSchedule.objects.count(), 0)

    def test_retrieve_task_schedule_happy(self) -> None:
        task_schedule = TaskSchedule.objects.create(
            operation="1+1",
            priority=5,
            every_x_days=2,
            schedule_x_times=3,
        )
        Task.objects.create(
            operation="1+1",
            priority=5,
            task_schedule=task_schedule,
        )

        response = self.client.get(
            reverse("task-schedule-detail", args=[task_schedule.task_schedule_id])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["task_schedule_id"], task_schedule.task_schedule_id
        )
        self.assertEqual(len(response.data["tasks"]), 1)

    def test_retrieve_task_schedule_not_found(self) -> None:
        response = self.client.get(reverse("task-schedule-detail", args=[999]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_task_schedule_happy(self) -> None:
        task_schedule = TaskSchedule.objects.create(
            operation="1+1",
            priority=5,
            every_x_days=2,
            schedule_x_times=3,
        )

        response = self.client.delete(
            reverse("task-schedule-detail", args=[task_schedule.task_schedule_id])
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(TaskSchedule.objects.count(), 0)

    def test_delete_task_schedule_not_found(self) -> None:
        response = self.client.delete(reverse("task-schedule-detail", args=[999]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
