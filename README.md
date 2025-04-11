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
```
