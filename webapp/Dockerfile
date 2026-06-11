FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create workspace directory for file storage
RUN mkdir -p /app/workspace/40-training-log/daily \
             /app/workspace/40-training-log/weekly \
             /app/workspace/50-outputs

EXPOSE 8501

ENV WORKSPACE_PATH=/app/workspace

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "webapp/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
