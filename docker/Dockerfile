FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=false \
    POETRY_VIRTUALENVS_CREATE=false

RUN pip install poetry

WORKDIR /app

COPY poetry.lock pyproject.toml ./
RUN poetry install --no-dev --no-root

COPY . .

EXPOSE 8080

CMD poetry run gunicorn -k uvicorn.workers.UvicornWorker -b 0.0.0.0:$PORT app.main:app
