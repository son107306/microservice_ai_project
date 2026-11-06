FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy logic chính của Worker
COPY worker/tasks.py ./worker/

# Copy các thư viện và module tái sử dụng
COPY shared/ shared/
COPY preprocessor.py .
COPY llm_adapter.py .

CMD ["celery", "-A", "worker.tasks", "worker", "--loglevel=info"]