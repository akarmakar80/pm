FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /usr/local/bin/uv
WORKDIR /app/backend
COPY requirements.txt ./
RUN uv pip install --system --no-cache -r requirements.txt
COPY . .
ENV STUDY_DB_PATH=/app/data/study.db PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
