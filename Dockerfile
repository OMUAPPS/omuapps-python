FROM python:3.12.0-slim

WORKDIR /appdata
COPY requirements.lock ./
COPY packages packages
RUN PYTHONDONTWRITEBYTECODE=1 pip install --no-cache-dir -r requirements.lock

COPY src .
CMD python -m omuserver
