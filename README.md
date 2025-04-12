# Django Celery Beat Project

This project is a Django application with Celery and Docker integration. Below are the steps to set up the project, install dependencies, and configure Git hooks.

## Prerequisites

Ensure the following tools are installed on your system:
- **Git**: Version control system.
- **Docker**: For containerized services.
- **Docker Compose**: To manage multi-container Docker applications.

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/GrozescuRares/django-celary-beat.git
cd django-celary-beat
```

### 2. Spin up the containers
```bash
docker compose up -d --build
```
### 3. Install git hooks
```bash
chmod +x misc/pre-commit.sh
cp misc/pre-commit.sh .git/hooks/pre-commit
chmod +x misc/pre-push.sh
cp misc/pre-push.sh .git/hooks/pre-push
```

## Swagger

The API documentation is available at: http://localhost:8000/swagger/
You can see some priorities taken into consideration if you create some tasks using the /batch-request task endpoint with the
payload saved in ./create_tasks_in_batch_example.json

## Flower

For monitoring Celery tasks, you can use Flower. Access it at: http://localhost:5555

## Architectural decisions.

1. Store task status and result directly inside the task table for better control. This option was preferred over hooking to the celery result backend. Also, I wanted to keep things simple and not create a dedicated task_result table.
2. Opted for creating dedicated columns in the task_schedule table for recurrence by hours and days. I am aware that this approach has its limitations, but for the purpose of this exercise it should be enough. In a real scenario I would go with https://dateutil.readthedocs.io/en/stable/rrule.html (I actually used it on a real project)
3. Expose dedicated endpoints for managing task schedules for simplicity and clear responsibility boundaries. This allows for easy management of task schedules and tasks.
4. Used celery beat for scheduling a recurring celery task as the system has to periodically check if schedules can create new tasks that have to be computed.

Application high level flows can be found in this [excalidraw](https://excalidraw.com/#json=CGgf7NHdMAOrrw10NQTin,ZyuNBwx1TnXyvXYd9zDnCw).
Github issues created for this project can be found [here](https://github.com/GrozescuRares/django-celary-beat/issues?q=is%3Aissue%20state%3Aclosed).