FROM python:3.11-slim

WORKDIR /app

# Install serving dependencies
COPY requirements-serve.txt .
RUN pip install --no-cache-dir -r requirements-serve.txt

# Copy FastAPI app
COPY serving/ serving/

# Copy model artifact downloaded by CI before docker build
COPY model_artifact/ model/

ENV MODEL_PATH=/app/model

EXPOSE 8080

CMD ["uvicorn", "serving.app:app", "--host", "0.0.0.0", "--port", "8080"]