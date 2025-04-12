from datetime import timedelta
from unittest import TestCase
from unittest.mock import patch

from django.core.management import call_command
from django.utils.timezone import now
from parameterized import parameterized
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from tasks.models import Task, TaskSchedule, TaskStatus

from core.tasks import process_task


class TaskViewSetTestCase(APITestCase):
    @patch("core.tasks.process_task.run")
    def test_create_task_happy(self, _) -> None:
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

        assert process_task.run(task.task_id)
        process_task.run.assert_called_once_with(task.task_id)

    @patch("core.tasks.process_task.run")
    def test_create_task_without_priority(self, _) -> None:
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

        assert process_task.run(task.task_id)
        process_task.run.assert_called_once_with(task.task_id)

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

    @patch("core.tasks.process_task.run")
    def test_batch_request_happy(self, _) -> None:
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

        assert process_task.run((task_1.task_id, task_2.task_id))
        process_task.run.assert_called_once_with((task_1.task_id, task_2.task_id))

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


class ProcessTaskSchedulesCommandTestCase(TestCase):
    def setUp(self) -> None:
        # Create task schedules for testing
        self.schedule1 = TaskSchedule.objects.create(
            operation="5+10",
            priority=1,
            schedule_x_times=3,
            every_x_days=1,
            checked_scheduling_at=now() - timedelta(days=2),
        )
        self.schedule2 = TaskSchedule.objects.create(
            operation="20+30",
            priority=2,
            schedule_x_times=1,
            every_x_days=1,
            checked_scheduling_at=now() - timedelta(days=2),
        )

    def tearDown(self) -> None:
        Task.objects.all().delete()
        TaskSchedule.objects.all().delete()

    @patch("core.tasks.process_task.run")
    def test_command_creates_tasks(self, _) -> None:
        # Call the management command
        call_command("process_task_schedules")

        # Assert tasks were created
        self.assertEqual(Task.objects.count(), 2)

        # Assert the schedules were updated
        self.schedule1.refresh_from_db()
        self.schedule2.refresh_from_db()
        self.assertEqual(self.schedule1.schedule_x_times, 2)
        self.assertEqual(self.schedule2.schedule_x_times, 0)

        task_1 = Task.objects.filter(task_schedule=self.schedule1).first()
        task_2 = Task.objects.filter(task_schedule=self.schedule2).first()
        assert process_task.run((task_1.task_id, task_2.task_id))
        process_task.run.assert_called_once_with((task_1.task_id, task_2.task_id))

    def test_command_skips_schedules_with_no_remaining_times(self) -> None:
        # Set schedule_x_times to 0 for one schedule
        self.schedule1.schedule_x_times = 0
        self.schedule1.save()

        # Call the management command
        call_command("process_task_schedules")

        # Assert only one task was created
        self.assertEqual(Task.objects.count(), 1)

    def test_command_handles_no_schedules(self) -> None:
        # Delete all schedules
        TaskSchedule.objects.all().delete()

        # Call the management command
        call_command("process_task_schedules")

        # Assert no tasks were created
        self.assertEqual(Task.objects.count(), 0)

    def test_schedule_creates_multiple_tasks_based_on_last_task_created_at(
        self,
    ) -> None:
        call_command("process_task_schedules")

        # Assert multiple tasks were created
        self.assertEqual(Task.objects.filter(task_schedule=self.schedule1).count(), 1)

        # Assert the schedule was updated
        self.schedule1.refresh_from_db()
        self.assertEqual(self.schedule1.schedule_x_times, 2)

        task = Task.objects.filter(task_schedule=self.schedule1).first()
        task.created_at = now() - timedelta(days=2)
        task.save()

        call_command("process_task_schedules")
        # Assert multiple tasks were created
        self.assertEqual(Task.objects.filter(task_schedule=self.schedule1).count(), 2)

        # Assert the schedule was updated
        self.schedule1.refresh_from_db()
        self.assertEqual(self.schedule1.schedule_x_times, 1)


class ProcessTaskTestCase(TestCase):
    def setUp(self) -> None:
        self.task = Task.objects.create(
            operation="5+10",
            priority=5,
        )

    def test_process_task_success(self) -> None:
        # Call the Celery task
        process_task(self.task.task_id)

        # Refresh the task from the database
        self.task.refresh_from_db()

        # Assert the task was processed successfully
        self.assertEqual(self.task.status, TaskStatus.SUCCESS)
        self.assertEqual(self.task.result, 15.0)

    def test_process_task_error(self) -> None:
        # Create a task with invalid operation
        self.task.operation = "invalid+operation"
        self.task.save()

        # Call the Celery task
        process_task(self.task.task_id)

        # Refresh the task from the database
        self.task.refresh_from_db()

        # Assert the task failed with an error
        self.assertEqual(self.task.status, TaskStatus.ERROR)
        self.assertIsNone(self.task.result)

    def test_process_task_deleted(self) -> None:
        # Delete the task before processing
        task_id = self.task.task_id
        self.task.delete()

        # Call the Celery task
        process_task(task_id)

        # Assert the task does not exist
        self.assertFalse(Task.objects.filter(task_id=task_id).exists())
