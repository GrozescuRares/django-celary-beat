#!/bin/bash

# Define the container name
CONTAINER_NAME="django"

# Run Ruff to fix linting issues inside the container
docker exec "$CONTAINER_NAME" ruff check --fix .

# Run Black to format the code inside the container
docker exec "$CONTAINER_NAME" black .

# Run Mypy for type checking inside the container
docker exec "$CONTAINER_NAME" mypy .

git add .

# Exit with the status of the last command
exit $?
