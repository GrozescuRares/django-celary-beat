#!/bin/sh

poetry install --sync
python manage.py migrate
python manage.py collectstatic --no-input --clear

exec "$@"
