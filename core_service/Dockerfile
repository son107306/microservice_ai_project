FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY core_service/main.py .
COPY preprocessor.py .
COPY shared/ shared/
COPY alembic.ini .
COPY alembic/ alembic/

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]