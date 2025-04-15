# pull official base image
FROM python:3.11-slim

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install PostgreSQL client for `pg_isready`
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip && pip install poetry

# Copy pyproject.toml and poetry.lock
COPY ./pyproject.toml ./poetry.lock* /usr/src/app/

# Install dependencies using Poetry
RUN poetry config virtualenvs.create false && poetry install --no-root

# copy entrypoint.sh
COPY ./entrypoint.sh /usr/src/app/entrypoint.sh

# copy project
COPY . /usr/src/app/

# run entrypoint.sh
ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
