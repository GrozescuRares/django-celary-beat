#!/bin/bash

set -e

# Define the container name
CONTAINER_NAME="django"

docker exec "$CONTAINER_NAME" python manage.py test

# Exit with the status of the last command
exit $?
